# Construction vocabulary vs. the BARD glossary

A term-level comparison of our SKOS construction scheme (`sources/construction-methods.ttl`) against the
Book Arts Research Database glossary (`docs/bard-glossary.pdf`). **Report only — no vocabulary changes have been made.**

Our scheme: **225 concepts**. BARD glossary: **208 terms**.

| | our concepts | |
|---|---:|---|
| Identical to a BARD term | 35 | same string, nothing to do |
| Match differing only in form | 47 | case, plural, punctuation, or a BARD `X/Y` alternate — **the cheap alignment wins** |
| Close match | 9 | same idea, different wording — needs a judgment call |
| Partial / broader-narrower | 21 | ours is broader or narrower than the BARD term |
| **No BARD counterpart** | **113** | see §1 |

Also: **6** concepts match a BARD term filed under a *different* category (§4), and
**108 of BARD's terms** have no counterpart in our scheme (§5).

## Method and caveats

Terms were extracted from the PDF text layer: a term is a single-line block under a category heading, with each
category's list terminated by its catch-all `Other` entry. Matching normalizes case, accents, parentheticals and
plurals, expands BARD's `X/Y` alternates and `Papermaking Fiber: X` prefixes, then falls back to fuzzy ratio (≥0.82)
and word-subset containment. Where a term matched several BARD entries, the one in the same category won.

Two consequences worth keeping in mind while reading:

- **`Hand Papermaking Traditions` has no terms in the glossary.** The section is an explanatory essay only, which is
  why no row in `decisions.csv` uses that category — the vocabulary to fill it does not exist in this document.
- Fuzzy and partial matches are *candidates*, not findings. A few are wrong on inspection (e.g. `Stab binding` →
  `Post Binding` scores 0.83 but they are different structures). Read §3 as a worklist, not a set of conclusions.

## §1 Our terms with no BARD counterpart

113 concepts. These split into a few recognizable kinds, noted per category.

### Materials — 25

Mostly specific commercial or everyday substrates BARD does not enumerate (it stops at `Fabric`, `Decorative Paper`, `Plastics`). Several are arguably narrower instances of a BARD term we already use.

> Artificial fur; Bamboo; Beads; Bristol board; Burlap; Canvas; Cardboard; Construction paper; Dowel; Felt; Glassine; Gouache; Japanese paper (handmade paper); Metallic paper; Mylar; Nylon; Papier-mâché; Rag paper; Recycled material; String; Tissue paper; Transparent paper; Vinyl; Watercolor (paint); Yarn

### Process/Technique — 22

Largely finer-grained print processes. BARD deliberately stops at `Etching`, `Engraving` and `Intaglio Printing` — it has no aquatint, drypoint, photogravure or photolithography — so these are genuine BARD gaps rather than naming mismatches.

> Aquatint; Asemic writing; Baking or cooking; Collograph printing; Crochet; Cut-paper work; Drypoint; Embroidery; Gocco printing; Halftone (color effect); Hand binding; Hand composition; Monotype (planographic printing); Overprinting; Palladium process; Photocollage; Photogravure; Photolithography; Pyrography; Sculpture; Side stitching; Typewriting

### Structure/Physical Format — 39

The largest group, and the most mixed: some are real structures BARD omits (`Coptic binding`, `Ethiopian bindings`), but many are *carrier* or *document* types (`Blu-Ray-Disc`, `Phonograph record`, `Sound recording`, `Video recording`, `Playing cards`, `Sports cards`) that may not belong in a construction vocabulary at all.

> Backless binding; Blu-Ray-Disc; Bookmark; Braille; Broadsheet; Chicago screw binding; Coptic binding; Corrugated board bindings; Cutout; Dioramas; Double leaf; Endpapers; Ethiopian bindings; Exquisite corpse; Flyer; Folded; Frontispiece; Game; Greeting card; Handscrolls; Interleaving; Non-adhesive binding; One-of-a-kind; Paper doll; Phonograph record; Playing cards; Postage stamp; Sound recording; Split-page book; Sports cards; Staple binding; Tab binding; Textured book; Translucent element; Transparent element; Triptychs; Unbound sheets; Unopened book; Video recording

### Enclosure — 5

Small set; BARD lists only 8 enclosure terms.

> Bag; Box set; Dust jacket; Film canister; Pot (vessel)

### Genre/Form — 22

Bibliographic genre terms inherited from the MARC headings (LCGFT/FAST). BARD's Genre/Form list is much shorter and artist-book-specific, so most of ours have no counterpart by design.

> Anthology; Anxometric projection; Bestiary; Board book; Calendar; Chart or diagram; Collective work; Coloring book; Diary; Dictionary; Discography; E-book; Exhibition catalog; Facsimile; Letters (correspondence); Multimedia work; Obituary; Photobook; Play; Short stories; Song; Video game

## §2 Exact matches

### Identical — 35

Already aligned; listed for completeness.

> Biography; Broadside; Chapbook; Collage; Cookbook; Cord; Die-cutting; Drawing; Embossing; Engraving; Envelope; Ephemera; Erasure; Etching; Fiction; Ink; List; Lithography; Marbling; Metal; Photography; Pochoir; Poetry; Portfolio; Postcard; Poster; Quotations; Ribbon; Scroll; Slipcase; Stamping (by hand); Stenciling; Thread; Wood; Zine

### Differing only in form — 47

Same concept, different surface. **This is the cheapest alignment work**: adopting the BARD spelling here costs
nothing semantically. Sorted by category.

| our label | BARD term | difference |
|---|---|---|
| Book cloth | Book Cloth | capitalization |
| Decorative paper | Decorative Paper | capitalization |
| Found object (manmade) | Found Object/s | BARD offers alternates |
| Handmade paper | Handmade Paper | capitalization |
| Magnet | Magnet/s | plural form |
| Mixed media | Mixed Media | capitalization |
| Natural material | Natural Materials (sticks, rocks, flora…) | BARD qualifies with examples |
| Natural material (animal) | Natural Materials (sticks, rocks, flora…) | BARD qualifies with examples |
| Paint | Paint (acrylic, gouache, watercolor) | BARD qualifies with examples |
| Pigment | Pigments | plural form |
| Plastic | Plastics (acrylic, acetate, plexiglass) | BARD qualifies with examples |
| Textile | Papermaking Fiber: Textiles (linen, cotton, hemp) | BARD qualifies with examples |
| Blind embossing | Blind Embossing/Debossing | BARD offers alternates |
| Chine collé | Chine-collé | wording |
| Debossing | Blind Embossing/Debossing | BARD offers alternates |
| Digital printing | Digital Printing | capitalization |
| Gelatin printing | Gelatin Printing | capitalization |
| Hand coloring | Hand-coloring | wording |
| Handwriting | Handlettering/Handwriting | BARD offers alternates |
| Hot stamping | Hot Stamping | capitalization |
| Inkjet printing | Inkjet Printing | capitalization |
| Intaglio printing | Intaglio Printing | capitalization |
| Laser cutting | Laser Cutting/CNC cutting | BARD offers alternates |
| Letterpress printing | Letterpress Printing (image) | BARD qualifies with examples |
| Linoleum block printing | Linoleum Block Printing | capitalization |
| Offset lithography | Offset Lithography | capitalization |
| Pulp painting | Pulp Painting (Pulp Imaging) | BARD qualifies with examples |
| Relief printing | Relief Printing | capitalization |
| Screen printing | Screen Printing | capitalization |
| Stamping | Stamping (by hand) | BARD qualifies with examples |
| Woodblock printing | Woodblock Printing | capitalization |
| Altered book | Altered Book | capitalization |
| Carousel book | Carousel Book | capitalization |
| Comb binding | Spiral/Comb Binding | BARD offers alternates |
| Flag book | Flag Book | capitalization |
| Flip book | Flip Book | capitalization |
| Miniature book | Miniature Book | capitalization |
| Pamphlet binding | Pamphlet Binding | capitalization |
| Perfect binding | Perfect Binding | capitalization |
| Pop-up element | Pop-up Elements | plural form |
| Sculptural bookwork | Sculptural Bookwork | capitalization |
| Spiral binding | Spiral/Comb Binding | BARD offers alternates |
| Stickers | Sticker/s | plural form |
| Tunnel book | Tunnel Book | capitalization |
| Wrapper | Wrapper (paper or card) | BARD qualifies with examples |
| Found text | Found Text | capitalization |
| Graphic novel | Graphic Novel | capitalization |

## §3 Close and partial matches

30 concepts. Each needs a human call: adopt BARD's term, keep ours as a narrower concept, or
reject the match. `score` is string similarity (close) or word overlap (partial) — low scores are weak evidence.

| our label | our category | BARD term | BARD category | kind | score |
|---|---|---|---|---|---:|
| Papermaking fiber (paper mulberry) | Materials | Papermaking Fiber: Mix | Materials | close | 0.872 |
| Papermaking fiber (textile) | Materials | Papermaking Fiber: Mix | Materials | close | 0.872 |
| Papermaking fiber (wood) | Materials | Papermaking Fiber: Mix | Materials | close | 0.872 |
| Saddle stitching | Process/Technique | Saddle Stitch | Structure/Physical Format ⚠️ | close | 0.897 |
| Hardcover | Structure/Physical Format | Hard Cover (binder’s board/wood, etc.) | Structure/Physical Format | close | 0.947 |
| Movable element | Structure/Physical Format | Moveable Element/s | Structure/Physical Format | close | 0.938 |
| Volvelle | Structure/Physical Format | Vovelle/Wheel | Structure/Physical Format | close | 0.933 |
| Foldout | Structure/Physical Format | Fold-out/s | Structure/Physical Format | close | 0.875 |
| Stab binding | Structure/Physical Format | Post Binding | Structure/Physical Format | close | 0.833 |
| Cloth | Materials | Book Cloth | Materials | partial | 0.5 |
| Paper | Materials | Decorative Paper | Materials | partial | 0.5 |
| Vellum | Materials | Limp Vellum Binding | Structure/Physical Format ⚠️ | partial | 0.333 |
| Handmade | Process/Technique | Handmade Paper | Materials ⚠️ | partial | 0.5 |
| Painting (process) | Process/Technique | Pulp Painting (Pulp Imaging) | Process/Technique | partial | 0.5 |
| Photopolymer plate | Process/Technique | Photopolymer (image) | Process/Technique | partial | 0.5 |
| Photocopy | Process/Technique | Reprographic Printing (Photocopy/Laser) | Process/Technique | partial | 0.333 |
| Dos-à-dos binding | Structure/Physical Format | Dos-a-dos | Structure/Physical Format | partial | 0.667 |
| Fold-out book | Structure/Physical Format | Fold-out/s | Structure/Physical Format | partial | 0.667 |
| Limp binding | Structure/Physical Format | Limp Vellum Binding | Structure/Physical Format | partial | 0.667 |
| Accordion binding | Structure/Physical Format | Accordion | Structure/Physical Format | partial | 0.5 |
| Concertina binding | Structure/Physical Format | Concertina | Structure/Physical Format | partial | 0.5 |
| Map | Structure/Physical Format | Map Fold | Structure/Physical Format | partial | 0.5 |
| Blocks (shaped masses) | Structure/Physical Format | Linoleum Block Printing | Process/Technique ⚠️ | partial | 0.333 |
| Box | Enclosure | Lidded Box | Enclosure | partial | 0.5 |
| Case | Enclosure | Case Binding | Structure/Physical Format ⚠️ | partial | 0.5 |
| Comics | Genre/Form | Comix/Comic Book | Genre/Form | partial | 0.5 |
| Multiple | Genre/Form | Multiple-genre | Genre/Form | partial | 0.5 |
| Novel | Genre/Form | Graphic Novel | Genre/Form | partial | 0.5 |
| Wordless book | Genre/Form | Wordless/Visual | Genre/Form | partial | 0.5 |
| Guide or manual | Genre/Form | Guidebook/Manual/Reference | Genre/Form | partial | 0.333 |

## §4 Category disagreements

Concepts whose best BARD match sits in a different category. Worth checking — either our categorization or the
match is wrong.

| our label | our category | BARD term | BARD category | match kind |
|---|---|---|---|---|
| Blocks (shaped masses) | Structure/Physical Format | Linoleum Block Printing | Process/Technique | partial |
| Case | Enclosure | Case Binding | Structure/Physical Format | partial |
| Handmade | Process/Technique | Handmade Paper | Materials | partial |
| Saddle stitching | Process/Technique | Saddle Stitch | Structure/Physical Format | close |
| Stickers | Structure/Physical Format | Sticker/s | Materials | exact |
| Vellum | Materials | Limp Vellum Binding | Structure/Physical Format | partial |

## §5 BARD terms we do not use

108 of 208 BARD terms have no counterpart here. Most reflect the collection: we can only
name what the MARC records describe. Useful mainly as a checklist if the scheme is ever extended by hand.

**Materials** (30) — Binder’s Board; Bone; Bosses; Clasps; Clay; Dyes; Fabric; Faux Leather; Glass; Gold Leaf; Graphite; Leather; Machine-made Paper; Mould-made Paper; Papyrus; Parchment; Paste Paper; Wax; Wooden Boards; Papermaking Fiber: Abaca; Papermaking Fiber: Bark (not pulped); Papermaking Fiber: Cotton linter or half-stuff; Papermaking Fiber: Flax; Papermaking Fiber: Gampi; Papermaking Fiber: Hemp; Papermaking Fiber: Mitsumata; Papermaking Fiber: Paper Mulberry (Kozo / Dak); Papermaking Fiber: Recycled Papers; Papermaking Fiber: Sulfite/Wood; Papermaking Fiber: Other

**Process/Technique** (28) — Blind Tooling; Blow-outs (hand papermaking); Collagraph/Sandragraph; Cyanotype/Blue Printing; Hand Papermaking Formation: Laminating/Beating (not pulped); Hand Papermaking Formation: Pouring (into a mould or deckle box); Hand Papermaking Formation: Floating (a mould); Handprinting (Baren, Spoon); Hectography/Spirit Duplication; Illustration; Inclusions; Letterpress Printing (type); Monoprinting; Monotyping; Paper Cutting (by hand); Paste Papers; Photopolymer (type); Pressure Printing; Pulp Printing; Risograph Printing; Suminagashi; Trace Monoprinting; Transfers; Typsetting: Digital; Typsetting: Metal; Typsetting: Wood; Watermark/s; Wood Engraving

**Structure/Physical Format** (36) — Accordion Variations; Album; Belly Band/s; Boustrophedon/Meander; Compound Structure; Double Pamphlet; Drum Leaf Binding; Endhands; Exposed Sewing; Flexagon; Folios (loose, unsewn); French-fold; Gatefold; Jacob’s Ladder; In-Boards Binding; Japanese Multi-Section Binding; Laced-on/Laced-in Binding; Lapped Case/Three Piece Binding; Limp Paper/Paper Case Binding; Link Stitch; Long & Link Stitch; Long Stitch; See Long & Link stitch; Loose Sheets; Mobius Strip; Multi-section Binding; Palm Leaf Binding; Section; Single-section Binding; Single-sheet Book; Soft Cover; Stab/Side-sewn; Stiff Leaf; Turkish Map Fold; Web-stitch/French Sewn Binding; Wire-edge Binding

**Enclosure** (3) — Clamshell/Drop-spine Box; Four-flap Wrapper; Hinged-lid Box

**Genre/Form** (11) — Abecedarium; Catalogue; Extracted Text; Fragments; Index; Memoir; Non-fiction; Performative Element; Photo Bookwork; Prose; Trade

