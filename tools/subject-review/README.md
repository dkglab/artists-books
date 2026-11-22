# subject-review

The shared subject review page for issue #225, published as a claude.ai
artifact (https://claude.ai/artifact/PoWThnZYgXgGKjc2qQeizw). Reviewers work
through four queues on it at once, live:

- **Reconcile the two passes**: the 1,113 headings in
  `sources/subjects/pr164-review.csv`, where Priya's pass in #164 differs from
  `decisions.csv` (Mert's pass and everything before it), in four tabs by what
  Priya did. Keep the current row, use Priya's, edit it, or mark it unsure.
- **Draft places**: the geographic headings still noted `auto-seeded draft;
  review`, less those in the first queue. Confirm, leave out, edit (often
  filing a subdivided heading under its place to merge it), or mark unsure.
- **Subject or construction**: `construction-overlap-review.csv`'s groups 1, 2
  and 5 (group 3, Screen prints, is settled). Each heading goes to
  construction, subjects, both or neither. A construction decision checks the
  pre-filled concept or picks one, and writes `construction/decisions.csv`.
  The ~100 label-match pre-fills (#108) are held at `include=n`, off the site,
  until a decision here confirms them. The
  16 headings also in the first queue get only their construction side here.
- **Labels**: subject concepts that share a label (merge them, or keep them
  apart with distinct labels) and mis-cased labels, with a suggestion taken
  from the concept's own LCSH/FAST heading where one matches but for case.

The page flags what the build would reject (no category or label, a concept ID
that isn't a slug, a concept with two labels) before a decision counts as done,
and any decision clears the seed's `...; review` note.

The `complex` headings and the `needs exactMatch` ones are set aside for later
(see #225).

Decisions live in the artifact's shared database: `rows` (one document per
heading and queue, with `q` and the tab `g`) and `concepts` (per subject
concept: a label for the whole concept, or a merge into another).

- `build_data.py OUT`: builds `data.json` (gitignored) from the committed
  sources. Rebuild and republish it when those change.
- `index.html`: the page.
- `pull_decisions.py DIR`: writes a saved copy of both collections into
  `subjects/decisions.csv` and `construction/decisions.csv`, with the same
  checks as the page, and keeps Priya's finer categories (`topical-people`,
  `geographic-city`, ...) for the rows taken from her side in
  `subjects/fine-categories.csv`. It writes nothing if any check fails. Then rebuild with
  `make -C sources subject-terms.ttl construction-methods.ttl`.
