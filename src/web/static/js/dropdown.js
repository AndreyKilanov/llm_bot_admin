document.addEventListener('DOMContentLoaded', () => {
    initCustomDropdowns();
});

function initCustomDropdowns() {
    const dropdowns = document.querySelectorAll('.custom-dropdown');

    dropdowns.forEach(dropdown => {
        const trigger = dropdown.querySelector('.dropdown-trigger');
        const menu = dropdown.querySelector('.dropdown-menu');
        const options = dropdown.querySelectorAll('.dropdown-option');
        const hiddenInput = document.getElementById(dropdown.dataset.inputId);
        const selectedText = dropdown.querySelector('.selected-text');

        // Toggle dropdown
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            closeAllDropdowns(dropdown); // Close others
            dropdown.classList.toggle('active');
        });

        // Select option
        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const value = option.dataset.value;
                const text = option.textContent.trim();

                // Update UI
                selectedText.textContent = text;
                hiddenInput.value = value;

                // Active class for styling
                options.forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');

                // Close dropdown
                dropdown.classList.remove('active');

                // Trigger change event if needed (for other scripts)
                const event = new Event('change');
                hiddenInput.dispatchEvent(event);

                // Call global handler if exists (legacy support)
                if (typeof onProviderChange === 'function' && hiddenInput.id === 'conn_provider') {
                    onProviderChange();
                }
            });
        });
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
        closeAllDropdowns();
    });
}

function closeAllDropdowns(except = null) {
    document.querySelectorAll('.custom-dropdown').forEach(dropdown => {
        if (dropdown !== except) {
            dropdown.classList.remove('active');
        }
    });
}
