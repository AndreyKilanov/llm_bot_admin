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
            <div class="prompt-card ${p.is_active ? 'active' : ''}">
                <div class="flex justify-between items-center mb-2">
                    <div class="flex items-center gap-3">
                        <strong style="font-size: 1.1rem;">${p.name}</strong>
                        ${p.is_active ? `
                            <span class="prompt-status-badge status-active">
                                <i data-lucide="check-circle" style="width: 12px; height: 12px;"></i>
                                Активен
                            </span>
                        ` : ''}
                    </div>
                    <div class="flex" style="gap: 0.5rem;">
                        <button class="btn-icon" onclick="editPrompt(${p.id}, '${p.name.replace(/'/g, "\\'")}', '${p.content.replace(/\n/g, "\\n").replace(/'/g, "\\'")}')" title="Редактировать">
                            <i data-lucide="edit-3" style="width: 18px; height: 18px;"></i>
                        </button>
                        <button class="btn-icon delete-prompt" onclick="deletePrompt(${p.id})" title="Удалить" style="color: var(--danger)">
                            <i data-lucide="trash-2" style="width: 18px; height: 18px;"></i>
                        </button>
                    </div>
                </div>
                
                <div class="prompt-preview">${p.content}</div>
                
                <div class="prompt-actions-bottom">
                    ${p.is_active ? `
                        <button class="btn btn-status-toggle btn-danger" onclick="deactivatePrompt(${p.id})">
                            <i data-lucide="power" style="width: 16px; height: 16px;"></i>
                            Деактивировать
                        </button>
                    ` : `
                        <button class="btn btn-primary btn-status-toggle" onclick="activatePrompt(${p.id})">
                            <i data-lucide="zap" style="width: 16px; height: 16px;"></i>
                            Активировать
                        </button>
                    `}
                </div>
            </div>
        `).join("");
        document.getElementById("prompts_list").innerHTML = html || "<p style='color:var(--text-secondary); text-align:center; padding: 2rem;'>Промптов пока нет. Добавьте свой первый промпт ниже.</p>";
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Failed to load prompts:", e);
    }
}

function editPrompt(id, name, content) {
    editingPromptId = id;
    document.getElementById("prompt_name").value = name;
    document.getElementById("prompt_content").value = content;
    document.getElementById("prompt_submit_btn").innerHTML = `<i data-lucide="save" style="width: 18px; height: 18px;"></i> Сохранить`;
    document.getElementById("prompt_cancel_btn").style.display = "inline-flex";
    document.getElementById("prompt_form_title").textContent = "Редактировать промпт";
    if (window.lucide) lucide.createIcons();

    // Scroll to form inside modal body
    const form = document.getElementById("prompt_form");
    if (form) {
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    document.getElementById("prompt_name").focus();
}

function cancelEditPrompt() {
    editingPromptId = null;
    document.getElementById("prompt_name").value = '';
    document.getElementById("prompt_content").value = '';
    document.getElementById("prompt_submit_btn").innerHTML = `<i data-lucide="plus-square" style="width: 18px; height: 18px;"></i> Добавить`;
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
            showToast("Промпт успешно обновлен");
        } else {
            // Create
            data.is_active = false;
            await api("/llm/connections/" + selectedConnId + "/prompts", "POST", data);
            showToast("Промпт успешно создан");
        }
        await loadPrompts();
        cancelEditPrompt();
    } catch (e) { }
}

async function activatePrompt(id) {
    try {
        await api("/llm/prompts/" + id + "/activate", "POST");
        showToast("Промпт активирован");
        await loadPrompts();
    } catch (e) { }
}

async function deactivatePrompt(id) {
    try {
        await api("/llm/prompts/" + id + "/deactivate", "POST");
        showToast("Промпт деактивирован");
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
