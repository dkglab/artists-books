
// Shopping cart functionality
// Created 10/20/08 by Andreas Orphanides

var shoppingCartURL = "./markeditems";
var itemCount = 0;
var highlighted = 0;

$(document).ready(function() {
	
	// When page loads, get number of items for populating list.
	
	if (highlighted > 0) {
		$("#markedItemBox").show();
	}
	pageHasSelected();
	
	
	
	
	$("#removeAllFromCart").click(function() {
		var itemID = $(this).attr("keys");
		$.get(shoppingCartURL, {id: itemID, op: "rm", xml: "t"}, function (data) {
			itemCount = $("markedCount", data).text();
			var outcome = $("remove", data).attr("outcome");
			if (outcome == "failure") {
				//alert("Error: " + $("remove", data).text());
			}
			countUpdate (itemCount);
		}, "xml" );
		
		$(".addItemToCart").each(function(){
				$(this).attr("src","images/folder.gif");
				$(this).attr("title","Add this title to your marked items list");
				if ($(this).attr("id").indexOf("|") == -1)
					$(this).attr("marked", "0");
				$("#l" + $(this).attr("id")).attr("innerHTML", "Add");
			});
	});
	
	$("#addAllToCart").click(function() {
		var itemID = $(this).attr("keys");
		$.get(shoppingCartURL, {id: itemID, op: "add"}, function (data) {
			itemCount = $("markedCount", data).text();
			var outcome = $("add", data).attr("outcome");
			if (outcome == "failure") {
				//alert("Error: " + $("add", data).text());
			}
			countUpdate (itemCount);
		}, "xml" );		
		
		$(".addItemToCart").each(function(){
				$(this).attr("src","images/folder_page.gif");
				$(this).attr("title","Remove this title from your marked items list");
				if ($(this).attr("id").indexOf("|") == -1)
					$(this).attr("marked", "1");
				$("#l" + $(this).attr("id")).attr("innerHTML", "Remove");
			});
	});
	
	
	// Add a single item to the cart when checkbox is clicked, or remove
	// item from cart if checkbox is unclicked.
	// Controls icon used and which alt tag to provide
	$(".addItemToCart").click(function () {
		var itemID = $(this).attr("id");
		
		var selectedText = (itemID.substring(0,1) == "l");
		if (selectedText)
			itemID = itemID.substring(1,itemID.length);
		var itemRollup = $("#" + itemID).attr("rollup");
		//alert(itemID + "|" + selectedText); 
		if ($("#" + itemID).attr("marked") == "1"){
			$.get(shoppingCartURL, {id: itemRollup, op: "rm", xml: "t"}, function (data) {
				itemCount = $("markedCount", data).text();
				var outcome = $("remove", data).attr("outcome");
				if (outcome == "failure") {
					//alert("1Error: " + $("remove", data).text());
				}
				$("#" + itemID).attr("src","images/folder.gif");
				$("#" + itemID).attr("title","Add this title to your marked items list");
				$("#" + itemID).attr("marked", "0");
				$("#l" + itemID).attr("innerHTML", "Add");
				countUpdate (itemCount);
			}, "xml" );
		}
		else {
			$.get(shoppingCartURL, {id: itemID, op: "add"}, function (data) {
				itemCount = $("markedCount", data).text();
				var outcome = $("add", data).attr("outcome");
				if (outcome == "failure") {
					//alert("2Error: " + $("add", data).text());
				}
				$("#" + itemID).attr("src","images/folder_page.gif");
				$("#" + itemID).attr("title","Remove this title from your marked items list");
				$("#" + itemID).attr("marked", "1");
				$("#l" + itemID).attr("innerHTML", "Remove");
				countUpdate (itemCount);
			}, "xml" );		
		}
	});
});


function pageHasSelected(){
	$("#removeAllFromCart").hide();
	$(".addItemToCart").each(function(){
		if ($(this).attr("marked") == 1){
			$("#removeAllFromCart").show();
			return;
		}
	});
}

// Update count of items and show counter box if it's not showing.

function countUpdate (itemCount) {
	pageHasSelected();
	if (itemCount > 0) {
		$("#cartCount").text("Added (" + itemCount + ")");
		$("#folderlink").attr("class", "folderfull");
		$("#foldertabicon").attr("src", "images/folder_page.gif");
	}
	else {
		$("#cartCount").text("Added (0)");
		$("#folderlink").attr("class", "");
		$("#foldertabicon").attr("src", "images/folder.gif");
	}
}