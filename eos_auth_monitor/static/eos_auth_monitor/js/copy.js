/*
 * Copy buttons: a button marked data-eos-auth-monitor-copy="<text>" puts the
 * text on the clipboard - the names of a to-do group, ready to paste as the
 * recipients of an EVE mail - and says so for a moment
 * (data-eos-auth-monitor-copied). The Clipboard API needs HTTPS; over plain
 * HTTP the older execCommand route takes over.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const fallback = (text) => {
        const area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        try {
            document.execCommand("copy");
        } finally {
            document.body.removeChild(area);
        }
    };

    const confirm = (button) => {
        const label = button.querySelector("span");
        const icon = button.querySelector("i");
        if (!label || button.dataset.eosAuthMonitorCopying) {
            return;
        }
        button.dataset.eosAuthMonitorCopying = "1";
        const text = label.textContent;
        label.textContent = button.dataset.eosAuthMonitorCopied || text;
        icon?.classList.replace("fa-copy", "fa-check");
        window.setTimeout(() => {
            label.textContent = text;
            icon?.classList.replace("fa-check", "fa-copy");
            delete button.dataset.eosAuthMonitorCopying;
        }, 1500);
    };

    document.querySelectorAll("[data-eos-auth-monitor-copy]").forEach((button) => {
        button.addEventListener("click", () => {
            const text = button.dataset.eosAuthMonitorCopy || "";
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(
                    () => confirm(button),
                    () => {
                        fallback(text);
                        confirm(button);
                    },
                );
            } else {
                fallback(text);
                confirm(button);
            }
        });
    });
});
