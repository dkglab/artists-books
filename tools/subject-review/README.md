# subject-review

The shared page for reconciling the two subject passes in #164, published as a
claude.ai artifact (https://claude.ai/artifact/PoWThnZYgXgGKjc2qQeizw). It
covers the 1,113 headings in `sources/subjects/pr164-review.csv`, where Priya's
pass differs from `decisions.csv` (Mert's pass and everything before it).

For each heading, reviewers keep the current row, use Priya's, edit it, or mark
it unsure. The page shows both rows side by side, the books with the heading,
and the concept it sits under, with the other headings already filed there. It
flags what the build would reject (no category or label, a concept ID that
isn't a slug, a concept with two labels) before the decision counts as done. A
label can also be set once for a whole concept, which relabels every heading
under it.

Decisions live in the artifact's shared database, not in the page: `rows` (one
document per heading) and `concepts` (concept-wide labels).

- `build_data.py OUT`: builds `data.json` (gitignored) from the committed
  sources. Rebuild and republish it if `pr164-review.csv` or `decisions.csv`
  changes.
- `index.html`: the page.
- `pull_decisions.py DIR`: writes a saved copy of both collections into
  `decisions.csv`, with the same checks as the page. It writes nothing if any
  check fails. Then rebuild the scheme with `make -C sources subject-terms.ttl`.
