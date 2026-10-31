/**
 * BookBridge — Vanilla JavaScript interactive helpers
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Multi-image file preview for donation listings
    const imageInput = document.getElementById('id_donation_images');
    const previewContainer = document.getElementById('image-preview-container');

    if (imageInput && previewContainer) {
        imageInput.addEventListener('change', function(e) {
            previewContainer.innerHTML = '';
            const files = Array.from(e.target.files);
            
            if (files.length === 0) return;

            files.forEach((file, index) => {
                if (!file.type.startsWith('image/')) return;
                
                const reader = new FileReader();
                reader.onload = function(event) {
                    const thumbBox = document.createElement('div');
                    thumbBox.className = 'preview-thumb-box position-relative';
                    
                    const img = document.createElement('img');
                    img.src = event.target.result;
                    img.alt = `Book image ${index + 1}`;
                    
                    const badge = document.createElement('span');
                    badge.className = 'position-absolute top-0 start-0 badge bg-dark text-white p-1 m-1';
                    badge.style.fontSize = '0.65rem';
                    badge.textContent = index === 0 ? 'Cover' : `#${index + 1}`;
                    
                    thumbBox.appendChild(img);
                    thumbBox.appendChild(badge);
                    previewContainer.appendChild(thumbBox);
                };
                reader.readAsDataURL(file);
            });
        });
    }

    // 2. Initialize Bootstrap Tooltips & Popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) {
        return new bootstrap.Tooltip(el);
    });

    // 3. Generic confirmation handlers for sensitive actions
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // 4. Auto-dismiss alerts after 6 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert-dismissible').forEach(alertNode => {
            const bsAlert = bootstrap.Alert.getInstance(alertNode) || new bootstrap.Alert(alertNode);
            bsAlert.close();
        });
    }, 6000);
});
