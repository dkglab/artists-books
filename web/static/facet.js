// The shared base of the filter sidebar's facet elements (#138, #143).
//
// Its shape follows FacetPanel in british-music-trade/spaestiem: a facet
// filters nothing itself. The page gives it `tree`, `selected` and `counts`,
// and it sends `facet-toggle` ({ key }) and `facet-clear` events back up,
// bubbling. It knows nothing of books or URLs, so further facets are additions
// to the page controller (facets.js), not rewrites of this.
//
// This class owns what every facet has: the heading, the chips for the
// selection with their Clear button, the text box, and one checkbox row per
// concept. How the rows are laid out, and what the text box does to them, is
// up to the subclass (hierarchical-facet.js, flat-facet.js), through three
// hooks: buildList(), syncList() and narrow().
//
// Built from ordinary page elements (no Shadow DOM) so style.css styles it like
// the rest of the site. Concepts are real <label> + checkbox rows, which give
// keyboard and screen-reader support without extra ARIA.

export function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

export class Facet extends HTMLElement {
  #tree = { categories: [] };
  #selected = new Set();
  // concept key -> { li, box, n, key, label, count }, in the order built.
  #rows = new Map();

  #selectedCount;
  #chipBar;
  #chips;
  #search;
  #list;

  get tree() { return this.#tree; }

  // { categories: [{ key, label, concepts: [{ key, label, count }] }] }
  set tree(tree) {
    this.#tree = tree;
    this.#render();
    this.#sync(new Set());
  }

  get selected() { return new Set(this.#selected); }

  // Only updates the checkboxes, chips and summaries; the list isn't rebuilt,
  // so the text box and scroll position survive.
  set selected(keys) {
    const previous = this.#selected;
    this.#selected = new Set(keys);
    this.#sync(previous);
  }

  // Each concept's book count narrowed by the *other* facets' selections, as a
  // Map from concept key, or null for the overall counts. A concept that would
  // leave no works is dimmed rather than hidden, so the list doesn't jump about
  // as other facets change; a ticked one is never dimmed, so it stays easy to
  // find and untick.
  set counts(counts) {
    for (const row of this.#rows.values()) {
      const n = counts ? (counts.get(row.key) ?? 0) : row.count;
      row.n.textContent = String(n);
      row.li.classList.toggle("facet-empty", n === 0 && !row.box.checked);
    }
  }

  // For the subclasses.
  get rows() { return this.#rows; }
  get query() { return this.#search.value.trim().toLowerCase(); }

  // A checkbox row for one concept, registered in `rows`.
  row(concept) {
    const box = el("input", { type: "checkbox", value: concept.key });
    const n = el("span", { className: "n", textContent: String(concept.count) });
    const li = el("li", {},
      el("label", {}, box, " ", el("span", { className: "facet-label", textContent: concept.label }),
        " ", n));
    this.#rows.set(concept.key, { li, box, n, ...concept });
    return li;
  }

  // Hooks. buildList(list, tree) fills the list container with rows (via
  // row()); syncList(previous) runs after the checkboxes have been set to a new
  // selection; narrow() runs when the text box changes.
  buildList(_list, _tree) {}
  syncList(_previous) {}
  narrow() {}

  #render() {
    const name = this.dataset.label || "Facet";
    const find = this.dataset.search || `Find a ${name.toLowerCase()} term`;
    this.#rows = new Map();

    this.#selectedCount = el("span", { className: "facet-selected-count" });
    const heading = el("h3", { className: "facet-heading" }, name, this.#selectedCount);

    this.#chips = el("ul", { className: "chips" });
    const clear = el("button", { type: "button", className: "facet-clear", textContent: "Clear" });
    clear.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("facet-clear", { bubbles: true }));
      this.#search.focus();
    });
    this.#chipBar = el("div", { className: "facet-chips", hidden: true }, this.#chips, clear);
    this.#chips.addEventListener("click", (e) => this.#onChipClick(e));

    this.#search = el("input", {
      type: "search",
      className: "facet-search",
      placeholder: find,
      autocomplete: "off",
    });
    this.#search.setAttribute("aria-label", find);
    this.#search.addEventListener("input", () => this.narrow());

    this.#list = el("div", { className: "facet-list" });
    this.buildList(this.#list, this.#tree);
    // One delegated listener for every concept row.
    this.#list.addEventListener("change", (e) => {
      if (e.target.matches("input[type=checkbox]")) {
        this.dispatchEvent(new CustomEvent("facet-toggle", {
          bubbles: true,
          detail: { key: e.target.value },
        }));
      }
    });

    this.replaceChildren(el("section", { className: "facet" },
      heading, this.#chipBar, this.#search, this.#list));
  }

  #sync(previous) {
    if (!this.#list) return;
    const n = this.#selected.size;
    this.#selectedCount.textContent = n ? ` · ${n} selected` : "";

    for (const row of this.#rows.values()) {
      row.box.checked = this.#selected.has(row.key);
      if (row.box.checked) row.li.classList.remove("facet-empty");
    }
    this.syncList(previous);

    this.#chips.replaceChildren(...[...this.#selected]
      .filter((key) => this.#rows.has(key))
      .map((key) => {
        const { label } = this.#rows.get(key);
        const remove = el("button", { type: "button", textContent: "×" });
        remove.value = key;
        remove.setAttribute("aria-label", `Remove ${label}`);
        return el("li", {}, el("span", { textContent: label }), remove);
      }));
    this.#chipBar.hidden = n === 0;
  }

  #onChipClick(e) {
    const button = e.target.closest("button");
    if (!button) return;
    const index = [...this.#chips.querySelectorAll("button")].indexOf(button);
    this.dispatchEvent(new CustomEvent("facet-toggle", {
      bubbles: true,
      detail: { key: button.value },
    }));
    // The page's handler runs synchronously and re-renders the chips, so the
    // clicked button is gone: keep focus nearby rather than dropping it.
    const buttons = this.#chips.querySelectorAll("button");
    (buttons[Math.min(index, buttons.length - 1)] ?? this.#search).focus();
  }
}
