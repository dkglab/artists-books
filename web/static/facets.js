// Page controller for the homepage filter sidebar (#138, #143).
//
// It owns the selection state, keeps it in the query string
// (e.g. /?construction=accordion-fold,zine&place=mexico) and filters the grid
// Snowman already rendered by hiding the cards that don't match. The facet
// elements only display what they're given and report toggles (see facet.js),
// so cross-facet logic lives here.
//
// Within a facet the selection is OR (the union of the ticked concepts' books);
// across facets it is AND. Each facet's counts are narrowed by the *other*
// facets' selections, so a count says how many works ticking that concept
// would show.
//
// The images facet (#160) is a boolean one, on by default: with no `images`
// parameter only the works with an image are shown, and `?images=off` shows
// them all. Its book set comes from the grid (the cards with an <img>), so it
// needs no index and is applied before the others have loaded — the grid
// narrows to the illustrated works as soon as this script runs.

import { HierarchicalFacet } from "./hierarchical-facet.js";
import { FlatFacet } from "./flat-facet.js";
import { BooleanFacet } from "./boolean-facet.js";

customElements.define("construction-facet", class extends HierarchicalFacet {});
customElements.define("subject-facet", class extends FlatFacet {});
customElements.define("place-facet", class extends FlatFacet {});
customElements.define("image-facet", class extends BooleanFacet {});

const sidebar = document.querySelector(".filters");
const countLine = document.querySelector(".page-intro .count");
const noResults = document.querySelector(".no-results");
const grid = document.querySelector(".book-grid");
const total = Number(countLine.dataset.total);

// item key -> card, collected once.
const cards = new Map(
  [...document.querySelectorAll(".book-grid li[data-key]")].map((li) => [li.dataset.key, li]));

// One entry per facet element: its URL parameter, its concept -> item keys
// index, the current selection, and (boolean facets) whether it is on by
// default.
const facets = [];

// Facets may share an index (Subject and Place both read subject-facet.json),
// so each is fetched once.
const indexes = new Map();
function fetchIndex(src) {
  if (!indexes.has(src)) {
    indexes.set(src, fetch(src).then((response) => {
      if (!response.ok) throw new Error(`${src}: HTTP ${response.status}`);
      return response.json();
    }));
  }
  return indexes.get(src);
}

// A facet with `data-category` takes only that category of its index.
async function load(element) {
  const index = await fetchIndex(element.dataset.src);
  const only = element.dataset.category;
  const books = new Map();
  const tree = {
    categories: index.categories.filter((category) => !only || category.key === only).map((category) => ({
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

// A boolean facet: one key, whose books are the cards matching `data-cards`.
function boolean(element) {
  const items = new Set([...cards].filter(([, li]) => li.matches(element.dataset.cards)).map(([key]) => key));
  element.total = items.size;
  return {
    element,
    param: element.dataset.param,
    books: new Map([[element.key, items]]),
    selected: new Set(),
    defaultOn: element.dataset.default === "on",
  };
}

// Read each facet's selection from the URL, dropping keys its index doesn't know.
function readURL() {
  const params = new URLSearchParams(location.search);
  for (const facet of facets) {
    const value = params.get(facet.param) ?? "";
    if (facet.defaultOn) {
      facet.selected = new Set(value === "off" ? [] : [facet.element.key]);
      continue;
    }
    facet.selected = new Set(value.split(",").filter((key) => facet.books.has(key)));
  }
}

// Write the selection back, leaving any other query parameters alone. Keys are
// sorted so equal selections give the same URL.
function writeURL() {
  const params = new URLSearchParams(location.search);
  for (const facet of facets) {
    if (facet.defaultOn) {
      if (facet.selected.size) params.delete(facet.param);
      else params.set(facet.param, "off");
      continue;
    }
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
  // facet -> that union, for the facets with a selection.
  const byFacet = new Map(facets
    .filter((facet) => facet.selected.size)
    .map((facet) => {
      const union = new Set();
      for (const key of facet.selected) for (const item of facet.books.get(key)) union.add(item);
      return [facet, union];
    }));
  const unions = [...byFacet.values()];

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

  countLine.textContent = unions.length ? `${shown} of ${total} books` : `${total} books`;
  noResults.hidden = shown > 0;
  for (const facet of facets) {
    facet.element.selected = facet.selected;
    facet.element.counts = narrowedCounts(facet, byFacet);
  }
}

// A facet's concept -> count of its books that pass every *other* active
// facet, or null (the overall counts) when no other facet is active.
function narrowedCounts(facet, byFacet) {
  const others = [...byFacet].filter(([f]) => f !== facet).map(([, union]) => union);
  if (!others.length) return null;
  const counts = new Map();
  for (const [key, items] of facet.books) {
    let n = 0;
    for (const item of items) if (others.every((union) => union.has(item))) n += 1;
    counts.set(key, n);
  }
  return counts;
}

async function init() {
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

  // The boolean facets first: they need no index, and the images one is on by
  // default, so applying it now keeps the full grid from lingering while the
  // indexes load. The sidebar shows from here, so it can always be turned off.
  facets.push(...[...sidebar.querySelectorAll("[data-cards][data-param]")].map(boolean));
  readURL();
  apply();
  sidebar.hidden = false;

  const elements = [...sidebar.querySelectorAll("[data-src][data-param]")];
  facets.push(...await Promise.all(elements.map(load)));
  readURL();
  apply();
}

// If an index fails to load, its facets stay empty; the boolean ones still work.
init().catch((error) => console.error("Filters unavailable:", error));
