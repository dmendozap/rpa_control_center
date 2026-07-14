"use strict";


function initializePasswordToggle() {
    const toggle = document.querySelector(
        "[data-password-toggle]"
    );

    if (!toggle) {
        return;
    }

    const inputId = toggle.getAttribute(
        "aria-controls"
    );

    const input = document.getElementById(
        inputId
    );

    const eyeIcon = toggle.querySelector(
        ".icon-eye"
    );

    const eyeOffIcon = toggle.querySelector(
        ".icon-eye-off"
    );

    if (!input) {
        return;
    }

    toggle.addEventListener(
        "click",
        () => {
            const currentlyVisible = (
                input.type === "text"
            );

            input.type = (
                currentlyVisible
                    ? "password"
                    : "text"
            );

            toggle.setAttribute(
                "aria-pressed",
                String(!currentlyVisible)
            );

            toggle.setAttribute(
                "aria-label",
                currentlyVisible
                    ? "Mostrar contraseña"
                    : "Ocultar contraseña"
            );

            eyeIcon?.classList.toggle(
                "is-hidden",
                !currentlyVisible
            );

            eyeOffIcon?.classList.toggle(
                "is-hidden",
                currentlyVisible
            );

            input.focus();
        }
    );
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