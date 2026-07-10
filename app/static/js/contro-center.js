"use strict";

const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    ?.getAttribute("content");


function formatUptime(seconds) {
    if (
        seconds === null ||
        seconds === undefined
    ) {
        return "—";
    }

    const days = Math.floor(
        seconds / 86400
    );

    const hours = Math.floor(
        (seconds % 86400) / 3600
    );

    const minutes = Math.floor(
        (seconds % 3600) / 60
    );

    if (days > 0) {
        return `${days}d ${hours}h ${minutes}m`;
    }

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }

    return `${minutes}m`;
}


function setText(container, field, value) {
    const element = container.querySelector(
        `[data-field="${field}"]`
    );

    if (element) {
        element.textContent = value ?? "—";
    }
}


function setServiceState(container, state) {
    const element = container.querySelector(
        '[data-field="service-state"]'
    );

    if (!element) {
        return;
    }

    const normalized = state || "unknown";

    element.textContent = normalized.replaceAll(
        "_",
        " "
    );

    element.className =
        `status-badge status-${normalized}`;
}


function renderSnapshot(container, snapshot) {
    const service = snapshot.service || {};
    const health = snapshot.health || {};
    const metrics = snapshot.metrics || {};

    setServiceState(
        container,
        service.state
    );

    setText(
        container,
        "service-name",
        service.name
    );

    setText(
        container,
        "start-mode",
        service.start_mode
    );

    setText(
        container,
        "process-id",
        service.process_id || "—"
    );

    setText(
        container,
        "health-status",
        health.status || "—"
    );

    setText(
        container,
        "response-time",
        health.response_time_ms !== null &&
        health.response_time_ms !== undefined
            ? `${health.response_time_ms} ms`
            : "—"
    );

    setText(
        container,
        "cpu",
        metrics.cpu_percent !== null &&
        metrics.cpu_percent !== undefined
            ? `${metrics.cpu_percent}%`
            : "—"
    );

    setText(
        container,
        "memory",
        metrics.memory_mb !== null &&
        metrics.memory_mb !== undefined
            ? `${metrics.memory_mb} MB`
            : "—"
    );

    setText(
        container,
        "uptime",
        formatUptime(
            metrics.uptime_seconds
        )
    );

    container.dataset.serviceState =
        service.state || "unknown";

    container.dataset.healthState =
        health.status || "unknown";
}


async function refreshApplication(container) {
    const code = container.dataset.appCode;

    if (!code) {
        return;
    }

    try {
        const response = await fetch(
            `/applications/${code}/status`,
            {
                headers: {
                    "Accept": "application/json"
                },
                credentials: "same-origin"
            }
        );

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(
                payload.error ||
                "No fue posible consultar el estado."
            );
        }

        renderSnapshot(
            container,
            payload
        );

    } catch (error) {
        setServiceState(
            container,
            "unknown"
        );

        setText(
            container,
            "health-status",
            "unavailable"
        );

        container.dataset.serviceState =
            "unknown";

        container.dataset.healthState =
            "unhealthy";
    }
}


function updateSummary() {
    const cards = [
        ...document.querySelectorAll(
            "[data-application-card]"
        )
    ];

    const running = cards.filter(
        card =>
            card.dataset.serviceState
            === "running"
    ).length;

    const stopped = cards.filter(
        card =>
            card.dataset.serviceState
            === "stopped"
    ).length;

    const unhealthy = cards.filter(
        card =>
            card.dataset.healthState
            === "unhealthy"
    ).length;

    const runningElement =
        document.getElementById(
            "summary-running"
        );

    const stoppedElement =
        document.getElementById(
            "summary-stopped"
        );

    const unhealthyElement =
        document.getElementById(
            "summary-unhealthy"
        );

    if (runningElement) {
        runningElement.textContent = running;
    }

    if (stoppedElement) {
        stoppedElement.textContent = stopped;
    }

    if (unhealthyElement) {
        unhealthyElement.textContent =
            unhealthy;
    }
}


async function refreshAll() {
    const containers = [
        ...document.querySelectorAll(
            "[data-application-card]"
        ),
        ...document.querySelectorAll(
            "[data-application-detail]"
        )
    ];

    await Promise.all(
        containers.map(refreshApplication)
    );

    updateSummary();
}


async function executeServiceAction(button) {
    const code = button.dataset.appCode;
    const action =
        button.dataset.serviceAction;

    const originalText =
        button.textContent;

    const confirmationText = {
        start: "¿Iniciar este servicio?",
        stop: "¿Detener este servicio?",
        restart: "¿Reiniciar este servicio?"
    }[action];

    if (!window.confirm(confirmationText)) {
        return;
    }

    button.disabled = true;
    button.textContent = "Procesando...";

    try {
        const response = await fetch(
            `/applications/${code}/actions/${action}`,
            {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Accept":
                        "application/json",
                    "X-CSRFToken":
                        csrfToken
                }
            }
        );

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(
                payload.error ||
                "La operación falló."
            );
        }

        showToast(
            payload.message,
            "success"
        );

        await refreshAll();

    } catch (error) {
        showToast(
            error.message,
            "error"
        );

    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}


function showToast(
    message,
    type = "success"
) {
    const container =
        document.getElementById(
            "toast-container"
        );

    if (!container) {
        return;
    }

    const toast =
        document.createElement("div");

    toast.className =
        `toast toast-${type}`;

    toast.textContent = message;

    container.appendChild(toast);

    window.setTimeout(
        () => toast.remove(),
        5000
    );
}


function initializeLogStream() {
    const detail =
        document.querySelector(
            "[data-application-detail]"
        );

    const terminal =
        document.getElementById(
            "live-log"
        );

    if (!detail || !terminal) {
        return;
    }

    const code = detail.dataset.appCode;

    const source = new EventSource(
        `/applications/${code}/logs/stream`,
        {
            withCredentials: true
        }
    );

    source.onmessage = event => {
        try {
            const payload =
                JSON.parse(event.data);

            terminal.textContent +=
                `${payload.line}\n`;

            terminal.scrollTop =
                terminal.scrollHeight;

        } catch {
            // Ignora mensajes SSE inválidos.
        }
    };

    source.onerror = () => {
        showToast(
            "La conexión de logs "
            + "se está reintentando.",
            "error"
        );
    };

    document
        .querySelector("[data-clear-log]")
        ?.addEventListener(
            "click",
            () => {
                terminal.textContent = "";
            }
        );

    window.addEventListener(
        "beforeunload",
        () => source.close()
    );
}


document.addEventListener(
    "click",
    event => {
        const button = event.target.closest(
            "[data-service-action]"
        );

        if (button) {
            executeServiceAction(button);
        }
    }
);


document.addEventListener(
    "DOMContentLoaded",
    async () => {
        await refreshAll();

        initializeLogStream();

        window.setInterval(
            refreshAll,
            10000
        );
    }
);