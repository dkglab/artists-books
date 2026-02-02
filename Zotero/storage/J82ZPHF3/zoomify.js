//---: Zoomify Javascript functions for swapping out the main image for Zoomify flash objects.
//---: Author: Andy Cummins
//---: Date: 06/08/2008

//***if zoomify available add links to swap the flash in.

function addZoomifyLinks(zoomifyPath, zoomifyDiv, artist, title, work_date, fullscreenMode, callback)
{
    callback = (typeof callback === "undefined") ? false : callback;

	if (document.getElementById(zoomifyDiv)) 
	{
		var fullZoomifyPath = "http://www.moma.org/collection_images/zoomifyImages/"+zoomifyPath;
		var playerPath = 'flash/release/fullscreenViewer_redux.swf';
		var objZoomLink = document.getElementById(zoomifyDiv);
		objZoomLink.innerHTML ='<a id="zoomLink" class="collectionlink" href="#"> Zoom</a>';
		document.getElementById('zoomLink').onclick=function(){swap4Zoomify(playerPath,fullZoomifyPath,artist,title,work_date,fullscreenMode,callback);return false;};
		//document.getElementById('zoomImageLink').onclick=function(){swap4Zoomify(playerPath,zoomifyPath,artist,title,work_date,fullscreenMode);return false;};
    }
}

function clearZoomifyLink(zoomifyDiv)
{
	if (document.getElementById(zoomifyDiv)) 
	{
		var objZoomLink = document.getElementById(zoomifyDiv);
		objZoomLink.innerHTML ='';
	}
}

//***replace main image with zoomify flash object

function swap4Zoomify(playerPath, assetPath, artist, title, work_date,fullscreenMode,callback)
{
	if(artist == ''){
		var workStr = "test";
	}
	else {
		var workStr = artist+". "+title+". "+work_date;
	}
		var flashvars = {zoomifyImagePath: assetPath, workStr: workStr, fullscreenMode: fullscreenMode};
		var params = {bgcolor: "#f3f3f3", allowFullScreen: "true", wmode: "transparent"};
	swfobject.embedSWF(playerPath, "mainImage", "480", "496", "6","",flashvars,params);
	document.getElementById("zoomifyDiv").style.display="none";
	//document.getElementById("bgColourStylesheet").href="white.css";

    if (callback) {
        callback;
    }
}
