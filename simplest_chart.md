```mermaid
flowchart TD
Book -->|subclass| Reference_Book
Reference_Book -->|authored_by|Agent
Reference_Book -->|contributed_to_by|Agent
Reference_Book -->|published_by|Agent    
Reference_Book -->|published_in|Year
Reference_Book -->|published_in|Location
Reference_Book -->|is|Edition_Number
Reference_Book -->|related_to|Book
Reference_Book -->|identified_by|ISBN
Reference_Book -->|identified_by|OCLC
Book -->|subclass|Artist_Book
Artist_Book -->|created_by|Agent
Artist_Book -->|contributed_to_by|Agent
Artist_Book -->|image_of|Link_to_photos
Artist_Book -->|published_by|Agent
Artist_Book -->|published_in|Year
Artist_Book -->|published_in|Location
Artist_Book -->|described_as|Description
Artist_Book -->|indentifed_by|ISBN
Artist_Book -->|indentifed_by|OCLC
Artist_Book -->|has|Form_Description
Book -->|held_by|Worldcat_link
Citation -->|cited_by|Reference_Book
Citation -->|cites|Artist_Book
Citation -->|includes|Image_of_Artist_Book
Citation -->|includes|Text_Only
Citation -->|on_page_number|on_page_number
```