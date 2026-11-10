// A single-level facet for a long tail of terms (#143): the Subject and Place
// facets. The heading, chips, text box and rows come from Facet (facet.js);
// this lays the rows out as one list, most-used first.
//
// Most subject terms are used by a single book, so listing them all would bury
// the useful ones. With the text box empty, only the terms used by at least
// `data-min` works are shown (plus any that are ticked, so a selection from the
// URL or from a search stays visible); typing searches every term. The
// threshold is on the overall counts, not the ones narrowed by other facets,
// so the list doesn't change shape as other facets change.

import { Facet, el } from "./facet.js";

export class FlatFacet extends Facet {
  #hint;

  get min() { return Number(this.dataset.min) || 0; }

  buildList(list, tree) {
    const concepts = tree.categories
      .flatMap((category) => category.concepts)
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
    this.#hint = el("p", { className: "facet-hint" });
    list.append(el("ul", {}, ...concepts.map((concept) => this.row(concept))), this.#hint);
    list.classList.add("facet-list-flat");
  }

  syncList() { this.#filter(); }
  narrow() { this.#filter(); }

  #filter() {
    const q = this.query;
    const min = this.min;
    let shown = 0;
    for (const row of this.rows.values()) {
      const visible = q
        ? row.label.toLowerCase().includes(q)
        : row.count >= min || row.box.checked;
      row.li.hidden = !visible;
      if (visible) shown += 1;
    }
    const rest = this.rows.size - shown;
    if (q) this.#hint.textContent = shown ? "" : "No matching terms.";
    else this.#hint.textContent = rest ? `${rest} less-used terms: type above to find them.` : "";
    this.#hint.hidden = !this.#hint.textContent;
  }
}
