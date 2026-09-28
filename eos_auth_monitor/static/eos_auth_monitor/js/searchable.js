/* Dropdowns that filter while typing: every select marked data-eos-auth-monitor-search. */
document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    document.querySelectorAll("select[data-eos-auth-monitor-search]").forEach((select) => {
        // read before Tom Select hides the original: these are the colours the
        // active theme gives its form fields, see tom-select-theme.css
        const style = window.getComputedStyle(select);
        const background = style.backgroundColor;
        const color = style.color;

        const control = new TomSelect(select, {
            allowEmptyOption: true,
            maxOptions: null,
        });

        control.wrapper.style.setProperty("--eos-auth-monitor-ts-bg", background);
        control.wrapper.style.setProperty("--eos-auth-monitor-ts-color", color);
    });
});
