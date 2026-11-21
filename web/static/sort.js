// The homepage grid's sort order (#22): by title (as Snowman renders it), or
// by date, oldest or newest first. It is kept in the query string
// (?sort=date, ?sort=date-desc) beside the facets' parameters, which
// facets.js leaves alone, as this leaves theirs.
//
// The date orders sort on each card's data-year, the normalized bf:date,
// never on the date the card displays ("c1978", "199-?", "1972–1974"). Within
// a year the cards keep their title order (Array.prototype.sort is stable),
// and the cards with no year come last either way.

const grid = document.querySelector(".book-grid");
const control = document.querySelector(".sort");
const select = control.querySelector("select");

const byTitle = [...grid.children];
const year = (li) => (li.dataset.year ? Number(li.dataset.year) : null);
const dated = byTitle.filter((li) => year(li) !== null);
const undated = byTitle.filter((li) => year(li) === null);
const orders = {
  title: byTitle,
  date: [...[...dated].sort((a, b) => year(a) - year(b)), ...undated],
  "date-desc": [...[...dated].sort((a, b) => year(b) - year(a)), ...undated],
};

function current() {
  const value = new URLSearchParams(location.search).get("sort");
  return Object.hasOwn(orders, value) ? value : "title";
}

// Reordered with the grid detached, as facets.js toggles the cards, so the
// ~7,900 moves cost one relayout.
function apply(order) {
  select.value = order;
  const parent = grid.parentNode;
  const next = grid.nextSibling;
  grid.remove();
  grid.append(...orders[order]);
  parent.insertBefore(grid, next);
}

select.addEventListener("change", () => {
  const params = new URLSearchParams(location.search);
  if (select.value === "title") params.delete("sort");
  else params.set("sort", select.value);
  const query = params.toString().replace(/%2C/gi, ",");
  history.pushState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
  apply(select.value);
});
window.addEventListener("popstate", () => apply(current()));

if (current() !== "title") apply(current());
else select.value = "title";
control.hidden = false;
