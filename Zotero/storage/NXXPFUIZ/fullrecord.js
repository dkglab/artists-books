	function toggleExpandAllButtons(button, expand){
		if (expand){
			$("." + button + "_AllButton").html("List All Volumes");
		} else {
			$("." + button + "_AllButton").html("Hide All Volumes");
		}
	}
	
	function toggleAllHoldings(){
		prefix = $(this).attr("class").split("_")[0];
		
		//If they clicked on the text instead of the image, trim off the leading letter
		var selectedText = (prefix.substring(0,1) == "t");
		if (selectedText)
			prefix = prefix.substring(1,prefix.length);
		
		expand = ($("." + prefix + "_AllButton").html() == "List All Volumes");
		if (expand){
			$("#" + prefix + "_SerialsHoldings img.serialsExpandButton").each(function(){
				//alert(this + "|" + "#" + this.id + "_ItemLevel");
				showHoldings(this.id, "#" + this.id + "_ItemLevel");
			});
		} else {
			$("#" + prefix + "_SerialsHoldings img.serialsExpandButton").each(function(){
				//alert(this + "|" + "#" + this.id + "_ItemLevel");
				hideHoldings(this.id, "#" + this.id + "_ItemLevel");
			});
		}
		toggleExpandAllButtons(prefix, !expand);
	}
	
	function showHoldings(button, itemLevelID){
		$(itemLevelID).removeClass("hidden");
		$("#"+button).attr("src","images/collapse.gif");
		$("#"+button).attr("title","Hide volume information for this location.");
		$("#t"+button).html("Hide");
	}
	
	function hideHoldings(button, itemLevelID){
		$(itemLevelID).addClass("hidden");
		$("#"+button).attr("src","images/expand.gif");
		$("#"+button).attr("title","Display volume information for this location.");
		$("#t"+button).html("Expand");
	}
	
	function toggleHoldingsDisplay(button, itemLevelID){
		if ($(itemLevelID+".hidden").length > 0){
			showHoldings(button, itemLevelID);
			return true;
		} else {
			hideHoldings(button, itemLevelID);
			return false;
		}
	}
	
	function toggleHoldings(){
		var id = this.id;
		var selectedText = (id.substring(0,1) == "t");
		if (selectedText)
			id = id.substring(1, id.length);
		itemLevelID = "#" + id + "_ItemLevel";
		prefix = id.split("_")[0];
		
		expanded = toggleHoldingsDisplay(id, itemLevelID);
		if ($("#" + prefix + "_SerialsHoldings .itemLevel.hidden").length == 0){
			//If there are no more hidden items left then make expand all into collapse all
			toggleExpandAllButtons(prefix, false);
		} else if ($("#" + prefix + "_SerialsHoldings .itemLevel:not(.hidden)").length == 0){
			//If there are no more non-hidden items left then make collapse all into expand all
			toggleExpandAllButtons(prefix, true);
		}
		return false;
	}
		
		function toggleSummary(){
			var seeMore = "";
			if ($(this).html() == "see more"){
				$(this).html("see less");
				$("#summaryextended").removeClass("hidden");
				$("#summaryelipses").addClass("hidden");
				seeMore = "1";
			} else {
				$(this).html("see more");
				$("#summaryextended").addClass("hidden");
				$("#summaryelipses").removeClass("hidden");
				seeMore = "0";
			}
			if ($(".fullrecordnavlink").length > 0){
				$(".fullrecordnavlink").each(function (){
					$(this).attr("href", replaceParameter($(this).attr("href"), "summary", seeMore));
				});
			}
			return false;
		}
		
		function activateSubject(){
		$(this).children("a").each(function(){
			var parent = $(this).parents("span");
			var startIndex = $(this).attr("class").split(' ');
			if (startIndex.length > 1){
				var i = 0;
				for (; i < startIndex.length && isNaN(startIndex[i]); i++);
				if (i < startIndex.length){
					startIndex = startIndex[i];
				} else startIndex = 1;
			}
			$(this).hover(function(){
				for (var i = startIndex; i > 0; i--){
					$(parent).children("." + i).css("text-decoration", "underline");
					$(parent).children("." + i).css("background", "#eeeeff");
				}
			}, function(){
				for (var i = startIndex; i > 0; i--){
					$(parent).children("." + i).css("text-decoration", "none");
					$(parent).children("." + i).css("background", "none");
				}
			});
		});
	}
		
	$(document).ready(function(){
		var preselected = self.document.location.hash.substring(1);
		var tabPosition = preselected && preselected.indexOf("tab") == 0? getTabPosition("#"+preselected) : 1;
		
		$(".c").highlight(lastsearchterm);
		$("#tabs").tabs({
			active : tabPosition,
			activate : function(event, ui) {
				$(".fullrecordnavlink").each(function(){
					var tabnum = ui.newTab.attr("aria-controls");
					var currNewPage = $(this).attr("href").replace(/#tab[0-9a-z]+/, "").replace(/&t=[0-9a-z]+/, "");
					$(this).attr("href", currNewPage + "&t=" + tabnum + "#" + tabnum); 
				});
				loadEADContent(ui.newPanel, eadid, lastsearchterm, eadProxyPath, eadXMLPath, eadStylesheetPath);
			}
		});
		
		$("#moreLink", ".recordbox_summary").live('click', toggleSummary);
		$(".serialsExpandButton").click(toggleHoldings);
		$(".location_AllButton").click(toggleAllHoldings);
		$(".tlocation_AllButton").click(toggleAllHoldings);
		$(".fullRecord_AllButton").click(toggleAllHoldings);
		$(".tfullRecord_AllButton").click(toggleAllHoldings);
		
		if (preselected == "tab7a" || preselected == "tab7b" || preselected == "tab7c" || preselected == "tab8"){
			loadEADContent($("#"+preselected), eadid, lastsearchterm, eadProxyPath, eadXMLPath, eadStylesheetPath);
		}
		
		$.getJSON("content?q=" + syndeticsContentQuery, processExternalContent);
		$.getJSON("content?q=" + externalContentQuery, processExternalContent);
		
		$(".subject").each(activateSubject);
	});