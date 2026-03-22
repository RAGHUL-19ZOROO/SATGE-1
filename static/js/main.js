const chatState = new Map();

function setStatus(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerText = text;
    }
}

function setButtonLoading(button, isLoading, idleText, loadingText) {
    if (!button) {
        return;
    }
    button.disabled = isLoading;
    button.innerText = isLoading ? loadingText : idleText;
}

function formatSavedTime(value) {
    if (!value) {
        return "";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "";
    }

    return date.toLocaleString();
}

function activateTab(targetId) {
    document.querySelectorAll(".player-tab").forEach((tab) => {
        tab.classList.toggle("is-active", tab.dataset.tabTarget === targetId);
    });

    document.querySelectorAll(".player-tab-panel").forEach((panel) => {
        panel.classList.toggle("is-active", panel.id === targetId);
    });
}

function fillList(elementId, items) {
    const element = document.getElementById(elementId);
    if (!element) {
        return;
    }

    element.innerHTML = "";
    if (!Array.isArray(items) || !items.length) {
        const li = document.createElement("li");
        li.innerText = "No content available yet.";
        element.appendChild(li);
        return;
    }

    items.forEach((item) => {
        const li = document.createElement("li");
        li.innerText = item;
        element.appendChild(li);
    });
}

function createMessageCard(role, title) {
    const card = document.createElement("article");
    card.className = `message-card ${role}`;

    const header = document.createElement("div");
    header.className = "message-head";
    header.innerHTML = `<span>${title}</span>`;
    card.appendChild(header);
    return card;
}

function appendTextBlock(parent, className, text) {
    if (!text) {
        return;
    }

    const block = document.createElement("div");
    block.className = className;
    block.innerText = text;
    parent.appendChild(block);
}

function appendList(parent, title, items, className) {
    if (!Array.isArray(items) || !items.length) {
        return;
    }

    const heading = document.createElement("h4");
    heading.className = "section-title";
    heading.innerText = title;
    parent.appendChild(heading);

    const list = document.createElement("ul");
    list.className = className;

    items.forEach((item) => {
        const li = document.createElement("li");
        li.innerText = item;
        list.appendChild(li);
    });

    parent.appendChild(list);
}

function appendSources(parent, sources) {
    if (!Array.isArray(sources) || !sources.length) {
        return;
    }

    const heading = document.createElement("h4");
    heading.className = "section-title";
    heading.innerText = "Sources";
    parent.appendChild(heading);

    const list = document.createElement("div");
    list.className = "source-list";

    sources.forEach((source) => {
        const link = document.createElement("a");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.innerText = source.title || source.url;
        list.appendChild(link);
    });

    parent.appendChild(list);
}

function appendImages(parent, images) {
    if (!Array.isArray(images) || !images.length) {
        return;
    }

    const heading = document.createElement("h4");
    heading.className = "section-title";
    heading.innerText = "Visual References";
    parent.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "image-grid";

    images.forEach((image) => {
        const card = document.createElement("a");
        card.className = "image-card";
        card.href = image.source_url;
        card.target = "_blank";
        card.rel = "noopener noreferrer";

        const img = document.createElement("img");
        img.src = image.image_url;
        img.alt = image.title || "Reference image";

        const caption = document.createElement("span");
        caption.innerText = image.title || "Reference";

        card.appendChild(img);
        card.appendChild(caption);
        grid.appendChild(card);
    });

    parent.appendChild(grid);
}

function getChatStorageKey(topic) {
    return topic;
}

function renderChatHistory(topic) {
    const chat = document.getElementById("chatHistory");
    if (!chat) {
        return;
    }

    chat.innerHTML = "";
    const history = chatState.get(getChatStorageKey(topic)) || [];
    if (!history.length) {
        const empty = document.createElement("div");
        empty.className = "placeholder-copy";
        empty.innerText = "Your doubt history will appear here.";
        chat.appendChild(empty);
        return;
    }

    history.forEach((entry) => {
        const card = createMessageCard(entry.role, entry.title);
        appendTextBlock(card, "message-body", entry.body);
        appendTextBlock(card, "message-body", entry.example ? `Example: ${entry.example}` : "");
        appendList(card, "Key Points", entry.key_points, "chip-list");
        appendList(card, "Flow Steps", entry.flow_steps, "step-list");
        appendTextBlock(card, "follow-up", entry.follow_up_tip ? `Next step: ${entry.follow_up_tip}` : "");
        appendImages(card, entry.images);
        appendSources(card, entry.sources);
        chat.appendChild(card);
    });

    chat.scrollTop = chat.scrollHeight;
}

function saveChatEntry(topic, entry) {
    const history = [...(chatState.get(getChatStorageKey(topic)) || [])];
    history.push(entry);
    chatState.set(getChatStorageKey(topic), history);
    renderChatHistory(topic);
}

async function loadStudentNotes(topic) {
    const input = document.getElementById("studentNotesInput");
    const status = document.getElementById("studentNotesStatus");
    const meta = document.getElementById("studentNotesMeta");

    if (!input || !status || !meta) {
        return;
    }

    status.innerText = "Loading";
    meta.innerText = "Fetching your notes...";

    try {
        const response = await fetch(`/student-notes/${topic}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to load your notes.");
        }

        input.value = data.notes || "";
        status.innerText = "Ready";
        meta.innerText = data.updated_at
            ? `Last saved: ${formatSavedTime(data.updated_at)}`
            : "No saved notes yet.";
    } catch (error) {
        status.innerText = "Retry";
        meta.innerText = error.message || "Unable to load your notes.";
    }
}

async function saveStudentNotes(topic) {
    const input = document.getElementById("studentNotesInput");
    const button = document.getElementById("saveStudentNotesButton");
    const status = document.getElementById("studentNotesStatus");
    const meta = document.getElementById("studentNotesMeta");

    if (!input || !button || !status || !meta) {
        return;
    }

    setButtonLoading(button, true, "Save My Notes", "Saving...");
    status.innerText = "Saving";
    meta.innerText = "Saving your notes...";

    try {
        const response = await fetch(`/student-notes/${topic}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: input.value }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to save your notes.");
        }

        status.innerText = "Saved";
        meta.innerText = data.updated_at
            ? `Last saved: ${formatSavedTime(data.updated_at)}`
            : "Your notes have been saved.";
    } catch (error) {
        status.innerText = "Retry";
        meta.innerText = error.message || "Unable to save your notes.";
    } finally {
        setButtonLoading(button, false, "Save My Notes", "Saving...");
    }
}

function renderMcqs(mcqs) {
    const testForm = document.getElementById("testForm");
    const submitButton = document.getElementById("submitTestButton");
    if (!testForm) {
        return;
    }

    testForm.innerHTML = "";

    mcqs.forEach((mcq, index) => {
        const card = document.createElement("article");
        card.className = "mcq-card";

        const question = document.createElement("h3");
        question.innerText = `${index + 1}. ${mcq.question}`;
        card.appendChild(question);

        const options = document.createElement("div");
        options.className = "options-grid";

        Object.entries(mcq.options).forEach(([key, value]) => {
            const label = document.createElement("label");
            label.className = "option-pill";

            const input = document.createElement("input");
            input.type = "radio";
            input.name = mcq.id;
            input.value = key;

            const text = document.createElement("span");
            text.innerText = `${key}. ${value}`;

            label.appendChild(input);
            label.appendChild(text);
            options.appendChild(label);
        });

        card.appendChild(options);
        testForm.appendChild(card);
    });

    submitButton.disabled = false;
}

function renderResults(result) {
    document.getElementById("resultPanel").classList.remove("hidden");
    document.getElementById("scoreBadge").innerText = `${result.percentage}%`;
    document.getElementById("scoreText").innerText = `${result.score} / ${result.total}`;
    document.getElementById("feedbackText").innerText = result.feedback;

    const breakdown = document.getElementById("resultBreakdown");
    breakdown.innerHTML = "";

    result.results.forEach((item) => {
        const card = document.createElement("article");
        card.className = `result-item ${item.is_correct ? "correct" : "wrong"}`;
        card.innerHTML = `
            <h4>${item.question}</h4>
            <p>Selected: ${item.selected_answer || "No answer"}</p>
            <p>Correct: ${item.correct_answer}</p>
            <p>${item.explanation}</p>
        `;
        breakdown.appendChild(card);
    });
}

async function loadLearningPackage(topic) {
    const learnButton = document.getElementById("learnButton");
    setButtonLoading(learnButton, true, "Learn", "Loading...");
    setStatus("learnStatus", "Generating...");

    try {
        const response = await fetch("/learn", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to generate lesson package.");
        }

        document.getElementById("explanation").innerText = data.explanation;
        fillList("keyPoints", data.key_points);
        fillList("examples", data.examples);
        fillList("flowchart", data.flowchart);
        fillList("examNotes", data.exam_notes);
        renderMcqs(data.mcqs || []);
        setStatus("learnStatus", "Ready");
        setStatus("testStatus", "Quiz Ready");
    } catch (error) {
        document.getElementById("explanation").innerText = error.message;
        setStatus("learnStatus", "Retry");
    } finally {
        setButtonLoading(learnButton, false, "Learn", "Loading...");
    }
}

async function askDoubt(topic) {
    const input = document.getElementById("questionInput");
    const question = input.value.trim();
    const askButton = document.getElementById("askButton");

    if (!question) {
        return;
    }

    saveChatEntry(topic, {
        role: "user",
        title: "You",
        body: question,
    });
    input.value = "";
    setStatus("agentStatus", "Thinking...");
    setButtonLoading(askButton, true, "Ask Doubt Agent", "Thinking...");

    try {
        const response = await fetch("/doubt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic, question }),
        });
        const data = await response.json();

        saveChatEntry(topic, {
            role: "assistant",
            title: data.in_scope === false ? "Doubt Agent - Refocused" : "Doubt Agent",
            body: data.answer || data.error || "Unable to answer right now.",
            example: data.example,
            key_points: data.key_points || [],
            flow_steps: data.flow_steps || [],
            follow_up_tip: data.follow_up_tip || "",
            images: data.images || [],
            sources: data.sources || [],
        });
        setStatus("agentStatus", response.ok ? "Ready" : "Retry");
    } catch (error) {
        saveChatEntry(topic, {
            role: "assistant",
            title: "Doubt Agent",
            body: "Unable to answer right now.",
        });
        setStatus("agentStatus", "Retry");
    } finally {
        setButtonLoading(askButton, false, "Ask Doubt Agent", "Thinking...");
    }
}

async function submitTest(topic) {
    const submitButton = document.getElementById("submitTestButton");
    setButtonLoading(submitButton, true, "Submit Test", "Checking...");
    setStatus("testStatus", "Evaluating...");

    const answers = {};
    document.querySelectorAll("#testForm input[type='radio']:checked").forEach((input) => {
        answers[input.name] = input.value;
    });

    try {
        const response = await fetch("/test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic, answers }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to evaluate test.");
        }

        renderResults(data);
        setStatus("testStatus", "Completed");
    } catch (error) {
        setStatus("testStatus", "Retry");
        alert(error.message);
    } finally {
        setButtonLoading(submitButton, false, "Submit Test", "Checking...");
    }
}

async function handleUpload() {
    const form = document.getElementById("uploadForm");
    const status = document.getElementById("uploadStatus");
    const formData = new FormData(form);

    status.innerText = "Uploading...";

    try {
        const response = await fetch("/upload", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        status.innerText = data.message || data.error || "Upload finished.";
        if (response.ok) {
            form.reset();
        }
    } catch (error) {
        status.innerText = "Upload failed.";
    }
}

async function handleUnitCreate() {
    const form = document.getElementById("unitForm");
    const status = document.getElementById("unitStatus");
    const button = form.querySelector("button[type='submit']");
    const payload = {
        title: form.elements.title.value.trim(),
    };

    status.innerText = "Creating unit...";
    setButtonLoading(button, true, "Create Unit", "Creating...");

    try {
        const response = await fetch("/staff/unit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        status.innerText = data.message || data.error || "Request finished.";
        if (response.ok) {
            form.reset();
            window.setTimeout(() => window.location.reload(), 700);
        }
    } catch (error) {
        status.innerText = "Unable to create unit.";
    } finally {
        setButtonLoading(button, false, "Create Unit", "Creating...");
    }
}

async function handleTopicCreate() {
    const form = document.getElementById("topicForm");
    const status = document.getElementById("topicStatus");
    const button = form.querySelector("button[type='submit']");
    const formData = new FormData(form);

    status.innerText = "Creating topic...";
    setButtonLoading(button, true, "Create Topic", "Creating...");

    try {
        const response = await fetch("/staff/topic", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        status.innerText = data.message || data.error || "Request finished.";
        if (response.ok) {
            form.reset();
            window.setTimeout(() => window.location.reload(), 700);
        }
    } catch (error) {
        status.innerText = "Unable to create topic.";
    } finally {
        setButtonLoading(button, false, "Create Topic", "Creating...");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;

    if (page === "topic") {
        const topic = document.body.dataset.topic;
        renderChatHistory(topic);
        loadStudentNotes(topic);

        document.querySelectorAll(".player-tab").forEach((tab) => {
            tab.addEventListener("click", () => activateTab(tab.dataset.tabTarget));
        });

        document.getElementById("learnButton").addEventListener("click", () => loadLearningPackage(topic));
        document.getElementById("askButton").addEventListener("click", () => askDoubt(topic));
        document.getElementById("submitTestButton").addEventListener("click", () => submitTest(topic));
        const saveStudentNotesButton = document.getElementById("saveStudentNotesButton");
        const studentNotesInput = document.getElementById("studentNotesInput");
        const studentNotesStatus = document.getElementById("studentNotesStatus");
        const studentNotesMeta = document.getElementById("studentNotesMeta");

        if (saveStudentNotesButton) {
            saveStudentNotesButton.addEventListener("click", () => saveStudentNotes(topic));
        }

        if (studentNotesInput && studentNotesStatus && studentNotesMeta) {
            studentNotesInput.addEventListener("input", () => {
                studentNotesStatus.innerText = "Editing";
                studentNotesMeta.innerText = "Unsaved changes.";
            });
        }

        document.getElementById("questionInput").addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                askDoubt(topic);
            }
        });
    }

    if (page === "staff") {
        const noVideoCheckbox = document.getElementById("noVideo");
        const youtubeInput = document.getElementById("youtubeUrl");

        if (noVideoCheckbox && youtubeInput) {
            const syncVideoRequirement = () => {
                youtubeInput.disabled = noVideoCheckbox.checked;
                youtubeInput.required = !noVideoCheckbox.checked;
                if (noVideoCheckbox.checked) {
                    youtubeInput.value = "";
                    youtubeInput.placeholder = "Video disabled for this topic";
                } else {
                    youtubeInput.placeholder = "https://www.youtube.com/watch?v=...";
                }
            };

            noVideoCheckbox.addEventListener("change", syncVideoRequirement);
            syncVideoRequirement();
        }

        document.getElementById("unitForm").addEventListener("submit", (event) => {
            event.preventDefault();
            handleUnitCreate();
        });

        document.getElementById("topicForm").addEventListener("submit", (event) => {
            event.preventDefault();
            handleTopicCreate();
        });

        document.getElementById("uploadForm").addEventListener("submit", (event) => {
            event.preventDefault();
            handleUpload();
        });
    }
});
