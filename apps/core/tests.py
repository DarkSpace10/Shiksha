import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import (
    User, UserRole, DonorProfile, StudentProfile, StudentVerificationStatus, AcademicLevel
)
from apps.ngos.models import NGO, NGOMembership, NGOMemberRole, NGOStatus, NGOServiceArea
from apps.donations.models import (
    DonationListing, DonationStatus, BookCategory, ConditionGrade, PickupJob, PickupStatus
)
from apps.inventory.models import InventoryCopy, InventoryStatus
from apps.requests.models import (
    BookRequest, RequestStatus, Allocation, AllocationStatus, DeliveryJob, DeliveryStatus,
    StudentVerification
)


class DonationToDeliveryWorkflowTest(TestCase):
    """
    End-to-End integration test for the entire 10-step BookBridge lifecycle:
    Donor registration -> Donation listing -> NGO review -> Pickup schedule -> Book collected ->
    Physical inspection & SKU creation -> Catalogue publication -> Student registration & verification ->
    Book request -> Transactional allocation -> Delivery dispatch -> Student receipt confirmation.
    """

    def setUp(self):
        self.client = Client()

        # Create Platform Admin
        self.admin = User.objects.create_user(
            username='admin_tester',
            email='admin@test.org',
            password='Password@123',
            role=UserRole.PLATFORM_ADMIN,
            is_staff=True,
            is_superuser=True
        )

        # Create NGO
        self.ngo = NGO.objects.create(
            name='Test Vidya Trust',
            registration_number='REG-TEST-001',
            email='ngo@test.org',
            phone='+91 9876543210',
            address='123 Test Street',
            city='Delhi',
            state='Delhi',
            postal_code='110001',
            description='Test NGO for educational books distribution',
            status=NGOStatus.APPROVED,
            approved_by=self.admin,
            approved_at=timezone.now()
        )

        # Create NGO Staff
        self.ngo_staff = User.objects.create_user(
            username='ngo_officer',
            email='officer@test.org',
            password='Password@123',
            role=UserRole.NGO_STAFF
        )
        self.membership = NGOMembership.objects.create(
            user=self.ngo_staff,
            ngo=self.ngo,
            role=NGOMemberRole.NGO_ADMIN,
            can_review_donations=True,
            can_schedule_pickups=True,
            can_inspect_books=True,
            can_manage_inventory=True,
            can_verify_students=True,
            can_review_requests=True,
            can_manage_deliveries=True
        )

        # Create Donor
        self.donor = User.objects.create_user(
            username='donor_user',
            email='donor@test.org',
            password='Password@123',
            phone_number='+91 9999888877',
            role=UserRole.DONOR
        )
        self.donor_profile = DonorProfile.objects.create(
            user=self.donor,
            address_line1='Flat 101, Test Apartments',
            city='Delhi',
            state='Delhi',
            postal_code='110001'
        )

        # Create Student
        self.student = User.objects.create_user(
            username='student_user',
            email='student@test.org',
            password='Password@123',
            role=UserRole.STUDENT
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            institution_name='Delhi Engineering College',
            student_id_number='DEC-2026-100',
            course_of_study='B.Tech CSE',
            academic_level=AcademicLevel.UNDERGRADUATE,
            financial_need_statement='Need textbook assistance for syllabus exams',
            delivery_address='Hostel Block A, DEC Campus',
            delivery_city='Delhi',
            delivery_state='Delhi',
            delivery_postal_code='110001',
            verification_status=StudentVerificationStatus.PENDING
        )

    def test_complete_donation_to_delivery_lifecycle(self):
        # Step 1: Donor creates donation listing
        self.client.login(username='donor_user', password='Password@123')
        create_resp = self.client.post(reverse('donations:donation_create'), {
            'ngo': str(self.ngo.id),
            'title': 'Operating System Concepts',
            'author': 'Silberschatz',
            'isbn': '978-1119800361',
            'category': BookCategory.SCIENCE_TECH,
            'academic_level': AcademicLevel.UNDERGRADUATE,
            'subject': 'Computer Science',
            'declared_condition': ConditionGrade.VERY_GOOD,
            'donor_condition_description': 'Gently used college textbook, all pages intact.',
            'pickup_address': 'Flat 101, Test Apartments',
            'pickup_city': 'Delhi',
            'pickup_state': 'Delhi',
            'pickup_postal_code': '110001',
            'donor_contact_phone': '+91 9999888877',
        })
        self.client.logout()

        donation = DonationListing.objects.get(title='Operating System Concepts')
        self.assertEqual(donation.status, DonationStatus.SUBMITTED)
        self.assertEqual(donation.ngo, self.ngo)
        self.assertEqual(donation.donor, self.donor)

        # Step 2: NGO Staff reviews & approves donation
        self.client.login(username='ngo_officer', password='Password@123')
        review_resp = self.client.post(reverse('donations:ngo_donation_review', kwargs={'donation_id': donation.id}), {
            'decision': 'APPROVED',
            'comments': 'Book verified against local college syllabus. Approved for pickup.'
        })
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.APPROVED)

        # Step 3: NGO schedules pickup
        pickup_resp = self.client.post(reverse('donations:ngo_pickup_schedule', kwargs={'donation_id': donation.id}), {
            'scheduled_date': '2026-11-01',
            'time_slot': 'MORNING',
            'assigned_agent_name': 'Ramesh Volunteer',
            'assigned_agent_phone': '+91 9876500000',
            'notes': 'Call 30 mins before arrival'
        })
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.PICKUP_SCHEDULED)
        pickup_job = donation.pickup_job
        self.assertEqual(pickup_job.assigned_agent_name, 'Ramesh Volunteer')

        # Step 4: Book is collected from donor
        collect_resp = self.client.post(
            reverse('donations:ngo_pickup_status_update', kwargs={'pickup_id': pickup_job.id}),
            {'status': 'COLLECTED', 'notes': 'Received in good condition'}
        )
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.COLLECTED)

        # Step 5: NGO performs physical quality inspection -> SKU generated -> published to inventory
        inspect_resp = self.client.post(reverse('donations:ngo_physical_inspection', kwargs={'donation_id': donation.id}), {
            'decision': 'PASSED',
            'verified_condition': ConditionGrade.VERY_GOOD,
            'location_shelf': 'Shelf CS-01',
            'inspection_notes': 'Binding clean, all chapters present.'
        })
        donation.refresh_from_db()
        self.assertEqual(donation.status, DonationStatus.INVENTORIED)

        # Verify InventoryCopy was created
        inventory_copy = InventoryCopy.objects.get(donation_listing=donation)
        self.assertEqual(inventory_copy.status, InventoryStatus.AVAILABLE)
        self.assertTrue(inventory_copy.is_published)
        self.assertEqual(inventory_copy.location_shelf, 'Shelf CS-01')
        self.assertTrue(inventory_copy.tracking_code.startswith('BB-'))

        # Step 6: NGO verifies student eligibility
        verify_resp = self.client.post(reverse('requests:ngo_verify_student', kwargs={'profile_id': self.student_profile.id}), {
            'status': 'APPROVED',
            'comments': 'Verified engineering enrollment.'
        })
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.verification_status, StudentVerificationStatus.VERIFIED)
        self.client.logout()

        # Step 7: Student requests the book
        self.client.login(username='student_user', password='Password@123')
        req_resp = self.client.post(reverse('requests:request_create', kwargs={'copy_id': inventory_copy.id}), {
            'educational_purpose': 'Need for semester 4 OS curriculum.',
            'urgent_need': True,
            'urgency_reason': 'Upcoming midterms',
            'delivery_address': 'Hostel Block A, DEC Campus',
            'delivery_city': 'Delhi',
            'delivery_state': 'Delhi',
            'delivery_postal_code': '110001',
            'contact_phone': '+91 9899001122'
        })
        self.client.logout()

        book_req = BookRequest.objects.get(student=self.student, inventory_copy=inventory_copy)
        self.assertEqual(book_req.status, RequestStatus.PENDING)

        # Step 8: NGO approves and executes transactional allocation
        self.client.login(username='ngo_officer', password='Password@123')
        alloc_resp = self.client.post(reverse('requests:ngo_execute_allocation', kwargs={'request_id': book_req.id}))

        book_req.refresh_from_db()
        inventory_copy.refresh_from_db()
        self.assertEqual(book_req.status, RequestStatus.ALLOCATED)
        self.assertEqual(inventory_copy.status, InventoryStatus.ALLOCATED)

        # Verify Allocation and DeliveryJob were created
        allocation = book_req.allocation
        self.assertIsNotNone(allocation)
        self.assertEqual(allocation.status, AllocationStatus.ACTIVE)

        delivery_job = allocation.delivery_job
        self.assertIsNotNone(delivery_job)
        self.assertEqual(delivery_job.status, DeliveryStatus.PREPARING)
        self.assertTrue(delivery_job.tracking_number.startswith('DEL-'))

        # Step 9: NGO dispatches delivery with courier
        dispatch_resp = self.client.post(reverse('requests:ngo_delivery_dispatch', kwargs={'delivery_id': delivery_job.id}), {
            'courier_name': 'India Post SpeedPost',
            'tracking_number': 'SP-DELHI-998877',
            'dispatch_notes': 'Securely bubble-wrapped and dispatched'
        })
        delivery_job.refresh_from_db()
        self.assertEqual(delivery_job.status, DeliveryStatus.DISPATCHED)
        self.assertEqual(delivery_job.courier_name, 'India Post SpeedPost')
        self.client.logout()

        # Step 10: Student confirms delivery receipt
        self.client.login(username='student_user', password='Password@123')
        confirm_resp = self.client.post(reverse('requests:student_confirm_receipt', kwargs={'delivery_id': delivery_job.id}), {
            'student_feedback': 'Received in excellent condition! Thank you!'
        })

        delivery_job.refresh_from_db()
        book_req.refresh_from_db()
        allocation.refresh_from_db()
        inventory_copy.refresh_from_db()

        self.assertTrue(delivery_job.student_confirmed)
        self.assertEqual(delivery_job.status, DeliveryStatus.DELIVERED)
        self.assertEqual(book_req.status, RequestStatus.COMPLETED)
        self.assertEqual(allocation.status, AllocationStatus.FULFILLED)
        self.assertEqual(inventory_copy.status, InventoryStatus.DELIVERED)


class OrganizationIsolationTest(TestCase):
    """
    Tests strict organization boundary isolation between independent NGOs.
    NGO Staff A must NOT be able to view, review, or modify records belonging to NGO B.
    """

    def setUp(self):
        self.client = Client()

        # Create NGO A and Staff A
        self.ngo_a = NGO.objects.create(
            name='NGO Alpha Delhi',
            registration_number='REG-ALPHA-01',
            email='alpha@test.org',
            city='Delhi',
            state='Delhi',
            postal_code='110001',
            status=NGOStatus.APPROVED
        )
        self.staff_a = User.objects.create_user(
            username='staff_alpha',
            email='alpha_user@test.org',
            password='Password@123',
            role=UserRole.NGO_STAFF
        )
        NGOMembership.objects.create(
            user=self.staff_a,
            ngo=self.ngo_a,
            role=NGOMemberRole.NGO_ADMIN,
            can_review_donations=True,
            can_review_requests=True
        )

        # Create NGO B and Staff B
        self.ngo_b = NGO.objects.create(
            name='NGO Beta Mumbai',
            registration_number='REG-BETA-02',
            email='beta@test.org',
            city='Mumbai',
            state='Maharashtra',
            postal_code='400001',
            status=NGOStatus.APPROVED
        )
        self.staff_b = User.objects.create_user(
            username='staff_beta',
            email='beta_user@test.org',
            password='Password@123',
            role=UserRole.NGO_STAFF
        )
        NGOMembership.objects.create(
            user=self.staff_b,
            ngo=self.ngo_b,
            role=NGOMemberRole.NGO_ADMIN,
            can_review_donations=True,
            can_review_requests=True
        )

        # Create Donor and Donation for NGO B
        self.donor = User.objects.create_user(
            username='donor_b',
            email='donorb@test.org',
            password='Password@123',
            role=UserRole.DONOR
        )
        self.donation_b = DonationListing.objects.create(
            donor=self.donor,
            ngo=self.ngo_b,
            title='Confidential Textbook B',
            author='Author B',
            pickup_address='Mumbai address',
            pickup_city='Mumbai',
            pickup_state='Maharashtra',
            pickup_postal_code='400001',
            status=DonationStatus.SUBMITTED
        )

    def test_ngo_a_cannot_review_ngo_b_donation(self):
        # Staff A logs in and attempts to access NGO B's donation review endpoint
        self.client.login(username='staff_alpha', password='Password@123')
        response = self.client.get(reverse('donations:ngo_donation_review', kwargs={'donation_id': self.donation_b.id}))
        # Must return 404 because query filters by request.ngo
        self.assertEqual(response.status_code, 404)

        # Staff A attempts to post review on NGO B's donation
        post_response = self.client.post(
            reverse('donations:ngo_donation_review', kwargs={'donation_id': self.donation_b.id}),
            {'decision': 'APPROVED', 'comments': 'Illegal unauthorized review'}
        )
        self.assertEqual(post_response.status_code, 404)

        # Verify donation B status was not modified
        self.donation_b.refresh_from_db()
        self.assertEqual(self.donation_b.status, DonationStatus.SUBMITTED)


class ConcurrentBookAllocationTest(TestCase):
    """
    Tests transactional allocation logic and prevents double-allocation
    using select_for_update row-level locking.
    """

    def setUp(self):
        self.ngo = NGO.objects.create(
            name='Concurrent Test NGO',
            registration_number='REG-CONCUR-01',
            email='concur@test.org',
            city='Delhi',
            state='Delhi',
            postal_code='110001',
            status=NGOStatus.APPROVED
        )
        self.staff = User.objects.create_user(
            username='concur_staff',
            email='staff@concur.org',
            password='Password@123',
            role=UserRole.NGO_STAFF
        )
        NGOMembership.objects.create(
            user=self.staff,
            ngo=self.ngo,
            role=NGOMemberRole.NGO_ADMIN,
            can_review_requests=True
        )

        # Single available inventory copy
        self.single_copy = InventoryCopy.objects.create(
            ngo=self.ngo,
            tracking_code='BB-CONCUR-001',
            book_title='Rare Medical Encyclopedia',
            author='Dr. Specialist',
            status=InventoryStatus.AVAILABLE,
            is_published=True,
            location_shelf='Vault Shelf 1'
        )

        # Two different students
        self.student_1 = User.objects.create_user(
            username='student_one',
            email='one@test.org',
            password='Password@123',
            role=UserRole.STUDENT
        )
        StudentProfile.objects.create(
            user=self.student_1,
            institution_name='Medical College A',
            student_id_number='MED-1',
            course_of_study='MBBS',
            verification_status=StudentVerificationStatus.VERIFIED
        )

        self.student_2 = User.objects.create_user(
            username='student_two',
            email='two@test.org',
            password='Password@123',
            role=UserRole.STUDENT
        )
        StudentProfile.objects.create(
            user=self.student_2,
            institution_name='Medical College B',
            student_id_number='MED-2',
            course_of_study='MBBS',
            verification_status=StudentVerificationStatus.VERIFIED
        )

        # Both students submit request for the same book copy
        self.req_1 = BookRequest.objects.create(
            student=self.student_1,
            inventory_copy=self.single_copy,
            ngo=self.ngo,
            educational_purpose='Semester exams',
            delivery_address='Address 1',
            delivery_city='Delhi',
            delivery_state='Delhi',
            delivery_postal_code='110001',
            status=RequestStatus.PENDING
        )

        self.req_2 = BookRequest.objects.create(
            student=self.student_2,
            inventory_copy=self.single_copy,
            ngo=self.ngo,
            educational_purpose='Semester exams',
            delivery_address='Address 2',
            delivery_city='Delhi',
            delivery_state='Delhi',
            delivery_postal_code='110001',
            status=RequestStatus.PENDING
        )

    def test_single_allocation_prevents_double_booking(self):
        client = Client()
        client.login(username='concur_staff', password='Password@123')

        # First allocation succeeds
        client.post(reverse('requests:ngo_execute_allocation', kwargs={'request_id': self.req_1.id}))

        self.req_1.refresh_from_db()
        self.single_copy.refresh_from_db()
        self.assertEqual(self.req_1.status, RequestStatus.ALLOCATED)
        self.assertEqual(self.single_copy.status, InventoryStatus.ALLOCATED)

        # Second allocation attempt for the same copy is caught by transactional status verification
        client.post(reverse('requests:ngo_execute_allocation', kwargs={'request_id': self.req_2.id}))

        self.req_2.refresh_from_db()
        # Second request must NOT be allocated; it is gracefully moved to WAITLISTED
        self.assertEqual(self.req_2.status, RequestStatus.WAITLISTED)

        # Verify only one Allocation record exists
        self.assertEqual(Allocation.objects.filter(inventory_copy=self.single_copy).count(), 1)
