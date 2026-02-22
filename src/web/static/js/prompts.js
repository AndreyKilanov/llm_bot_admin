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
        const list = document.getElementById("prompts_list");
        list.innerHTML = "";

        if (prompts.length === 0) {
            list.innerHTML = "<p class='text-secondary text-center p-8'>Промптов пока нет. Добавьте свой первый промпт ниже.</p>";
            return;
        }

        const template = document.getElementById("prompt_card_template");

        prompts.forEach(p => {
            const clone = template.content.cloneNode(true);
            const card = clone.querySelector(".prompt-card");

            if (p.is_active) card.classList.add("active");

            clone.querySelector(".prompt-name").textContent = p.name;
            clone.querySelector(".prompt-preview").textContent = p.content;

            const statusBadge = clone.querySelector(".prompt-status-badge");
            if (!p.is_active) statusBadge.remove();

            const editBtn = clone.querySelector(".edit-btn");
            editBtn.onclick = () => editPrompt(p.id, p.name, p.content);

            const deleteBtn = clone.querySelector(".delete-btn");
            deleteBtn.onclick = () => deletePrompt(p.id);

            const activateBtn = clone.querySelector(".activate-btn");
            const deactivateBtn = clone.querySelector(".deactivate-btn");

            if (p.is_active) {
                deactivateBtn.style.display = "inline-flex";
                deactivateBtn.onclick = (e) => { e.stopPropagation(); deactivatePrompt(p.id); };
                activateBtn.remove();
            } else {
                activateBtn.style.display = "inline-flex";
                activateBtn.onclick = (e) => { e.stopPropagation(); activatePrompt(p.id); };
                deactivateBtn.remove();
            }

            list.appendChild(clone);
        });

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Failed to load prompts:", e);
    }
}

function editPrompt(id, name, content) {
    editingPromptId = id;
    document.getElementById("prompt_name").value = name;
    document.getElementById("prompt_content").value = content;

    const submitBtn = document.getElementById("prompt_submit_btn");
    submitBtn.textContent = 'Сохранить';

    document.getElementById("prompt_cancel_btn").classList.remove("hidden");
    document.getElementById("prompt_form_title").textContent = "Изменить промпт";
    if (window.lucide) lucide.createIcons();

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

    const submitBtn = document.getElementById("prompt_submit_btn");
    submitBtn.textContent = 'Добавить';

    document.getElementById("prompt_cancel_btn").classList.add("hidden");
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
