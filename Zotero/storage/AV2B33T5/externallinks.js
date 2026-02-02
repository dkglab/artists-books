function ProcessListGBSBookInfo(booksInfo) {
	var $ = jQuery;
	
	for (identifier in booksInfo) {
		var bookInfo = booksInfo[identifier];
		identifier = identifier.replace(/:/g,"\\:");
		if (bookInfo){
			$(".gbsContainer." + identifier).each(function(){
				$(this).css("display", "");
				if ($(this).hasClass("fullRecord")){
					if (bookInfo.preview == "full")
						$(this).append("<td class=\"fullonlinestatus\"><a href=\"" + bookInfo.preview_url
								 + "\"><img src='images/gbs_preview_sticker1.gif'/></a></td>" 
								 + "<td class=\"fullonlinelink\"><a href=\"" + bookInfo.preview_url
								 + "\">Full view available via Google Book Search</a></td>");
					if (bookInfo.preview == "partial")
						$(this).append("<td class=\"fullonlinestatus\"><a href=\"" + bookInfo.preview_url
								 + "\"><img src='images/gbs_preview_sticker1.gif'/></a></td>" 
								 + "<td class=\"fullonlinelink\"><a href=\"" + bookInfo.preview_url
								 + "\">Limited preview available via Google Book Search</a></td>");
				} else {
					if (bookInfo.preview == "full"){
						$(this).append("<td colspan=\"3\" class=\"brieflibrary\"><a href=\"" + bookInfo.preview_url
								 + "\">Full view available via Google Book Search</a></td><td class=\"briefstatus\">"
								 + "<span class=\"status\">Online Access</span></td>");
					}
					if (bookInfo.preview == "partial"){
						$(this).append("<td colspan=\"3\" class=\"brieflibrary\"><a href=\"" + bookInfo.preview_url
								 + "\">Limited preview available via Google Book Search</a></td><td class=\"briefstatus\">"
								 + "<span class=\"status\">Limited Preview</span></td>");
					}
				}
				 
			}).removeClass().addClass("gbsContainer");
		}
	}
}

function ProcessListHathi(booksInfo) {
	var $ = jQuery;
	
	for (identifier in booksInfo) {
		var bookInfo = booksInfo[identifier];
		identifier = identifier.replace(/:/g,"\\:");
		if (bookInfo) {
			var urlArray = new Array();
			
			if (bookInfo.items.length == 1) {
				// Only one item for this result, store it if Full View rights
				if (bookInfo.items[0].usRightsString == "Full view") {
					urlArray[bookInfo.items[0].fromRecord] = bookInfo.items[0].itemURL;
				}
			} else if (bookInfo.items.length > 1) {
				// Multiple items, determine the number of full view items per record
				$.each(bookInfo.items, function(index){
					itemInfo = bookInfo.items[index];
					if (itemInfo.usRightsString == "Full view") {
						fromRecord = itemInfo.fromRecord;
						if ("fullViewCount" in bookInfo.records[fromRecord]){
							bookInfo.records[fromRecord]["fullViewCount"]++;
						} else {
							// Store the first item url as a representative
							bookInfo.records[fromRecord]["representativeItemURL"] = itemInfo.itemURL;
							bookInfo.records[fromRecord]["fullViewCount"] = 1;
						}
					}
				});
				
				// Store the best URL for each record.
				$.each(bookInfo.records, function(index){
					recordInfo = bookInfo.records[index];
					if ("fullViewCount" in recordInfo){
						if (recordInfo.fullViewCount == 1){
							// Only one full view item for this record, use its url.
							urlArray[index] = recordInfo.representativeItemURL;
						} else if (recordInfo.fullViewCount > 1){
							// Multiple, link to the record url
							urlArray[index] = recordInfo.recordURL; 
						}
						// If there were no full view items, discard this record.
					}
				});
			}
			
			for (recordID in urlArray) {
				$(".hathiContainer." + identifier).each(function(){
					$(this).css("display", "");
					multivolumeText = "";
					if (bookInfo.records[recordID].fullViewCount > 1)
						multivolumeText = " (multiple volumes)";
					if ($(this).hasClass("fullRecord")){
						$(this).append("<td class=\"fullonlinestatus\"><a href=\"" + urlArray[recordID]
								 + "\"><img src='images/hathitrust.png'/></a></td>" 
								 + "<td class=\"fullonlinelink\"><a href=\"" + urlArray[recordID]
								 + "\">Full text available via HathiTrust" + multivolumeText + "</a></td>");
					} else {
						$(this).append("<td colspan=\"3\" class=\"brieflibrary\"><a href=\"" + urlArray[recordID]
								 + "\">Full text available via HathiTrust" + multivolumeText + "</a></td><td class=\"briefstatus\">"
								 + "<span class=\"status\">Online Access</span></td>");
					}
				}).removeClass().addClass("hathiContainer");
			}
		}
	}
}