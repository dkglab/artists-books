function GetTerms(SearchURL) {
    sTerms = document.searchBox.query.value;
    var strout;
    SearchURL += sTerms;
    var newWin = window.open(SearchURL, "NCSU");
    return false;
}

function GetSort() {
    var sortIndex = document.sortForm.sortField.selectedIndex;
    var sortURL = document.sortForm.sortField[sortIndex].value;
    window.location=sortURL;
}

function clearCookies(){ 
	document.cookie = "ntt=;expires=Thu, 01-Jan-1970 00:00:01 GM";
}

function getUrlVars(){
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++) {
        hash = hashes[i].split('=');
        vars.push(hash[0]);
        vars[hash[0]] = hash[1];
    }
    return vars;
}

function replaceParameter(href, key, value){
  	var pathSplit = href.split("?");
  	var anchorSplit = new Array();
  	var parameterSplit = new Array();
  	if (pathSplit.length > 1){
  		anchorSplit = pathSplit[1].split("#");
  		if (anchorSplit.length > 0){
  			parameterSplit = anchorSplit[0].split("&");
  		}
  	}
  	var paramCNT = 0;
  	for (; paramCNT < parameterSplit.length && parameterSplit[paramCNT].indexOf(key+"=") != 0; paramCNT++);
	if (parameterSplit.length > 0 && paramCNT < parameterSplit.length){
		parameterSplit[paramCNT] = escape(key) + "=" + escape(value);
	} else {
		parameterSplit.push(escape(key) + "=" + escape(value));
	}
  		
	var url = parameterSplit.join("&");
	if (pathSplit.length > 1){
		url = pathSplit[0] + "?" + url;
	} else {
		url = "?" + url;
	}
	if (anchorSplit.length > 1){
		url = url + "#" + anchorSplit[1];
	}
	return url;
}

(function($) {

var regExp = new RegExp("//" + location.host + "($|/)");

function log_event() {
	var $this = $(this);
	contents = $this.html();
	if (contents !== undefined) {
		var label = contents.replace(/<[^>]+>/g, "").replace(/^\s+|\s+$/g, '');
		var href = $this.attr("href");
		var isLocal = (href.substring(0,4) === "http") ? regExp.test(href) : true;
		var eventName = $this.data("event");
		if (!eventName) {
			eventName = "other";
		}
		
		ga('send', 'event', eventName, isLocal? 'local-click' : 'external-click', href);
	}
}

function submit_search() {
	var searchWithin = $("input[name='searchWithinBox']").prop("checked");
	var searchIndex = $("input[name='Ntk']").val();
	if (!searchIndex) {
		searchIndex = "Keyword";
	}
	var terms = $("input[name='Ntt'],#keywordAnywhere").val();
	
	ga('send', 'event', searchIndex, searchWithin? 'search within' : 'search', terms);
}

$(document).ready(function() {
	if (!($.browser.msie && parseInt($.browser.version, 10) <= 7)){
		$("body").delegate("a", "mouseup", log_event);
	}
	$("#sortField").change(GetSort);
	$(".requestlink_choice").click(function(){return false;});
	$("#queryBox").submit(submit_search);
	$(".request.multiple > a").qtip({
		content: {
			text : function(api) {
				return $(this).parent().find(".request_choices").clone();
			}
		},
		position: {
			at: "bottom right",
			my: "top right"
		},
		style: {
			'width': '245px',
			classes: "request_choices_dropdown",
			tip: false
		},
		api :{
			onRender: function() {
				console.log("Render time");
			}
		},
		show: {
			event: 'click',
			delay : 0
		},
		hide: {
			event: 'unfocus click',
			fixed: true
		}
	}).bind('click', function(event){ event.preventDefault(); return false; });
});

})( jQuery );