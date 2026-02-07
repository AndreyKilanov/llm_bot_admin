function onProviderChange() {
    const urlInput = document.getElementById("conn_url");
    const dropdown = document.querySelector('.custom-dropdown[data-input-id="conn_provider"]');
    if (!dropdown) return;

    const selectedOption = dropdown.querySelector('.dropdown-option.selected');
    if (selectedOption) {
        const url = selectedOption.dataset.url;
        if (url) {
            urlInput.value = url;
        } else if (selectedOption.dataset.value === "custom") {
            urlInput.value = "";
        }
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

        // Custom handling for dropdown if it exists, otherwise standard select logic if changed
        const providerInput = document.getElementById("conn_provider");
        if (providerInput) providerInput.value = conn.provider || "custom";

        // Trigger dropdown update if using custom dropdown
        const dropdown = document.querySelector('.custom-dropdown[data-input-id="conn_provider"]');
        if (dropdown) {
            const option = dropdown.querySelector(`.dropdown-option[data-value="${conn.provider || 'custom'}"]`);
            if (option) {
                dropdown.querySelector('.selected-text').textContent = option.textContent.trim();
                dropdown.querySelectorAll('.dropdown-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
            }
        }

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

    // Reset dropdown text
    const dropdown = document.querySelector('.custom-dropdown[data-input-id="conn_provider"]');
    if (dropdown) {
        dropdown.querySelector('.selected-text').textContent = "Выберите провайдера...";
        dropdown.querySelectorAll('.dropdown-option').forEach(o => o.classList.remove('selected'));
    }

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
