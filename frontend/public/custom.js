(function () {
    console.log("⚡ Troubleshoot AI: custom.js initialized");

    function injectModal() {
        if (document.getElementById("adminModalOverlay")) return;

        const modalHTML = `
        <div id="adminModalOverlay" class="modal-overlay" style="display: none;">
            <div class="modal-window">
                <div class="modal-header">
                    <span class="modal-title">⚡ Switch to ADMIN MODE</span>
                    <span style="font-size: 0.8rem; color: #8ab4f8;">Identity Platform</span>
                </div>
                
                <div class="modal-input-group">
                    <label>Admin User ID / Email</label>
                    <input type="text" id="adminEmailInput" class="modal-input" placeholder="admin@example.com" autocomplete="off" />
                </div>

                <div class="modal-input-group">
                    <label>Password</label>
                    <div class="password-container">
                        <input type="password" id="adminPasswordInput" class="modal-input" placeholder="••••••••" />
                        <button type="button" id="togglePasswordEye" class="eye-btn" title="Show / Hide Password">👁️</button>
                    </div>
                </div>

                <div class="modal-actions">
                    <button type="button" id="adminModalCancel" class="modal-btn-cancel">Cancel</button>
                    <button type="button" id="adminModalSubmit" class="modal-btn-submit">Sign In</button>
                </div>
            </div>
        </div>
        `;

        if (document.body) {
            document.body.insertAdjacentHTML("beforeend", modalHTML);
            bindModalEvents();
        } else {
            document.addEventListener("DOMContentLoaded", function () {
                document.body.insertAdjacentHTML("beforeend", modalHTML);
                bindModalEvents();
            });
        }
    }

    function bindModalEvents() {
        const overlay = document.getElementById("adminModalOverlay");
        const emailInput = document.getElementById("adminEmailInput");
        const passInput = document.getElementById("adminPasswordInput");
        const eyeBtn = document.getElementById("togglePasswordEye");
        const cancelBtn = document.getElementById("adminModalCancel");
        const submitBtn = document.getElementById("adminModalSubmit");

        if (!overlay || overlay.dataset.bound === "true") return;
        overlay.dataset.bound = "true";

        if (eyeBtn && passInput) {
            eyeBtn.addEventListener("click", function () {
                if (passInput.type === "password") {
                    passInput.type = "text";
                    eyeBtn.textContent = "🙈";
                } else {
                    passInput.type = "password";
                    eyeBtn.textContent = "👁️";
                }
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener("click", function () {
                overlay.style.display = "none";
                if (passInput) passInput.value = "";
            });
        }

        if (submitBtn) {
            submitBtn.addEventListener("click", function () {
                const email = emailInput ? emailInput.value.trim() : "";
                const password = passInput ? passInput.value.trim() : "";

                if (!email || !password) {
                    alert("Please enter both Email and Password");
                    return;
                }

                overlay.style.display = "none";
                if (passInput) passInput.value = "";

                window.populateChatInput("__AUTH_ADMIN__:" + email + ":" + password, true);
            });
        }

        if (passInput) {
            passInput.addEventListener("keydown", function (e) {
                if (e.key === "Enter" && submitBtn) {
                    submitBtn.click();
                }
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectModal);
    } else {
        injectModal();
    }

    window.openAdminModal = function () {
        injectModal();
        const overlay = document.getElementById("adminModalOverlay");
        if (overlay) {
            overlay.style.display = "flex";
            const emailInput = document.getElementById("adminEmailInput");
            if (emailInput) {
                setTimeout(function () {
                    emailInput.focus();
                }, 50);
            }
        }
    };

    window.populateChatInput = function (text, autoSubmit) {
        if (autoSubmit === undefined) autoSubmit = false;

        const chatInput =
            document.querySelector('textarea[data-testid="chat-input"]') ||
            document.querySelector("#chat-input") ||
            document.querySelector("textarea");

        if (!chatInput) {
            console.warn("⚠️ Chat input textarea not found!");
            return;
        }

        try {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                "value"
            ).set;
            if (nativeInputValueSetter) {
                nativeInputValueSetter.call(chatInput, text);
            } else {
                chatInput.value = text;
            }
        } catch (e) {
            chatInput.value = text;
        }

        chatInput.dispatchEvent(new Event("input", { bubbles: true }));
        chatInput.dispatchEvent(new Event("change", { bubbles: true }));
        chatInput.focus();

        if (autoSubmit) {
            setTimeout(function () {
                const sendBtn =
                    document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector("#send-button") ||
                    (chatInput.form && chatInput.form.querySelector('button[type="submit"]')) ||
                    document.querySelector('button[aria-label="Send message"]');

                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                } else {
                    chatInput.dispatchEvent(
                        new KeyboardEvent("keydown", {
                            key: "Enter",
                            code: "Enter",
                            keyCode: 13,
                            which: 13,
                            bubbles: true,
                        })
                    );
                }
            }, 120);
        }
    };

    document.addEventListener(
        "click",
        function (e) {
            const loginBtn = e.target.closest(".mode-btn-login");
            if (loginBtn) {
                e.preventDefault();
                e.stopPropagation();
                console.log("⚡ Admin login button clicked");
                window.openAdminModal();
                return;
            }

            const publicBtn = e.target.closest(".mode-btn-public");
            if (publicBtn) {
                e.preventDefault();
                e.stopPropagation();
                console.log("🛡️ Switch to Public Mode button clicked");
                window.populateChatInput("__SWITCH_PUBLIC__", true);
                return;
            }

            const chip = e.target.closest(".gemini-chip");
            if (chip) {
                e.preventDefault();
                e.stopPropagation();
                const prompt = chip.getAttribute("data-prompt");
                if (prompt) {
                    window.populateChatInput(prompt);
                }
                return;
            }
        },
        true
    );

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            const overlay = document.getElementById("adminModalOverlay");
            if (overlay && overlay.style.display !== "none") {
                overlay.style.display = "none";
            }
        }
    });
})();