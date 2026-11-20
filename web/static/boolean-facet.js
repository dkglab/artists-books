// A single on/off filter for the sidebar (#160): "Only books with images".
//
// It speaks the same protocol as the concept facets (facet.js) so the page
// controller treats it as one more facet: the page sets `selected` (a Set
// holding the one key, or empty) and `counts`, and a click sends
// `facet-toggle` ({ key }) up, bubbling. Unlike them it has no chips, text box
// or list — just a heading and one switch — and no index to fetch: the
// page builds its book set from the grid itself.
//
// The key is `data-key`, the row's text `data-text`.

import { el } from "./facet.js";

const books = (n) => `${n} ${n === 1 ? "book" : "books"}`;

export class BooleanFacet extends HTMLElement {
  #box;
  #n;
  #total = 0;

  get key() { return this.dataset.key; }

  // How many works the filter keeps, unnarrowed; shown when `counts` is null.
  set total(n) {
    this.#total = n;
    this.#render();
    this.#n.textContent = books(n);
  }

  set selected(keys) {
    this.#render();
    this.#box.checked = keys.has(this.key);
  }

  // As for the concept facets: a Map from key narrowed by the other facets'
  // selections, or null for the overall count.
  set counts(counts) {
    this.#render();
    this.#n.textContent = books(counts ? (counts.get(this.key) ?? 0) : this.#total);
  }

  #render() {
    if (this.#box) return;
    // A checkbox drawn as a switch (style.css); role=switch has screen readers
    // announce it as on/off rather than checked/unchecked.
    this.#box = el("input", { type: "checkbox", className: "switch", value: this.key });
    this.#box.setAttribute("role", "switch");
    this.#n = el("span", { className: "n" });
    this.#box.addEventListener("change", () => {
      this.dispatchEvent(new CustomEvent("facet-toggle", {
        bubbles: true,
        detail: { key: this.key },
      }));
    });
    this.replaceChildren(el("section", { className: "facet" },
      el("h3", { className: "facet-heading" }, this.dataset.label || "Filter"),
      el("div", { className: "facet-list" },
        // The count goes under the text: beside it, with the switch, the row is
        // too wide for the sidebar and the text wraps.
        el("label", { className: "facet-switch" },
          el("span", { className: "facet-label" }, this.dataset.text || "", el("br"), this.#n),
          " ", this.#box))));
  }
}
