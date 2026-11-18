/*
 * Help mode: the navbar's switch marked data-eos-auth-monitor-help-toggle
 * shows or hides the question marks of partials/help.html, each a Bootstrap
 * popover with its text. Each change is saved for the user (views.help_mode),
 * so the next page starts as it was left; the switch stays hidden on a page
 * without help texts.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const toggle = document.querySelector("[data-eos-auth-monitor-help-toggle]");
    const hints = document.querySelectorAll(".eos-auth-monitor-help");
    if (!toggle || !hints.length) {
        return;
    }

    hints.forEach((hint) => {
        new bootstrap.Popover(hint);
        // inside a <summary> the click would fold the list open or shut
        hint.addEventListener("click", (event) => event.preventDefault());
    });

    const apply = () => {
        toggle.classList.toggle("bg-success", toggle.checked);
        toggle.classList.toggle("border-success", toggle.checked);
        hints.forEach((hint) => {
            hint.classList.toggle("d-none", !toggle.checked);
            if (!toggle.checked) {
                bootstrap.Popover.getInstance(hint).hide();
            }
        });
    };

    toggle.closest(".eos-auth-monitor-help-mode").classList.remove("d-none");
    toggle.addEventListener("change", apply);
    toggle.addEventListener("change", () => {
        fetch(toggle.dataset.eosAuthMonitorHelpUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": toggle.dataset.eosAuthMonitorCsrf },
            body: new URLSearchParams({ on: toggle.checked ? "1" : "0" }),
        });
    });
    // the browser may restore an unticked switch when going back to the page
    apply();
});
