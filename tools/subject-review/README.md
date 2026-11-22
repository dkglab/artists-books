# subject-review

The shared subject review page, published as a claude.ai artifact
(https://claude.ai/artifact/PoWThnZYgXgGKjc2qQeizw). Reviewers work through
three queues on it at once, live:

- **Two passes** (#164): the 1,113 headings in
  `sources/subjects/pr164-review.csv`, where Priya's pass differs from
  `decisions.csv` (Mert's pass and everything before it), in four tabs by what
  Priya did. Keep the current row, use Priya's, edit it, or mark it unsure.
- **Draft places** (#108): the geographic headings still noted `auto-seeded
  draft; review`, less those in Two passes. Confirm, leave out, edit (often
  filing a subdivided heading under its place to merge it), or mark unsure.
- **Subject or construction** (#108): `construction-overlap-review.csv`'s
  groups 1, 2 and 5 (group 3, Screen prints, is settled). Each heading goes to
  construction, subjects, both or neither. A construction decision checks the
  pre-filled concept or picks one, and writes `construction/decisions.csv`.
  The 16 headings also in Two passes get only their construction side here.

The page flags what the build would reject (no category or label, a concept ID
that isn't a slug, a concept with two labels) before a decision counts as done,
and any decision clears the seed's `...; review` note. A label can also be set
once for a whole subject concept, which relabels every heading under it.

Left for later, as agreed in #108: the `complex` headings and the `needs
exactMatch` ones.

Decisions live in the artifact's shared database: `rows` (one document per
heading and queue, with `q` and the tab `g`) and `concepts` (concept-wide
labels).

- `build_data.py OUT`: builds `data.json` (gitignored) from the committed
  sources. Rebuild and republish it when those change.
- `index.html`: the page.
- `pull_decisions.py DIR`: writes a saved copy of both collections into
  `subjects/decisions.csv` and `construction/decisions.csv`, with the same
  checks as the page. It writes nothing if any check fails. Then rebuild with
  `make -C sources subject-terms.ttl construction-methods.ttl`.
