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

    const tabItem = $(`.tab-item[onclick="switchSettingsTab('${tab}')"]`);
    if (tabItem) tabItem.classList.add('active');

    const tabPane = $(`#tab_${tab}`);
    if (tabPane) tabPane.classList.add('active');

    // Load data for this tab
    loadWhitelist(tab);
}

async function loadGlobalSettings() {
    try {
        const res = await api("/settings/global");

        // Telegram
        const tgEnabled = $('#setting_tg_enabled'); if (tgEnabled) tgEnabled.checked = res.telegram.enabled;
        const tgPrivate = $('#setting_tg_private'); if (tgPrivate) tgPrivate.checked = res.telegram.allow_private;
        const tgNew = $('#setting_tg_new_chats'); if (tgNew) tgNew.checked = res.telegram.allow_new_chats;
        const tgMem = $('#setting_tg_memory'); if (tgMem) tgMem.value = res.telegram.memory_limit;

        // Discord
        const dcEnabled = $('#setting_dc_enabled'); if (dcEnabled) dcEnabled.checked = res.discord.enabled;
        const dcDm = $('#setting_dc_dm'); if (dcDm) dcDm.checked = res.discord.allow_dms;
        const dcNew = $('#setting_dc_new_chats'); if (dcNew) dcNew.checked = res.discord.allow_new_chats;
        const dcMusic = $('#setting_dc_music'); if (dcMusic) dcMusic.checked = res.discord.music_enabled;
        const dcMem = $('#setting_dc_memory'); if (dcMem) dcMem.value = res.discord.memory_limit;
        const dcSeek = $('#setting_dc_seek'); if (dcSeek) dcSeek.value = res.discord.seek_time;

    } catch (e) { }
}

async function saveSettings() {
    const data = {
        telegram: {
            enabled: $('#setting_tg_enabled')?.checked || false,
            allow_private: $('#setting_tg_private')?.checked || false,
            allow_new_chats: $('#setting_tg_new_chats')?.checked || false,
            memory_limit: parseInt($('#setting_tg_memory')?.value) || 10
        },
        discord: {
            enabled: $('#setting_dc_enabled')?.checked || false,
            allow_dms: $('#setting_dc_dm')?.checked || false,
            allow_new_chats: $('#setting_dc_new_chats')?.checked || false,
            music_enabled: $('#setting_dc_music')?.checked || false,
            memory_limit: parseInt($('#setting_dc_memory')?.value) || 10,
            seek_time: parseInt($('#setting_dc_seek')?.value) || 10
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
                    <button class="btn-icon delete-btn text-danger" onclick="deleteWhitelistItem(${item.id}, '${platform}')">
                        <i data-lucide="trash-2" class="icon-small"></i>
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
