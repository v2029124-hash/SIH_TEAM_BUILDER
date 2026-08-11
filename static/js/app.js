document.addEventListener("DOMContentLoaded", () => {
    
    // Simple form validation for WhatsApp formatting
    const createForm = document.getElementById('createForm');
    if(createForm) {
        createForm.addEventListener('submit', (e) => {
            const phoneInput = document.querySelector('input[name="whatsapp_number"]').value;
            // Checks if it contains at least 10 digits
            const digitCount = phoneInput.replace(/\D/g, '').length;
            
            if(digitCount < 10) {
                e.preventDefault();
                alert('Please enter a valid WhatsApp number with country code (e.g. +91 9999999999).');
            }
        });
    }

    // Add subtle reveal animations for cards
    const cards = document.querySelectorAll('.team-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
});