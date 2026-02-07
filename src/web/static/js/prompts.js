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
