const THEME_STORAGE_KEY = "satge_theme";

function getInitialTheme() {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light") {
        return stored;
    }

    const prefersDark = window.matchMedia
        && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
}

function applyTheme(mode) {
    const isDark = mode === "dark";
    document.body.classList.toggle("theme-dark", isDark);

    document.querySelectorAll(".theme-toggle").forEach((button) => {
        button.innerText = isDark ? "Light Mode" : "Dark Mode";
        button.setAttribute("aria-pressed", isDark ? "true" : "false");
    });
}

function setupThemeToggle() {
    const toggles = document.querySelectorAll(".theme-toggle");
    if (!toggles.length) {
        return;
    }

    applyTheme(getInitialTheme());

    toggles.forEach((button) => {
        button.addEventListener("click", () => {
            const darkNow = document.body.classList.contains("theme-dark");
            const nextTheme = darkNow ? "light" : "dark";
            window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
            applyTheme(nextTheme);
        });
    });
}

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

function setupMinimalVideoControls() {
    const frame = document.getElementById("topicVideoFrame");
    const playPauseButton = document.getElementById("videoPlayPauseButton");
    const soundButton = document.getElementById("videoSoundButton");

    if (!frame || !playPauseButton || !soundButton) {
        return;
    }

    let isPlaying = false;
    let isMuted = false;

    const sendPlayerCommand = (func, args = []) => {
        frame.contentWindow.postMessage(
            JSON.stringify({
                event: "command",
                func,
                args,
            }),
            "https://www.youtube-nocookie.com"
        );
    };

    playPauseButton.addEventListener("click", () => {
        if (isPlaying) {
            sendPlayerCommand("pauseVideo");
            isPlaying = false;
            playPauseButton.innerText = "Play";
            return;
        }

        sendPlayerCommand("playVideo");
        isPlaying = true;
        playPauseButton.innerText = "Pause";
    });

    soundButton.addEventListener("click", () => {
        if (isMuted) {
            sendPlayerCommand("unMute");
            isMuted = false;
            soundButton.innerText = "Sound On";
            return;
        }

        sendPlayerCommand("mute");
        isMuted = true;
        soundButton.innerText = "Sound Off";
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

async function handleContentCreate() {
    const form = document.getElementById("contentForm");
    const status = document.getElementById("contentStatus");
    const button = form.querySelector("button[type='submit']");

    const newUnitTitle = form.elements.new_unit_title.value.trim();
    const selectedUnitSlug = form.elements.unit_slug.value.trim();
    const topicTitle = form.elements.title.value.trim();
    const topicDescription = form.elements.description.value.trim();
    const youtubeUrl = form.elements.youtube_url.value.trim();
    const noVideo = Boolean(form.elements.no_video.checked);
    const notesFile = form.elements.notes_file.files && form.elements.notes_file.files[0];

    if (!newUnitTitle && !topicTitle) {
        status.innerText = "Provide at least a new unit title or a topic title.";
        return;
    }

    status.innerText = "Creating content...";
    setButtonLoading(button, true, "Create Content", "Creating...");

    try {
        let unitSlug = selectedUnitSlug;

        if (newUnitTitle) {
            const unitResponse = await fetch("/staff/unit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: newUnitTitle }),
            });
            const unitData = await unitResponse.json();
            if (!unitResponse.ok) {
                throw new Error(unitData.error || "Unable to create unit.");
            }
            unitSlug = (unitData.unit || {}).slug || unitSlug;
        }

        if (topicTitle) {
            if (!unitSlug) {
                throw new Error("Select a unit or provide a new unit title for topic creation.");
            }

            if (!noVideo && !youtubeUrl) {
                throw new Error("Provide a YouTube link or enable 'No Video for this topic'.");
            }

            const topicFormData = new FormData();
            topicFormData.append("unit_slug", unitSlug);
            topicFormData.append("title", topicTitle);
            topicFormData.append("description", topicDescription);
            topicFormData.append("youtube_url", youtubeUrl);
            topicFormData.append("no_video", noVideo ? "true" : "false");
            if (notesFile) {
                topicFormData.append("notes_file", notesFile);
            }

            const topicResponse = await fetch("/staff/topic", {
                method: "POST",
                body: topicFormData,
            });
            const topicData = await topicResponse.json();
            if (!topicResponse.ok) {
                throw new Error(topicData.error || "Unable to create topic.");
            }
        }

        status.innerText = "Content created successfully.";
        form.reset();
        window.setTimeout(() => window.location.reload(), 700);
    } catch (error) {
        status.innerText = error.message || "Unable to create content.";
    } finally {
        setButtonLoading(button, false, "Create Content", "Creating...");
    }
}


async function handleAdminDirectorySave() {
    const form = document.getElementById("adminDirectoryForm");
    const status = document.getElementById("adminDirectoryStatus");
    const button = form.querySelector("button[type='submit']");
    const payload = {
        section: form.elements.section.value.trim(),
        name: form.elements.name.value.trim(),
        details: form.elements.details.value.trim(),
    };

    status.innerText = "Saving entry...";
    setButtonLoading(button, true, "Add Entry", "Saving...");

    try {
        const response = await fetch("/admin/directory", {
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
        status.innerText = "Unable to save entry.";
    } finally {
        setButtonLoading(button, false, "Add Entry", "Saving...");
    }
}

async function handleTextContentSave() {
    const form = document.getElementById("textContentForm");
    const status = document.getElementById("textContentStatus");
    const button = form.querySelector("button[type='submit']");
    const extraFields = [];
    document.querySelectorAll(".extra-field-row").forEach((row) => {
        const label = (row.querySelector(".extra-field-label") || {}).value || "";
        const value = (row.querySelector(".extra-field-value") || {}).value || "";
        if (label.trim() || value.trim()) {
            extraFields.push({
                label: label.trim(),
                value: value.trim(),
            });
        }
    });

    const relatedUrls = [];
    document.querySelectorAll(".related-url-row").forEach((row) => {
        const title = (row.querySelector(".related-url-title") || {}).value || "";
        const url = (row.querySelector(".related-url-value") || {}).value || "";
        if (title.trim() || url.trim()) {
            relatedUrls.push({
                title: title.trim(),
                url: url.trim(),
            });
        }
    });

    const images = [];
    document.querySelectorAll(".image-ref-row").forEach((row) => {
        const title = (row.querySelector(".image-ref-title") || {}).value || "";
        const url = (row.querySelector(".image-ref-url") || {}).value || "";
        if (title.trim() || url.trim()) {
            images.push({
                title: title.trim(),
                url: url.trim(),
            });
        }
    });

    const payload = {
        topic_slug: form.elements.topic_slug.value.trim(),
        explanation: form.elements.explanation.value.trim(),
        example: form.elements.example.value.trim(),
        analogy: form.elements.analogy.value.trim(),
        extra_fields: extraFields,
        related_urls: relatedUrls,
        images,
    };

    status.innerText = "Saving text content...";
    setButtonLoading(button, true, "Save Text Content", "Saving...");

    try {
        const response = await fetch("/staff/text-content", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        status.innerText = data.message || data.error || "Request finished.";
        if (response.ok) {
            form.reset();
        }
    } catch (error) {
        status.innerText = "Unable to save text content.";
    } finally {
        setButtonLoading(button, false, "Save Text Content", "Saving...");
    }
}

function buildDynamicRow(className, firstClass, firstPlaceholder, secondClass, secondPlaceholder) {
    const row = document.createElement("div");
    row.className = `dynamic-row ${className}`;

    const first = document.createElement("input");
    first.type = "text";
    first.className = firstClass;
    first.placeholder = firstPlaceholder;

    const second = document.createElement("input");
    second.type = "text";
    second.className = secondClass;
    second.placeholder = secondPlaceholder;

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "secondary-btn";
    removeButton.innerText = "Remove";
    removeButton.addEventListener("click", () => row.remove());

    row.appendChild(first);
    row.appendChild(second);
    row.appendChild(removeButton);

    return row;
}

function setupTextContentBuilder() {
    const extraFieldsContainer = document.getElementById("extraFieldsContainer");
    const relatedUrlsContainer = document.getElementById("relatedUrlsContainer");
    const addExtraFieldButton = document.getElementById("addExtraFieldButton");
    const addRelatedUrlButton = document.getElementById("addRelatedUrlButton");
    const imageRefsContainer = document.getElementById("imageRefsContainer");
    const addImageRefButton = document.getElementById("addImageRefButton");
    const uploadTextImageButton = document.getElementById("uploadTextImageButton");
    const textImageTitle = document.getElementById("textImageTitle");
    const textImageFile = document.getElementById("textImageFile");
    const textImageUploadStatus = document.getElementById("textImageUploadStatus");

    if (
        !extraFieldsContainer || !relatedUrlsContainer || !imageRefsContainer
        || !addExtraFieldButton || !addRelatedUrlButton || !addImageRefButton
        || !uploadTextImageButton || !textImageTitle || !textImageFile || !textImageUploadStatus
    ) {
        return;
    }

    const addExtraFieldRow = () => {
        extraFieldsContainer.appendChild(
            buildDynamicRow(
                "extra-field-row",
                "extra-field-label",
                "Field Label",
                "extra-field-value",
                "Field Value"
            )
        );
    };

    const addRelatedUrlRow = () => {
        relatedUrlsContainer.appendChild(
            buildDynamicRow(
                "related-url-row",
                "related-url-title",
                "URL Title (optional)",
                "related-url-value",
                "https://example.com/reference"
            )
        );
    };

    const addImageRefRow = (preset = {}) => {
        const row = buildDynamicRow(
            "image-ref-row",
            "image-ref-title",
            "Image Title (optional)",
            "image-ref-url",
            "https://example.com/image.png"
        );

        const titleInput = row.querySelector(".image-ref-title");
        const urlInput = row.querySelector(".image-ref-url");
        if (titleInput) {
            titleInput.value = preset.title || "";
        }
        if (urlInput) {
            urlInput.value = preset.url || "";
        }

        imageRefsContainer.appendChild(row);
    };

    addExtraFieldButton.addEventListener("click", addExtraFieldRow);
    addRelatedUrlButton.addEventListener("click", addRelatedUrlRow);
    addImageRefButton.addEventListener("click", () => addImageRefRow());

    uploadTextImageButton.addEventListener("click", async () => {
        const file = textImageFile.files && textImageFile.files[0];
        if (!file) {
            textImageUploadStatus.innerText = "Select an image to upload.";
            return;
        }

        const formData = new FormData();
        formData.append("image_file", file);
        formData.append("title", (textImageTitle.value || "").trim());

        setButtonLoading(uploadTextImageButton, true, "Upload", "Uploading...");
        textImageUploadStatus.innerText = "Uploading image...";

        try {
            const response = await fetch("/staff/text-content/image", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Unable to upload image.");
            }

            addImageRefRow(data.image || {});
            textImageTitle.value = "";
            textImageFile.value = "";
            textImageUploadStatus.innerText = data.message || "Image uploaded.";
        } catch (error) {
            textImageUploadStatus.innerText = error.message || "Unable to upload image.";
        } finally {
            setButtonLoading(uploadTextImageButton, false, "Upload", "Uploading...");
        }
    });

    addExtraFieldRow();
    addRelatedUrlRow();
    addImageRefRow();
}

function renderDmMessages(messages) {
    const dmMessages = document.getElementById("dmMessages");
    const currentUserId = Number(document.body.dataset.userId || 0);
    if (!dmMessages) {
        return;
    }

    dmMessages.innerHTML = "";
    if (!Array.isArray(messages) || !messages.length) {
        const empty = document.createElement("div");
        empty.className = "placeholder-copy";
        empty.innerText = "No messages yet. Start the conversation.";
        dmMessages.appendChild(empty);
        return;
    }

    messages.forEach((entry) => {
        const role = Number(entry.sender_id) === currentUserId ? "user" : "assistant";
        const card = createMessageCard(role, `${entry.sender_name} · ${entry.sender_role}`);
        appendTextBlock(card, "message-body", entry.message);
        appendTextBlock(card, "follow-up", formatSavedTime(entry.created_at));
        dmMessages.appendChild(card);
    });

    dmMessages.scrollTop = dmMessages.scrollHeight;
}

function renderDmContacts(contacts, onSelect) {
    const container = document.getElementById("dmContacts");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (!Array.isArray(contacts) || !contacts.length) {
        const empty = document.createElement("div");
        empty.className = "placeholder-copy";
        empty.innerText = "No contacts available.";
        container.appendChild(empty);
        return;
    }

    contacts.forEach((contact, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "dm-contact-item";
        button.dataset.contactId = String(contact.id);
        button.innerHTML = `<strong>${contact.name}</strong><span>${contact.role}</span>`;
        button.addEventListener("click", () => onSelect(contact));
        container.appendChild(button);

        if (index === 0) {
            onSelect(contact);
        }
    });
}

async function loadDmThread(contactId) {
    const response = await fetch(`/dm/thread/${contactId}`);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Unable to load messages.");
    }
    return data;
}

async function initDmPage() {
    const dmStatus = document.getElementById("dmStatus");
    const dmChatTitle = document.getElementById("dmChatTitle");
    const dmSendButton = document.getElementById("dmSendButton");
    const dmInput = document.getElementById("dmInput");

    if (!dmStatus || !dmChatTitle || !dmSendButton || !dmInput) {
        return;
    }

    let activeContact = null;

    const selectContact = async (contact) => {
        activeContact = contact;
        dmChatTitle.innerText = `${contact.name} (${contact.role})`;
        dmSendButton.disabled = false;

        document.querySelectorAll(".dm-contact-item").forEach((item) => {
            item.classList.toggle("is-active", Number(item.dataset.contactId) === Number(contact.id));
        });

        dmStatus.innerText = "Loading";
        try {
            const payload = await loadDmThread(contact.id);
            renderDmMessages(payload.messages || []);
            dmStatus.innerText = "Ready";
        } catch (error) {
            renderDmMessages([]);
            dmStatus.innerText = "Retry";
        }
    };

    dmStatus.innerText = "Loading";
    try {
        const response = await fetch("/dm/contacts");
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Unable to load contacts.");
        }

        renderDmContacts(data.contacts || [], selectContact);
        dmStatus.innerText = "Ready";
    } catch (error) {
        dmStatus.innerText = "Retry";
        renderDmContacts([], () => {});
    }

    dmSendButton.addEventListener("click", async () => {
        if (!activeContact) {
            return;
        }

        const message = dmInput.value.trim();
        if (!message) {
            return;
        }

        setButtonLoading(dmSendButton, true, "Send Message", "Sending...");
        dmStatus.innerText = "Sending";

        try {
            const response = await fetch(`/dm/thread/${activeContact.id}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message }),
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to send message.");
            }

            dmInput.value = "";
            const payload = await loadDmThread(activeContact.id);
            renderDmMessages(payload.messages || []);
            dmStatus.innerText = "Ready";
        } catch (error) {
            dmStatus.innerText = "Retry";
            alert(error.message || "Unable to send message.");
        } finally {
            setButtonLoading(dmSendButton, false, "Send Message", "Sending...");
        }
    });

    dmInput.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            dmSendButton.click();
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();

    const page = document.body.dataset.page;

    if (page === "topic") {
        const topic = document.body.dataset.topic;
        loadStudentNotes(topic);
        setupMinimalVideoControls();

        const watchVideoTopButton = document.getElementById("watchVideoTopButton");
        const readNotesTopButton = document.getElementById("readNotesTopButton");

        if (watchVideoTopButton && readNotesTopButton) {
            const setTopSwitchState = (activeButton) => {
                watchVideoTopButton.classList.toggle("is-active", activeButton === "video");
                readNotesTopButton.classList.toggle("is-active", activeButton === "notes");
            };

            if (watchVideoTopButton.disabled) {
                setTopSwitchState("notes");
            }

            watchVideoTopButton.addEventListener("click", () => {
                activateTab("overviewTab");
                setTopSwitchState("video");
                const frame = document.querySelector(".player-frame");
                if (frame) {
                    frame.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });

            readNotesTopButton.addEventListener("click", () => {
                activateTab("notesTab");
                setTopSwitchState("notes");
            });

            document.querySelectorAll(".player-tab").forEach((tab) => {
                tab.addEventListener("click", () => {
                    if (tab.dataset.tabTarget === "notesTab") {
                        setTopSwitchState("notes");
                    } else if (tab.dataset.tabTarget === "overviewTab") {
                        setTopSwitchState("video");
                    }
                });
            });
        }

        document.querySelectorAll(".player-tab").forEach((tab) => {
            tab.addEventListener("click", () => activateTab(tab.dataset.tabTarget));
        });

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

        document.getElementById("contentForm").addEventListener("submit", (event) => {
            event.preventDefault();
            handleContentCreate();
        });

        document.getElementById("uploadForm").addEventListener("submit", (event) => {
            event.preventDefault();
            handleUpload();
        });

        const textContentForm = document.getElementById("textContentForm");
        if (textContentForm) {
            setupTextContentBuilder();
            textContentForm.addEventListener("submit", (event) => {
                event.preventDefault();
                handleTextContentSave();
            });
        }

    }

    if (page === "admin") {
        const form = document.getElementById("adminDirectoryForm");
        if (form) {
            form.addEventListener("submit", (event) => {
                event.preventDefault();
                handleAdminDirectorySave();
            });
        }
    }

    if (page === "dm") {
        initDmPage();
    }
});
