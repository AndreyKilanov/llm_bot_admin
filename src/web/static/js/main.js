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
    initTooltips();
    initClickEffect();
    if (window.lucide) {
        lucide.createIcons();
    }

    // Hide loader after a brief moment to ensure sleek transition
    setTimeout(() => {
        loader.hide();
    }, 500);
});

function initTooltips() {
    document.querySelectorAll('[title]').forEach(el => {
        el.setAttribute('data-tooltip', el.getAttribute('title'));
        el.removeAttribute('title');
    });
}

function initClickEffect() {
    document.addEventListener('mousedown', (e) => {
        const effect = document.createElement('div');
        effect.className = 'click-effect';
        effect.style.left = `${e.clientX}px`;
        effect.style.top = `${e.clientY}px`;
        document.body.appendChild(effect);

        setTimeout(() => {
            effect.remove();
        }, 400);
    });
}
