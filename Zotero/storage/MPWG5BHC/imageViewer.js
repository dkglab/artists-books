
(function($){$.fn.imageviewer=function(options){$.fn.imageviewer.defaults={server_api_url:"",dmid:"",parentElement:"",toolbarDiv:"imageviewer_toolbar",toolBarButtonKill:"",image_height:options.imageInfo.imageinfo.height,image_width:options.imageInfo.imageinfo.width,debug:false,runDebug:true,viewportObj:{"height":484,"width":"100%","top":0,"left":0},imageLayerObj:{"top":0,"left":0},thumbnailOpenOnLoad:true,thumbnailBoxMaxSize:125,thumbnailBox:{"height":125,"width":125,"bgcolor":"white","overlayColor":"cornflowerblue"},thumbnailScale:0,thumbnailDispMultiplierY:0,thumbnailDispMultiplierY:0,currentImagePath:"",originalImageObj:{"width":parseInt(options.imageInfo.imageinfo.width,10),"height":parseInt(options.imageInfo.imageinfo.height,10),"CISOPTR":options.itemId,"CISOROOT":options.collection},mousePos:{"x":0,"y":0},tileSize:512,viewerDirectory:"",loadImageDir:"/images",loadImageUrlDir:"",imgDivBg:options.imgDivBg,imageviewerbgcolor:options.imageviewerbgcolor,imageviewerbgImg:options.imageviewerbgImg,imageviewerbgUrl:"",imageviewerbordercolor:"solid gray",imageviewerbordersize:1,zoomBorderColor:"cornflowerblue",zoomBorderWidth:"4px",zoomOverlayPlus:"zoom_plus.gif",zoomOverlayMinus:"zoom_minus.gif",imageTileOverlap:0,loadImageFile:"singlePixelTrans.gif",loadImageUrl:"",imgDivBgUrl:"",initialzoom:"width",initialzoomcustom:35,fullBrowserButtonId:"toolbar_corner",fullBrowserMode:false,fullBrowserText:false,fullBrowserWindowOffset:157,fullBrowserWindowView:"singleitem",prevImgScale:0,scaleArray:new Array(5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,125,150,200),scaleIndex:0,scaleIndexMin:0,imgScale:0,oldImgScale:0,imgMinScale:options.scaleArray[0],imgMaxScale:options.scaleArray[options.scaleArray.length-1],currentZoom:0,imgRotation:0,adjustedH:0,adjustedW:0,rows:0,cols:0,imgWidthModulo:0,imgHeightModulo:0,tiles:{},startPosTop:0,startPosLeft:0,loadImageCountdown:"",initLoad:true,pubDelta:0,mouseboxInit:true,contextDebugInput:" ",arrowKeyDistance:10,shiftDown:false,ctlDown:false,keyZoom:false,setToTop:false,sliderBaseSize:0,arrImageDivs:"",arrImageImgs:"",rotation:0,clipArea:{"height":200,"width":300},clipTargetElement:"viewport",fullTextSearchTerm:"",newspaperArticles:"",currentDivId:"",articleArray:{},lang:"",brandImage:""};$.fn.imageviewer.options=$.extend({},$.fn.imageviewer.defaults,options);if($.fn.imageviewer.options.scaleArray==""){$.fn.imageviewer.options.scaleArray=new Array(5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,125,150,200);}
if($.fn.imageviewer.options.initialzoom==""){$.fn.imageviewer.options.initialzoom="width";}
$.fn.imageviewer.options.initialzoomcustom=parseInt($.fn.imageviewer.options.initialzoomcustom,10);if($.fn.imageviewer.options.initialzoomcustom>200){$.fn.imageviewer.options.initialzoomcustom=200;}
if($.fn.imageviewer.options.initialzoomcustom<0){$.fn.imageviewer.options.initialzoomcustom=0;}
$.fn.imageviewer.options.initialzoomcustom=$.fn.imageviewer.options.initialzoomcustom+"";if($.fn.imageviewer.options.initialzoomcustom==""){$.fn.imageviewer.options.initialzoomcustom="0";}
$.fn.imageviewer.options.scaleArray=$.fn.imageviewer.options.scaleArray.sort(sortNumber);for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++){if($.fn.imageviewer.options.scaleArray[i]>200){$.fn.imageviewer.options.scaleArray[i]=200;}}
checkMinZoom();for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++){if($.fn.imageviewer.options.scaleArray[i]==$.fn.imageviewer.options.scaleArray[i+1]){$.fn.imageviewer.options.scaleArray.splice(i,1);i--;}}
if(options.debug){debug(this);}
return this.each(function(options){$this=$(this);$.fn.imageviewer.options.parentElement=this.id;$.fn.imageviewer.prepToolbar()
$.fn.imageviewer.varInit();$.fn.imageviewer.createImageViewer(this);$.fn.imageviewer.setImageDiv();$.fn.imageviewer.imageInit();$.fn.imageviewer.setToolbarSlider();$.fn.imageviewer.windowResize($.fn.imageviewer.options.parentElement);$.fn.imageviewer.loadImage();$.fn.imageviewer.options.compObjId=$('#cdm_id').val();if(!$.fn.imageviewer.options.fullBrowserMode)
{$.fn.imageviewer.loadVerticalDragbar();}
loadDebug();$.fn.imageviewer.loadThumbnail();refreshDebugLayer();$.fn.imageviewer.options.initLoad=false;var t=setTimeout("viewportResize($.fn.imageviewer.options.parentElement)",10);$(document).keyup(function(e){document.defaultAction=false;var evt=e||window.event;switch(evt.keyCode){case(16):$.fn.imageviewer.options.shiftDown=false;break;case(17):$.fn.imageviewer.options.ctlDown=false;break;}});$(document).keydown(function(e){document.defaultAction=false;var evt=e||window.event;switch(evt.keyCode){case(16):$.fn.imageviewer.options.shiftDown=true;return document.defaultAction;break;case(17):$.fn.imageviewer.options.ctlDown=true;return document.defaultAction;break;case(107):if($.fn.imageviewer.options.ctlDown==false&&($.fn.imageviewer.textBoxNotFocused())){zoomButtonHandler(evt.keyCode)
return document.defaultAction;}
break;case(187):if($.fn.imageviewer.options.ctlDown==false&&($.fn.imageviewer.textBoxNotFocused())){zoomButtonHandler(evt.keyCode)
return document.defaultAction;}
break;case 109:if($.fn.imageviewer.options.ctlDown==false&&($.fn.imageviewer.textBoxNotFocused())){zoomButtonHandler(evt.keyCode)
return document.defaultAction;}
break;case 189:if($.fn.imageviewer.options.ctlDown==false&&($.fn.imageviewer.textBoxNotFocused())){zoomButtonHandler(evt.keyCode)
return document.defaultAction;}
break;case 37:if($.fn.imageviewer.options.shiftDown&&($.fn.imageviewer.textBoxNotFocused())){moveImgLayer("left",$.fn.imageviewer.options.arrowKeyDistance);return document.defaultAction;}
break;case 39:if($.fn.imageviewer.options.shiftDown&&($.fn.imageviewer.textBoxNotFocused())){moveImgLayer("right",$.fn.imageviewer.options.arrowKeyDistance);return document.defaultAction;}
break;case 38:if($.fn.imageviewer.options.shiftDown&&($.fn.imageviewer.textBoxNotFocused())){moveImgLayer("up",$.fn.imageviewer.options.arrowKeyDistance);return document.defaultAction;}
break;case 40:if($.fn.imageviewer.options.shiftDown&&($.fn.imageviewer.textBoxNotFocused())){moveImgLayer("down",$.fn.imageviewer.options.arrowKeyDistance);return document.defaultAction;}
break;default:}});});};$.fn.imageviewer.textBoxNotFocused=function(){var selectedElement=$(document.activeElement);if(selectedElement.get(0).tagName=="INPUT"||selectedElement.get(0).tagName=="TEXTAREA"){if(selectedElement.attr("type")=="text"||selectedElement.get(0).tagName=="TEXTAREA"){return false;}}
return true;}
function sortNumber(a,b)
{return a-b;}
$.fn.imageviewer.setBrand=function()
{$('#brandImg').remove();var $brandImg=$("<img id='brandImg' src='"+$.fn.imageviewer.options.brandImage+"' style='display:none;position:absolute;z-index:1010;'/>");$('#imageLayer').prepend($brandImg);$('#brandImg').load(function(){$('#brandImg').css("display","block");$('#brandImg').css("top",$("#imageLayer").height()-$('#brandImg').height());$('#brandImg').css("left",$("#imageLayer").width()-$('#brandImg').width());});}
$.fn.imageviewer.loadBrandLayer=function()
{$('#brandLayer').remove();var $brandLayerDiv=$('<div/>');$brandLayerDiv.attr("id","brandLayer");$(SELECTOR_VIEWPORT).prepend($brandLayerDiv);$('#brandLayer').css("position","absolute");$('#brandLayer').css("cursor","default");$('#brandLayer').width($("#imageLayer").width());$('#brandLayer').height($("#imageLayer").height());$('#brandLayer').css("z-index","1001");$('#brandLayer').css("vertical-align","bottom");$('#brandLayer').css("text-align","right");$('#brandLayer').css("filter","alpha(opacity=50)");$('#brandLayer').css("-moz-opacity","0.5");$('#brandLayer').css("-khtml-opacity","0.5");$('#brandLayer').css("opacity","0.5");loadBrand();positionBrand();}
loadBrand=function(){var $SkellyLayerDiv=$("<div id='skullydiv' style='position:relative;height:100%;width:100%;z-index:1010;vertical-align:bottom;'><img id='skully' src='/ui/cdm/default/collection/default/images/skullxbones.png'/></div>");$('#brandLayer').prepend($SkellyLayerDiv);}
positionBrand=function(){$("#skullydiv").css('top',200);}
refreshBrandLayer=function()
{}
newspaperLoader=function(){if($("#cdm_newspaper").val()=="1"){$.ajax({type:"get",url:"/utils/getarticles/collection/"+$.fn.imageviewer.options.collection+"/id/"+$.fn.imageviewer.options.itemId,dataType:"json",success:function(msg){$.fn.imageviewer.options.newspaperArticles=msg;$.fn.imageviewer.setArticlesDiv();drawArticleBoundries(true);}});}else{}}
cdmIVConsoleLogger=function(msg){if(typeof console!=='undefined'){console.log(msg);}}
$.fn.imageviewer.setArticlesDiv=function()
{$('#articleBoundryLayer').remove();var $articleBoundryLayerDiv=$('<div/>');$articleBoundryLayerDiv.attr("id","articleBoundryLayer");$("#imageLayer").prepend($articleBoundryLayerDiv);$('#articleBoundryLayer').css("position","absolute");$('#articleBoundryLayer').css("cursor","default");$('#articleBoundryLayer').width($("#imageLayer").width());$('#articleBoundryLayer').height($("#imageLayer").height());$('#articleBoundryLayer').css("z-index","1000");}
drawArticleBoundries=function(setClick)
{var zcounter=0;zcounter=0;$('#articleListContainer_'+$.fn.imageviewer.options.itemId).html("");$.fn.imageviewer.options.articleArray={};for(var i=0;i<$.fn.imageviewer.options.newspaperArticles.articles.length;i++)
{for(var j=0;j<$.fn.imageviewer.options.newspaperArticles.articles[i].article.clip.coords.length;j++)
{var thisInpage=$.trim($.fn.imageviewer.options.newspaperArticles.articles[i].article.clip.coords[j].coord['inpage']);if(thisInpage==$.fn.imageviewer.options.itemId)
{var clipObj="";if($.fn.imageviewer.options.currentDivId=='clippingArea_'+$.fn.imageviewer.options.newspaperArticles.articles[i].article.id+"~"+j)
{if(setClick)
{clipObj=$.fn.imageviewer.options.options.newspaperArticles.articles[i].article.clip.coords[j].coord['value'].split(":");createArticleBoundryDiv($.fn.imageviewer.options.originalImageObj.height,$.fn.imageviewer.options.originalImageObj.width,$.fn.imageviewer.options.newspaperArticles.articles[i].article.id+"~"+j,$.fn.imageviewer.options.newspaperArticles.articles[i].article.id,clipObj[1],clipObj[0],clipObj[2],clipObj[3],$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex],setClick,$.fn.imageviewer.options.newspaperArticles.articles[i].article.title,thisInpage);zcounter++;}}else{clipObj=$.fn.imageviewer.options.newspaperArticles.articles[i].article.clip.coords[j].coord['value'].split(":");createArticleBoundryDiv($.fn.imageviewer.options.originalImageObj.height,$.fn.imageviewer.options.originalImageObj.width,$.fn.imageviewer.options.newspaperArticles.articles[i].article.id+"~"+j,$.fn.imageviewer.options.newspaperArticles.articles[i].article.id,clipObj[1],clipObj[0],clipObj[2],clipObj[3],$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex],setClick,$.fn.imageviewer.options.newspaperArticles.articles[i].article.title,thisInpage);zcounter++;}}}}
$("div[id^='articleListContainer_']").css("visibility","hidden");$("div[id^='articleListContainer_']").html("");var img_plus="<img src='/ui/cdm/default/collection/default/images/newspaper_plus.gif' style='border:none; padding-right:7px;'/>"
var img_minus="<img src='/ui/cdm/default/collection/default/images/newspaper_minus.gif' style='border:none; padding-right:7px;'/>"
$("a[id^='contentLink-'][id!='contentLink-"+thisInpage+"']").children("img").remove();$("a[id^='contentLink-'][id!='contentLink-"+thisInpage+"']").prepend("<img src='/ui/cdm/default/collection/default/images/newspaper_plus.gif' style='border:none; padding-right:7px;'/>");$("a[id='contentLink-"+thisInpage+"']").children("img").remove();$("a[id='contentLink-"+thisInpage+"']").prepend("<img src='/ui/cdm/default/collection/default/images/newspaper_minus.gif' style='border:none; padding-right:7px;'/>");for(prop in $.fn.imageviewer.options.articleArray){var thisId1=prop+"";var $articleListContainerItemDiv=$('<div/>');var articleListContainerItemId="articleListContainerItem_"+prop;$articleListContainerItemDiv.attr("id",articleListContainerItemId);$('#articleListContainer_'+thisInpage).append($articleListContainerItemDiv);$('#articleListContainer_'+thisInpage).append($('<hr style="border-style: none;width:60%;color:silver;background-color:silver;align:right;height:1px;"/>'));$('#'+articleListContainerItemId).html($.fn.imageviewer.options.articleArray[prop].title);$('#'+articleListContainerItemId).css("cursor","pointer");$('#'+articleListContainerItemId).css("padding-left","15px");$('#'+articleListContainerItemId).css("padding-top","0px");$('#'+articleListContainerItemId).css("padding-bottom","0px");$('#'+articleListContainerItemId).attr("title",$("#cdm_language_clicktoopenarticle").val());$('#'+articleListContainerItemId).attr("articleId",prop);$('#'+articleListContainerItemId).attr("class","body_link_11");var thisArticleListContainerItem=document.getElementById(articleListContainerItemId);thisArticleListContainerItem.setAttribute("onmouseover","$.fn.imageviewer.articleMouseover('"+$.fn.imageviewer.options.articleArray[prop].id+"')");thisArticleListContainerItem.setAttribute("onmouseout","$.fn.imageviewer.articleMouseout('"+$.fn.imageviewer.options.articleArray[prop].id+"')");thisArticleListContainerItem.setAttribute("onclick","$.fn.imageviewer.articleOpen('"+$.fn.imageviewer.options.articleArray[prop].id+"')");}
$('#articleListContainer_'+thisInpage).css("visibility","visible");}
$.fn.imageviewer.articleMouseover=function(thisArticleId){$('div[article="'+thisArticleId+'"]').css("filter","alpha(opacity=50)");$('div[article="'+thisArticleId+'"]').css("opacity","0.5");$('div[article="'+thisArticleId+'"]').css("-moz-opacity","0.5");$('div[article="'+thisArticleId+'"]').css("-khtml-opacity","0.5");$('div[articleid="'+thisArticleId+'"]').css("background","#fbec88");}
$.fn.imageviewer.articleMouseout=function(thisArticleId){$('div[article="'+thisArticleId+'"]').css("filter","alpha(opacity=0)");$('div[article="'+thisArticleId+'"]').css("opacity","0");$('div[article="'+thisArticleId+'"]').css("-moz-opacity","0.0");$('div[article="'+thisArticleId+'"]').css("-khtml-opacity","0.0");$('div[articleid="'+thisArticleId+'"]').css("background","");}
$.fn.imageviewer.articleOpen=function(thisArticleId){var myWindow=window.open('/utils/getarticleclippings/collection/'+$.fn.imageviewer.options.collection+'/id/'+$.fn.imageviewer.options.itemId+'/articleId/'+thisArticleId+'/compObjId/'+$.fn.imageviewer.options.compObjId+'/lang/'+$.fn.imageviewer.options.lang+'/dmtext/'+$.fn.imageviewer.options.fullTextSearchTerm.replace(' ','%20').replace('+','%20'),'','width=650,height=658,toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,copyhistory=no,resizable=yes')}
function createArticleBoundryDiv(imgHeight,imgWidth,thisId,thisArticle,thisTop,thisLeft,thisWidth,thisHeight,thisScale,setClick,title,pageId)
{cdmIVConsoleLogger('createArticleBoundryDiv: running');var left_offset=0;var top_offset=0;var multiplier=65535;var this_top=((thisTop/multiplier)*imgHeight)*thisScale/100;var this_left=((thisLeft/multiplier)*imgWidth)*thisScale/100;var this_width=((thisWidth/multiplier)*imgWidth)*thisScale/100;var this_height=((thisHeight/multiplier)*imgHeight)*thisScale/100;this_top=parseInt(this_top+top_offset);this_left=parseInt(this_left+left_offset);this_width=parseInt(this_width);this_height=parseInt(this_height);if(this_top<0){this_top=0;}
if(this_left<0){this_left=0;}
if(this_top+this_height>=$('#articleBoundryLayer').height()+top_offset-1)
{this_height=$('#articleBoundryLayer').height()-this_top+top_offset-2;}
if(this_left+this_width>=$('#articleBoundryLayer').width()+left_offset-1)
{this_width=$('#articleBoundryLayer').width()-this_left+left_offset-2;}
var $newDiv=$('<div/>');var thisNewDivId="clippingArea_"+thisId;$newDiv.attr("id",thisNewDivId);$newDiv.attr("article",thisArticle);$('#articleBoundryLayer').append($newDiv);$('div[id$="'+thisId+'"]').html("<div> </div>");$('div[id$="'+thisId+'"]').css("display","");$('div[id$="'+thisId+'"]').css("position","absolute");$('div[id$="'+thisId+'"]').css("cursor","default");$('div[id$="'+thisId+'"]').css("left",this_left);$('div[id$="'+thisId+'"]').css("top",this_top);$('div[id$="'+thisId+'"]').width(this_width);$('div[id$="'+thisId+'"]').height(this_height);if(title!=='')
{$('div[id$="'+thisId+'"]').attr("title",$("#cdm_language_dblclicktoopen").val()+" "+title);}else{$('div[id$="'+thisId+'"]').attr("title",$("#cdm_language_dblclicktoopen").val());}
if(title===""){$.fn.imageviewer.options.articleArray[thisArticle]={"title":"(untitled article)","id":thisArticle};}else{$.fn.imageviewer.options.articleArray[thisArticle]={"title":title,"id":thisArticle};}
$('div[article="'+thisArticle+'"]').css("background","#fbec88");$('div[article="'+thisArticle+'"]').css("filter","alpha(opacity=0)");$('div[article="'+thisArticle+'"]').css("opacity","0");$('div[article="'+thisArticle+'"]').css("-moz-opacity","0.0");$('div[article="'+thisArticle+'"]').css("-khtml-opacity","0.0");$('div[id$="'+thisId+'"]').mouseover(function(){$('div[article="'+thisArticle+'"]').css("filter","alpha(opacity=50)");$('div[article="'+thisArticle+'"]').css("opacity","0.5");$('div[article="'+thisArticle+'"]').css("-moz-opacity","0.5");$('div[article="'+thisArticle+'"]').css("-khtml-opacity","0.5");$('div[articleid="'+thisArticle+'"]').css("background","#fbec88");});$('div[id$="'+thisId+'"]').mouseout(function(){$('div[article="'+thisArticle+'"]').css("filter","alpha(opacity=0)");$('div[article="'+thisArticle+'"]').css("opacity","0");$('div[article="'+thisArticle+'"]').css("-moz-opacity","0.0");$('div[article="'+thisArticle+'"]').css("-khtml-opacity","0.0");$('div[articleid="'+thisArticle+'"]').css("background","");});$('div[id$="'+thisId+'"]').dblclick(function(){$.fn.imageviewer.articleOpen(thisArticle)});}
articleMouseOver=function(){}
loader=function(){}
function debug($obj){};$.fn.imageviewer.getColor=function(){return $.fn.imageviewer.options.zoomBorderColor;};$.fn.inlineOffset=function(){var el=$('<i id="tempEl"/>').css('display','inline').insertBefore(this[0]);var pos=$("#tempEl").offset();el.remove();return pos;};$.fn.imageviewer.varInit=function(){if($.fn.imageviewer.options.loadImageDir!=""){$.fn.imageviewer.options.loadImageUrlDir=$.fn.imageviewer.options.viewerDirectory+$.fn.imageviewer.options.loadImageDir;}else{$.fn.imageviewer.options.loadImageUrlDir="";}
if($.fn.imageviewer.options.imageviewerbgImg!=""){$.fn.imageviewer.options.imageviewerbgUrl="url("+$.fn.imageviewer.options.loadImageUrlDir+"/"+$.fn.imageviewer.options.imageviewerbgImg+")";}else{$.fn.imageviewer.options.imageviewerbgUrl="";}
if($.fn.imageviewer.options.loadImageFile!=""){$.fn.imageviewer.options.loadImageUrl=$.fn.imageviewer.options.loadImageUrlDir+"/"+$.fn.imageviewer.options.loadImageFile;}else{$.fn.imageviewer.options.loadImageUrl="";}
if($.fn.imageviewer.options.imgDivBg!=""){$.fn.imageviewer.options.imgDivBgUrl=$.fn.imageviewer.options.loadImageUrlDir+"/"+$.fn.imageviewer.options.imgDivBg;}else{$.fn.imageviewer.options.imgDivBgUrl="";}
if(typeof itemViewerFullScreen!="undefined")
{$.fn.imageviewer.options.fullBrowserMode=itemViewerFullScreen;$.fn.imageviewer.killToolBarButtons($.fn.imageviewer.options.fullBrowserButtonId);}}
String.prototype.endsWith=function(str)
{return(this.match(str+"$")==str)}
$.fn.imageviewer.getColor2=function(){return $.fn.imageviewer.options.zoomBorderColor;};$.fn.imageviewer.prepToolbar=function()
{if($.fn.imageviewer.options.toolBarButtonKill!="")
{$.fn.imageviewer.killToolBarButtons($.fn.imageviewer.options.toolBarButtonKill);}
$("#"+$.fn.imageviewer.options.toolbarDiv).css("display","block");}
$.fn.imageviewer.killToolBarButtons=function(delimitedString){var strArry=delimitedString.split(/\|/);for(x in strArry)
{$("#"+strArry[x]).remove();}}
$.fn.imageviewer.windowResize=function(el)
{viewportResize(el);if($(SELECTOR_VIEWPORT).length>0)
{dragStop();}}
viewportResize=function(el)
{if($(SELECTOR_VIEWPORT).length>0)
{setViewPortObjHeight();$.fn.imageviewer.options.viewportObj.width=$("#"+el).width()-(2*$.fn.imageviewer.options.imageviewerbordersize);$.fn.imageviewer.options.viewportObj.top=$('#viewport').offset().top+parseInt($('#viewport').css("borderTopWidth"),10);$.fn.imageviewer.options.viewportObj.left=$('#viewport').offset().left+parseInt($('#viewport').css("borderLeftWidth"),10);$('#verticalDragbarImg').css("left",(parseInt($('#viewport').width())/2)-$('#viewport').offset().left);$('#viewport').css("width",$.fn.imageviewer.options.viewportObj.width);$('#viewport').css("height",$.fn.imageviewer.options.viewportObj.height);setThumbnailDragBoxDiminsions();refreshDebugLayer();}}
$.fn.imageviewer.loadVerticalDragbar=function()
{if(cdm.ItemViewer.imageBandHeight>0&&cdm.ItemViewer.mixedCompoundObj){ibh=cdm.ItemViewer.imageBandHeight;}else{ibh=0;}
if($('#verticalDragbarImg').exists()){cdmIVConsoleLogger("removing old dragbar");$('#verticalDragbarImg').remove();}
var $verticalDragbar=$('<img>');$verticalDragbar.attr("id","verticalDragbarImg");$("#img_view_container").append($verticalDragbar);setVerticalDragbarDrag();$('#verticalDragbarImg').css("position","absolute");$('#verticalDragbarImg').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/grabber_horiz.gif");$('#verticalDragbarImg').css("z-index","9999")
$('#verticalDragbarImg').css("left",(parseInt($('#viewport').width())/2)-$('#viewport').offset().left)
$('#verticalDragbarImg').css("top",parseInt($('#img_view_container').css("top"))+parseInt($('#img_view_container').height())+ibh);$('#verticalDragbarImg').css("display","inline");if(ibh>0){tempTop=$('#verticalDragbarImg').offset().top;$('#verticalDragbarImg').offset({top:tempTop+ibh});cdm.ItemViewer.imageBandHeight=0;cdm.ItemViewer.mixedCompoundObj=false;}}
setVerticalDragbarDrag=function()
{var dragOpt={cursor:"n-resize",axis:"y",drag:function(event,ui){$.fn.imageviewer.options.viewportObj.height=parseInt($('#verticalDragbarImg').offset().top)-$('#viewport').offset().top-parseInt($('#img_rights_band').css("height"),10);$('#viewport').css("height",$.fn.imageviewer.options.viewportObj.height);refreshDebugLayer();},stop:function(event,ui){$.fn.imageviewer.options.viewportObj.height=parseInt($('#verticalDragbarImg').offset().top)-$('#viewport').offset().top-parseInt($('#img_rights_band').css("height"),10);$('#viewport').css("height",$.fn.imageviewer.options.viewportObj.height);setThumbnailDragBoxDiminsions();refreshDebugLayer();dragStop();if($("#cdm_view").val()=="compoundobject"){$('#verticalDragbarImg').css("top",parseInt($('#verticalDragbarImg').css("top"))-($.fn.imageviewer.options.imageviewerbordersize+2));cdm.CompoundObject.viewerHeight=$.fn.imageviewer.options.viewportObj.height;cdm.CompoundObject.resetWrapperHeight();}}};$('#verticalDragbarImg').draggable("destroy");$('#verticalDragbarImg').draggable(dragOpt);$('#verticalDragbarImg').css("cursor","n-resize");}
$.fn.imageviewer.setToolbarSlider=function()
{$("#scaleSlider").slider({animate:true,value:$.fn.imageviewer.options.scaleIndex,min:$.fn.imageviewer.options.scaleIndexMin,max:$.fn.imageviewer.options.scaleArray.length-1,step:1,slide:function(event,ui){$("#zoomLabel").html($.fn.imageviewer.options.scaleArray[ui.value]+'%');zoomToIndex(ui.value);}});}
zoomButtonHandler=function(keycode)
{switch(keycode){case(107):$("#toolbar_plus_button").focus()
zoomKeys(1);break;case(187):$("#toolbar_plus_button").focus()
zoomKeys(1);break;case 109:$("#toolbar_minus_button").focus()
zoomKeys(-1);break;case 189:$("#toolbar_minus_button").focus()
zoomKeys(-1);break;}}
buttonHandler=function(el)
{switch(el.id){case("toolbar_minus_button"):zoomKeys(-1);break;case("toolbar_plus_button"):zoomKeys(1);break;case("toolbar_fit"):$.fn.imageviewer.options.keyZoom=true;zoomFitToViewport();break;case("toolbar_fit_width"):$.fn.imageviewer.options.keyZoom=true;zoomFitToWidth();break;case("toolbar_actual_size"):$.fn.imageviewer.options.keyZoom=true;zoomActualSize();break;case("toolbar_rotate_left"):$.fn.imageviewer.options.keyZoom=true;imageRotateLeft();break;case("toolbar_rotate_rt"):$.fn.imageviewer.options.keyZoom=true;imageRotateRight();break;case("toolbar_area_select"):var clipArea={height:200,width:300};var clipTargetElement='viewport';$.fn.imageviewer.clipImage(clipTargetElement,clipArea);break;}}
$.fn.imageviewer.clipImage=function(thisClipTargetElement,thisClipArea)
{$('#'+thisClipTargetElement).imgAreaSelect({handles:true,x1:$('#'+thisClipTargetElement).width()/2-Math.round(thisClipArea.width/2),y1:$('#'+thisClipTargetElement).height()/2-Math.round(thisClipArea.height/2),x2:$('#'+thisClipTargetElement).width()/2+Math.round(thisClipArea.width/2),y2:$('#'+thisClipTargetElement).height()/2+Math.round(thisClipArea.height/2),onSelectEnd:function(img,selection){$('#'+thisClipTargetElement).imgAreaSelect({remove:true});}});}
buttonKeyDow=function(el)
{document.defaultAction=false;switch(event.keyCode){case(32):buttonHandler(el);return document.defaultAction;break;case(13):buttonHandler(el);return document.defaultAction;break;}}
zoomKeys=function(thisDelta)
{$.fn.imageviewer.options.pubDelta=thisDelta;$.fn.imageviewer.options.keyZoom=true;stopCount();var newImgScale=getImgScale($.fn.imageviewer.options.pubDelta);if(newImgScale>$.fn.imageviewer.options.imgScale&&$.fn.imageviewer.options.imgScale==$.fn.imageviewer.options.imgMaxScale)
{startCount()
return false;}
if(newImgScale<$.fn.imageviewer.options.imgScale&&$.fn.imageviewer.options.imgScale==$.fn.imageviewer.options.imgMinScale)
{startCount()
return false;}
$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;$.fn.imageviewer.options.imgScale=newImgScale;$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();startCount();}
zoomToIndex=function(thisIndex)
{$.fn.imageviewer.options.keyZoom=true;stopCount();$.fn.imageviewer.options.scaleIndex=thisIndex;var newImgScale=$.fn.imageviewer.options.scaleArray[thisIndex];$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;$.fn.imageviewer.options.imgScale=newImgScale;$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();startCount();}
zoomToCustom=function(thisScale)
{if(thisScale==""){$.fn.imageviewer.options.initialzoomcustom=$.fn.imageviewer.options.scaleArray[0];thisScale=$.fn.imageviewer.options.scaleArray[0];}
if(thisScale<$.fn.imageviewer.options.scaleArray[0]){$.fn.imageviewer.options.initialzoomcustom=$.fn.imageviewer.options.scaleArray[0];thisScale=$.fn.imageviewer.options.scaleArray[0];}
$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;var thisImgScale=thisScale;if(thisImgScale>$.fn.imageviewer.options.imgMaxScale)
{thisImgScale=$.fn.imageviewer.options.imgMaxScale;}
for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++)
{if(thisImgScale==$.fn.imageviewer.options.scaleArray[i])
{$.fn.imageviewer.options.scaleIndex=i;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}else{if($.fn.imageviewer.options.scaleArray[i]>thisImgScale)
{$.fn.imageviewer.options.scaleIndex=i-1;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}}}
$.fn.imageviewer.options.setToTop=true;stopCount();$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();mouseBox();$.fn.imageviewer.countComplete();}
zoomActualSize=function()
{stopCount();$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;$.fn.imageviewer.options.scaleIndex=$.fn.imageviewer.options.scaleArray.length-1;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();$.fn.imageviewer.countComplete();}
zoomFitToWidth=function()
{var thisImgScale=parseInt((parseInt($(SELECTOR_VIEWPORT).width())/$.fn.imageviewer.options.originalImageObj.width)*100,10);if($.fn.imageviewer.options.imgScale!=undefined){$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;}else{$.fn.imageviewer.options.prevImgScale=thisImgScale;$.fn.imageviewer.options.imgScale=thisImgScale;}
if(thisImgScale>$.fn.imageviewer.options.imgMaxScale)
{thisImgScale=$.fn.imageviewer.options.imgMaxScale;}
for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++)
{if(thisImgScale==$.fn.imageviewer.options.scaleArray[i])
{$.fn.imageviewer.options.scaleIndex=i;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}else{if($.fn.imageviewer.options.scaleArray[i]>thisImgScale)
{$.fn.imageviewer.options.scaleIndex=i-1;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}}}
if($.fn.imageviewer.options.imgScale==undefined){$.fn.imageviewer.options.imgScale=thisImgScale;}
$.fn.imageviewer.options.setToTop=true;stopCount();$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();mouseBox();$.fn.imageviewer.countComplete();}
checkMinZoom=function()
{$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;var thisXScale=parseInt(($.fn.imageviewer.options.viewportObj.width/$.fn.imageviewer.options.originalImageObj.width)*100,10);var thisYScale=parseInt(($.fn.imageviewer.options.viewportObj.height/$.fn.imageviewer.options.originalImageObj.height)*100,10);var tempImgScale=0;if(thisXScale<thisYScale)
{tempImgScale=thisXScale;}else{tempImgScale=thisYScale;}
var thisImgScale=tempImgScale;if(thisImgScale<$.fn.imageviewer.options.scaleArray[0])
{$.fn.imageviewer.options.scaleArray.unshift(thisImgScale);if($.fn.imageviewer.options.scaleArray[0]<1)
{$.fn.imageviewer.options.scaleArray[0]=1;}}}
zoomFitToViewport=function()
{cdmIVConsoleLogger("zoomFitToViewport");cdmIVConsoleLogger("initial zoom is: "+$.fn.imageviewer.options.initialzoom);$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;var thisXScale=parseInt(($.fn.imageviewer.options.viewportObj.width/$.fn.imageviewer.options.originalImageObj.width)*100,10);var thisYScale=parseInt(($.fn.imageviewer.options.viewportObj.height/$.fn.imageviewer.options.originalImageObj.height)*100,10);var tempImgScale=0;if(thisXScale<thisYScale)
{tempImgScale=thisXScale;}else{tempImgScale=thisYScale;}
var thisImgScale=tempImgScale;cdmIVConsoleLogger("thisImgScale:"+thisImgScale);if(thisImgScale<$.fn.imageviewer.options.scaleArray[0])
{$.fn.imageviewer.options.scaleArray.unshift(thisImgScale-1);cdmIVConsoleLogger("$.fn.imageviewer.options.scaleArray[0]:"+thisImgScale);}
for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++)
{cdmIVConsoleLogger("---thisImgScale: "+thisImgScale+" :: "+"scaleArray["+i+"]: "+$.fn.imageviewer.options.scaleArray[i]+" :: tempImgScale: "+tempImgScale);if(thisImgScale==$.fn.imageviewer.options.scaleArray[i])
{$.fn.imageviewer.options.scaleIndex=i;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}else{if($.fn.imageviewer.options.scaleArray[i]>thisImgScale)
{$.fn.imageviewer.options.scaleIndex=i-1;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}}}
stopCount();$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();$.fn.imageviewer.countComplete();}
moveImgLayer=function(thisDirection,thisDistance)
{switch(thisDirection){case("up"):$('#imageLayer').css("top",(parseInt($('#imageLayer').css("top"))-thisDistance));break;case("down"):$('#imageLayer').css("top",(parseInt($('#imageLayer').css("top"))+thisDistance));break;case("left"):$('#imageLayer').css("left",(parseInt($('#imageLayer').css("left"))-thisDistance));break;case("right"):$('#imageLayer').css("left",(parseInt($('#imageLayer').css("left"))+thisDistance));break;}
movethumbnailDragDiv();dragStop();}
$(window).resize(function(){if(typeof($.fn.imageviewer.options)!=='undefined'&&$.fn.imageviewer.options!=null){$.fn.imageviewer.windowResize($.fn.imageviewer.options.parentElement);}else{cdmIVConsoleLogger("image viewer options null!");}});loadDebug=function()
{var $debugDiv=$('<div/>');$debugDiv.attr("id","debugLayer");$("#imageDiv").prepend($debugDiv);$('#debugLayer').css("position","absolute");$('#debugLayer').css("overflow","hidden");$('#debugLayer').css("z-index","9999")
$('#debugLayer').css("left",$('#viewport').css("left"));$('#debugLayer').css("top",$('#viewport').css("top"));$('#debugLayer').css("padding",15);$('#debugLayer').css("overflow","auto");$('#debugLayer').css("background","white");$('#debugLayer').css("height",$.fn.imageviewer.options.viewportObj.height-29);$('#debugLayer').css("width",($.fn.imageviewer.options.viewportObj.width-29)*.5);$('#debugLayer').css("display","none");$('#debugLayer').css("filter","alpha(opacity=50)");$('#debugLayer').css("-moz-opacity","0.5");$('#debugLayer').css("-khtml-opacity","0.5");$('#debugLayer').css("opacity","0.5");}
refreshDebugLayer=function()
{$('#debugLayer').css("height",$.fn.imageviewer.options.viewportObj.height-29);$('#debugLayer').css("width",($.fn.imageviewer.options.viewportObj.width-29)*.5);$('#debugLayer').html(debugLayerContentGen()+debugInfo()+$.fn.imageviewer.options.contextDebugInput);}
debugLayerContentGen=function()
{return"<input type='button' value='Reload' onclick='refreshDebugLayer()'/><br/><br/>"}
setViewPortObjHeight=function()
{if($.fn.imageviewer.options.fullBrowserMode)
{$.fn.imageviewer.options.viewportObj.height=$(window).height()-$('#viewport').offset().top-$.fn.imageviewer.options.fullBrowserWindowOffset-parseInt($("#img_rights_band").css("height"),10);}}
scaleOverlayCreate=function()
{if($("#imageLayer").length>0)
{if($("#scaleOverlay").length<=0)
{var $scaleOverlayDiv=$('<div/>');$scaleOverlayDiv.attr("id","scaleOverlay");$("body").append($scaleOverlayDiv);$('#scaleOverlay').css("position","absolute");$('#scaleOverlay').css("overflow","hidden");$('#scaleOverlay').css("z-index","1000")
$('#scaleOverlay').css("left",$('#viewport').offset().left);$('#scaleOverlay').css("top",$('#viewport').offset().top);$('#scaleOverlay').css("filter","alpha(opacity=30)");$('#scaleOverlay').css("-moz-opacity","0.3");$('#scaleOverlay').css("-khtml-opacity","0.3");$('#scaleOverlay').css("opacity","0.3");$('#scaleOverlay').css("height",$.fn.imageviewer.options.viewportObj.height);$('#scaleOverlay').css("width",$.fn.imageviewer.options.viewportObj.width);$('#scaleOverlay').css("text-align","center");$('#scaleOverlay').css("vertical-align","middle");$('#scaleOverlay').css("color","red");$('#scaleOverlay').css("font-size","72px");$('#scaleOverlay').css("font-weight","bold");$('#scaleOverlay').css("display","block");}
var thisImg="";if($.fn.imageviewer.options.pubDelta>0)
{thisImg=$.fn.imageviewer.options.zoomOverlayPlus;}else{thisImg=$.fn.imageviewer.options.zoomOverlayMinus;}
$('#scaleOverlay').html("<img src='"+$.fn.imageviewer.options.loadImageUrlDir+"/"+thisImg+"' id='zoom_icon'/>");$('#zoom_icon').css("position","absolute");$('#zoom_icon').css("left",(($.fn.imageviewer.options.viewportObj.width*.5)-(parseInt($('#zoom_icon').css("width"))/2)));$('#zoom_icon').css("top",(($.fn.imageviewer.options.viewportObj.height*.5)-(parseInt($('#zoom_icon').css("height"))/2)));$("#scaleSlider").slider("option","value",$.fn.imageviewer.options.scaleIndex);if($.fn.imageviewer.options.scaleIndex<0){$('#scaleSlider').attr('title',$.fn.imageviewer.options.imgScale+"%");}else{$('#scaleSlider').attr('title',$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex]+"%");}}}
scaleOverlayDestroy=function()
{$('#scaleOverlay').remove();$('#zoomBox').remove();}
mouseBoxDestroy=function()
{$('#mouseBox').remove();}
mouseBox=function()
{$.fn.imageviewer.options.viewportObj.top=$('#viewport').offset().top+parseInt($('#viewport').css("borderTopWidth"),10);$.fn.imageviewer.options.viewportObj.left=$('#viewport').offset().left+parseInt($('#viewport').css("borderLeftWidth"),10);var viewportBoundryLeft=$('#viewport').offset().left+parseInt($('#viewport').css("borderTopWidth"),10);var viewportBoundryTop=$('#viewport').offset().top+parseInt($('#viewport').css("borderLeftWidth"),10);if($("#mouseBox").length<1)
{var $mouseBoxDiv=$('<div/>');$mouseBoxDiv.attr("id","mouseBox");$("body").append($mouseBoxDiv);$('#mouseBox').css("z-index","1000")
$('#mouseBox').css("position","absolute");$('#mouseBox').css("overflow","hidden");$('#mouseBox').css("left",viewportBoundryLeft);$('#mouseBox').css("top",viewportBoundryTop);$('#mouseBox').css("height",$.fn.imageviewer.options.viewportObj.height-parseInt($('#viewport').css("borderTopWidth"),10));$('#mouseBox').css("width",$.fn.imageviewer.options.viewportObj.width-parseInt($('#viewport').css("borderLeftWidth"),10));$('#mouseBox').css("border","solid "+$.fn.imageviewer.options.zoomBorderColor+" "+$.fn.imageviewer.options.zoomBorderWidth);$("#mouseBox").mousemove(function(e){mouseMove(e)});$("#mouseBox").click(function(){clearTimeout($.fn.imageviewer.options.loadImageCountdown);$.fn.imageviewer.countComplete();});$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.oldImgScale/$.fn.imageviewer.options.imgScale;}else{$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.oldImgScale/$.fn.imageviewer.options.imgScale;$().mousemove(function(e){setMousePos(e);});if(($.fn.imageviewer.options.viewportObj.width-parseInt($('#viewport').css("borderLeftWidth"),10))*$.fn.imageviewer.options.currentZoom<parseInt($.fn.imageviewer.options.viewportObj.width))
{$('#mouseBox').css("width",($.fn.imageviewer.options.viewportObj.width-parseInt($('#viewport').css("borderLeftWidth"),10))*$.fn.imageviewer.options.currentZoom);}
if(($.fn.imageviewer.options.viewportObj.height-parseInt($('#viewport').css("borderTopWidth"),10))*$.fn.imageviewer.options.currentZoom<parseInt($.fn.imageviewer.options.viewportObj.height))
{$('#mouseBox').css("height",($.fn.imageviewer.options.viewportObj.height-parseInt($('#viewport').css("borderTopWidth"),10))*$.fn.imageviewer.options.currentZoom);}
if($.fn.imageviewer.options.mousePos.x-($('#mouseBox').width()/2)>viewportBoundryLeft)
{$('#mouseBox').css("left",$.fn.imageviewer.options.mousePos.x-($('#mouseBox').width()/2));}else{$('#mouseBox').css("left",viewportBoundryLeft);}
if($.fn.imageviewer.options.mousePos.x+($('#mouseBox').width()/2)>(0+(parseInt($.fn.imageviewer.options.viewportObj.width))+viewportBoundryLeft-8))
{$('#mouseBox').css("left",(0+parseInt($.fn.imageviewer.options.viewportObj.width)+viewportBoundryLeft-8)-$('#mouseBox').width());}
if($.fn.imageviewer.options.mousePos.y-($('#mouseBox').height()/2)>viewportBoundryTop-1)
{$('#mouseBox').css("top",$.fn.imageviewer.options.mousePos.y-($('#mouseBox').height()/2));}else{$('#mouseBox').css("top",viewportBoundryTop);}
if($.fn.imageviewer.options.mousePos.y+($('#mouseBox').height()/2)>(0+(parseInt($.fn.imageviewer.options.viewportObj.height))+viewportBoundryTop-8))
{$('#mouseBox').css("top",(0+parseInt($.fn.imageviewer.options.viewportObj.height)+viewportBoundryTop-8)-$('#mouseBox').height());}}
if($.fn.imageviewer.options.imgScale<=$.fn.imageviewer.options.oldImgScale)
{$('#mouseBox').css("border","solid red 0px");}else{$('#mouseBox').css("border","solid "+$.fn.imageviewer.options.zoomBorderColor+" "+$.fn.imageviewer.options.zoomBorderWidth);}}
$.fn.imageviewer.createImageViewer=function(el)
{if($(SELECTOR_VIEWPORT).length<=0)
{$("#"+el.id).html("<div id='imageDiv'></div>");var $imageViewerDiv=$('<div/>');$imageViewerDiv.attr("id","viewport");$("#imageDiv").append($imageViewerDiv);$('#viewport').css("position","relative");$('#viewport').css("overflow","hidden");if($.fn.imageviewer.options.imageviewerbgUrl!=""){$('#viewport').css("background-image",$.fn.imageviewer.options.imageviewerbgUrl);}
else{$('#viewport').css("background",$.fn.imageviewer.options.imageviewerbgcolor);}
setViewPortObjHeight();$('#viewport').css("height",$.fn.imageviewer.options.viewportObj.height);$.fn.imageviewer.options.viewportObj.width=$.fn.imageviewer.options.viewportObj.width-(2*$.fn.imageviewer.options.imageviewerbordersize);$('#viewport').css("width",$.fn.imageviewer.options.viewportObj.width);$('#viewport').css("border",$.fn.imageviewer.options.imageviewerbordercolor+" "+$.fn.imageviewer.options.imageviewerbordersize+"px");$(SELECTOR_VIEWPORT).mousemove(function(e){mouseMove(e)});$.fn.imageviewer.options.viewportObj.top=parseInt($('#viewport').offset().top)+parseInt($('#viewport').css("borderTopWidth"),10);if($.fn.imageviewer.options.fullBrowserText){$.fn.imageviewer.options.viewportObj.left=parseInt($('#viewport').offset().left)+parseInt($('#viewport').css("borderLeftWidth"),10)+10;}else{$.fn.imageviewer.options.viewportObj.left=parseInt($('#viewport').offset().left)+parseInt($('#viewport').css("borderLeftWidth"),10);}}}
mouseMove=function(e)
{setMousePos(e);if($("#mouseBox").length>=1)
{resetCount();mouseBox();}}
setMousePos=function(e)
{$.fn.imageviewer.options.mousePos.x=e.pageX||e.clientX;$.fn.imageviewer.options.mousePos.y=e.pageY||e.clientY;var pageCoords="( "+$.fn.imageviewer.options.mousePos.x+", "+$.fn.imageviewer.options.mousePos.y+" )";var clientCoords="( "+$.fn.imageviewer.options.mousePos.x+", "+$.fn.imageviewer.options.mousePos.y+" )";}
mouseWheelFunc=function(event,delta)
{stopCount();if($.fn.imageviewer.options.mouseboxInit)
{$.fn.imageviewer.options.pubDelta=0;$.fn.imageviewer.options.mouseboxInit=false;}else{if(delta<0)
{$.fn.imageviewer.options.pubDelta=-1;}else{$.fn.imageviewer.options.pubDelta=1;}}
var newImgScale=getImgScale($.fn.imageviewer.options.pubDelta);if(newImgScale>$.fn.imageviewer.options.imgScale&&$.fn.imageviewer.options.imgScale==$.fn.imageviewer.options.imgMaxScale)
{startCount()
return false;}
if(newImgScale<$.fn.imageviewer.options.imgScale&&$.fn.imageviewer.options.imgScale==$.fn.imageviewer.options.imgMinScale)
{startCount()
return false;}
$.fn.imageviewer.options.prevImgScale=$.fn.imageviewer.options.imgScale;$.fn.imageviewer.options.imgScale=newImgScale;$.fn.imageviewer.options.currentZoom=$.fn.imageviewer.options.currentZoom+(($.fn.imageviewer.options.prevImgScale-$.fn.imageviewer.options.imgScale)*.01);scaleOverlayCreate();mouseBox();startCount();return true;}
$.fn.imageviewer.setImageDiv=function()
{$('#imageLayer').remove();var $imageLayerDiv=$('<div/>');$imageLayerDiv.attr("id","imageLayer");$(SELECTOR_VIEWPORT).append($imageLayerDiv);$('#imageLayer').css("position","relative");$('#imageLayer').css("cursor","default");}
$.fn.imageviewer.imageInit=function()
{var thisXdim;var thisYdim;if($.fn.imageviewer.options.rotation==90||$.fn.imageviewer.options.rotation==270)
{thisXdim=parseInt($.fn.imageviewer.options.originalImageObj.height);thisYdim=parseInt($.fn.imageviewer.options.originalImageObj.width);}else{thisXdim=parseInt($.fn.imageviewer.options.originalImageObj.width);thisYdim=parseInt($.fn.imageviewer.options.originalImageObj.height);}
var thisXScale=parseInt((parseInt($(SELECTOR_VIEWPORT).width())/thisXdim)*100,10);var thisYScale=parseInt((parseInt($(SELECTOR_VIEWPORT).height())/thisYdim)*100,10);var tempImgScale=0;if(thisXScale<thisYScale)
{tempImgScale=thisXScale;}else{tempImgScale=thisYScale;}
if(tempImgScale>$.fn.imageviewer.options.imgMaxScale)
{tempImgScale=$.fn.imageviewer.options.imgMaxScale;}
var thisImgScale=0;if(!$.fn.imageviewer.options.fullBrowserMode){thisImgScale=tempImgScale;}else{if($.fn.imageviewer.options.fullBrowserText){thisImgScale=parseInt((parseInt($(SELECTOR_VIEWPORT).width()-10)/$.fn.imageviewer.options.originalImageObj.width)*100,10);}else{thisImgScale=parseInt((parseInt($(SELECTOR_VIEWPORT).width())/$.fn.imageviewer.options.originalImageObj.width)*100,10);}
$.fn.imageviewer.options.setToTop=true;}
if(thisImgScale>$.fn.imageviewer.options.imgMaxScale)
{thisImgScale=$.fn.imageviewer.options.imgMaxScale;}
for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++)
{if(thisImgScale==$.fn.imageviewer.options.scaleArray[i])
{$.fn.imageviewer.options.scaleIndex=i;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}else{if($.fn.imageviewer.options.scaleArray[i]>thisImgScale)
{$.fn.imageviewer.options.scaleIndex=i-1;$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];i=$.fn.imageviewer.options.scaleArray.length;}}}
if((parseInt($(SELECTOR_VIEWPORT).width())>=$.fn.imageviewer.options.originalImageObj.width)&&(parseInt($(SELECTOR_VIEWPORT).height())>=$.fn.imageviewer.options.originalImageObj.height))
{$.fn.imageviewer.options.scaleIndex=$.fn.imageviewer.options.scaleArray.length-1
$.fn.imageviewer.options.imgScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];}
$.fn.imageviewer.options.scaleIndexMin=$.fn.imageviewer.options.scaleIndex;$.fn.imageviewer.options.imgMinScale=$.fn.imageviewer.options.imgScale;if($.fn.imageviewer.options.scaleIndexMin==$.fn.imageviewer.options.scaleArray.length-1)
{$.fn.imageviewer.options.scaleIndexMin=$.fn.imageviewer.options.scaleIndex-1;$.fn.imageviewer.options.imgMinScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndexMin];}
$.fn.imageviewer.options.scaleIndexMin=0;$.fn.imageviewer.options.imgMinScale=$.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndexMin];;$.fn.imageviewer.options.oldImgScale=$.fn.imageviewer.options.imgScale;switch($.fn.imageviewer.options.initialzoom){case("width"):zoomFitToWidth();$.fn.imageviewer.options.setToTop=true;break;case("window"):zoomFitToViewport();break;case("custom"):zoomToCustom($.fn.imageviewer.options.initialzoomcustom);break;}}
resetCount=function()
{stopCount();startCount();}
stopCount=function()
{clearTimeout($.fn.imageviewer.options.loadImageCountdown);}
startCount=function()
{$.fn.imageviewer.options.loadImageCountdown=setTimeout("$.fn.imageviewer.countComplete();",700);}
$.fn.imageviewer.countComplete=function()
{if($.fn.imageviewer.options.keyZoom)
{if($.fn.imageviewer.options.pubDelta>0)
{}else{}}
setZoomViewCoords();$.fn.imageviewer.loadImage();$.fn.imageviewer.loadThumbnail();newspaperLoader();}
$.fn.imageviewer.loadImage=function()
{mouseBoxDestroy();scaleOverlayDestroy();$('#imageLayer').css("cursor","wait");initTiles();setDrag();$.fn.imageviewer.setBrand();dragStop();}
setZoomViewCoords=function()
{$.fn.imageviewer.options.mouseboxInit=true;if($.fn.imageviewer.options.imgScale==undefined&&$.fn.imageviewer.options.oldImgScale==undefined&&$.fn.imageviewer.options.initialzoom=="width"){cdmIVConsoleLogger("houston we have a problem...");}
if($.fn.imageviewer.options.imgScale<=$.fn.imageviewer.options.oldImgScale||$.fn.imageviewer.options.keyZoom||$.fn.imageviewer.options.initialzoom=="window"){var thisVPH=$(SELECTOR_VIEWPORT).height();var thisVPW=$(SELECTOR_VIEWPORT).width();var thisILW=0;var thisILH=0;if($.fn.imageviewer.options.rotation==90||$.fn.imageviewer.options.rotation==270)
{thisILW=parseInt($.fn.imageviewer.options.originalImageObj.height*($.fn.imageviewer.options.imgScale*.01),10);thisILH=parseInt($.fn.imageviewer.options.originalImageObj.width*($.fn.imageviewer.options.imgScale*.01),10);}else{thisILH=parseInt($.fn.imageviewer.options.originalImageObj.height*($.fn.imageviewer.options.imgScale*.01),10);thisILW=parseInt($.fn.imageviewer.options.originalImageObj.width*($.fn.imageviewer.options.imgScale*.01),10);}
$.fn.imageviewer.options.startPosTop=(thisVPH/2)-thisILH/2;$.fn.imageviewer.options.startPosLeft=(thisVPW/2)-thisILW/2;$.fn.imageviewer.options.keyZoom=false;if($.fn.imageviewer.options.setToTop)
{$.fn.imageviewer.options.startPosTop=0;$.fn.imageviewer.options.setToTop=false;}}else{var viewportPosTop=$('#viewport').offset().top;var viewporttPosLeft=parseInt($('#viewport').css("left"));var mouseBoxPosTop=($('#mouseBox').offset().top-$('#viewport').offset().top);var mouseBoxPosLeft=(parseInt($('#mouseBox').offset().left)-parseInt($('#viewport').offset().left));var mouseBoxHeight=parseInt($('#mouseBox').css("height"));var mouseBoxWidth=parseInt($('#mouseBox').css("width"));var imageLayerPosTop=parseInt($('#imageLayer').css("top"));var imageLayertPosLeft=parseInt($('#imageLayer').css("left"));var currentImageWidth=parseInt($('#imageLayer').css("width"));var currentImageHeight=parseInt($('#imageLayer').css("height"));var currentScaleMultiplier=$.fn.imageviewer.options.originalImageObj.width/currentImageWidth;var oldImgScaleAdjustedMousePosOnImageLayerTop=mouseBoxPosTop-imageLayerPosTop;var oldImgScaleAdjustedMousePosOnImageLayerLeft=mouseBoxPosLeft-imageLayertPosLeft;$.fn.imageviewer.options.startPosTop=((oldImgScaleAdjustedMousePosOnImageLayerTop*currentScaleMultiplier)*($.fn.imageviewer.options.imgScale*.01))*-1;$.fn.imageviewer.options.startPosLeft=((oldImgScaleAdjustedMousePosOnImageLayerLeft*currentScaleMultiplier)*($.fn.imageviewer.options.imgScale*.01))*-1;if($.fn.imageviewer.options.setToTop)
{$.fn.imageviewer.options.startPosTop=0;$.fn.imageviewer.options.setToTop=false;}
$.fn.imageviewer.options.startPosTop+=4;$.fn.imageviewer.options.startPosLeft+=4;}
$.fn.imageviewer.options.contextDebugInput=""+"Rows: "+$.fn.imageviewer.options.rows+"<br/>"+"Cols: "+$.fn.imageviewer.options.cols+"<br/>"+"imgWidthModulo: "+$.fn.imageviewer.options.imgWidthModulo+"<br/>"+"imgHeightModulo: "+$.fn.imageviewer.options.imgHeightModulo+"<br/>"+"originalImageObj.height: "+$.fn.imageviewer.options.originalImageObj.height+"<br/>"+"originalImageObj.width: "+$.fn.imageviewer.options.originalImageObj.width+"<br/>"+"oldImgScale:  "+$.fn.imageviewer.options.oldImgScale+"<br/>"+"imgScale:  "+$.fn.imageviewer.options.imgScale+"<br/>"+"mouseBoxPosTop: "+mouseBoxPosTop+"<br/>"+"mouseBoxPosLeft: "+mouseBoxPosLeft+"<br/>"+"mouseBoxHeight: "+mouseBoxHeight+"<br/>"+"mouseBoxWidth: "+mouseBoxWidth+"<br/>"+"viewportObj.width: "+$.fn.imageviewer.options.viewportObj.width+"<br/>"+"viewportObj.height: "+$.fn.imageviewer.options.viewportObj.height+"<br/>"+"viewportPosTop: "+viewportPosTop+"<br/>"+"viewporttPosLeft: "+viewporttPosLeft+"<br/>"+"currentImageWidth: "+currentImageWidth+"<br/>"+"currentImageHeight: "+currentImageHeight+"<br/>"+"imageLayerPosTop: "+imageLayerPosTop+"<br/>"+"imageLayertPosLeft: "+imageLayertPosLeft+"<br/>"+"oldImgScaleAdjustedMousePosOnImageLayerTop: "+oldImgScaleAdjustedMousePosOnImageLayerTop+"<br/>"+"oldImgScaleAdjustedMousePosOnImageLayerLeft: "+oldImgScaleAdjustedMousePosOnImageLayerLeft+"<br/>"+"currentScaleMultiplier: "+currentScaleMultiplier+"<br/>"+"startPosTop: "+$.fn.imageviewer.options.startPosTop+"<br/>"+"startPosLeft: "+$.fn.imageviewer.options.startPosLeft}
$.fn.imageviewer.loadThumbnail=function()
{var thisXScale=parseInt(($.fn.imageviewer.options.thumbnailBoxMaxSize/$.fn.imageviewer.options.originalImageObj.width)*100,10);var thisYScale=parseInt(($.fn.imageviewer.options.thumbnailBoxMaxSize/$.fn.imageviewer.options.originalImageObj.height)*100,10);var tempImgScale=0;if(thisXScale<thisYScale)
{if(thisXScale<=0)
{thisXScale=1;}
$.fn.imageviewer.options.thumbnailScale=thisXScale;}else{if(thisYScale<=0)
{thisYScale=1;}
$.fn.imageviewer.options.thumbnailScale=thisYScale;}
if($.fn.imageviewer.options.rotation==90||$.fn.imageviewer.options.rotation==270)
{$.fn.imageviewer.options.thumbnailBox.width=Math.round(($.fn.imageviewer.options.thumbnailScale/100)*$.fn.imageviewer.options.originalImageObj.height);$.fn.imageviewer.options.thumbnailBox.height=Math.round(($.fn.imageviewer.options.thumbnailScale/100)*$.fn.imageviewer.options.originalImageObj.width);}else{$.fn.imageviewer.options.thumbnailBox.height=Math.round(($.fn.imageviewer.options.thumbnailScale/100)*$.fn.imageviewer.options.originalImageObj.height);$.fn.imageviewer.options.thumbnailBox.width=Math.round(($.fn.imageviewer.options.thumbnailScale/100)*$.fn.imageviewer.options.originalImageObj.width);}
if($("#thumbnailNav").length!=0)
{$("#thumbnailNav").remove();$('#thumbnailNavToggle').remove();}
var $thumbnailNavDiv=$('<div/>');$thumbnailNavDiv.attr("id","thumbnailNav");$("#imageDiv").prepend($thumbnailNavDiv);$('#thumbnailNav').css("position","absolute");$('#thumbnailNav').css("z-index","9998")
$('#thumbnailNav').css("overflow","hidden");$('#thumbnailNav').css("left",$('#imageDiv').css("left"));$('#thumbnailNav').css("top",$('#imageDiv').css("top"));$('#thumbnailNav').css("margin-left",$.fn.imageviewer.options.imageviewerbordersize)
$('#thumbnailNav').css("margin-top",$.fn.imageviewer.options.imageviewerbordersize)
$('#thumbnailNav').css("background",$.fn.imageviewer.options.thumbnailBox.bgcolor);$('#thumbnailNav').css("height",$.fn.imageviewer.options.thumbnailBox.height);$('#thumbnailNav').css("width",$.fn.imageviewer.options.thumbnailBox.width);$('#thumbnailNav').css("border","solid black thin");$('#thumbnailNav').css("display","none");loadThumbnailNavImage($.fn.imageviewer.options.thumbnailScale);bindClickToPan();$("#thumbnailNav").mousemove(function(e){});setThumbnailDragDiv();var $thumbnailNavToggleHandle=$('<img>');$thumbnailNavToggleHandle.attr("id","thumbnailNavToggle");$("#imageDiv").prepend($thumbnailNavToggleHandle);$('#thumbnailNavToggle').css("position","absolute");if($.fn.imageviewer.options.thumbnailOpenOnLoad)
{$('#thumbnailNavToggle').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/thum_control_expanded.gif");}else{$('#thumbnailNavToggle').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/thum_control_collapsed.gif");}
$('#thumbnailNavToggle').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/thum_control_collapsed.gif");$('#thumbnailNavToggle').css("z-index","9999")
$('#thumbnailNavToggle').css("overflow","hidden");$('#thumbnailNavToggle').css("left",$('#imageDiv').css("left"));$('#thumbnailNavToggle').css("top",$('#imageDiv').css("top"));$('#thumbnailNavToggle').css("cursor","pointer");setThumbnailDragBoxDiminsions();setThumbnailDragBoxPosition();$('#thumbnailNavToggle').click(function(){if($('#thumbnailNav').css("display")=="none")
{thumbnailExpand();}else{thumbnailContract();}});setThumbnailDrag();if($.fn.imageviewer.options.thumbnailOpenOnLoad)
{thumbnailExpand();}
movethumbnailDragDiv();}
loadThumbnailNavImage=function(thisScale)
{var imgUrl="";imgUrl+=$.fn.imageviewer.options.server_api_url;imgUrl+="?CISOROOT="+$.fn.imageviewer.options.collection;imgUrl+="&CISOPTR="+$.fn.imageviewer.options.itemId;imgUrl+="&action=2";imgUrl+="&DMSCALE="+thisScale;imgUrl+="&DMWIDTH="+Math.round(($.fn.imageviewer.options.thumbnailScale/100)*$.fn.imageviewer.options.originalImageObj.width);imgUrl+="&DMHEIGHT="+Math.round(($.fn.imageviewer.options.thumbnailScale/100)*$.fn.imageviewer.options.originalImageObj.height);imgUrl+="&DMX="+0;imgUrl+="&DMY="+0;imgUrl+="&DMTEXT="+$.fn.imageviewer.options.fullTextSearchTerm.replace(' ','%20').replace('+','%20');imgUrl+="&DMROTATE="+$.fn.imageviewer.options.rotation;if($.fn.imageviewer.options.dmid!=""){imgUrl+="&"+$.fn.imageviewer.options.dmid;}
var $imagetag=$('<img>');$imagetag.attr("id","thmbnl");$imagetag.attr("src",imgUrl);$imagetag.attr("alt","Thumbnail navigator for current image.  Drag around to view image in more detail.");$("#thumbnailNav").append($imagetag);$("#thmbnl").css("position","absolute");$("#thmbnl").css("overflow","hidden");if($.fn.imageviewer.options.imgDivBgUrl!=""){$("#thmbnl").css("background-image","url('"+$.fn.imageviewer.options.imgDivBgUrl+"')");}}
setThumbnailDragBoxPosition=function()
{$('#thumbnailDragLayer').css("top",0);$('#thumbnailDragLayer').css("left",0);}
setThumbnailDragBoxDiminsions=function()
{$.fn.imageviewer.options.thumbnailDispMultiplierX=$.fn.imageviewer.options.thumbnailBox.width/parseInt($.fn.imageviewer.options.originalImageObj.width*($.fn.imageviewer.options.imgScale*.01),10);$.fn.imageviewer.options.thumbnailDispMultiplierY=$.fn.imageviewer.options.thumbnailBox.height/parseInt($.fn.imageviewer.options.originalImageObj.height*($.fn.imageviewer.options.imgScale*.01),10);$.fn.imageviewer.options.thumbnailDragBoxHeight=$.fn.imageviewer.options.thumbnailDispMultiplierY*parseInt($(SELECTOR_VIEWPORT).height());$.fn.imageviewer.options.thumbnailDragBoxWidth=$.fn.imageviewer.options.thumbnailDispMultiplierX*parseInt($(SELECTOR_VIEWPORT).width());$('#thumbnailDragLayer').css("width",$.fn.imageviewer.options.thumbnailDragBoxWidth);$('#thumbnailDragLayer').css("height",$.fn.imageviewer.options.thumbnailDragBoxHeight);}
thumbnailExpand=function()
{$('#thumbnailNavToggle').css("display","none");$('#thumbnailNav').animate({"height":"toggle","width":"toggle"},300,"linear",function(){if($.fn.imageviewer.options.rotation==90||$.fn.imageviewer.options.rotation==270)
{$('#thumbnailNavToggle').css("margin-left",$.fn.imageviewer.options.imageviewerbordersize+$.fn.imageviewer.options.thumbnailBox.width-15);$('#thumbnailNavToggle').css("margin-top",$.fn.imageviewer.options.imageviewerbordersize+$.fn.imageviewer.options.thumbnailBox.height-15);}else{$('#thumbnailNavToggle').css("margin-left",$.fn.imageviewer.options.imageviewerbordersize+$.fn.imageviewer.options.thumbnailBox.width-15);$('#thumbnailNavToggle').css("margin-top",$.fn.imageviewer.options.imageviewerbordersize+$.fn.imageviewer.options.thumbnailBox.height-15);}
$('#thumbnailNavToggle').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/thum_control_expanded.gif");$('#thumbnailNavToggle').css("display","inline");});$.fn.imageviewer.options.thumbnailOpenOnLoad=true;}
thumbnailContract=function()
{$('#thumbnailNavToggle').css("display","none");$('#thumbnailNav').animate({"height":"toggle","width":"toggle"},300,"linear",function(){$('#thumbnailNavToggle').css("margin-left",$.fn.imageviewer.options.imageviewerbordersize)
$('#thumbnailNavToggle').css("margin-top",$.fn.imageviewer.options.imageviewerbordersize)
$('#thumbnailNavToggle').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/thum_control_collapsed.gif");$('#thumbnailNavToggle').css("display","inline");});$.fn.imageviewer.options.thumbnailOpenOnLoad=false;}
setThumbnailDragDiv=function()
{var $thumbnailDragLayerDiv=$('<div/>');$thumbnailDragLayerDiv.attr("id","thumbnailDragLayer");$("#thumbnailNav").append($thumbnailDragLayerDiv);$('#thumbnailDragLayer').css("position","relative");$('#thumbnailDragLayer').css("cursor","default");$('#thumbnailDragLayer').css("background",$.fn.imageviewer.options.thumbnailBox.overlayColor);$('#thumbnailDragLayer').css("opacity","0.4");$('#thumbnailDragLayer').css("border","solid navy 1px");}
setThumbnailDrag=function()
{var dragOpt={drag:function(event,ui){moveImageLayer();}};$('#thumbnailDragLayer').draggable("destroy");$('#thumbnailDragLayer').draggable(dragOpt);$('#thumbnailDragLayer').css("cursor","move");}
bindClickToPan=function()
{$("#thmbnl").bind("click",function(e)
{var thisX=0;var thisY=0;if(!e)var e=window.event;if(e.pageX||e.pageY){thisX=e.pageX;thisY=e.pageY;}
else if(e.clientX||e.clientY){thisX=e.clientX+document.body.scrollLeft+document.documentElement.scrollLeft;thisY=e.clientY+document.body.scrollTop+document.documentElement.scrollTop;}
var dragLayerTop=(thisY-$("#thumbnailNav").offset().top)-(parseInt($("#thumbnailDragLayer").height())/2);var dragLayerLeft=(thisX-$("#thumbnailNav").offset().left)-(parseInt($("#thumbnailDragLayer").width())/2);var thisImageLayerLeft=parseInt(-1*((parseInt($('#imageLayer').width())/parseInt($('#thumbnailNav').width()))*dragLayerLeft));var thisImageLayerTop=parseInt(-1*(($('#imageLayer').height()/$('#thumbnailNav').height())*dragLayerTop));$('#imageLayer').animate({top:thisImageLayerTop,left:thisImageLayerLeft},"normal","swing",function(){dragStop();});$('#thumbnailDragLayer').animate({top:dragLayerTop,left:dragLayerLeft},"normal","swing");});}
getImgScale=function(increment)
{if($.fn.imageviewer.options.scaleIndex+increment<=0)
{$.fn.imageviewer.options.scaleIndex=0;return $.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];}
if($.fn.imageviewer.options.scaleIndex+increment>$.fn.imageviewer.options.scaleArray.length-1)
{$.fn.imageviewer.options.scaleIndex=$.fn.imageviewer.options.scaleArray.length-1;return $.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];}
else
{$.fn.imageviewer.options.scaleIndex=$.fn.imageviewer.options.scaleIndex+increment;return $.fn.imageviewer.options.scaleArray[$.fn.imageviewer.options.scaleIndex];}}
getScaleIndex=function(thisScaleIn)
{var scaleIndexOut=0;for(var i=0;i<$.fn.imageviewer.options.scaleArray.length;i++){if($.fn.imageviewer.options.scaleArray[i]=thisScaleIn){scaleIndexOut=i;}}
return scaleIndexOut;}
debugInfo=function()
{var strOutput="";strOutput+="originalImageObj.width: "+$.fn.imageviewer.options.originalImageObj.width+"<br/>";strOutput+="originalImageObj.height: "+$.fn.imageviewer.options.originalImageObj.height+"<br/><br/>";strOutput+="currentImageTop: "+$('#imageLayer').css("top")+"<br/>";strOutput+="currentImageLeft: "+$('#imageLayer').css("left")+"<br/><br/>";strOutput+="viewportObj.width: "+$.fn.imageviewer.options.viewportObj.width+"<br/>";strOutput+="viewportObj.height: "+$.fn.imageviewer.options.viewportObj.height+"<br/>";strOutput+="viewportObj.left: "+$.fn.imageviewer.options.viewportObj.left+"<br/>";strOutput+="viewportObj.top: "+$.fn.imageviewer.options.viewportObj.top+"<br/><br/>";strOutput+="currentImageWidth: "+$('#imageLayer').css("width")+"<br/>";strOutput+="currentImageHeight: "+$('#imageLayer').css("height")+"<br/><br/>";strOutput+="startPosTop: "+$.fn.imageviewer.options.startPosTop+"<br/>";strOutput+="startPosLeft: "+$.fn.imageviewer.options.startPosLeft+"<br/><br/><br/>";return strOutput}
setDragDiv=function()
{$('#dragLayer').remove();var $dragLayerDiv=$('<div/>');$dragLayerDiv.attr("id","dragLayer");$(SELECTOR_VIEWPORT).append($dragLayerDiv);$('#dragLayer').css("position","absolute");$('#dragLayer').attr("src",$.fn.imageviewer.options.loadImageUrlDir+"/ajax-loader.gif");$('#dragLayer').css("top",($(SELECTOR_VIEWPORT).top));$('#dragLayer').css("left",($(SELECTOR_VIEWPORT).left));$('#dragLayer').css("width",($(SELECTOR_VIEWPORT).width()));$('#dragLayer').css("height",($(SELECTOR_VIEWPORT).width()));$('#dragLayer').css("cursor","default");}
imageLayerInitPosition=function()
{var thisVPH=$(SELECTOR_VIEWPORT).height();var thisVPW=$(SELECTOR_VIEWPORT).width();var thisILH=$('#imageLayer').height();var thisILW=$('#imageLayer').width();if(!$.fn.imageviewer.options.setToTop)
{$.fn.imageviewer.options.startPosTop=(thisVPH/2)-$('#imageLayer').height()/2;}
$.fn.imageviewer.options.startPosLeft=(thisVPW/2)-$('#imageLayer').width()/2;}
imageRotateLeft=function()
{$.fn.imageviewer.options.rotation=$.fn.imageviewer.options.rotation-90;if($.fn.imageviewer.options.rotation<0)
{$.fn.imageviewer.options.rotation=270;}
$.fn.imageviewer.countComplete();}
imageRotateRight=function()
{$.fn.imageviewer.options.rotation=$.fn.imageviewer.options.rotation+90;if($.fn.imageviewer.options.rotation>270)
{$.fn.imageviewer.options.rotation=0;}
$.fn.imageviewer.countComplete();}
initTiles=function()
{$.fn.imageviewer.options.arrImageDivs=new Array();$.fn.imageviewer.options.arrImageImgs=new Array();var thisImgHeight=0
var thisImgWidth=0
var thisTileHeight=0
var thisTileWidth=0
$.fn.imageviewer.options.oldImgScale=$.fn.imageviewer.options.imgScale;thisImgHeight=parseInt($.fn.imageviewer.options.originalImageObj.height*($.fn.imageviewer.options.imgScale*.01),10);thisImgWidth=parseInt($.fn.imageviewer.options.originalImageObj.width*($.fn.imageviewer.options.imgScale*.01),10);if(thisImgHeight%$.fn.imageviewer.options.tileSize==0)
{$.fn.imageviewer.options.rows=thisImgHeight/$.fn.imageviewer.options.tileSize;}else{$.fn.imageviewer.options.rows=parseInt(thisImgHeight/$.fn.imageviewer.options.tileSize)+1;}
if(thisImgWidth%$.fn.imageviewer.options.tileSize==0)
{$.fn.imageviewer.options.cols=thisImgWidth/$.fn.imageviewer.options.tileSize;}else{$.fn.imageviewer.options.cols=parseInt(thisImgWidth/$.fn.imageviewer.options.tileSize)+1;}
$.fn.imageviewer.options.imgHeightModulo=thisImgHeight%$.fn.imageviewer.options.tileSize;$.fn.imageviewer.options.imgWidthModulo=thisImgWidth%$.fn.imageviewer.options.tileSize;for(var i=0;i<$.fn.imageviewer.options.rows;i++)
{for(var j=0;j<$.fn.imageviewer.options.cols;j++)
{$.fn.imageviewer.options.arrImageImgs[i]=new Array($.fn.imageviewer.options.cols);}}
thisY=0;for(var r=0;r<$.fn.imageviewer.options.rows;r++)
{thisX=0;for(var c=0;c<$.fn.imageviewer.options.cols;c++)
{if(c==$.fn.imageviewer.options.cols-1&&$.fn.imageviewer.options.imgWidthModulo!=0)
{thisTileWidth=$.fn.imageviewer.options.imgWidthModulo;}else{thisTileWidth=$.fn.imageviewer.options.tileSize;}
if(r==$.fn.imageviewer.options.rows-1&&$.fn.imageviewer.options.imgHeightModulo!=0)
{thisTileHeight=$.fn.imageviewer.options.imgHeightModulo;}else{thisTileHeight=$.fn.imageviewer.options.tileSize;}
$.fn.imageviewer.options.arrImageImgs[r][c]='tileImage_'+$.fn.imageviewer.options.imgScale+'_'+thisX+'_'+thisY+'_'+thisTileWidth+'_'+thisTileHeight;thisX=thisX+$.fn.imageviewer.options.tileSize;}
thisY=thisY+$.fn.imageviewer.options.tileSize;}
var output=""
for(var i=0;i<$.fn.imageviewer.options.rows;i++)
{for(var j=0;j<$.fn.imageviewer.options.cols;j++)
{output+=$.fn.imageviewer.options.arrImageImgs[i][j];if(j!=$.fn.imageviewer.options.cols-1)
{output+="::";}}
output+="\n";}
if($.fn.imageviewer.options.rotation==90||$.fn.imageviewer.options.rotation==270)
{$('#imageLayer').css("width",thisImgHeight);$('#imageLayer').css("height",thisImgWidth);}else{$('#imageLayer').css("width",thisImgWidth);$('#imageLayer').css("height",thisImgHeight);}
$('#imageLayer').html("");keepImageLayerInView();if($.fn.imageviewer.options.initLoad)
{imageLayerInitPosition();}
setImagePos();switch($.fn.imageviewer.options.rotation)
{case(0):for(var r=0;r<$.fn.imageviewer.options.rows;r++)
{for(var c=0;c<$.fn.imageviewer.options.cols;c++)
{var thisImgArray=$.fn.imageviewer.options.arrImageImgs[r][c].split("_");var thisDivId='tileDiv_'+thisImgArray[1]+"_"+thisImgArray[2]+"_"+thisImgArray[3]+"_"+thisImgArray[4]+"_"+thisImgArray[5];addImageToDiv($('#imageLayer'),$.fn.imageviewer.options.arrImageImgs[r][c],thisDivId);}}
break;case(270):var thisX=0;for(var r=0;r<$.fn.imageviewer.options.rows;r++)
{var thisY=thisImgWidth;for(var c=0;c<$.fn.imageviewer.options.cols;c++)
{var thisImgArray=$.fn.imageviewer.options.arrImageImgs[r][c].split("_");thisY=thisY+(-1*thisImgArray[4]);var thisDivId='tileDiv_'+thisImgArray[0]+"_"+thisX+"_"+thisY+"_"+thisImgArray[5]+"_"+thisImgArray[4];addImageToDiv($('#imageLayer'),$.fn.imageviewer.options.arrImageImgs[r][c],thisDivId);}
thisX=thisX+(1*$.fn.imageviewer.options.tileSize);}
break;case(180):var thisY=thisImgHeight;for(var r=0;r<$.fn.imageviewer.options.rows;r++)
{var thisImgArrayX=$.fn.imageviewer.options.arrImageImgs[r][0].split("_");thisY=thisY+(-1*thisImgArrayX[5]);var thisX=thisImgWidth;for(var c=0;c<$.fn.imageviewer.options.cols;c++)
{var thisImgArray=$.fn.imageviewer.options.arrImageImgs[r][c].split("_");thisX=thisX+(-1*thisImgArray[4]);var thisDivId='tileDiv_'+thisImgArray[0]+"_"+thisX+"_"+thisY+"_"+thisImgArray[4]+"_"+thisImgArray[5];addImageToDiv($('#imageLayer'),$.fn.imageviewer.options.arrImageImgs[r][c],thisDivId);}}
break;case(90):var thisX=thisImgHeight;for(var r=0;r<$.fn.imageviewer.options.rows;r++)
{var thisImgArrayX=$.fn.imageviewer.options.arrImageImgs[r][0].split("_");thisX=thisX+(-1*thisImgArrayX[5]);var thisY=0;for(var c=0;c<$.fn.imageviewer.options.cols;c++)
{var thisImgArray=$.fn.imageviewer.options.arrImageImgs[r][c].split("_");var thisDivId='tileDiv_'+thisImgArray[0]+"_"+thisX+"_"+thisY+"_"+thisImgArray[5]+"_"+thisImgArray[4];addImageToDiv($('#imageLayer'),$.fn.imageviewer.options.arrImageImgs[r][c],thisDivId);thisY=thisY+(1*$.fn.imageviewer.options.tileSize);}}
break;}}
setImagePos=function()
{if($.fn.imageviewer.options.setToTop)
{$.fn.imageviewer.options.startPosTop=0;$.fn.imageviewer.options.setToTop=false;}
$('#imageLayer').css("top",$.fn.imageviewer.options.startPosTop);$('#imageLayer').css("left",$.fn.imageviewer.options.startPosLeft);}
keepImageLayerInView=function()
{if($('#imageLayer').height()<$.fn.imageviewer.options.viewportObj.height)
{if($('#imageLayer').offset().top<=$.fn.imageviewer.options.viewportObj.top)
{$('#imageLayer').css("top",0);}}
if($('#imageLayer').width()<=$.fn.imageviewer.options.viewportObj.width)
{if($('#imageLayer').offset().left<$.fn.imageviewer.options.viewportObj.left)
{$('#imageLayer').css("left",0);}}}
addImageToDiv=function(thisDiv,imgId,divId)
{var thisImgArray=imgId.split("_");var thisDivArray=divId.split("_");var $imageDiv=$('<div/>');$imageDiv.attr("id",divId);thisDiv.append($imageDiv);var $imagetag=$('<img>');var thisImgId=imgId;$imagetag.attr("id",thisImgId);$imagetag.attr("src",$.fn.imageviewer.options.loadImageUrl);$imageDiv.append($imagetag);$imageDiv.css("position","absolute");$imageDiv.css("overflow","hidden");$imageDiv.css("left",thisDivArray[2]+"px");$imageDiv.css("top",thisDivArray[3]+"px");$imageDiv.css("width",thisDivArray[4]+"px");$imageDiv.css("height",thisDivArray[5]+"px");if($.fn.imageviewer.options.imgDivBgUrl!=""){var bgimageurl="url('"+$.fn.imageviewer.options.imgDivBgUrl+"')";$imageDiv.css("background-image",bgimageurl);}}
setDrag=function()
{$.fn.imageviewer.options.adjustedH=$.fn.imageviewer.options.rows*$.fn.imageviewer.options.tileSize;$.fn.imageviewer.options.adjustedW=$.fn.imageviewer.options.cols*$.fn.imageviewer.options.tileSize;if($('#imageLayerCover').length>0)
{$('#imageLayerCover').remove();}
var thisHeightLimit=(($.fn.imageviewer.options.adjustedH-$.fn.imageviewer.options.viewportObj.height-$.fn.imageviewer.options.viewportObj.top)*-1);var thisWidthLimit=(($.fn.imageviewer.options.adjustedW-$.fn.imageviewer.options.viewportObj.width-$.fn.imageviewer.options.viewportObj.left)*-1);var dragOpt="";if($.fn.imageviewer.options.adjustedH<=$.fn.imageviewer.options.viewportObj.height||$.fn.imageviewer.options.adjustedW<=$.fn.imageviewer.options.viewportObj.width)
{if($.fn.imageviewer.options.adjustedH<=$.fn.imageviewer.options.viewportObj.height&&$.fn.imageviewer.options.adjustedW<=$.fn.imageviewer.options.viewportObj.width)
{$('#imageLayer').draggable("destroy");$('#imageLayer').css("cursor","default");return;}
if($.fn.imageviewer.options.adjustedH<=$.fn.imageviewer.options.viewportObj.height)
{dragOpt={stop:function(ev,ui){dragStop();},drag:function(event,ui){dragMain();}};}
if($.fn.imageviewer.options.adjustedW<=$.fn.imageviewer.options.viewportObj.width)
{dragOpt={stop:function(ev,ui){dragStop();},drag:function(event,ui){dragMain();}};}}else{dragOpt={stop:function(ev,ui){dragStop();},drag:function(event,ui){dragMain();}};}
$('#imageLayer').draggable("destroy");$('#imageLayer').draggable(dragOpt);$("img[id^=tileImage_]").each(function(){imgPosCheck(this)});$('#imageLayer').css("cursor","move");}
dragStop=function()
{if($('#imageLayer').exists()){$.fn.imageviewer.options.imageLayerObj.top=$('#imageLayer').offset().top;$.fn.imageviewer.options.imageLayerObj.left=$('#imageLayer').offset().left;}
fireImgPosCheck();}
dragMain=function()
{movethumbnailDragDiv();}
moveImageLayer=function()
{var dragLayerLeft=parseInt($("#thumbnailDragLayer").offset().left-$("#thumbnailNav").offset().left);var dragLayerTop=parseInt($("#thumbnailDragLayer").offset().top-$("#thumbnailNav").offset().top);var thisImageLayerLeft=parseInt(-1*((parseInt($("#imageLayer").width())/parseInt($("#thumbnailNav").width()))*dragLayerLeft));var thisImageLayerTop=parseInt(-1*((parseInt($("#imageLayer").height())/parseInt($("#thumbnailNav").height()))*dragLayerTop));$('#imageLayer').css("left",thisImageLayerLeft)
$('#imageLayer').css("top",thisImageLayerTop);dragStop();}
movethumbnailDragDiv=function()
{var thisImgH=parseInt($.fn.imageviewer.options.originalImageObj.height*($.fn.imageviewer.options.imgScale*.01),10);var thisImgW=parseInt($.fn.imageviewer.options.originalImageObj.width*($.fn.imageviewer.options.imgScale*.01),10);var thumbnailRatioWidth=$.fn.imageviewer.options.thumbnailBox.width/thisImgW;var thumnailRatioHeight=$.fn.imageviewer.options.thumbnailBox.height/thisImgH;var dragLayerLeft=parseInt(-1*(parseInt($('#imageLayer').css("left"))*thumbnailRatioWidth));var dragLayerTop=parseInt(-1*(parseInt($('#imageLayer').css("top"))*thumnailRatioHeight));$("#thumbnailDragLayer").css("left",dragLayerLeft+"px");$("#thumbnailDragLayer").css("top",dragLayerTop+"px");}
fireImgPosCheck=function()
{$("img[id^=tileImage_]").each(function(){imgPosCheck(this)});}
imgPosCheck=function(el)
{var thisEl=el;var thisID=el.id;var thisParent=$("#"+el.id).parent();var thisSrc="";thisSrc+=el.src+"";if(thisSrc.endsWith($.fn.imageviewer.options.loadImageFile)==true)
{var idArray=el.id.split("_");var viewportRight=$.fn.imageviewer.options.viewportObj.left+$.fn.imageviewer.options.viewportObj.width;var viewportBottom=$.fn.imageviewer.options.viewportObj.top+$.fn.imageviewer.options.viewportObj.height;var thisElementTop=parseInt(parseInt(thisParent.css("top")))+parseInt($.fn.imageviewer.options.imageLayerObj.top);var thisElementLeft=parseInt(parseInt(thisParent.css("left")))+parseInt($.fn.imageviewer.options.imageLayerObj.left);var thisElementBottom=parseInt(parseInt(thisParent.css("top")))+parseInt($.fn.imageviewer.options.imageLayerObj.top)+parseInt(thisParent.height());var thisElementRight=parseInt(parseInt(thisParent.css("left")))+parseInt($.fn.imageviewer.options.imageLayerObj.left)+parseInt(thisParent.width());if(((thisElementTop>$.fn.imageviewer.options.viewportObj.top-$.fn.imageviewer.options.tileSize)&&(thisElementTop<viewportBottom))&&((thisElementLeft>$.fn.imageviewer.options.viewportObj.left-$.fn.imageviewer.options.tileSize)&&(thisElementLeft<viewportRight)))
{var thisX=parseInt(idArray[2]);var thisY=parseInt(idArray[3]);var thisWidth=parseInt(idArray[4])+$.fn.imageviewer.options.imageTileOverlap;var thisHeight=parseInt(idArray[5])+$.fn.imageviewer.options.imageTileOverlap;var imgUrl="";imgUrl+=$.fn.imageviewer.options.server_api_url;imgUrl+="?CISOROOT="+$.fn.imageviewer.options.collection;imgUrl+="&CISOPTR="+$.fn.imageviewer.options.itemId;imgUrl+="&action=2";imgUrl+="&DMSCALE="+idArray[1];imgUrl+="&DMWIDTH="+thisWidth;imgUrl+="&DMHEIGHT="+thisHeight;imgUrl+="&DMX="+thisX;imgUrl+="&DMY="+thisY;imgUrl+="&DMTEXT="+$.fn.imageviewer.options.fullTextSearchTerm.replace(' ','%20').replace('+','%20');imgUrl+="&DMROTATE="+$.fn.imageviewer.options.rotation;if($.fn.imageviewer.options.dmid!=""){imgUrl+="&"+$.fn.imageviewer.options.dmid;}
thisParent.html("");var $imagetag=$('<img>');var thisImgId=thisID;$imagetag.attr("id",thisImgId);$imagetag.attr("src",imgUrl);thisParent.append($imagetag);}}}})(jQuery);