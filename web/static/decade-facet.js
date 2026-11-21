// The Decade facet (#22): one checkbox row per decade of publication, oldest
// first. The decades come from the grid itself (facets.js builds the tree
// from the cards' data-year), and there are only a few dozen, so unlike the
// concept facets it has no text box and lists every row in the order given.

import { Facet, el } from "./facet.js";

export class DecadeFacet extends Facet {
  get searchable() { return false; }

  buildList(list, tree) {
    const concepts = tree.categories.flatMap((category) => category.concepts);
    list.append(el("ul", {}, ...concepts.map((concept) => this.row(concept))));
    list.classList.add("facet-list-flat");
  }

  // A decade that would leave no works given the other facets is hidden.
  narrow() {
    for (const row of this.rows.values()) row.li.hidden = row.empty;
  }
}
