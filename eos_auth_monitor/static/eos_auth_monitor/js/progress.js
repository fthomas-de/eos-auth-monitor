/*
 * Progress bar of the snapshot task.
 *
 * Asks the server for the task's state every two seconds while it is queued
 * or running, and reloads the page once a run it has watched is done - the
 * page then shows the new result. Idle, it asks once on load and stops.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const box = document.querySelector("[data-eos-auth-monitor-progress]");
    if (!box) {
        return;
    }
    const url = box.dataset.eosAuthMonitorProgress;
    const label = box.querySelector(".eos-auth-monitor-progress-label");
    const bar = box.querySelector(".progress-bar");
    const button = document.querySelector(".eos-auth-monitor-rebuild");
    let watched = false;

    const show = (text, percent) => {
        box.classList.remove("d-none");
        label.textContent = text;
        bar.style.width = `${percent}%`;
        bar.textContent = percent ? `${percent} %` : "";
        if (button) {
            button.disabled = true;
        }
    };

    const poll = () => {
        fetch(url, { credentials: "same-origin" })
            .then((response) => (response.ok ? response.json() : null))
            .then((data) => {
                if (!data) {
                    return;
                }
                if (data.state === "queued" || data.state === "running") {
                    watched = true;
                    show(data.state === "queued" ? box.dataset.eosAuthMonitorQueued : data.phase, data.percent);
                    window.setTimeout(poll, 2000);
                } else if (data.state === "done" && watched) {
                    window.location.reload();
                } else if (data.state === "failed" && watched) {
                    show(box.dataset.eosAuthMonitorFailed, 0);
                    bar.classList.add("bg-danger");
                    if (button) {
                        button.disabled = false;
                    }
                }
            })
            .catch(() => window.setTimeout(poll, 5000));
    };

    poll();
});
