/**
 * Truth Shield MVP - Interactive Frontend Logic
 * Handles tabs, drag-and-drop, validation, scanning radar, and forensic viewer.
 */

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initFileUploads();
    initPresetButtons();
    initForensicForms();
    initReportViewer();
});

/* ==========================================================================
   Tab Navigation System
   ========================================================================== */

function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const navButtons = document.querySelectorAll(".nav-btn[data-tab]");

    function switchTab(targetId) {
        tabButtons.forEach(btn => {
            const isMatch = btn.getAttribute("data-target") === targetId;
            btn.classList.toggle("active", isMatch);
            btn.setAttribute("aria-selected", isMatch ? "true" : "false");
        });

        tabPanels.forEach(panel => {
            panel.classList.toggle("active", panel.id === targetId);
        });

        navButtons.forEach(btn => {
            const mappedTarget = btn.getAttribute("data-tab").replace("-tab", "-panel");
            btn.classList.toggle("active", mappedTarget === targetId);
        });
    }

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-target");
            switchTab(target);
        });
    });

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const panelId = btn.getAttribute("data-tab").replace("-tab", "-panel");
            switchTab(panelId);
            const terminal = document.querySelector(".terminal-card");
            if (terminal) {
                terminal.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });
}

/* ==========================================================================
   File Drag & Drop and Preview Handlers
   ========================================================================== */

function initFileUploads() {
    // --- Image Dropzone ---
    const imageDropzone = document.getElementById("image-dropzone");
    const imageInput = document.getElementById("image-file-input");
    const imagePrompt = document.getElementById("image-drop-prompt");
    const imagePreviewCard = document.getElementById("image-preview-card");
    const imagePreviewElem = document.getElementById("image-preview-element");
    const imageNameElem = document.getElementById("image-file-name");
    const imageSizeElem = document.getElementById("image-file-size");
    const removeImageBtn = document.getElementById("remove-image-btn");

    if (imageDropzone && imageInput) {
        setupDragEvents(imageDropzone);

        imageInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) handleImageFileSelection(file);
        });

        imageDropzone.addEventListener("drop", (e) => {
            const file = e.dataTransfer.files[0];
            if (file) {
                imageInput.files = e.dataTransfer.files;
                handleImageFileSelection(file);
            }
        });

        if (removeImageBtn) {
            removeImageBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                imageInput.value = "";
                imagePreviewCard.style.display = "none";
                imagePrompt.style.display = "block";
            });
        }
    }

    function handleImageFileSelection(file) {
        // Validate type
        const validTypes = ["image/jpeg", "image/png", "image/webp", "image/bmp"];
        if (!validTypes.includes(file.type)) {
            alert("Please select a valid image file (JPG, PNG, or WEBP).");
            imageInput.value = "";
            return;
        }

        // Validate size (16MB)
        if (file.size > 16 * 1024 * 1024) {
            alert("Image size exceeds the 16MB limit. Please choose a smaller file.");
            imageInput.value = "";
            return;
        }

        // Render preview
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreviewElem.src = e.target.result;
            imageNameElem.textContent = file.name;
            imageSizeElem.textContent = formatBytes(file.size);
            imagePrompt.style.display = "none";
            imagePreviewCard.style.display = "flex";
        };
        reader.readAsDataURL(file);
    }

    // --- Video Dropzone ---
    const videoDropzone = document.getElementById("video-dropzone");
    const videoInput = document.getElementById("video-file-input");
    const videoPrompt = document.getElementById("video-drop-prompt");
    const videoPreviewCard = document.getElementById("video-preview-card");
    const videoPreviewElem = document.getElementById("video-preview-element");
    const videoNameElem = document.getElementById("video-file-name");
    const videoSizeElem = document.getElementById("video-file-size");
    const removeVideoBtn = document.getElementById("remove-video-btn");

    if (videoDropzone && videoInput) {
        setupDragEvents(videoDropzone);

        videoInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) handleVideoFileSelection(file);
        });

        videoDropzone.addEventListener("drop", (e) => {
            const file = e.dataTransfer.files[0];
            if (file) {
                videoInput.files = e.dataTransfer.files;
                handleVideoFileSelection(file);
            }
        });

        if (removeVideoBtn) {
            removeVideoBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                videoInput.value = "";
                videoPreviewElem.pause();
                videoPreviewElem.removeAttribute("src");
                videoPreviewCard.style.display = "none";
                videoPrompt.style.display = "block";
            });
        }
    }

    function handleVideoFileSelection(file) {
        // Validate type
        const validVideoTypes = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"];
        if (!validVideoTypes.includes(file.type) && !file.name.match(/\.(mp4|mov|avi|webm)$/i)) {
            alert("Please select a supported video format (MP4, MOV, or WEBM).");
            videoInput.value = "";
            return;
        }

        // Validate size (50MB)
        if (file.size > 50 * 1024 * 1024) {
            alert("Video file size exceeds the 50MB limit.");
            videoInput.value = "";
            return;
        }

        const objectUrl = URL.createObjectURL(file);
        videoPreviewElem.src = objectUrl;
        videoNameElem.textContent = file.name;
        videoSizeElem.textContent = formatBytes(file.size);
        videoPrompt.style.display = "none";
        videoPreviewCard.style.display = "flex";
    }

    function setupDragEvents(dropzone) {
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            });
        });
    }

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + " B";
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        else return (bytes / 1048576).toFixed(2) + " MB";
    }
}

/* ==========================================================================
   Preset Demo Samples (1-Click Verification)
   ========================================================================== */

function initPresetButtons() {
    const presetButtons = document.querySelectorAll(".preset-btn[data-demo]");

    presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const demoType = btn.getAttribute("data-demo");

            if (demoType === "news_mars") {
                const claimInput = document.getElementById("claim-input");
                if (claimInput) {
                    claimInput.value = "NASA discovers alien city on Mars with pyramids and canals";
                    claimInput.focus();
                }
            } else if (demoType === "news_ev") {
                const claimInput = document.getElementById("claim-input");
                if (claimInput) {
                    claimInput.value = "Electric vehicles catch fire 10 times more frequently than gasoline cars";
                    claimInput.focus();
                }
            } else {
                // Send directly to demo processing
                runForensicScanSimulation("Investigating Preset Sample Media...", () => {
                    const formData = new FormData();
                    formData.append("sample_type", demoType);

                    fetch("/analyze/demo", {
                        method: "POST",
                        body: formData,
                        headers: { "X-Requested-With": "XMLHttpRequest" }
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.redirect_url) {
                            window.location.href = data.redirect_url;
                        } else if (data.error) {
                            hideScanningModal();
                            alert(data.error);
                        }
                    })
                    .catch(err => {
                        hideScanningModal();
                        console.error(err);
                        alert("An error occurred during verification.");
                    });
                });
            }
        });
    });
}

/* ==========================================================================
   Forensic Scanning Modal & Async Submission
   ========================================================================== */

const modal = document.getElementById("scanning-modal");
const modalTitle = document.getElementById("scan-modal-title");
const modalStepText = document.getElementById("scan-step-text");
const progressBar = document.getElementById("scan-progress-bar");
const terminalLogs = document.getElementById("scan-terminal-logs");

function showScanningModal(title) {
    if (!modal) return;
    if (title && modalTitle) modalTitle.textContent = title;
    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");
}

function hideScanningModal() {
    if (!modal) return;
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
}

function runForensicScanSimulation(title, onReady) {
    showScanningModal(title);
    if (!progressBar || !terminalLogs || !modalStepText) {
        if (onReady) onReady();
        return;
    }

    progressBar.style.width = "20%";
    terminalLogs.innerHTML = "<div class='log-line'>▸ Validating input headers & container integrity...</div>";
    modalStepText.textContent = "Verifying payload structure...";

    setTimeout(() => {
        progressBar.style.width = "55%";
        terminalLogs.innerHTML += "<div class='log-line'>▸ Running compression / fact-check cross-referencing...</div>";
        modalStepText.textContent = "Synthesizing empirical evidence...";
    }, 600);

    setTimeout(() => {
        progressBar.style.width = "85%";
        terminalLogs.innerHTML += "<div class='log-line'>▸ Computing localized variance & confidence score...</div>";
        modalStepText.textContent = "Finalizing evidence dossier...";
        if (onReady) onReady();
    }, 1200);
}

function initForensicForms() {
    const forms = [
        { formId: "news-form", title: "Verifying News Claim & Fact Archives" },
        { formId: "image-form", title: "Running Error Level Analysis (ELA) & EXIF Scan" },
        { formId: "video-form", title: "Analyzing Temporal Continuity & Frame Deltas" }
    ];

    forms.forEach(({ formId, title }) => {
        const formElem = document.getElementById(formId);
        if (!formElem) return;

        formElem.addEventListener("submit", (e) => {
            e.preventDefault();

            // Client-side quick check
            if (formId === "news-form") {
                const claimVal = document.getElementById("claim-input").value.trim();
                if (!claimVal) {
                    alert("Please enter a claim to investigate.");
                    return;
                }
            }

            const formData = new FormData(formElem);

            runForensicScanSimulation(title, () => {
                fetch(formElem.action, {
                    method: "POST",
                    body: formData,
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.redirect_url) {
                        progressBar.style.width = "100%";
                        window.location.href = data.redirect_url;
                    } else if (data.error) {
                        hideScanningModal();
                        alert("Verification Notice: " + data.error);
                    }
                })
                .catch(err => {
                    hideScanningModal();
                    console.error("Analysis error:", err);
                    // Fallback to standard form submit if fetch had network glitch
                    formElem.submit();
                });
            });
        });
    });
}

/* ==========================================================================
   Report Page (results.html) Viewer & Share Actions
   ========================================================================== */

function initReportViewer() {
    // Copy Link Action
    const copyBtn = document.getElementById("copy-report-link-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(window.location.href).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = "✅ Link Copied!";
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                }, 2000);
            }).catch(() => {
                alert("Report URL: " + window.location.href);
            });
        });
    }

    // Image ELA Toggle Buttons
    const btnSideBySide = document.getElementById("btn-show-sidebyside");
    const btnShowEla = document.getElementById("btn-show-ela");
    const btnShowOrig = document.getElementById("btn-show-orig");
    const panelOrig = document.getElementById("panel-orig");
    const panelEla = document.getElementById("panel-ela");
    const viewerGrid = document.getElementById("viewer-comparison-grid");

    if (btnSideBySide && btnShowEla && btnShowOrig && panelOrig && panelEla) {
        btnSideBySide.addEventListener("click", () => {
            setActiveToggle(btnSideBySide);
            panelOrig.style.display = "block";
            panelEla.style.display = "block";
            if (viewerGrid) viewerGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(320px, 1fr))";
        });

        btnShowEla.addEventListener("click", () => {
            setActiveToggle(btnShowEla);
            panelOrig.style.display = "none";
            panelEla.style.display = "block";
            if (viewerGrid) viewerGrid.style.gridTemplateColumns = "1fr";
        });

        btnShowOrig.addEventListener("click", () => {
            setActiveToggle(btnShowOrig);
            panelOrig.style.display = "block";
            panelEla.style.display = "none";
            if (viewerGrid) viewerGrid.style.gridTemplateColumns = "1fr";
        });
    }

    function setActiveToggle(activeBtn) {
        [btnSideBySide, btnShowEla, btnShowOrig].forEach(b => {
            if (b) b.classList.remove("active");
        });
        activeBtn.classList.add("active");
    }

    // Peer Confirmation Form Submission
    const confirmForm = document.getElementById("peer-confirmation-form");
    const submitConfBtn = document.getElementById("submit-confirmation-btn");
    if (confirmForm && submitConfBtn) {
        confirmForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const originalText = submitConfBtn.innerHTML;
            submitConfBtn.innerHTML = "<span>Sealing Cryptographic Record...</span>";
            submitConfBtn.disabled = true;

            const formData = new FormData(confirmForm);
            fetch(confirmForm.action, {
                method: "POST",
                body: formData,
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                } else if (data.error) {
                    alert("Confirmation Error: " + data.error);
                    submitConfBtn.innerHTML = originalText;
                    submitConfBtn.disabled = false;
                }
            })
            .catch(err => {
                console.error("Confirmation error:", err);
                confirmForm.submit();
            });
        });
    }
}
