function ProcessRealTimeStatus(statusInfo) {
	var $ = jQuery;
	
	for (identifier in statusInfo) {
		var aStatus = statusInfo[identifier];
		identifier = identifier.replace(/:/g,"\\:");
		identifier = identifier.replace(/\|/g,"\\|");
		if (aStatus) {
			//alert(aStatus + "|" + identifier + "|" + $("#stat" + identifier).html());
			if (aStatus == "Available" || aStatus == "Available (library use only)"
					|| aStatus == "In-Library Use Only")
				$(".stat" + identifier).html("<span class=\"status\">" + aStatus + "</span>");
			else $(".stat" + identifier).html("<span class=\"status2\">" + aStatus + "</span>");
		}
	}
}