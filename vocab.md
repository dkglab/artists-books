
##Simplest Version

| Class | Description |
| ----- | ----------- |
|Book|A book.|
|Reference_book|Subclass of book. Listed in the Zotero Ref resources -- completed file. Written about Artists' Books.|
|Artist_book|Subclass of book. Listed in the Zotero ABCI file. Book created by an artist as a work of art.| 
|Creator|An entity that is credited with creating all or part of a book.|
|Author|Subclass of creator. Credited as author of a book.|
|Contributor|Contributed to a book but is not listed as a creator or subclass of creator.|

| Properties | Description |
| ----- | ----------- |
|written by| Relates an author to a book they wrote.|
|created by| Relates a creator to a book they created.|
|on page number| Assigns a number that is the page number in a Reference_book where the Artists_book is cited.|
|cites|Relates an Artists_book to a Reference_book that cites it.|
|contributed to| Relates a Contributor to a Book they contributed to.|



##Graph



  
```mermaid
flowchart TD
  %% Classes

    B("Book")
    AB("Artists' book")
    RB("Reference book")
    CR("Creator")
    AU("Author")
    CO("Contributor")
    INT("integer")
    
    %% Properties
    
    WB("written by")
    CB("created by")
    CT("contributed to")
    P{"on page number"}
    C("cites")
  
   %% Sub-class relations
RB -->|"is a subclass of"|B
AB -->|"is a subclass of"|B
AU -->|"is a subclass of"|CR

 WB-->|"domain"|B
 WB -->|"range"|CR
 CB -->|"domain"|B
 CB -->|"range"|CR
 CT -->|"domain"|B
 CT -->|"range"|CO
 P -->|"domain"|B
 P-->|"range"|INT
 C -->|"domain"|B
 C -->|"range"|B