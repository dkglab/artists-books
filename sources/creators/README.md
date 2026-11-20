# Creator authority (issue #170)

One `bf:Agent` per real person or body, shared by both construct queries.

## Why

The construct queries used to decide a creator's identity **one MARC field at a
time**: the field's VIAF/ISNI (`$1`), else `ab:creator/<LC id>` (`$0`), else a
slug of `$a`. How well a heading is controlled depends on *which catalogue the
record came from*, not on who the person is, so the same heading
(`100 $a Drucker, Johanna, $d 1952-`) arrived three ways: UNC's record carried
`$0` and `$1` (VIAF agent), Clark's only `$0` (LC-id agent), Harvard's and LC's
neither (slug agent). The synthesized eHive/UW records never carry `$0`/`$1`, so
every creator there landed on the slug path. Across both graphs, 762 names were
spread over 1,774 agent URIs.

## Pipeline

Same *mine → curate → build* shape as `construction/` and `subjects/`.
Regenerate with `make -C sources <target>` (GNU Make ≥ 4.3).

| File | Made by | What |
|---|---|---|
| `occurrences.csv` | `mine.py` | Every 100/110/111/700/710/711 field of both MARC directories: source (`book`/`reference`), canonical key, tag, the `$a` exactly as the queries see it (`name`), full heading, dates, and its LC id / VIAF / ISNI / GND / WorldCat Entity ids. |
| `zotero-creators.csv` | `mine.py` | The structured Zotero creators (last, first, single-field mode, creator type) of every canonical artists' book. |
| `lc-viaf.csv` | `reconcile.py` | **Frozen** id.loc.gov lookup per LC id: VIAF, ISNI, authorized label, and the successor of a deprecated id. External and resumable, like the MARC harvest; committed. |
| `decisions.csv` | a person | Hand overrides (below). Not generated. |
| `authority.csv` | `build.py` | One row per resolved agent: key, URI, label, ids, work/occurrence counts, every heading seen. For reading and review. |
| `agents.csv` | `build.py` | **The join table both construct queries read**: `(source, canonicalKey, tag, name) → agentKey, agentUri, label`, plus `tag = zotero` rows for the fallback. |
| `review.csv` | `build.py` | What the rules declined to decide. |

`mine.py` reads the MARC directories, `zotero.sqlite` and `artists-books.csv`,
none of which is a make prerequisite (as for the other mining targets), so after
a re-harvest or re-dedup rerun with `make -C sources -B creators/occurrences.csv`.

## Clustering rules (`build.py`)

Union-find over field occurrences:

1. **Identifiers.** Occurrences sharing an LC id, VIAF, ISNI, GND id or WorldCat
   Entity are one agent, and ids in one field link each other. `lc-viaf.csv`
   adds each LC id's VIAF/ISNI and maps a deprecated LC id to its successor.
   A **name/title field** (one with `$t`) contributes no ids: its `$0`/`$1`
   identify the *work*, and reading them as the person's split Cendrars, Paz
   and Perrault across several LC ids.
2. **Same dated heading.** Personal names with the same name *and* the same
   birth year (`Drucker, Johanna, 1952-` / `…, 1952-2030`) are one agent;
   corporate and meeting names with the same full heading likewise. A merge that
   would put two different LC ids in one agent is refused and reported
   (`conflicting-ids`); the group's id-less part is still pooled.
3. **Name joins**, for agents still without an LC/VIAF/ISNI anchor (a GND id
   alone can't contradict an LC one, so GND-only agents count as unanchored):
   - a *dated* one joins the single anchored agent of that name whose birth
     year doesn't contradict it;
   - then every *undated* one of that name is pooled and joins the single other
     agent carrying the name.
   Several candidates → `review.csv`, and it stays a local agent of its own.

Name keys drop accents, case, punctuation and spacing, so `Di Palma`/`DiPalma`
and `Van Abbe-Museum`/`Van Abbemuseum` meet; the letters must still agree.

**URI**: VIAF (LC's current one when the agent has an LC id — VIAF renumbers
merged clusters, so a MARC `$1` can be stale), else ISNI, else
`ab:creator/<lcId>`, else `ab:creator/<slug of label>`. **Label**: LC's
authorized heading when the agent has an LC id, else its commonest controlled,
then dated, then any heading — exactly one `rdfs:label` per agent.

**Zotero fallback.** A book with no MARC creator field is credited from its
Zotero creators, matched by name key to an agent only when exactly one agent
carries the name. Unmatched Zotero names are not minted as new agents. Artist,
author and creator types become `bflc:PrimaryContribution` (the equivalent of a
1xx) so the site's cards credit them.

## `decisions.csv`

```
action,a,b,note
merge,lc:n86821635,lc:nb2006019729,same person: LC duplicate
separate,name:phillipstom,,the undated "Phillips, Tom" is not resolvable
label,lc:n81067311,"Drucker, Johanna, 1952-",
```

- `merge a b` — union the agents holding keys `a` and `b`.
- `separate a` — exempt a name key or heading key from rules 2–3 (the heading
  stays its own agent).
- `label a b` — set the preferred label of the agent holding `a` to `b`.

Keys are typed: `lc:`, `viaf:`, `isni:`, `gnd:`, `name:<name key>`,
`heading:<heading key>` — copy them from `review.csv`. A `merge` whose key no
longer exists is reported as `stale-decision`.

## Join mechanics

The queries join `agents.csv` on `?canonical_key ?ctag ?creator_name` inside a
sub-SELECT (one CSV read, hash join — see `docs/QUERY-PERFORMANCE.md`).
`name` must therefore be byte-identical to the query's `?creator_name`.
`mine.py` mirrors SPARQL-Anything here: its XML reader trims each text chunk and
an entity splits the chunks, so `Peter &amp; Donna Thomas` reaches SPARQL as
`Peter&Donna Thomas` (which is also why the old graph *labelled* it that way).
A record with two same-tag fields that share `$a` but differ in `$b`/`$d`
(`Scripps College` / `Scripps College. Press`) joins both agents.

## Results (at #170)

| | before | after |
|---|---|---|
| agents (both graphs) | 7,251 | 6,274 |
| names split over several agents | 762 over 1,774 URIs | 18 over 40 |
| works with any creator | 5,818 | 6,737 |
| works with a primary creator | 5,234 | 6,137 |
| Johanna Drucker | 3 agents (41 books, 6 refs) | 1 agent, 67 books, 6 refs |

The residue is mostly pairs of *distinct* LC records with one name (homonyms
such as Margaret Randall 1919-/1936-, or LC duplicates such as Helen Douglas
`n86821635`/`nb2006019729`) — for `decisions.csv`, not for a rule.
