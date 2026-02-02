function getTabPosition(relativeTo){
	var $tabs = $("#tabs li a");
	var i=0, n = $tabs.length
	for(;  i < n && $tabs[i].getAttribute("href") < relativeTo;  ++i);//{alert($($tabs[i]).attr("href") + "|" + relativeTo);}
	return i;
}

function populateTab(id, content, contentHeader, className){
	var results = "<div id='" + id + "'><table width=\"100%\"><tr><td>" +
		"<div class=\"shaded label\">" + contentHeader + "</div>";
	if (className != "")
		results += "<div class=\"" + className + "\">";
	else results += "<div>";
	results += content+"</div></td></tr></table></div>";
	return results;
	$("#"+id).html(results);
}

function addTab(id, label, content, contentHeader, className){
	var position = getTabPosition("#"+id);
	$("#tabs li").eq(position).before("<li><a href='#" + id + "'><span>" + label + "</span></a></li>");
	$("#tabs > .xboxcontent").append(populateTab(id, content, contentHeader, className));
	$("#tabs").tabs("refresh");
	var preselected = self.document.location.hash.substring(1);
	if (preselected == id)
		$("#tabs").tabs("select", position);
}

function processMARCData(content){
	for (contentType in content) {
		var contentRecord = content[contentType];
		if (contentRecord){
			if (contentType == "marc"){
				$("#marccontent").html(contentRecord);
			}
		}
	}
}

function processSyndeticsData(content){
	//If there is no medium sized cover image, than take it away.
	if (content["cover"] != undefined){
		if (content["cover_lc"] == undefined){ 
			$(".record_cover").html($(".fullBookCover").html());
			$(".record_cover").html("<img class=\"bookCover\" src=\"" + content["cover"] + "\" title=\"Cover\"/>");
		} else {
			$(".record_cover").html("<a href=\"" + content["cover_lc"] + "\" class=\"fullBookCover\"><img class=\"bookCover\" src=\"" + content["cover"] + "\" title=\"Cover--Click to expand.\"/></a>");
			generateLightBox("record_cover");
		}
	}
	for (contentType in content) {
		var contentRecord = content[contentType];
		if (contentRecord){
			if (contentType == "summary"){
				contentRecord = contentRecord.substring(5, contentRecord.length - 7);
				if (String(contentRecord).length > 200 && (contentRecord.indexOf("<div class=\"syndeticscopyrightblock\">") > 200 || contentRecord.indexOf("<div class=\"syndeticscopyrightblock\">") == -1)){
					getParameters = getUrlVars(); 
					//Determine if we should show summaries by default
					var showSummary = "0";
					if (typeof(getParameters["summary"]) != 'undefined'){
						showSummary = getParameters["summary"];
					}
					var summaryOutput = "<td class='recordbox_summary' colspan='2'>Summary:<br/>" + 
							"<div class='recordbox_summary_content hlcontent'>" + 
							contentRecord.substring(0, 200);
					if (showSummary == "1"){
						summaryOutput += "<span id=\"summaryextended\">" + contentRecord.substring(200) + "</span>";
						summaryOutput += "<span id=\"summaryelipses\" class=\"hidden\">...</span> " +
							"(<a href=\"\" id=\"moreLink\">see less</a>)";
					} else {
						summaryOutput += "<span id=\"summaryextended\" class=\"hidden\">" + contentRecord.substring(200) + "</span>";
						summaryOutput += "<span id=\"summaryelipses\">...</span> " +
							"(<a href=\"\" id=\"moreLink\">see more</a>)";
					}
					
					summaryOutput += "</div></td>";
					$("#abovesummarycontent").html(summaryOutput);
				} else {
					$("#abovesummarycontent").html("<td class='recordbox_summary' colspan=\"2\">Summary:<br/><div class='recordbox_summary_content hlcontent'>" + contentRecord + "</div></td>");
				}
				$("#fullsummarycontent").html("<td>Summary:</td><td class=\"hlcontent\">" + contentRecord + "</td>");
			} else if (contentType == "avlisting"){
				addTab("tab4", "A/V Details", contentRecord, "Audio Track Listings / Video Summary", "hlcontent");
				$("#fullavcontent").html("<br/><table width=\"100%\"><tr><td><b>Audio Track Listings / Video Summary</b><div class=\"hlcontent\">" +
						contentRecord +
						"</div></td></tr></table>");
			} else if (contentType == "chapter"){
				addTab("tab6", "First Chapter", contentRecord, "First Chapter or Excerpt", "hlcontent");
			} else if (contentType == "toc"){
				if ($("#tab3").length > 0){
					$("#toccontent").html("<div class=\"hlcontent\">" + contentRecord + "</div>");
					if (preselected == "#tab3")
						$("#tabs").tabs("select", getTabPosition("#tab3"));
				} else {
					addTab("tab3", "Table of Contents", contentRecord, "Table of Contents", "hlcontent");
				}
				$("#fulltoccontent").html("<br/><div class=\"shaded label\">Table of Contents</div><div class=\"hlcontent\">" +
						contentRecord +
						"</div>");
				
			}
		}
	}
	$(".hlcontent").highlight(lastsearchterm);
}

function processExternalContent(content){
	
	for (contentType in content) {
		var contentRecord = content[contentType];
		if (contentRecord){
			if (contentType == "marc"){
				processMARCData(contentRecord);
			} else if (contentType == "syndetics"){
				processSyndeticsData(contentRecord);
			}
		}
	}
}

function loadEADContent(container, eadid, lastsearchterm, eadProxyPath, eadXMLPath, eadStylesheetPath){
	var tabID = $(container).attr("id");
	var element = "";
	if ($(container).html().length <= 17 || ($("#eadarrangementcontent").length > 0 && tabID == "tab8" && $("#eadarrangementcontent").html().length == 0)){
		if (tabID == "tab7a") 
			element = "bioghist";
		else if (tabID == "tab7b") 
			element = "overview"; 
		else if (tabID == "tab7c") 
			element = "dsc";
		else if (tabID == "tab8") 
			element = "arrangement";
	}
	if (element != ""){
		if (tabID == "tab8"){
			tabID = "eadarrangementcontent";
		}
		$.get(eadProxyPath, {"url": eadXMLPath + "/" + eadid + ".xml", "stylesheet": eadStylesheetPath, "sterm": "", "element": element, "format": "jsonp"},
				function (data) {
					$("#" + tabID).html(data["content"]);
					$("#" + tabID).highlight(lastsearchterm, true);
				}, "jsonp");
	}		
}

function getWorldCatCount(content){
	if (content == null || content["worldcatcount"].length == 0)
		return;
	numberOfResults = content["worldcatcount"];
	digitsNumberOfResults = content.length;
	if (digitsNumberOfResults > 3){
		numberOfResults = numberOfResults.substring(0,3);
		for (i=0; i<digitsNumberOfResults-3; i++)
			numberOfResults += "0";
	}
	if (numberOfResults != "0" && numberOfResults != "")
		numberOfResults += "+";
	$("#worldcatresultscount").html(numberOfResults);
}