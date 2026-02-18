
##Simplest Version

| Class | Description |
| ----- | ----------- |
|Book|A book.|
|Reference_book|Subclass of book. Listed in the Zotero Ref resources -- completed file. Written about Artists' Books.|
|Artist_book|Subclass of book. Listed in the Zotero ABCI file. Book created by an artist as a work of art.| 
|Agent|Something that can do things.|
|Person|Subclass of Agent. A human being.|
|Group|Subclass of Agent. A group of agents.|
|Citation| Is a relationship between an Artist Book and a Reference Book.|

| Properties | Description |
| ----- | ----------- |
|written by| Relates an Agent to a Book they wrote.|
|created by| Relates an Agent to a Book they created.|
|contributed to| Relates a Agent to a Book they contributed to.|
|uses| Relates an Artist Book to a Book it uses in its creation.|
|related to| Relates an Artist Book to a Book that it takes inspiration from or is responding to.|


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