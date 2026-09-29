/*
 * View switch: buttons marked data-eos-auth-monitor-view="<name>" show the
 * element marked data-eos-auth-monitor-view-pane="<name>" and hide the other
 * panes. Used on the overview for tiles or table. The choice is kept per
 * browser; storage may be blocked, and then the tiles simply come first.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const buttons = document.querySelectorAll("[data-eos-auth-monitor-view]");
    const panes = document.querySelectorAll("[data-eos-auth-monitor-view-pane]");
    if (!buttons.length || !panes.length) {
        return;
    }
    const storageKey = "eos_auth_monitor.view";

    const show = (name) => {
        panes.forEach((pane) => pane.classList.toggle("d-none", pane.dataset.eosAuthMonitorViewPane !== name));
        buttons.forEach((button) => {
            const active = button.dataset.eosAuthMonitorView === name;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    };

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const name = button.dataset.eosAuthMonitorView;
            show(name);
            try {
                window.localStorage.setItem(storageKey, name);
            } catch (error) {
                // private window or blocked storage: the switch still works for this visit
            }
        });
    });

    let stored = null;
    try {
        stored = window.localStorage.getItem(storageKey);
    } catch (error) {
        stored = null;
    }
    if (stored && document.querySelector(`[data-eos-auth-monitor-view-pane="${stored}"]`)) {
        show(stored);
    }
});
