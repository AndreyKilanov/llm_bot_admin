const loader = {
    show: () => {
        const el = document.getElementById('page-loader');
        if (el) el.classList.remove('hidden-loader');
    },
    hide: () => {
        const el = document.getElementById('page-loader');
        if (el) el.classList.add('hidden-loader');
    }
};

// Expose to window
window.loader = loader;

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    if (window.lucide) {
        lucide.createIcons();
    }

    // Hide loader after a brief moment to ensure sleek transition
    setTimeout(() => {
        loader.hide();
    }, 500);
});
