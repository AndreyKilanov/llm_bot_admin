// Basic utils
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

/**
 * Custom confirmation modal
 * @param {string} msg 
 * @param {string} title 
 * @returns {Promise<boolean>}
 */
function confirmAction(msg, title = "Подтвердите действие") {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm_modal');
        const okBtn = document.getElementById('confirm_ok_btn');
        const cancelBtn = document.getElementById('confirm_cancel_btn');
        const crossBtn = document.getElementById('confirm_cross_btn');
        const msgEl = document.getElementById('confirm_message');
        const titleEl = document.getElementById('confirm_title');

        msgEl.textContent = msg;
        titleEl.textContent = title;
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('show'), 10);

        const onOk = () => {
            cleanup();
            resolve(true);
        };

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        const cleanup = () => {
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
            if (crossBtn) crossBtn.removeEventListener('click', onCancel);
        };

        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        if (crossBtn) crossBtn.addEventListener('click', onCancel);
    });
}

// Toast Notifications
function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.borderColor = isError ? 'var(--danger)' : 'var(--success)';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// API Wrapper
async function api(url, method = "GET", body = null) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);

    try {
        const r = await fetch("/admin/api" + url, opts);

        if (r.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        const isJson = r.headers.get("content-type")?.includes("application/json");
        const data = isJson ? await r.json() : null;

        if (!r.ok) {
            const errorMsg = data?.detail || r.statusText || "Ошибка сервера";
            throw new Error(errorMsg);
        }

        return data;
    } catch (e) {
        let msg = e.message;
        if (msg.includes("Unexpected token")) msg = "Сервер вернул некорректный ответ (500 Error)";
        showToast(msg, true);
        throw e;
    }
}
