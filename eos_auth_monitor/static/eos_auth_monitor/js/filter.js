/*
 * Live filter: an input marked data-eos-auth-monitor-filter="<selector>" hides
 * every element matching the selector whose data-eos-auth-monitor-filter-text
 * does not contain what was typed (case-insensitive, every word must match).
 * Used above the Corporation tiles of the overview.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    document.querySelectorAll("input[data-eos-auth-monitor-filter]").forEach((input) => {
        const items = document.querySelectorAll(input.dataset.eosAuthMonitorFilter);
        const empty = document.querySelector(input.dataset.eosAuthMonitorFilterEmpty || "");

        const apply = () => {
            const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
            let shown = 0;
            items.forEach((item) => {
                const text = (item.dataset.eosAuthMonitorFilterText || "").toLowerCase();
                const match = words.every((word) => text.includes(word));
                item.classList.toggle("d-none", !match);
                if (match) {
                    shown += 1;
                }
            });
            if (empty) {
                empty.classList.toggle("d-none", shown > 0);
            }
        };

        input.addEventListener("input", apply);
        apply();
    });
});
