/*
 * Sortable tables: every table marked eos-auth-monitor-sortable.
 *
 * No paging: the lists are short enough, and a page break would hide rows a
 * reader scans for the warning mark. A search box only above long lists -
 * over an account's handful of characters it is just clutter, on a phone
 * most of all. Cells sort by their data-order where they have one, so the
 * problem mark sorts problem rows together.
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
            searching: table.tBodies[0].rows.length > 10,
            info: false,
            // keep the server's order until a header is clicked
            order: [],
            columnDefs: [{ targets: "eos-auth-monitor-no-sort", orderable: false }],
        });
    });
});
