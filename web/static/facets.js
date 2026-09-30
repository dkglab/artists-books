// Page controller for the homepage filter sidebar (#138).
//
// It owns the selection state, keeps it in the query string
// (e.g. /?construction=accordion-fold,zine) and filters the grid Snowman
// already rendered by hiding the cards that don't match. The facet elements
// only display what they're given and report toggles (see
// hierarchical-facet.js), so cross-facet logic lives here.
//
// Within a facet the selection is OR (the union of the ticked concepts' books);
// across facets it is AND. Only the Construction facet exists yet, so its
// counts are fixed at build time; once a second facet lands, the counts
// should narrow by the *other* facets' selections.

import { HierarchicalFacet } from "./hierarchical-facet.js";

customElements.define("construction-facet", class extends HierarchicalFacet {});

const sidebar = document.querySelector(".filters");
const countLine = document.querySelector(".page-intro .count");
const noResults = document.querySelector(".no-results");
const grid = document.querySelector(".book-grid");
const total = Number(countLine.dataset.total);

// item key -> card, collected once.
const cards = new Map(
  [...document.querySelectorAll(".book-grid li[data-key]")].map((li) => [li.dataset.key, li]));

// One entry per facet element: its URL parameter, its concept -> item keys
// index, and the current selection.
const facets = [];

async function load(element) {
  const response = await fetch(element.dataset.src);
  if (!response.ok) throw new Error(`${element.dataset.src}: HTTP ${response.status}`);
  const index = await response.json();
  const books = new Map();
  const tree = {
    categories: index.categories.map((category) => ({
      key: category.key,
      label: category.label,
      concepts: category.concepts.map((concept) => {
        books.set(concept.key, new Set(concept.books));
        return { key: concept.key, label: concept.label, count: concept.books.length };
      }),
    })),
  };
  element.tree = tree;
  return { element, param: element.dataset.param, books, selected: new Set() };
}

// Read each facet's selection from the URL, dropping keys its index doesn't know.
function readURL() {
  const params = new URLSearchParams(location.search);
  for (const facet of facets) {
    const value = params.get(facet.param) ?? "";
    facet.selected = new Set(value.split(",").filter((key) => facet.books.has(key)));
  }
}

// Write the selection back, leaving any other query parameters alone. Keys are
// sorted so equal selections give the same URL.
function writeURL() {
  const params = new URLSearchParams(location.search);
  for (const facet of facets) {
    if (facet.selected.size) params.set(facet.param, [...facet.selected].sort().join(","));
    else params.delete(facet.param);
  }
  // Concept keys are [a-z0-9-], so the only escaping URLSearchParams adds here
  // is to the separator; keep the commas readable.
  const query = params.toString().replace(/%2C/gi, ",");
  history.pushState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
}

function apply() {
  // Per active facet, the union of its selected concepts' books; a card is
  // shown when it is in every active facet's union.
  const unions = facets
    .filter((facet) => facet.selected.size)
    .map((facet) => {
      const union = new Set();
      for (const key of facet.selected) for (const item of facet.books.get(key)) union.add(item);
      return union;
    });

  // Toggle the cards with the grid detached. Setting `hidden` on ~7,900 cards
  // in place took ~5.5 s in headless Chrome when hiding most of them (the
  // common case: one concept selected); detached, the same loop plus relayout
  // is well under 100 ms. It goes back before anything reads layout, so the
  // page never renders without it.
  const parent = grid.parentNode;
  const next = grid.nextSibling;
  grid.remove();
  let shown = 0;
  for (const [key, li] of cards) {
    const visible = unions.every((union) => union.has(key));
    if (li.hidden === visible) li.hidden = !visible;
    if (visible) shown += 1;
  }
  parent.insertBefore(grid, next);

  countLine.textContent = unions.length ? `${shown} of ${total} works` : `${total} works`;
  noResults.hidden = shown > 0;
  for (const facet of facets) facet.element.selected = facet.selected;
}

async function init() {
  const elements = [...sidebar.querySelectorAll("[data-src][data-param]")];
  facets.push(...await Promise.all(elements.map(load)));

  sidebar.addEventListener("facet-toggle", (e) => {
    const facet = facets.find((f) => f.element.contains(e.target));
    const { key } = e.detail;
    if (facet.selected.has(key)) facet.selected.delete(key);
    else facet.selected.add(key);
    writeURL();
    apply();
  });
  sidebar.addEventListener("facet-clear", (e) => {
    const facet = facets.find((f) => f.element.contains(e.target));
    facet.selected.clear();
    writeURL();
    apply();
  });
  window.addEventListener("popstate", () => {
    readURL();
    apply();
  });

  readURL();
  apply();
  sidebar.hidden = false;
}

// On failure, the sidebar stays hidden and the full grid stays visible.
init().catch((error) => console.error("Filters unavailable:", error));
