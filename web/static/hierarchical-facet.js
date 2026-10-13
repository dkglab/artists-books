// A two-level facet (category -> concept) for the filter sidebar (#138).
//
// Its shape follows FacetPanel in british-music-trade/spaestiem: the element
// filters nothing itself. The page gives it `tree` and `selected`, and it sends
// `facet-toggle` ({ key }) and `facet-clear` events back up, bubbling. It knows
// nothing of books or URLs, so further facets are additions to the page
// controller (facets.js), not rewrites of this.
//
// Built from ordinary page elements (no Shadow DOM) so style.css styles it like
// the rest of the site. Categories are <details> headings only — they group and
// collapse but can't be ticked; only concepts are values. Concepts are real
// <label> + checkbox rows, which give keyboard and screen-reader support
// without extra ARIA.

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

export class HierarchicalFacet extends HTMLElement {
  #tree = { categories: [] };
  #selected = new Set();
  #labels = new Map(); // concept key -> label, for the chips
  #preSearchOpen = null; // category open states saved while the text box has text

  #heading;
  #selectedCount;
  #chipBar;
  #chips;
  #search;
  #list;

  get tree() { return this.#tree; }

  // { categories: [{ key, label, concepts: [{ key, label, count }] }] }
  set tree(tree) {
    this.#tree = tree;
    this.#labels = new Map(
      tree.categories.flatMap((c) => c.concepts.map((k) => [k.key, k.label])));
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

  #render() {
    const name = this.dataset.label || "Facet";
    this.#selectedCount = el("span", { className: "facet-selected-count" });
    this.#heading = el("h3", { className: "facet-heading" }, name, this.#selectedCount);

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
      placeholder: `Find a ${name.toLowerCase()} term`,
      autocomplete: "off",
    });
    this.#search.setAttribute("aria-label", `Find a ${name.toLowerCase()} term`);
    this.#search.addEventListener("input", () => this.#narrow());

    this.#list = el("div", { className: "facet-list" });
    for (const category of this.#tree.categories) {
      const rows = category.concepts.map((concept) => {
        const box = el("input", { type: "checkbox", value: concept.key });
        return el("li", {},
          el("label", {}, box, " ", el("span", { className: "facet-label", textContent: concept.label }),
            " ", el("span", { className: "n", textContent: String(concept.count) })));
      });
      const summary = el("summary", {},
        el("span", { textContent: category.label }),
        el("span", { className: "facet-cat-selected" }));
      const details = el("details", {}, summary, el("ul", {}, ...rows));
      details.dataset.category = category.key;
      this.#list.append(details);
    }
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
      this.#heading, this.#chipBar, this.#search, this.#list));
  }

  #sync(previous) {
    if (!this.#list) return;
    const n = this.#selected.size;
    this.#selectedCount.textContent = n ? ` · ${n} selected` : "";

    for (const details of this.#list.children) {
      let ticked = 0;
      let gained = false;
      for (const box of details.querySelectorAll("input[type=checkbox]")) {
        box.checked = this.#selected.has(box.value);
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

    this.#chips.replaceChildren(...[...this.#selected]
      .filter((key) => this.#labels.has(key))
      .map((key) => {
        const label = this.#labels.get(key);
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

  // Narrow the list to concepts whose label contains the typed text, hiding
  // categories with no match and opening the ones that have one. Ticks are
  // untouched. Clearing the box restores the categories' open states.
  #narrow() {
    const q = this.#search.value.trim().toLowerCase();
    const categories = [...this.#list.children];
    if (q && !this.#preSearchOpen) {
      this.#preSearchOpen = new Map(categories.map((d) => [d, d.open]));
    }
    for (const details of categories) {
      let matches = 0;
      for (const li of details.querySelectorAll("li")) {
        const hit = !q || li.querySelector(".facet-label").textContent.toLowerCase().includes(q);
        li.hidden = !hit;
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
