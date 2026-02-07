// Theme Switcher
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    const iconName = theme === 'dark' ? 'sun' : 'moon';

    const btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.innerHTML = `<i data-lucide="${iconName}"></i>`;
    }

    const btnLogin = document.getElementById('theme-toggle-login');
    if (btnLogin) {
        btnLogin.innerHTML = `<i data-lucide="${iconName}"></i>`;
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}
