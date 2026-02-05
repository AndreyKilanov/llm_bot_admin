// Basic utils
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

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

// LLM Provider Templates
const PROVIDER_TEMPLATES = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com",
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai/v1",
    "custom": ""
};

function onProviderChange() {
    const provider = document.getElementById("conn_provider").value;
    const urlInput = document.getElementById("conn_url");

    if (PROVIDER_TEMPLATES[provider] !== undefined && provider !== "custom") {
        urlInput.value = PROVIDER_TEMPLATES[provider];
    } else if (provider === "custom") {
        urlInput.value = "";
    }
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

// Actions
async function activateConn(id) {
    try {
        await api("/llm/connections/" + id + "/activate", "POST");
        window.location.reload();
    } catch (e) { }
}

async function checkConn(id) {
    try {
        const res = await api("/llm/connections/" + id + "/check", "POST");
        if (res.ok) {
            showToast("Подключение успешно!");
        } else {
            showToast("Ошибка: Проверьте ключ API и провайдера", true);
        }
    } catch (e) { }
}

async function checkCurrentConn() {
    const data = {
        name: document.getElementById("conn_name").value,
        provider: document.getElementById("conn_provider").value,
        model_name: document.getElementById("conn_model").value,
        api_key: document.getElementById("conn_key").value,
        base_url: document.getElementById("conn_url").value || null
    };

    if (!data.provider || !data.api_key) {
        showToast("Заполните провайдера и API Key для проверки", true);
        return;
    }

    const btn = document.getElementById("conn_check_btn");
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width: 16px; height: 16px;"></i> Проверка...`;
    if (window.lucide) lucide.createIcons();

    try {
        const res = await api("/llm/connections/check-temporary", "POST", data);
        if (res.ok) {
            showToast("Подключение успешно!");
        } else {
            showToast("Ошибка проверки: " + (res.detail || "Проверьте данные"), true);
        }
    } catch (e) {
    } finally {
        btn.innerHTML = originalHtml;
        if (window.lucide) lucide.createIcons();
    }
}

let editingConnId = null;

async function editConn(id) {
    try {
        const conn = await api("/llm/connections/" + id);
        editingConnId = id;
        document.getElementById("conn_name").value = conn.name;

        const providerSelect = document.getElementById("conn_provider");
        providerSelect.value = conn.provider || "custom";

        document.getElementById("conn_model").value = conn.model_name;
        document.getElementById("conn_key").value = conn.api_key;
        document.getElementById("conn_url").value = conn.base_url || "";

        document.getElementById("conn_submit_btn").innerHTML = `<i data-lucide="save" style="width: 16px; height: 16px;"></i> Сохранить изменения`;
        document.getElementById("conn_form_title").textContent = "Редактировать подключение";

        openConnModal();
    } catch (e) { }
}

function cancelEditConn() {
    editingConnId = null;
    document.getElementById("conn_name").value = "";
    document.getElementById("conn_provider").value = "";
    document.getElementById("conn_model").value = "";
    document.getElementById("conn_key").value = "";
    document.getElementById("conn_url").value = "";

    document.getElementById("conn_submit_btn").innerHTML = `<i data-lucide="save" style="width: 16px; height: 16px;"></i> Добавить`;
    document.getElementById("conn_form_title").textContent = "Добавить подключение";
}

function openConnModal() {
    if (!editingConnId) cancelEditConn();
    const modal = document.getElementById("conn_modal");
    modal.style.display = "flex";
    setTimeout(() => modal.classList.add("show"), 10);
    document.body.style.overflow = "hidden";
    if (window.lucide) lucide.createIcons();
}

function closeConnModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById("conn_modal");
    modal.classList.remove("show");
    setTimeout(() => {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
        cancelEditConn();
    }, 300);
}

async function deleteConn(id) {
    const confirmed = await confirmAction("Удалить это подключение? Все связанные промпты будут удалены.");
    if (!confirmed) return;
    try {
        await api("/llm/connections/" + id, "DELETE");
        window.location.reload();
    } catch (e) { }
}

async function addConn() {
    const data = {
        name: document.getElementById("conn_name").value,
        provider: document.getElementById("conn_provider").value,
        model_name: document.getElementById("conn_model").value,
        api_key: document.getElementById("conn_key").value,
        base_url: document.getElementById("conn_url").value || null,
        is_active: false
    };

    if (!data.name || !data.provider || !data.model_name || !data.api_key) {
        showToast("Заполните обязательные поля", true);
        return;
    }

    try {
        if (editingConnId) {
            await api("/llm/connections/" + editingConnId, "PUT", data);
            showToast("Подключение обновлено");
            window.location.reload();
        } else {
            await api("/llm/connections", "POST", data);
            window.location.reload();
        }
    } catch (e) { }
}

let selectedConnId = null;

async function showPrompts(id, name) {
    selectedConnId = id;
    document.getElementById("current_conn_name").textContent = name;

    const modal = document.getElementById("prompts_modal");
    modal.style.display = "flex";
    setTimeout(() => modal.classList.add("show"), 10);

    // Disable body scroll
    document.body.style.overflow = "hidden";

    await loadPrompts();
}

function closePrompts(event) {
    if (event && event.target !== event.currentTarget) return;

    const modal = document.getElementById("prompts_modal");
    modal.classList.remove("show");

    setTimeout(() => {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
        cancelEditPrompt();
    }, 300);
}

let editingPromptId = null;

async function loadPrompts() {
    try {
        const prompts = await api("/llm/connections/" + selectedConnId + "/prompts");
        const html = prompts.map(p => `
            <div class="card" style="margin-bottom: 0.5rem; padding: 1rem; ${p.is_active ? 'border-color: var(--accent-primary);' : ''}">
                <div class="flex justify-between mb-4">
                    <strong>${p.name}</strong>
                    <div class="flex" style="gap: 0.25rem;">
                        ${p.is_active ? '<span style="color:var(--success); font-size:0.8rem; margin-right: 0.5rem;">Активен</span>' : ''}
                        <button class="btn btn-icon" onclick="editPrompt(${p.id}, '${p.name.replace(/'/g, "\\'")}', '${p.content.replace(/\n/g, "\\n").replace(/'/g, "\\'")}')" title="Редактировать">
                            <i data-lucide="edit-2" style="width: 16px; height: 16px;"></i>
                        </button>
                        <button class="btn btn-icon delete-prompt" onclick="deletePrompt(${p.id})" title="Удалить" style="color: var(--danger)">
                            <i data-lucide="trash-2" style="width: 18px; height: 18px;"></i>
                        </button>
                    </div>
                </div>
                <pre style="white-space:pre-wrap; font-size:0.85rem; background:var(--bg-primary); padding:0.5rem; border-radius:4px; margin-bottom:0.5rem; color: var(--text-secondary)">${p.content}</pre>
                <div class="flex">
                    ${!p.is_active ?
                `<button class="btn btn-primary flex" style="width:34px; height:34px; padding:0; justify-content:center;" onclick="activatePrompt(${p.id})" title="Активировать"><i data-lucide="play" style="width: 16px; height: 16px;"></i></button>` :
                `<button class="btn flex" style="width:34px; height:34px; padding:0; justify-content:center; background: rgba(16, 185, 129, 0.1); color: var(--success); cursor: default; border: 1px solid rgba(16, 185, 129, 0.2);" title="Активен"><i data-lucide="check" style="width: 16px; height: 16px;"></i></button>`
            }
                </div>
            </div>
        `).join("");
        document.getElementById("prompts_list").innerHTML = html || "<p style='color:var(--text-secondary)'>Промптов пока нет</p>";
        if (window.lucide) lucide.createIcons();
    } catch (e) { }
}

function editPrompt(id, name, content) {
    editingPromptId = id;
    document.getElementById("prompt_name").value = name;
    document.getElementById("prompt_content").value = content;
    document.getElementById("prompt_submit_btn").innerHTML = `<i data-lucide="save" style="width: 16px; height: 16px;"></i> Сохранить`;
    document.getElementById("prompt_cancel_btn").style.display = "inline-flex";
    document.getElementById("prompt_form_title").textContent = "Редактировать промпт";
    if (window.lucide) lucide.createIcons();

    // Scroll to form
    const form = document.getElementById("prompt_form");
    if (form) {
        form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    document.getElementById("prompt_name").focus();
}

function cancelEditPrompt() {
    editingPromptId = null;
    document.getElementById("prompt_name").value = '';
    document.getElementById("prompt_content").value = '';
    document.getElementById("prompt_submit_btn").innerHTML = `<i data-lucide="plus-square" style="width: 16px; height: 16px;"></i> Добавить промпт`;
    document.getElementById("prompt_cancel_btn").style.display = "none";
    document.getElementById("prompt_form_title").textContent = "Добавить промпт";
    if (window.lucide) lucide.createIcons();
}

async function submitPrompt() {
    const name = document.getElementById("prompt_name").value;
    const content = document.getElementById("prompt_content").value;

    if (!name || !content) {
        showToast("Заполните все поля", true);
        return;
    }

    const data = { name, content };

    try {
        if (editingPromptId) {
            // Edit
            await api("/llm/prompts/" + editingPromptId, "PUT", data);
            showToast("Промпт обновлен");
        } else {
            // Create
            data.is_active = false;
            await api("/llm/connections/" + selectedConnId + "/prompts", "POST", data);
            showToast("Промпт создан");
        }
        await loadPrompts();
        cancelEditPrompt();
    } catch (e) { }
}

async function activatePrompt(id) {
    try {
        await api("/llm/prompts/" + id + "/activate", "POST");
        await loadPrompts();
    } catch (e) { }
}

async function deletePrompt(id) {
    const confirmed = await confirmAction("Удалить этот промпт?");
    if (!confirmed) return;
    try {
        await api("/llm/prompts/" + id, "DELETE");
        await loadPrompts();
        showToast("Промпт удален");
    } catch (e) { }
}

async function clearAll() {
    const confirmed = await confirmAction("Вы уверены, что хотите удалить ВСЮ историю?");
    if (!confirmed) return;
    try {
        await api("/clear-all", "POST");
        window.location.reload();
    } catch (e) { }
}

async function clearChat(id, platform) {
    const confirmed = await confirmAction("Удалить этот чат?");
    if (!confirmed) return;
    try {
        await api("/clear/" + id + "/" + platform, "POST");
        window.location.reload();
    } catch (e) { }
}

// --- Settings & Whitelist Logic ---

// --- Settings & Whitelist Logic ---

let currentSettingsTab = 'telegram';

function openSettingsModal() {
    const modal = document.getElementById("settings_modal");
    modal.style.display = "flex";
    setTimeout(() => modal.classList.add("show"), 10);
    document.body.style.overflow = "hidden";

    if (window.lucide) lucide.createIcons();

    // Switch to last used tab or default
    switchSettingsTab(currentSettingsTab);
    loadGlobalSettings();
}

function closeSettingsModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById("settings_modal");
    modal.classList.remove("show");
    setTimeout(() => {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    }, 300);
}

function switchSettingsTab(tab) {
    currentSettingsTab = tab;

    // Update tabs UI
    $$('.tab-item').forEach(el => el.classList.remove('active'));
    $$('.tab-pane').forEach(el => el.classList.remove('active'));

    $(`.tab-item[onclick="switchSettingsTab('${tab}')"]`).classList.add('active');
    $(`#tab_${tab}`).classList.add('active');

    // Load data for this tab
    loadWhitelist(tab);
}

async function loadGlobalSettings() {
    try {
        const res = await api("/settings/global");

        // Telegram
        $('#setting_tg_enabled').checked = res.telegram.enabled;
        $('#setting_tg_private').checked = res.telegram.allow_private;
        $('#setting_tg_new_chats').checked = res.telegram.allow_new_chats;
        $('#setting_tg_memory').value = res.telegram.memory_limit;

        // Discord
        $('#setting_dc_enabled').checked = res.discord.enabled;
        $('#setting_dc_dm').checked = res.discord.allow_dms;
        $('#setting_dc_new_chats').checked = res.discord.allow_new_chats;
        $('#setting_dc_memory').value = res.discord.memory_limit;

    } catch (e) { }
}

async function saveSettings() {
    const data = {
        telegram: {
            enabled: $('#setting_tg_enabled').checked,
            allow_private: $('#setting_tg_private').checked,
            allow_new_chats: $('#setting_tg_new_chats').checked,
            memory_limit: parseInt($('#setting_tg_memory').value) || 10
        },
        discord: {
            enabled: $('#setting_dc_enabled').checked,
            allow_dms: $('#setting_dc_dm').checked,
            allow_new_chats: $('#setting_dc_new_chats').checked,
            memory_limit: parseInt($('#setting_dc_memory').value) || 10
        }
    };

    try {
        await api("/settings/global", "POST", data);
        showToast("Настройки сохранены");
        closeSettingsModal();
    } catch (e) { }
}


async function loadWhitelist(platform) {
    try {
        const list = await api(`/whitelist?platform=${platform}`);
        const html = list.map(item => `
            <div class="whitelist-item">
                <div style="flex-grow: 1;">
                    <div style="font-weight: 500;">${item.title || 'Без названия'}</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); font-family: monospace;">${item.chat_id}</div>
                </div>
                <div class="flex" style="gap: 0.5rem; align-items: center;">
                    <label class="switch" title="${item.is_active ? 'Активна' : 'Неактивна'}">
                        <input type="checkbox" ${item.is_active ? 'checked' : ''} onchange="toggleWhitelistItem(${item.id}, this.checked, '${platform}')">
                        <span class="slider"></span>
                    </label>
                    <button class="btn btn-icon" onclick="deleteWhitelistItem(${item.id}, '${platform}')" style="color: var(--danger)">
                        <i data-lucide="trash-2" style="width: 16px; height: 16px;"></i>
                    </button>
                </div>
            </div>
        `).join("");

        const containerId = `whitelist_list_${platform}`;
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = html || "<p style='color:var(--text-secondary); text-align:center; padding: 1rem;'>Список пуст</p>";
            if (window.lucide) lucide.createIcons();
        }
    } catch (e) { console.error(e); }
}

async function addWhitelistItem(platform) {
    const prefix = platform === 'telegram' ? 'whitelist_tg' : 'whitelist_dc';
    const chat_id = document.getElementById(`${prefix}_id`).value.trim();
    const title = document.getElementById(`${prefix}_title`).value.trim();

    if (!chat_id) {
        showToast("Введите ID", true);
        return;
    }

    try {
        await api("/whitelist", "POST", {
            chat_id,
            platform,
            title: title || (platform === 'telegram' ? `Group ${chat_id}` : `Server ${chat_id}`)
        });
        document.getElementById(`${prefix}_id`).value = "";
        document.getElementById(`${prefix}_title`).value = "";
        await loadWhitelist(platform);
        showToast("Добавлено в белый список");
    } catch (e) { }
}

async function deleteWhitelistItem(id, platform) {
    if (!await confirmAction("Удалить из белого списка?")) return;

    try {
        await api("/whitelist/" + id, "DELETE");
        await loadWhitelist(platform);
    } catch (e) { }
}

async function toggleWhitelistItem(id, isActive, platform) {
    try {
        await api("/whitelist/" + id + "/toggle", "POST", { is_active: isActive });
        showToast(isActive ? "Включено" : "Отключено");
    } catch (e) {
        // Revert on error
        await loadWhitelist(platform);
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    if (window.lucide) {
        lucide.createIcons();
    }
});
