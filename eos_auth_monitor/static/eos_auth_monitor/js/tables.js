/*
 * Sortable tables: every table marked eos-auth-monitor-sortable.
 *
 * Pages of 100 rows by default, the size changeable above the table. A table
 * no longer than the smallest page size gets no paging at all: its controls
 * would only take room. A search box only above long lists - over an
 * account's handful of characters it is just clutter, on a phone most of
 * all. Cells sort by their data-order where they have one, so the problem
 * mark sorts problem rows together. Every column is left-aligned:
 * DataTables puts a column with numeric data-order to the right, which
 * would move a linked badge away from its name. A table marked
 * eos-auth-monitor-no-search has a filter of its own (filter.js) and gets
 * neither a search box nor pages: that filter hides rows itself and would
 * never see those on another page. No computed widths: the overview table
 * starts hidden behind the tiles, where DataTables would measure every
 * column as zero.
 */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const PAGE_LENGTHS = [25, 50, 100, 250, 500];
    const PAGE_LENGTH = 100;

    // Alliance Auth's DataTables translation for the viewer's language, set
    // by base.html; empty for English, where DataTables needs none
    const holder = document.querySelector("[data-eos-auth-monitor-datatables-language]");
    const languageUrl = holder ? holder.dataset.eosAuthMonitorDatatablesLanguage : "";

    document.querySelectorAll("table.eos-auth-monitor-sortable").forEach((table) => {
        const rows = table.tBodies[0].rows.length;
        const ownFilter = table.classList.contains("eos-auth-monitor-no-search");
        const paging = !ownFilter && rows > PAGE_LENGTHS[0];
        new DataTable(table, {
            ...(languageUrl ? { language: { url: languageUrl } } : {}),
            paging: paging,
            pageLength: PAGE_LENGTH,
            lengthMenu: PAGE_LENGTHS,
            searching: rows > 10 && !ownFilter,
            // "1 to 100 of 340" tells a reader there is more than this page
            info: paging,
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
