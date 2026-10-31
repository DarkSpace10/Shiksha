import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User, UserRole, DonorProfile, StudentProfile, StudentVerificationStatus, AcademicLevel, Notification, NotificationType
from apps.ngos.models import NGO, NGOMembership, NGOMemberRole, NGOServiceArea, NGOStatus
from apps.donations.models import DonationListing, DonationImage, DonationReview, PickupJob, DonationStatus, BookCategory, ConditionGrade, PickupStatus
from apps.inventory.models import InventoryCopy, InventoryStatus
from apps.requests.models import BookRequest, RequestStatus, Allocation, AllocationStatus, DeliveryJob, DeliveryStatus, StudentVerification, VerificationDocument, DocumentType
from apps.audit.models import AuditLog


class Command(BaseCommand):
    help = 'Seeds database with realistic initial users, verified NGOs, book donations, inventory, requests and delivery jobs.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding BookBridge demonstration database..."))

        with transaction.atomic():
            # 1. Platform Administrator
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@bookbridge.org',
                    'first_name': 'Platform',
                    'last_name': 'Administrator',
                    'role': UserRole.PLATFORM_ADMIN,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_verified': True,
                }
            )
            if created:
                admin_user.set_password('Admin@12345')
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f"Created Administrator: admin / Admin@12345"))

            # 2. NGOs
            ngo1, _ = NGO.objects.get_or_create(
                registration_number='TRUST-DEL-2018-9921',
                defaults={
                    'name': 'Vidya Jyoti Educational Trust',
                    'email': 'contact@vidyajyoti.org',
                    'phone': '+91 11 2345 6789',
                    'website': 'https://vidyajyoti.org',
                    'address': 'Plot 42, Institutional Area, Hauz Khas',
                    'city': 'New Delhi',
                    'state': 'Delhi',
                    'postal_code': '110016',
                    'description': 'Empowering underprivileged students across Delhi NCR with curriculum textbooks and competitive exam guidance.',
                    'mission_statement': 'Every book shared is a student graduated.',
                    'status': NGOStatus.APPROVED,
                    'approved_by': admin_user,
                    'approved_at': timezone.now(),
                }
            )

            ngo2, _ = NGO.objects.get_or_create(
                registration_number='SOC-MUM-2015-4412',
                defaults={
                    'name': 'Pratham Shiksha Foundation',
                    'email': 'books@prathamshiksha.org',
                    'phone': '+91 22 2654 3210',
                    'website': 'https://prathamshiksha.org',
                    'address': 'Level 3, Kalanagar Social Complex, Bandra East',
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'postal_code': '400051',
                    'description': 'Focusing on STEM and higher secondary books for economically weaker sections across Maharashtra.',
                    'status': NGOStatus.APPROVED,
                    'approved_by': admin_user,
                    'approved_at': timezone.now(),
                }
            )

            ngo3, _ = NGO.objects.get_or_create(
                registration_number='TRUST-BLR-2021-7788',
                defaults={
                    'name': 'Gyan Setu Learning Initiative',
                    'email': 'hello@gyansetu.org',
                    'phone': '+91 80 4123 9876',
                    'website': 'https://gyansetu.org',
                    'address': '12/A, Koramangala 4th Block',
                    'city': 'Bengaluru',
                    'state': 'Karnataka',
                    'postal_code': '560034',
                    'description': 'Connecting engineering, medical, and polytechnic college textbooks with rural Karnataka scholars.',
                    'status': NGOStatus.APPROVED,
                    'approved_by': admin_user,
                    'approved_at': timezone.now(),
                }
            )

            # Service Areas
            NGOServiceArea.objects.get_or_create(ngo=ngo1, city='New Delhi', state='Delhi')
            NGOServiceArea.objects.get_or_create(ngo=ngo1, city='Noida', state='Uttar Pradesh')
            NGOServiceArea.objects.get_or_create(ngo=ngo1, city='Gurugram', state='Haryana')
            NGOServiceArea.objects.get_or_create(ngo=ngo2, city='Mumbai', state='Maharashtra')
            NGOServiceArea.objects.get_or_create(ngo=ngo2, city='Thane', state='Maharashtra')
            NGOServiceArea.objects.get_or_create(ngo=ngo3, city='Bengaluru', state='Karnataka')

            # 3. NGO Staff Users
            v_admin, c = User.objects.get_or_create(
                username='vidya_admin',
                defaults={
                    'email': 'director@vidyajyoti.org',
                    'first_name': 'Sunita',
                    'last_name': 'Mishra',
                    'role': UserRole.NGO_STAFF,
                    'is_verified': True,
                }
            )
            if c:
                v_admin.set_password('Staff@12345')
                v_admin.save()
            NGOMembership.objects.get_or_create(
                user=v_admin,
                ngo=ngo1,
                defaults={
                    'role': NGOMemberRole.NGO_ADMIN,
                    'can_manage_staff': True,
                    'can_review_donations': True,
                    'can_schedule_pickups': True,
                    'can_inspect_books': True,
                    'can_manage_inventory': True,
                    'can_verify_students': True,
                    'can_review_requests': True,
                    'can_manage_deliveries': True
                }
            )

            v_inspector, c = User.objects.get_or_create(
                username='vidya_inspector',
                defaults={
                    'email': 'qa@vidyajyoti.org',
                    'first_name': 'Arun',
                    'last_name': 'Kashyap',
                    'role': UserRole.NGO_STAFF,
                    'is_verified': True,
                }
            )
            if c:
                v_inspector.set_password('Staff@12345')
                v_inspector.save()
            NGOMembership.objects.get_or_create(
                user=v_inspector,
                ngo=ngo1,
                defaults={
                    'role': NGOMemberRole.INSPECTOR,
                    'can_review_donations': True,
                    'can_inspect_books': True,
                    'can_manage_inventory': True,
                    'can_schedule_pickups': True
                }
            )

            p_admin, c = User.objects.get_or_create(
                username='pratham_admin',
                defaults={
                    'email': 'admin@prathamshiksha.org',
                    'first_name': 'Mahesh',
                    'last_name': 'Joshi',
                    'role': UserRole.NGO_STAFF,
                    'is_verified': True,
                }
            )
            if c:
                p_admin.set_password('Staff@12345')
                p_admin.save()
            NGOMembership.objects.get_or_create(
                user=p_admin,
                ngo=ngo2,
                defaults={'role': NGOMemberRole.NGO_ADMIN, 'can_manage_staff': True}
            )

            # 4. Donors
            donor1, c = User.objects.get_or_create(
                username='rahul_donor',
                defaults={
                    'email': 'rahul.sharma@example.com',
                    'first_name': 'Rahul',
                    'last_name': 'Sharma',
                    'phone_number': '+91 9811223344',
                    'role': UserRole.DONOR,
                    'is_verified': True,
                }
            )
            if c:
                donor1.set_password('Donor@12345')
                donor1.save()
            DonorProfile.objects.get_or_create(
                user=donor1,
                defaults={
                    'address_line1': 'B-14, Green Park Extension',
                    'city': 'New Delhi',
                    'state': 'Delhi',
                    'postal_code': '110016',
                    'total_donations_count': 3,
                    'preferred_pickup_instructions': 'Available after 4 PM weekdays. Ground floor ring bell.'
                }
            )

            donor2, c = User.objects.get_or_create(
                username='priya_donor',
                defaults={
                    'email': 'priya.deshmukh@example.com',
                    'first_name': 'Priya',
                    'last_name': 'Deshmukh',
                    'phone_number': '+91 9822334455',
                    'role': UserRole.DONOR,
                    'is_verified': True,
                }
            )
            if c:
                donor2.set_password('Donor@12345')
                donor2.save()
            DonorProfile.objects.get_or_create(
                user=donor2,
                defaults={
                    'address_line1': 'Flat 402, Sea Crest Towers, Bandra West',
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'postal_code': '400050',
                    'total_donations_count': 2
                }
            )

            # 5. Students
            student1, c = User.objects.get_or_create(
                username='ananya_student',
                defaults={
                    'email': 'ananya.verma@delhiuniv.ac.in',
                    'first_name': 'Ananya',
                    'last_name': 'Verma',
                    'phone_number': '+91 9899001122',
                    'role': UserRole.STUDENT,
                    'is_verified': True,
                }
            )
            if c:
                student1.set_password('Student@12345')
                student1.save()
            sp1, _ = StudentProfile.objects.get_or_create(
                user=student1,
                defaults={
                    'institution_name': 'Delhi Technological University (DTU)',
                    'student_id_number': '2K23/CO/045',
                    'course_of_study': 'B.Tech Computer Engineering',
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'graduation_year': 2027,
                    'financial_need_statement': 'Father is a daily wage artisan. Unable to afford original technical reference books and syllabus textbooks.',
                    'delivery_address': 'Room 108, Girls Hostel Block B, DTU Campus, Shahbad Daulatpur',
                    'delivery_city': 'New Delhi',
                    'delivery_state': 'Delhi',
                    'delivery_postal_code': '110042',
                    'verification_status': StudentVerificationStatus.VERIFIED,
                    'verified_at': timezone.now()
                }
            )

            student2, c = User.objects.get_or_create(
                username='rohit_student',
                defaults={
                    'email': 'rohit.kumar@mu.ac.in',
                    'first_name': 'Rohit',
                    'last_name': 'Kumar',
                    'phone_number': '+91 9711223344',
                    'role': UserRole.STUDENT,
                    'is_verified': True,
                }
            )
            if c:
                student2.set_password('Student@12345')
                student2.save()
            sp2, _ = StudentProfile.objects.get_or_create(
                user=student2,
                defaults={
                    'institution_name': 'Government Science College, Kurla',
                    'student_id_number': 'GSC-2024-889',
                    'course_of_study': 'B.Sc Physics Honours',
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'graduation_year': 2026,
                    'financial_need_statement': 'Single mother household. Need assistance with standard university physics manuals.',
                    'delivery_address': 'B-204, Shanti Nagar, Kurla West',
                    'delivery_city': 'Mumbai',
                    'delivery_state': 'Maharashtra',
                    'delivery_postal_code': '400070',
                    'verification_status': StudentVerificationStatus.PENDING
                }
            )

            # Verification Record for student1 by Vidya Jyoti
            StudentVerification.objects.get_or_create(
                student_profile=sp1,
                ngo=ngo1,
                defaults={
                    'status': 'APPROVED',
                    'verified_by': v_admin,
                    'comments': 'Verified enrollment records and fee concession certificate. Approved for direct allocations.',
                    'verified_at': timezone.now()
                }
            )

            # 6. Seed Realistic Inventory Copies (Ready for Student Requests)
            books_data = [
                {
                    'ngo': ngo1,
                    'tracking_code': 'BB-VIDYA-2026-ENG01',
                    'book_title': 'Introduction to Algorithms (CLRS)',
                    'author': 'Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest',
                    'isbn': '978-0262033848',
                    'publisher': 'MIT Press',
                    'publication_year': 2020,
                    'edition': '3rd Edition',
                    'category': BookCategory.SCIENCE_TECH,
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'subject': 'Computer Science / Algorithms',
                    'condition_grade': ConditionGrade.LIKE_NEW,
                    'location_shelf': 'Rack CS-01 / Shelf B3',
                    'status': InventoryStatus.AVAILABLE,
                    'is_published': True,
                },
                {
                    'ngo': ngo1,
                    'tracking_code': 'BB-VIDYA-2026-PHY02',
                    'book_title': 'Concepts of Physics - Volume 1',
                    'author': 'H. C. Verma',
                    'isbn': '978-8177091878',
                    'publisher': 'Bharati Bhawan',
                    'publication_year': 2022,
                    'edition': 'Revised 2022',
                    'category': BookCategory.TEXTBOOK,
                    'academic_level': AcademicLevel.SENIOR_SECONDARY,
                    'subject': 'Physics Class 11 & 12',
                    'condition_grade': ConditionGrade.VERY_GOOD,
                    'location_shelf': 'Rack PHY-02 / Shelf A1',
                    'status': InventoryStatus.AVAILABLE,
                    'is_published': True,
                },
                {
                    'ngo': ngo1,
                    'tracking_code': 'BB-VIDYA-2026-MED03',
                    'book_title': 'Guyton and Hall Textbook of Medical Physiology',
                    'author': 'John E. Hall, Michael E. Hall',
                    'isbn': '978-0323597128',
                    'publisher': 'Elsevier',
                    'publication_year': 2021,
                    'edition': '14th Edition',
                    'category': BookCategory.MEDICINE_HEALTH,
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'subject': 'Medical / MBBS 1st Prof',
                    'condition_grade': ConditionGrade.GOOD,
                    'location_shelf': 'Rack MED-01 / Shelf C2',
                    'status': InventoryStatus.AVAILABLE,
                    'is_published': True,
                },
                {
                    'ngo': ngo2,
                    'tracking_code': 'BB-PRATHAM-2026-MAT01',
                    'book_title': 'Higher Engineering Mathematics',
                    'author': 'B. S. Grewal',
                    'isbn': '978-8193328491',
                    'publisher': 'Khanna Publishers',
                    'publication_year': 2021,
                    'edition': '44th Edition',
                    'category': BookCategory.SCIENCE_TECH,
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'subject': 'Engineering Mathematics',
                    'condition_grade': ConditionGrade.LIKE_NEW,
                    'location_shelf': 'Mumbai Hub Shelf M-10',
                    'status': InventoryStatus.AVAILABLE,
                    'is_published': True,
                },
                {
                    'ngo': ngo3,
                    'tracking_code': 'BB-GYAN-2026-EXAM01',
                    'book_title': 'UPSC Indian Polity',
                    'author': 'M. Laxmikanth',
                    'isbn': '978-9389538472',
                    'publisher': 'McGraw Hill',
                    'publication_year': 2023,
                    'edition': '7th Edition',
                    'category': BookCategory.EXAM_PREP,
                    'academic_level': AcademicLevel.VOCATIONAL,
                    'subject': 'Civil Services & Competitive Exams',
                    'condition_grade': ConditionGrade.VERY_GOOD,
                    'location_shelf': 'BLR Central Bay 4',
                    'status': InventoryStatus.AVAILABLE,
                    'is_published': True,
                }
            ]

            created_copies = []
            for b in books_data:
                copy_obj, _ = InventoryCopy.objects.get_or_create(
                    tracking_code=b['tracking_code'],
                    defaults=b
                )
                created_copies.append(copy_obj)

            # 7. Seed Complete Demonstration Workflow Case:
            # Donor -> Listing -> Review -> Pickup -> Inspection -> Inventory -> Request -> Allocation -> Delivery -> Student Confirmed
            fulfilled_donation, _ = DonationListing.objects.get_or_create(
                donor=donor1,
                ngo=ngo1,
                title='Operating System Concepts (Dinosaur Book)',
                defaults={
                    'author': 'Abraham Silberschatz, Peter B. Galvin, Greg Gagne',
                    'isbn': '978-1119800361',
                    'publisher': 'Wiley',
                    'publication_year': 2021,
                    'category': BookCategory.SCIENCE_TECH,
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'subject': 'Operating Systems',
                    'declared_condition': ConditionGrade.VERY_GOOD,
                    'donor_condition_description': 'Clean pages, original hardcover, used for 3rd semester CSE course.',
                    'pickup_address': 'B-14, Green Park Extension',
                    'pickup_city': 'New Delhi',
                    'pickup_state': 'Delhi',
                    'pickup_postal_code': '110016',
                    'donor_contact_phone': '+91 9811223344',
                    'status': DonationStatus.INVENTORIED,
                    'verified_condition': ConditionGrade.VERY_GOOD,
                    'inspected_by': v_inspector,
                    'inspected_at': timezone.now(),
                    'inspection_notes': 'Physical inspection passed. Complete pages, binding firm, clean margin notations.'
                }
            )

            fulfilled_copy, _ = InventoryCopy.objects.get_or_create(
                tracking_code='BB-VIDYA-2026-OS09',
                defaults={
                    'ngo': ngo1,
                    'donation_listing': fulfilled_donation,
                    'book_title': fulfilled_donation.title,
                    'author': fulfilled_donation.author,
                    'isbn': fulfilled_donation.isbn,
                    'publisher': fulfilled_donation.publisher,
                    'category': fulfilled_donation.category,
                    'academic_level': fulfilled_donation.academic_level,
                    'subject': fulfilled_donation.subject,
                    'condition_grade': ConditionGrade.VERY_GOOD,
                    'location_shelf': 'Rack CS-02 / Shelf D1',
                    'status': InventoryStatus.DELIVERED,
                    'is_published': True
                }
            )

            fulfilled_req, _ = BookRequest.objects.get_or_create(
                student=student1,
                inventory_copy=fulfilled_copy,
                defaults={
                    'ngo': ngo1,
                    'educational_purpose': 'Required for Semester 4 Operating Systems course and lab assignments at DTU.',
                    'urgent_need': True,
                    'urgency_reason': 'Mid-semester exams approaching next month.',
                    'delivery_address': 'Room 108, Girls Hostel Block B, DTU Campus, Shahbad Daulatpur',
                    'delivery_city': 'New Delhi',
                    'delivery_state': 'Delhi',
                    'delivery_postal_code': '110042',
                    'contact_phone': '+91 9899001122',
                    'status': RequestStatus.COMPLETED
                }
            )

            fulfilled_alloc, _ = Allocation.objects.get_or_create(
                book_request=fulfilled_req,
                defaults={
                    'inventory_copy': fulfilled_copy,
                    'ngo': ngo1,
                    'allocated_by': v_admin,
                    'status': AllocationStatus.FULFILLED,
                    'notes': 'Allocated from shelf CS-02 to verified engineering student.'
                }
            )

            DeliveryJob.objects.get_or_create(
                allocation=fulfilled_alloc,
                defaults={
                    'ngo': ngo1,
                    'recipient_student': student1,
                    'tracking_number': 'DEL-DELHI-DTU-8821',
                    'courier_name': 'NGO Direct Volunteer Dispatch (Ramesh Kumar)',
                    'delivery_address': fulfilled_req.delivery_address,
                    'status': DeliveryStatus.DELIVERED,
                    'dispatched_at': timezone.now(),
                    'delivered_at': timezone.now(),
                    'student_confirmed': True,
                    'student_confirmed_at': timezone.now(),
                    'student_feedback': 'Thank you so much to the donor Rahul Sharma and Vidya Jyoti Trust! This book is invaluable for my studies.'
                }
            )

            # 8. Seed Donation in PENDING REVIEW state (for testing NGO review)
            DonationListing.objects.get_or_create(
                donor=donor2,
                ngo=ngo2,
                title='Organic Chemistry',
                defaults={
                    'author': 'Paula Yurkanis Bruice',
                    'isbn': '978-0134042282',
                    'publisher': 'Pearson',
                    'publication_year': 2020,
                    'category': BookCategory.SCIENCE_TECH,
                    'academic_level': AcademicLevel.UNDERGRADUATE,
                    'subject': 'Chemistry',
                    'declared_condition': ConditionGrade.GOOD,
                    'donor_condition_description': 'Used textbook with some pencil marks on chapter 4, otherwise solid binding.',
                    'pickup_address': 'Flat 402, Sea Crest Towers, Bandra West',
                    'pickup_city': 'Mumbai',
                    'pickup_state': 'Maharashtra',
                    'pickup_postal_code': '400050',
                    'donor_contact_phone': '+91 9822334455',
                    'status': DonationStatus.SUBMITTED
                }
            )

            # 9. Audit Logs
            AuditLog.objects.create(
                user=admin_user,
                action="SYSTEM_INITIALIZE_SEED",
                entity_type="Platform",
                entity_id="ALL",
                organization=None,
                details={"seed_status": "Complete demonstration seed applied."}
            )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded!"))
        self.stdout.write(self.style.SUCCESS("--- TEST CREDENTIALS ---"))
        self.stdout.write("1. Platform Admin : admin          / Admin@12345")
        self.stdout.write("2. NGO Admin      : vidya_admin    / Staff@12345 (Vidya Jyoti Trust - Delhi)")
        self.stdout.write("3. NGO Inspector  : vidya_inspector/ Staff@12345")
        self.stdout.write("4. NGO Admin 2    : pratham_admin  / Staff@12345 (Pratham Shiksha - Mumbai)")
        self.stdout.write("5. Donor          : rahul_donor    / Donor@12345")
        self.stdout.write("6. Student        : ananya_student / Student@12345 (Verified DTU Student)")
        self.stdout.write("7. Student 2      : rohit_student  / Student@12345 (Pending Verification)")
        self.stdout.write("------------------------")
