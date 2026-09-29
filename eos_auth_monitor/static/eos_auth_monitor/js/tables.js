/*
 * Sortable tables: every table marked eos-auth-monitor-sortable.
 *
 * No paging: the lists are short enough, and a page break would hide rows a
 * reader scans for the warning mark. A search box only above long lists -
 * over an account's handful of characters it is just clutter, on a phone
 * most of all. Cells sort by their data-order where they have one, so the
 * problem mark sorts problem rows together. Every column is left-aligned:
 * DataTables puts a column with numeric data-order to the right, which
 * would move a linked badge away from its name. A table marked
 * eos-auth-monitor-no-search has a filter of its own (filter.js) and gets no
 * search box. No computed widths: the overview table starts hidden behind
 * the tiles, where DataTables would measure every column as zero.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    // Alliance Auth's DataTables translation for the viewer's language, set
    // by base.html; empty for English, where DataTables needs none
    const holder = document.querySelector("[data-eos-auth-monitor-datatables-language]");
    const languageUrl = holder ? holder.dataset.eosAuthMonitorDatatablesLanguage : "";

    document.querySelectorAll("table.eos-auth-monitor-sortable").forEach((table) => {
        new DataTable(table, {
            ...(languageUrl ? { language: { url: languageUrl } } : {}),
            paging: false,
            searching: table.tBodies[0].rows.length > 10 && !table.classList.contains("eos-auth-monitor-no-search"),
            info: false,
            autoWidth: false,
            // keep the server's order until a header is clicked
            order: [],
            columnDefs: [
                { targets: "eos-auth-monitor-no-sort", orderable: false },
                { targets: "_all", className: "dt-left" },
            ],
        });
    });
});
