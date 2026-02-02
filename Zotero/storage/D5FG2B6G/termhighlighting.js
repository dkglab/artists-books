var highlightclass = "hltext";

/*
* Highlights content in the invoking tag.  If the optional simple parameter is true then performs
* a simpler version of highlighting that does not test for full word matching, but is less 
* computationally intensive for IE6's sake. 
*/
jQuery.fn.highlight = function(terms, simple){
	//Do regular term highlighting, tests for full word matching.
	function doHighlight(bodyText, searchTerm, highlightStartTag, highlightEndTag) {
		// find all occurences of the search term in the given text,
		// and add some "highlight" tags to them (we're not using a
		// regular expression search, because we want to filter out
		// matches that occur within HTML tags and script blocks, so
		// we have to do a little extra validation)
		var newText = "";
		var i = -1;
		var lcBodyText = bodyText.toLowerCase();
		var closeI = -1;
		var searchRegex = "";
		for (var i = 0; i < searchTerm.length; i++) {
			if (i>0)
				searchRegex += "|";
			searchRegex += searchTerm[i];
		}
		var re = new RegExp('(\\s|\\,|;|\\[|\\]|\\?|\\(|\\+|\\{|\\}|\\\\|\\/|\\$|\\^|\\)|\\*|\\&|"|^)(' + searchRegex + ')(?=\\s|\\,|;|\\[|\\]|\\?|\\(|\\+|\\{|\\}|\\\\|\\/|\\$|\\^|\\)|\\*|\\&|"|$)', 'gi');
		
		while (bodyText.length > 0) {
			i = lcBodyText.indexOf("<", i+1);
			if (i < 0){
				if (bodyText.substring(0).length > 0){
					newText += bodyText.substring(0).replace(re, highlightStartTag + "$1$2" + highlightEndTag);
					bodyText = "";
				}
			} else {
				newText += bodyText.substring(0, i).replace(re, highlightStartTag + "$1$2" + highlightEndTag);
				closeI = lcBodyText.indexOf(">", i+1);
				newText += bodyText.substring(i, closeI+1);
				bodyText = bodyText.substr(closeI+1);
				lcBodyText = bodyText.toLowerCase();
				i = -1;
			}
		}
		return newText;
	}
	
	//Do simple highlighting, does not test for full word matching, ignores search terms of length 1
	function doHighlightSimple(contentTag, searchArray, highlightStartTag, highlightEndTag) {
		if ((!highlightStartTag) || (!highlightEndTag)) {
			highlightStartTag = "<b>";
			highlightEndTag = "</b>";
		}
		var contentText = contentTag.html();
		
		for (var i = 0; i < searchArray.length; i++) {
			if (searchArray[i].length > 1){
				var bodyText = contentText;
				var newText = "";
				var lcBodyText = bodyText.toLowerCase();
				var lcSearchTerm = searchArray[i];
		  		var termStart = -1;
				while (bodyText.length > 0) {
					termStart = lcBodyText.indexOf(lcSearchTerm, termStart+1);
					if (termStart < 0) {
						newText += bodyText;
						bodyText = "";
					} else {
						// skip anything inside an HTML tag
						if (bodyText.lastIndexOf(">", termStart) >= bodyText.lastIndexOf("<", termStart)) {
							// skip anything inside a <script> block
							if (lcBodyText.lastIndexOf("/script>", termStart) >= lcBodyText.lastIndexOf("<script", termStart)) {
								newText += bodyText.substring(0, termStart) + highlightStartTag + bodyText.substr(termStart, lcSearchTerm.length) + highlightEndTag;
								bodyText = bodyText.substr(termStart + lcSearchTerm.length);
								lcBodyText = bodyText.toLowerCase();
								termStart = -1;
							}
						}
					}
				}
				contentText = newText;
			}
		}
		
		contentTag.html(contentText);
	}

	//Clean up search terms and perform highlighting.
	function highlight(terms, content, simple){
		terms = terms.replace(/&[a-zA-Z]{1,6};|\,|;|\[|\]|\?|\(|\+|\{|\}|\\|\/|\$|\^|\)|\*|\&|"/g,"");
		terms = terms.replace(/\s{2,}/g," ");
		terms = terms.replace(/^\s+|\s+$/g,"");
	
		if (terms == null || terms == "")
			return;
		var searchArray = terms.split(" ");
		//Perform normal highlighting
		if (!simple){
			return doHighlight($(content).html(), searchArray, "<span class=\"" + highlightclass + "\">", "</span>");
		}
		//Perform simple highlighting, no word boundary testing.
		return doHighlightSimple($(content), searchArray, "<span class=\"" + highlightclass + "\">", "</span>");
	}
	
	//Execute highlight function.
	return this.each(function() {
		$(this).html(highlight(terms.toLowerCase(), this, simple));
	});
};