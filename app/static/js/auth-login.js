"use strict";

function initializePasswordToggle() {
    const toggles = document.querySelectorAll(
        "[data-password-toggle]"
    );

    toggles.forEach(toggle => {
        const inputId = toggle.getAttribute(
            "aria-controls"
        );

        const input = document.getElementById(
            inputId
        );

        const visibleIcon = toggle.querySelector(
            ".auth-eye-visible"
        );

        const hiddenIcon = toggle.querySelector(
            ".auth-eye-hidden"
        );

        if (!input) {
            return;
        }

        toggle.addEventListener(
            "click",
            () => {
                const showingPassword = (
                    input.type === "text"
                );

                input.type = (
                    showingPassword
                        ? "password"
                        : "text"
                );

                toggle.setAttribute(
                    "aria-pressed",
                    String(!showingPassword)
                );

                toggle.setAttribute(
                    "aria-label",
                    showingPassword
                        ? "Mostrar contraseña"
                        : "Ocultar contraseña"
                );

                visibleIcon?.classList.toggle(
                    "is-hidden",
                    !showingPassword
                );

                hiddenIcon?.classList.toggle(
                    "is-hidden",
                    showingPassword
                );

                input.focus();
            }
        );
    });
}


function initializeSubmittingState() {
    const form = document.querySelector(
        ".auth-form"
    );

    const submitButton = form?.querySelector(
        ".auth-submit"
    );

    if (!form || !submitButton) {
        return;
    }

    form.addEventListener(
        "submit",
        () => {
            submitButton.disabled = true;
            submitButton.value = "Validando acceso...";
        }
    );
}


document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializePasswordToggle();
        initializeSubmittingState();
    }
);