// A two-level facet (category -> concept) for the filter sidebar (#138): the
// Construction facet. The heading, chips, text box and rows come from Facet
// (facet.js); this lays the rows out under their categories.
//
// Categories are <details> headings only — they group and collapse but can't
// be ticked; only concepts are values.

import { Facet, el } from "./facet.js";

export class HierarchicalFacet extends Facet {
  #preSearchOpen = null; // category open states saved while the text box has text

  buildList(list, tree) {
    for (const category of tree.categories) {
      const summary = el("summary", {},
        el("span", { textContent: category.label }),
        el("span", { className: "facet-cat-selected" }));
      const details = el("details", {}, summary,
        el("ul", {}, ...category.concepts.map((concept) => this.row(concept))));
      details.dataset.category = category.key;
      list.append(details);
    }
  }

  syncList(previous) {
    for (const details of this.querySelectorAll(".facet-list > details")) {
      let ticked = 0;
      let gained = false;
      for (const box of details.querySelectorAll("input[type=checkbox]")) {
        if (box.checked) {
          ticked += 1;
          if (!previous.has(box.value)) gained = true;
        }
      }
      details.querySelector(".facet-cat-selected").textContent =
        ticked ? ` · ${ticked} selected` : "";
      // Categories start collapsed; open one when a concept in it becomes
      // selected from outside (initial URL, back/forward). Ticking inside a
      // category means it is already open, so this never fights the user.
      if (gained) details.open = true;
    }
  }

  // Narrow the list to concepts whose label contains the typed text and that
  // would leave some works, hiding categories with nothing left and, while
  // searching, opening the ones that have a match. Ticks are untouched.
  // Clearing the box restores the categories' open states.
  narrow() {
    const q = this.query;
    const categories = [...this.querySelectorAll(".facet-list > details")];
    if (q && !this.#preSearchOpen) {
      this.#preSearchOpen = new Map(categories.map((d) => [d, d.open]));
    }
    for (const details of categories) {
      let matches = 0;
      for (const box of details.querySelectorAll("input[type=checkbox]")) {
        const row = this.rows.get(box.value);
        const hit = !row.empty && (!q || row.label.toLowerCase().includes(q));
        row.li.hidden = !hit;
        if (hit) matches += 1;
      }
      details.hidden = matches === 0;
      if (q) details.open = matches > 0;
    }
    if (!q && this.#preSearchOpen) {
      for (const [details, open] of this.#preSearchOpen) details.open = open;
      this.#preSearchOpen = null;
    }
  }
}
