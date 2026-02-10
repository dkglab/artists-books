## Scope and purpose
Basic Level: To connect artists' books within the Sloane Art Library Special Collection to the reference books about artists' books also held by the collection so someone using the graph could easily see what books are referenced in which books and on what page numbers.

Nice to haves: location held, other related works, additional creators and roles information from Book Arts Research Database or book itself, links to photos, distinction between pages where the book is mentioned versus pages where it is photographed, rarity of the book maybe by number held in worldcat, additional material or subject information

## Information source
Zotero ABCI and Ref resources -- completed; UNC Library Catalog

```mermaid
flowchart TD
  Reference_book -->|written by| Author
  Artists_book -->|created by| Creator
  Reference_book -->|on page number| Page_number
  Page_number -->|cites|Artists_book