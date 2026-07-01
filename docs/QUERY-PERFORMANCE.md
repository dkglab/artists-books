# Query performance — avoiding blowup in the construct step

Notes on keeping `queries/artists-books.rq` (and any future
SPARQL-Anything query) fast. The construct step reads the source CSVs and
`sources/marc/artists-books-marc.xml` through SPARQL-Anything's Facade-X and emits the
RDF graph; it is the one place in the pipeline where a careless pattern turns a
6-second build into a 5-minute one.

## The one rule that matters most: never traverse with a variable predicate

SPARQL-Anything represents XML/JSON as **Facade-X**: every element is a container
whose children hang off numbered membership properties `rdf:_1, rdf:_2, …`. It is
tempting to walk those children with a variable-predicate triple:

```sparql
# DON'T — matches rdf:_1..rdf:_N via a variable predicate
?record ?p   ?datafield .
?datafield ?q ?subfield .
```

The Facade-X in-memory graph evaluates `?s ?VAR ?o` as a **full scan of the
graph**. One scan is slow; **cross-joining two of them per record is quadratic**
and is what blows the query up. Use the `fx:anySlot` magic property instead:

```sparql
PREFIX fx: <http://sparql.xyz/facade-x/ns/>

# DO — fx:anySlot enumerates the members of a bound container natively
?record    fx:anySlot ?datafield .
?datafield fx:anySlot ?subfield .
```

`fx:anySlot` is a property function: given a bound subject it lists that
container's members directly, with no scan. Functionally it matches exactly the
same things as `?record ?p ?child` — it is a drop-in replacement.

### Measured impact (MARC creator extraction, 1340 records)

| query | time |
|-------|-----:|
| Triplify the XML + count records (parsing only) | 2 s |
| Creator extraction, **variable predicate**, one side | 84 s |
| Creator extraction, **variable predicate**, with the 999/itemKey join | > 150 s (timed out) |
| Creator extraction, **`fx:anySlot`**, one side | 4 s |
| **Full construct, `fx:anySlot`** | **6 s** |

The output was byte-for-byte identical before and after — only the access path
changed. Note that XML triplification itself is cheap (2 s); if a query is slow,
the scans are the cause, not the parsing.

## How to diagnose

Run the query with `-e` (ARQ explain). The plan prints to stderr before
execution, so you see it immediately even when the run itself is slow:

```sh
java -jar tools/sparql-anything/sparql-anything.jar -e -q queries/artists-books.rq > /dev/null 2> explain.txt
```

In `explain.txt`, look at the `ALGEBRA` block and the `Reorder/generic` lines:

- **Red flag:** a `(triple ?s ?var ?o)` inside a `(bgp …)` — a variable-predicate
  scan. Two of them in one BGP is the quadratic case.
- **Healthy:** `fx:anySlot` splits the BGP into small, separately-anchored pieces
  (each starting from a bound subject), so the optimizer never has to scan.

To attribute time between parsing and querying, time a trivial `COUNT(*)` over
the source first (that forces a full triplification but no join). If that is fast
and the real query is slow, the join is at fault.

## Other things that keep the construct fast

- **Anchor every traversal from something bound.** Reach members from a known
  container (`?record fx:anySlot …`), not from an unbound `?member` upward. Each
  `fx:anySlot` whose subject is already bound is cheap.

- **Fold multi-valued fields with an aggregating sub-SELECT.** A MARC creator may
  carry several `$1` (VIAF *and* ISNI) and several `$e` roles. Let those multiply
  inside a `SELECT … GROUP BY` that collapses to one row per creator (or per
  creator+role) *before* the CONSTRUCT, so you don't emit duplicate agents or
  fan out the rest of the query. See the creator sub-SELECT in the construct.

- **Join lookup tables on a private key, not the shared variable.** `OPTIONAL {
  VALUES (?key ?v) {…} }` that binds the *same* variable you're matching will,
  when that variable is unbound on a row, match **every** row of the table (an
  unbound variable is compatible with anything) — a silent fan-out. Bind a
  separate key variable and join with `FILTER(?tableKey = ?key)` so an unbound
  key matches nothing. (This is how the relator-term → LC relator URI map is
  wired.)

- **Keep `OPTIONAL` blocks small and self-contained.** Each should match a single
  subfield and bind one value; large optionals re-multiply intermediate results.

- **Guard minted URIs so empty nodes aren't emitted.** Build a per-row URI only
  when its inputs are bound (e.g. `?contribution` is minted from the creator key,
  which is unbound when there is no creator), so CONSTRUCT drops the whole block
  instead of writing a dangling typed-but-empty node.

## Quick checklist before committing a construct change

1. Did I add any `?s ?var ?o` to walk Facade-X members? Replace with `fx:anySlot`.
2. Can any pattern multiply rows (repeated subfields, a `VALUES` join on a shared
   var)? Aggregate it away or join on a private key.
3. `time` the rebuild (`make graph/artists-books.ttl`). It should be seconds. If
   it is not, run with `-e` and look for variable-predicate triples in the BGP.
