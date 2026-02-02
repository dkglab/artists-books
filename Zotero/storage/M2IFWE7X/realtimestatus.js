function ProcessRealTimeStatus(statusInfo) {
	var $ = jQuery;
	
	for (identifier in statusInfo) {
		var aStatus = statusInfo[identifier];
		identifier = identifier.replace(/:/g,"\\:");
		identifier = identifier.replace(/\|/g,"\\|");
		if (aStatus) {
			//alert(aStatus + "|" + identifier + "|" + $("#stat" + identifier).html());
			if (aStatus == "Available" || aStatus == "Available (library use only)"
					|| aStatus == "In-Library Use Only"
			                || aStatus == "Contact library for status")
				$(".stat" + identifier).html("<span class=\"status\">" + aStatus + "</span>");
			else $(".stat" + identifier).html("<span class=\"status2\">" + aStatus + "</span>");
		}
	}
}

function ProcessYazTimeStatus(statusInfo) {
	var $ = jQuery;
	
	for (identifier in statusInfo) {
		var aStatus = statusInfo[identifier];
		
		if (aStatus) {
			var holdingZone = $("#hold_" + identifier);
			if (holdingZone.length == 0)
				continue;
			
			var callLocMap = {};
			for (var itemIndex in aStatus) {
				var itemInfo = aStatus[itemIndex];
				
				var call = itemInfo["callnum"].replace(/[^\w]/g, "");
				var locationEntry = $(".call_" + call, holdingZone);
				if (locationEntry.length > 0) {
					if (locationEntry.length > 1) {
						var entryIndex;
						if (!(call in callLocMap)) {
							callLocMap[call] = -1;
						}
						entryIndex = ++callLocMap[call];
						$(".status_holder span, .briefstatus span", locationEntry.eq(entryIndex)).text(itemInfo["status"]);
					} else {
						$(".status_holder span, .briefstatus span", locationEntry.eq(0)).text(itemInfo["status"]);
					}
				}
			}
		}
	}
}