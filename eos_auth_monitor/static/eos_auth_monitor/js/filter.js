/*
 * Live filter: an input marked data-eos-auth-monitor-filter="<selector>" hides
 * every element matching the selector whose data-eos-auth-monitor-filter-text
 * does not contain what was typed (case-insensitive, every word must match).
 * A checkbox named by data-eos-auth-monitor-filter-problems="<selector>"
 * also hides every element whose data-eos-auth-monitor-problems is not "1".
 * Used above the Corporation tiles and the table of the overview, which carry
 * the same marks, so both views show the same Corporations.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    document.querySelectorAll("input[data-eos-auth-monitor-filter]").forEach((input) => {
        const items = document.querySelectorAll(input.dataset.eosAuthMonitorFilter);
        const empty = document.querySelector(input.dataset.eosAuthMonitorFilterEmpty || "");
        const problemsOnly = document.querySelector(input.dataset.eosAuthMonitorFilterProblems || "");

        const apply = () => {
            const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
            const onlyProblems = Boolean(problemsOnly && problemsOnly.checked);
            let shown = 0;
            items.forEach((item) => {
                const text = (item.dataset.eosAuthMonitorFilterText || "").toLowerCase();
                const match =
                    words.every((word) => text.includes(word)) &&
                    (!onlyProblems || item.dataset.eosAuthMonitorProblems === "1");
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
        problemsOnly?.addEventListener("change", apply);
        apply();
    });
});
