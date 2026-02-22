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
        // 1. Soft Ripple Effect
        const ripple = document.createElement('div');
        ripple.className = 'click-soft-ripple';
        ripple.style.left = `${e.clientX}px`;
        ripple.style.top = `${e.clientY}px`;
        document.body.appendChild(ripple);
        setTimeout(() => ripple.remove(), 300);

        // 2. Pixel Particles Explosion
        const particleCount = 6;
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'pixel-particle';

            const dx = (Math.random() - 0.5) * 60;
            const dy = (Math.random() - 0.5) * 60;
            const dr = (Math.random() - 0.5) * 360;

            particle.style.setProperty('--dx', `${dx}px`);
            particle.style.setProperty('--dy', `${dy}px`);
            particle.style.setProperty('--dr', `${dr}deg`);

            particle.style.left = `${e.clientX}px`;
            particle.style.top = `${e.clientY}px`;

            document.body.appendChild(particle);
            setTimeout(() => particle.remove(), 500);
        }
    });
}
