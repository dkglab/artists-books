/* NOTE: Commented out all remove/add/toggle Class('selected'),
as per new browse filter bar designs 10th March 2010 */

// Set variables
var strFilterToggle = "expanded";
var strFlipToggle = "flipped";

// Fixed browseFilterHeight also needs to be set in browse_filter.tpl
var browseFilterHeight = 330;
if (typeof germex != 'undefined') {
	browseFilterHeight = 330;
}
if (typeof lb != 'undefined') {
	browseFilterHeight = 700;
}
var artTermsListHeight = 490;
var minContentHeight = 580;
var finalSelectedArtists = new Array();
var lteIE7 = false /*@cc_on || @_jscript_version <= 5.7 @*/;
var searchFieldValue = "Search by Artist, Work, or Keyword";
var browser=navigator.appName;

var rightColContainerHeight = 490;
var leftColContainerHeight = 490;

// Class that handles the browse filter form functionality
MoMA.FiltersExtended = new Class({

	initialize: function(el) {    
	
	    // PERFORM ON INITIALISE CLASS

		// Hide these elements		
		// Note needed as adding hideContent to input[type=checkbox] is done in header.tpl.
		// Reinstate if using this code elsewhere
	    // el.getElements('form.browseFilter input[type=checkbox]').addClass('hideContent');
		
	    // Grab content
	    this.el = el;
	   // this.artistList = el.getElement('ul.artistList');
    	this.tableHeaders = el.getElements('form.browseFilter table tr th');
    	if (typeof germex != 'undefined' || typeof lb != 'undefined'){
    		this.tableHeaders = el.getElements('form.browseFilter table tr th.headerBox');
    	}
    	this.tableLabels = el.getElements('form.browseFilter label');
    	//this.artTermsLink = el.getElement('ul.artTermsLink');
	    //this.artTermsList = el.getElement('ul.artTermsList');
	    //this.closeArtTerms = el.getElement('a#closeArtTerms');
	    
		this.coverFilterContent = el.getElements('div#coverFilterOptions');
		//this.tableOfContent = el.getElements('ul.alphabetList li');
		//this.tableLinks = this.tableOfContent.getElements('a');
		this.formSubmit = el.getElement('input#filterSubmit')
		//this.artTermsBar = el.getElement('a#byArtTermSelected');
		this.browseFilter = el.getElement('.extendedFilter');
		this.filterOptions = el.getElement('div#filterOptions');

	/*	var previousSelectedArtists = el.getElement('input#previousSelectedArtists').get('value');

		if (previousSelectedArtists == "") {
			finalSelectedArtists = new Array();
		} else {
			finalSelectedArtists = previousSelectedArtists.split(',')
		}*/

	
		this.coverFilterContent.setStyle('height', browseFilterHeight);    	
    
	
	

		/* Clicking any of the filter options will toggle the 'selected' class,
		in sync with the checkbox state
	    this.tableLabels.each(function(item) {
		    item.addEvent('click', function(){
		    	this.toggleClass('selected');
		    });
	    }.bind(this)); */

		// Clicking on any table header label will deactivate it's related table cell labels, and vice versa
		this.tableHeaders.each(function(tableHeader){
			var headerID = tableHeader.id;
			if (el.getElements('form.browseFilter table tr td.' + headerID + ' label') != "") {
				var cellLabels = el.getElements('form.browseFilter table tr td.' + headerID + ' label');

				if (tableHeader.getElement('label') != "") {
					// on click of table header label, unhighlight all of that sections input fields
					tableHeader.getElement('label').addEvent('click', function() {
						//cellLabels.removeClass('selected');
						el.getElements('form.browseFilter table tr td.' + headerID + ' input[type=checkbox]').setProperty('checked',false);

	
					}.bind(this));
					
					tableHeader.getElement('input[type=checkbox]').addEvent('click', function() {
						//cellLabels.removeClass('selected');
						el.getElements('form.browseFilter table tr td.' + headerID + ' input[type=checkbox]').setProperty('checked',false);

	
					}.bind(this));
					
					// on click of that sections input fields, unhighlight table header label
					cellLabels.addEvent('click', function() {
						//tableHeader.getElement('label').removeClass('selected');
						tableHeader.getElement('input').setProperty('checked',false);
					});
					el.getElements('form.browseFilter table tr td.' + headerID + ' input[type=checkbox]').addEvent('click', function() {
						//tableHeader.getElement('label').removeClass('selected');
						tableHeader.getElement('input').setProperty('checked',false);
					});
				}
			}
			
			if (el.getElements('form.browseFilter table tr td.' + headerID + ' ul.artistList li') != "") {
				this.artistCells = el.getElements('form.browseFilter table tr td.' + headerID + ' ul.artistList li');
				//this.artistListBehaviour();
			}
			
		}.bind(this));

		// Loop through all labels and if their associated input checkboxes are ticked,
		// add a 'selected' class to the label
		this.tableLabels.each(function(item) {

			// Have to use an old JavaScript term for cross browser purposes
			var relatedInputField = item.htmlFor;
	    	var cellInput = el.getElement('#' + relatedInputField);
	    	
    		/* if our tick box is checked, then make our label class selected
			if (cellInput.getProperty('checked') == true) {
    			item.addClass('selected');
	    	} */
		}.bind(this));

	
    }
    
});

// This class will the handle the page turning animation popovers
MoMA.Bookbrowser = new Class({

	initialize: function(el) {
		
		this.el = el;

		if (el.getElement('div#coverContentFull'))
		    this.coverContentFull = el.getElement('div#coverContentFull');
		
		if (el.getElement('a#bookbrowserButton'))
			//get the button
			this.bookButton = el.getElement('a#bookbrowserButton');
			
		if (el.getElement('div#bookbrowser')) {
			this.bookbrowser = el.getElement('#bookbrowser');
			/*Create iframe and inject into bookbrowser div, the iframes src is the href of the bookbrowser button */
			frameSrc = this.bookButton.get('href');
			this.bookFrame = new Element('iframe');
			this.bookFrame.set( {'src':frameSrc, 'scrolling':'no', 'width':'1010', 'height':'650', 'frameborder':'0', 'id':'bookFrame'});

			this.closebook = new Element('a');
			this.closebook.set( { 'href':'#', 'html':'X','id':'closeBook' });
			this.closebook.inject(this.bookbrowser);
			this.bookFrame.inject(this.bookbrowser);
			
		}
		
		if (this.bookButton) {
			this.revealInteractive(this.bookButton,this.coverContentFull,this.bookbrowser, this.closebook);
		}
	},
	
	revealInteractive: function(activationButton,cover,book,close) {


			
			activationButton.addEvent('click', function(e) {
				e.stop();
				window.scrollTo(0,0);
				book.setStyle('display','block');
				// Need to set opacity before initial fade work
				cover.setStyle('opacity', 0);
				book.setStyle('opacity', 0);
				close.setStyle('opacity',0);
				cover.fade('in');
				book.fade('in');
				close.fade('in');
				//frame = book.getElement('iframe#bookFrame');
				//frame.contentDocument.location.reload(true);
				
			}.bind(this));
			
			cover.addEvent("click", function(e) {
					
					cover.fade('out');
					book.fade('out');
					close.fade('out');
					e.stop();
					
				}.bind(this));
				
			close.addEvent("click", function(e) {
					
					cover.fade('out');
					book.fade('out');
					close.fade('out');
					e.stop();
					
				}.bind(this));
		
		
	}
	
});

// Class to handle object overlays - initially concieved for Louise Bourgeois
MoMA.OverlayObjectViewer = new Class({

	initialize: function(el) {
		
		this.el = el;
		this.overlay = null;
		this.workBox = null;
		
		this.setUpFurniture();
		//	handle for when we are nested too far down in a function
		__OverlayObjectViewer_handle = this;
		
		//	add trigger to event 
		this.el.getElements("a.lightbox_link").each(function(link, index) {

			link.addEvent('click', function(e) {
				
				
				//alert("stop!");
				//	stop default action
				new Event(e).stop();
				
				//	find the corresponding object in the json packet
				lightboxWorks = JSON.decode(lightboxWorksJSON);
				currentWork = lightboxWorks.lightbox_works[index];
				__OverlayObjectViewer_handle.showWork(currentWork);
				
			}.bind(this));
			
		});
		
	},
	
	setUpFurniture: function() {
		
		//	create overlay element
		this.overlay = new Element("div", {
			id: "workOverlay"
		});
		
		this.overlay.addEvent("click", function(e) {
			//	hide work on click
			__OverlayObjectViewer_handle.hideWork();
		});
		
		this.overlay.setStyle("opacity", 0); //	This overcomes a bug where the first execution will not fade and just appear
		
		//	inject into body
		this.overlay.inject(this.el, 'top');

		//	set the initial html content of the work-box - this will get populated depending on the work clicked
		var defaultHtml = "<p id='work-overlay-external-label' class='external-label'></p>";
		defaultHtml += "<img id='work-overlay-image' src='' alt='' />";
		defaultHtml += "<p id='work-overlay-title'></p>";
		defaultHtml += "<p id='work-overlay-date'></p><hr/>";
		defaultHtml += "<p id='work-overlay-medium' class='has-label'>Medium: <span></span></p>";
		defaultHtml += "<p id='work-overlay-dimensions' class='has-label'>Dimensions: <span></span></p>";
		defaultHtml += "<p id='work-overlay-credit' class='has-label'>Credit Line: <span></span></p>";
		defaultHtml += "<p id='work-overlay-object-number' class='has-label'>Accession Number: <span></span></p>";
		defaultHtml += "<p id='work-overlay-rights'></p>";
		defaultHtml += "<p id='work-overlay-oc-link'></p>";
		
		//	create work-box element
		this.workBox = new Element("div", {
			html: defaultHtml,
			"id": "work-box"
		}).addEvent("click", function(e) {
			// hide work on click
			e.stopPropagation();
		});
		
		//	create close button
		var closeButton = new Element("a", {
			html: "<img src='images/lb/close-lightbox.png' alt='Close lightbox'/>",
			"id": "close-lightbox"
		}).addEvent('click', function(e) {
			__OverlayObjectViewer_handle.hideWork();
		});
		
		//	inject inside workbox
		closeButton.inject(this.workBox, 'top');
 
		//	inject work-box inside overlay
		this.workBox.inject(this.overlay, 'top');		
	},
	
	hideWork: function() {
		
		//	hide overlay and work-box
		this.overlay.fade("out");
	},
	
	showWork: function(theWork) {
		
		//	populate the work html with the json values
		$('work-overlay-image').setProperty('src', theWork.imageSrc);
		$('work-overlay-image').setProperty('alt', theWork.title);
		$('work-overlay-title').setProperty('html', theWork.title);
		$('work-overlay-date').setProperty('html', theWork.date);
		$('work-overlay-medium').getElements('span')[0].setProperty('html', theWork.medium);
		$('work-overlay-dimensions').getElements('span')[0].setProperty('html', theWork.dimensions);
		$('work-overlay-rights').setProperty('html', theWork.rights);
		
		//	is the work in the online collection proper - if so add link
		if (theWork.onlineCollectionLink != '') {
			$('work-overlay-oc-link').setProperty('html', "<a href='" + theWork.onlineCollectionLink + "' title='View " + theWork.title + " in the online collection'>View in MoMA's Online Collection</a>");
		}
		else {
			$('work-overlay-oc-link').setProperty('html', "");		
		}
		
		//	is the work external - if so inject text and hide optional fields
		if (theWork.externalFlag == 1) {
			$('work-overlay-external-label').setProperty('html', "NOT IN MoMA'S COLLECTION");
			$('work-overlay-credit').getElements('span')[0].setProperty('html', "")
			$('work-overlay-credit').setStyle("display", "none");
			$('work-overlay-object-number').getElements('span')[0].setProperty('html', "")
			$('work-overlay-object-number').setStyle("display", "none");
			this.workBox.addClass("external");
		}
		else {
			$('work-overlay-external-label').setProperty('html', "");
			this.workBox.removeClass("external");
			$('work-overlay-credit').getElements('span')[0].setProperty('html', theWork.creditLine)
			$('work-overlay-credit').setStyle("display", "block");
			$('work-overlay-object-number').getElements('span')[0].setProperty('html', theWork.objectNumber)
			$('work-overlay-object-number').setStyle("display", "block");
		}

        // If Louise Bourgeois.
        var is_lb = $('lb-primary-nav');
        if (is_lb) {
            // Set the margin of the workBox so that it is
            // positioned within the user's viewport.
            var margin_top = 50;
            var y_pos = window.getScroll().y;
            this.workBox.setStyle("margin-top", y_pos + margin_top);
        }
        
				
		//	show the overlay
		this.overlay.fade('in');
	}
	
});

// Class to handle the evolving composition compare view - initially concieved for Louise Bourgeois
MoMA.EvolvingCompositionCompare = new Class({
  
  initialize: function() {
    this.isOpen = false;
    this.left = null;
    this.right = null;
    this.diagramOpen = true;
    this.diagramHeight = null;
    this.containerHeight = null;
    this.sliderHeight = null;
    this.sliderTop = null;
    this.toggleLinkHtmlOpen = "Close evolving composition";
    this.toggleLinkHtmlClosed = "Open evolving composition";
    this.selectedLinks = {};
    this.setupContainer();
    this.setupTab();
    this.setupDropShadows();
    this.setupContent();
    this.setupTargetLinks();
    this.setUpDiagramToggleLink();
  },
  
  selectLeft: function(link) {
    this.select('left', link);
  },
  
  selectRight: function(link) {
    this.select('right', link);
  },
  
  select: function(side, link) {
    this[side]= link;
    var image = this.content.getElement('#ec_compare_' + side + ' .ec_image');
    var caption = this.content.getElement('#ec_compare_' + side + ' .caption');
    var label = this.content.getElement('#ec_compare_' + side + ' .label');
    if (link) {
      label.addClass('selected');
      var cell = link.getParent('.ec-cell');
      var targetImage = cell.getElement('img.over');
      var imageURL = targetImage.get('src').replace('w155h170', 'w500h420');
      image.setStyle('background', '#fff url(' + imageURL + ') no-repeat center center');
      image.set('html', '');

      // Set border color to match left side.
      if ('right' === side) {
          var borderStyle = $('ec_compare_left').getElement('.ec_image').getStyle('border-top');
          $('ec_compare_right').getElement('.ec_image').setStyle('border', borderStyle);
      }

      var targetCaption = cell.getElement('.ec-thumb-caption');
      caption.set('html', targetCaption.get('html'));
      
      this.togglePlaceHolderThumbs(link, side);
      
      if (!this.isOpen) {
        this.open();
      }
      
    } else {
      image.set('html', '<p id="ec-compare-image-placeholder">Select a work in the diagram below</p>');
      caption.set('html', '');
      label.removeClass('selected');
    }
  },
  
  togglePlaceHolderThumbs: function(link, side) {
  	
	//	Set the thumbnail image to A or B
	  var content = (side == "left") ? "A" : "B";
	  
	  //	If this has already been selected we need to reset the old thumb
	  if (this.selectedLinks[content]) {
		//	Remove placeholder element
		this.selectedLinks[content].getElement("span.place-holder-thumb").destroy();
		//	Show thumbnail img again
		this.selectedLinks[content].getElement("img").setStyle("display", "block");
		//	Remove parent selected class
		this.selectedLinks[content].getParent(".ec-cell").removeClass("selected");
	  }
		  
	  //	Add placeholder span with "A" or "B" in
	  var placeHolder = new Element("span", {
		"class": "place-holder-thumb",
		"html": content
	  });
	  placeHolder.inject(link);
	  //	Hide the thumbnail image
	  link.getElement("img").setStyle("display", "none");
	  //	Add a class to the parent cell to stop it's hover functionality
	  link.getParent(".ec-cell").addClass("selected");
	  //	Make this the new selected link
	  this.selectedLinks[content] = link;
  },
  
  toggle: function() {
    if (this.isOpen) {
      this.open();
    } else {
      this.close();
    }
  },
  
  open: function() {
    this.isOpen = true;
    if (!this.left) {
      this.selectLeft(null);
    }
    if (!this.right) {
      this.selectRight(null);
    }
    else {
	    this.togglePlaceHolderThumbs(this.right,"right");
    }
    
    
    // close scrollable caption first
	var scrollOuter = document.getElementById('scrollable-caption-outer');
	var scrollInner = document.getElementById("scrollable-caption");
	var link = document.getElementById("full-caption-link");
	//	Get parent where the link will be injected
	var linkContainer = scrollOuter.getParent();
	//	Store height to use when closing the caption again
	// n.b. if you change this, also update the height of #scrollable-caption in lb.css
	var initialHeight = 325;

	if (linkContainer.hasClass("open-caption")){
		//	already open so shrink and remove class
		scrollInner.tween('height', initialHeight).retrieve("tween").chain(function(){
			linkContainer.removeClass("open-caption");	
			link.innerHTML = "More";
		});
		
	} 

    // Get properties of various elements we need to calculate height of the open slider.
    var sovImageContainerHeight   = $('middle').getElements('div.left-column')[0].getSize().y,
        advancedSearchHeight      = $('viewListInner').getSize().y,
        collectionNavHeight       = $('collection-nav').getSize().y,
        compareContainerMarginTop = $('ec_compare_container').getStyle('margin-top').toInt(),
        overLapExtra              = 30,
        baseHeight                = sovImageContainerHeight;

    baseHeight += advancedSearchHeight;
    baseHeight += collectionNavHeight;
    baseHeight += compareContainerMarginTop;
    baseHeight += overLapExtra;
    
    //var newHeight = (baseHeight + collectionNavContainer.getSize().y) + 38;
    var newHeight = baseHeight;
    var newTop = (newHeight * -1) + overLapExtra;
    // Add a little extra so that the bottom underlaps the EC container.
    
    this.container.getElement('.slider').morph({
      width: 1044,
      height: newHeight,
      left: -30,
      top: newTop
    });
    
    
    this.tab.tween('left', 65).retrieve('tween').chain(function() {
      this.tab.getElement('.tab_middle').set('html', 'CLOSE COMPARE WORKS');
      this.container.addClass('open');
      this.content.fade('in');
      this.closeanchor.fade('in');
    }.bind(this));
    
    //	Show the "set as..." buttons on the thumbnails
    $$('.ec-cell.imageContent div.description .ec_compare_controls').each(function(el) {
    	el.setStyle("display", "block");
    });
    
    this.showNoCompareLinks();
  },
  
  close: function() {

	// close scrollable caption first
	var scrollOuter = document.getElementById('scrollable-caption-outer');
	var scrollInner = document.getElementById("scrollable-caption");
	var link = document.getElementById("full-caption-link");
	//	Get parent where the link will be injected
	var linkContainer = scrollOuter.getParent();
	//	Store height to use when closing the caption again
	// n.b. if you change this, also update the height of #scrollable-caption in lb.css
	var initialHeight = 325;

	if (linkContainer.hasClass("open-caption")){
		//	already open so shrink and remove class
		scrollInner.tween('height', initialHeight).retrieve("tween").chain(function(){
			linkContainer.removeClass("open-caption");	
			link.innerHTML = "More";
		});
	} 
	// now close compare panel
    this.isOpen = false;
    this.content.fade('hide');
    this.closeanchor.fade('hide');
    this.container.removeClass('open');
    this.container.getElement('.slider').morph({
      width: 970,
      height: 10,
      left: 5,
      top: -8
    });
    this.tab.tween('left', 15).retrieve('tween').chain(function() {
      this.tab.getElement('.tab_middle').set('html', 'OPEN TO COMPARE WORKS');
    }.bind(this));
    
     //	Hide the "set as..." buttons on the thumbnails
    $$('.ec-cell.imageContent div.description .ec_compare_controls').each(function(el) {
    	el.setStyle("display", "none");
    });
    
     $$('.place-holder-thumb').each(function(el) {
    	el.setStyle("display", "none");
    });
    
    $$('.ec-cell.imageContent.selected img').each(function(el) {
    	el.setStyle("display", "inline");
    });
    
    this.hideNoCompareLinks();
        
  },

  setupContainer: function() {
    this.container = new Element('div', {
      id: 'ec_compare_container',
      html: '<div class="slider"><div class="holder"></div></div>'
    });
    this.container.inject($('ec-diagram'), 'before');
    this.container.setStyles({
      width: $('ec-diagram').getSize().x,
      height: $('ec-diagram').getSize().y
    });
    this.containerHeight = this.container.getSize().y;
    $('ec-diagram').inject(this.container);
    this.holder = this.container.getElement('.holder');
  },
  
  setupTab: function() {
    this.tab = new Element('div', {
      id: 'ec_compare_tab',
      html: '<div class="tab_left"></div>' +
            '<div class="tab_middle">OPEN TO COMPARE WORKS</div>' +
            '<div class="tab_right"></div>' +
            '<div class="clear"></div>'
    });
    this.tab.inject(this.holder);
    this.tab.addEvent('click', function() {
      if (!this.isOpen) {
        this.selectLeft($$('img.selected-thumb')[0].getParent());
      } else {
        this.close();
      }
    }.bind(this));
  },
  
  setupDropShadows: function() {
    var bottom = new Element('div', {
      id: 'ec_compare_bottom_edge'
    });
    bottom.inject(this.holder);
    var ne = new Element('div', {
      id: 'ec_compare_ne_corner'
    });
    ne.inject(this.holder);
    var se = new Element('div', {
      id: 'ec_compare_se_corner'
    });
    se.inject(this.holder);
    var sw = new Element('div', {
      id: 'ec_compare_sw_corner'
    });
    sw.inject(this.holder);
  },
  
  setupContent: function() {
    this.content = new Element('div', {
      id: 'ec_compare_content',
      html: '<div id="ec_compare_left">' +
              '<div class="ec_image"></div>' +
              '<div class="caption"></div>' +
              '<div class="label selected">A</div>' +
            '</div>' +
            '<div id="ec_compare_separator"></div>' +
            '<div id="ec_compare_right">' +
              '<div class="ec_image"></div>' +
              '<div class="caption"></div>' +
              '<div class="label">B</div>' +
            '</div>' +
            '<div class="clear"></div>'
    });

    this.closeanchor = new Element('a', {href: '#', id: 'ec_compare_close'});

    this.content.fade('hide');
    this.closeanchor.fade('hide');
    this.closeanchor.inject(this.holder);
    this.content.inject(this.holder);
    $('ec_compare_close').addEvent('click', function(e) {
      new Event(e).stop();
      this.close();
      
    }.bind(this));
  },
  
  setupTargetLinks: function() {
    var controls;
    $$('.ec-cell.imageContent div.description').each(function(el) {
		//	Don't inject into final works i.e. class=no-compare
    	if (!el.getParent().getParent().hasClass("no-compare")) {
    		
		  controls = new Element('div', {
			'class': 'ec_compare_controls',
			'html': '<div class="ec_set_as">Set as:</div>' +
					'<a href="#" class="ec_set_left">A</a>' +
					'<div class="ec_set_or">or</div>' +
					'<a href="#" class="ec_set_right">B</a>' +
					'<div class="clear"></div>'
		  });
		  controls.inject(el, 'top'); /* inject at the top */
		  controls.getElement('.ec_set_left').addEvent('click', function(e) {
			new Event(e).stop();
			this.selectLeft(el.getParent('.ec-cell').getElement('a'));
		  }.bind(this));
		  controls.getElement('.ec_set_right').addEvent('click', function(e) {
			new Event(e).stop();
			this.selectRight(el.getParent('.ec-cell').getElement('a'));
		  }.bind(this));
      	}
    }.bind(this));
    
    
  },
  
  /*	
  	Two functions to get all the works that are not part of compare view
  	and show / hide the links to SOVs
  */
  
  showNoCompareLinks: function() {
  
  	//	Show links to SOV on the no-compare objects
  	$$('.ec-cell.imageContent div.description a.ec-to-sov-link').each(function(el) {
  	
  		el.setStyle("display", "block");
  	
  	}.bind(this));
  
  },
  
  hideNoCompareLinks: function() {
  
  	//	Show links to SOV on the no-compare objects
  	$$('.ec-cell.imageContent div.description a.ec-to-sov-link').each(function(el) {
  	
  		el.setStyle("display", "none");
  	
  	}.bind(this));
  
  },
  
  //	Function to add a link to the EC diagram which toggles it's height
  
  setUpDiagramToggleLink: function() {
  	
  	//	Get initial size of diagram and store for later use (- the padding)
  	this.diagramHeight = $('ec-diagram').getSize().y - $('ec-diagram').getStyle("padding-bottom").toInt() - $('ec-diagram').getStyle("padding-top").toInt() - $('ec-diagram').getStyle("border-top").toInt() - $('ec-diagram').getStyle("border-bottom").toInt();
  	//	Store slider height so it can be hidden / restored later
  	var slider = $('ec_compare_container').getElement(".slider");
  	this.sliderHeight = slider.getSize().y + slider.getElement("#ec_compare_tab").getSize().y;
  	this.sliderTop = slider.getStyle("top").toInt();
  	
  	//	Create the link that will toggle the diagrams height
  	var toggleLink = new Element("a", {
  						id: "ec-diagram-toggle",
  						href: "#",
  						title: "Click to toggle Evolving Composition diagram",
  						html: this.toggleLinkHtmlOpen
  					});
  	//	Show the link
  	toggleLink.setStyle("display", "inline");
  	
  	//	Does this diagram need the link to be visible?
  	//	Check for placeholder, if not found hide the link
  	if (!$('ec-diagram').getElement("span#related-view-toggle-placeholder")) {
  		toggleLink.setStyle("display", "none");
  	}
  	
  	//	Bind the toggle to it's click event
  	toggleLink.addEvent("click", function(e) {

  		new Event(e).stop();
  		this.toggleDiagram(toggleLink);
  	
  	}.bind(this));
  	//	Inject into the page
  	toggleLink.inject($('ec-diagram'), 'top');
  	
  	

  },
  
  toggleDiagram: function(toggleLink) {

  	var diagram = $('ec-diagram');
  	var container = $('ec_compare_container');
  	var slider = container.getElement(".slider");

  	if (this.diagramOpen) {
  	
  		// Close compare window if open
  		if (this.isOpen){
  			this.close();
  		}
  		//	Height we want to shrink it to depends on the height of the title Element etc
  		var title = $('ec-title')
  		var titleHeight = title.getSize().y;
  		var titleBottomMargin = title.getStyle("margin-bottom").toInt();
  		var diagramPaddingBottom = diagram.getStyle("padding-bottom").toInt();
  		var borderHeight = diagram.getStyle("border-top").toInt();
  		var smallHeight = titleHeight + titleBottomMargin - diagramPaddingBottom + 16;
  		var containerHeight = smallHeight + (diagramPaddingBottom*2) + borderHeight * 2;
		
		//diagram.addClass("padding-bottom", 0);		
  		//	Animate height
  		container.tween("height", containerHeight);
  		diagram.tween("height", smallHeight);
  		
  		//	Hide the overflow and set link text etc
  		diagram.setStyle("overflow", "hidden");
  		diagram.addClass("close-toggle");
  		toggleLink.set("html", this.toggleLinkHtmlClosed);
  		this.diagramOpen = false;
  		
  		//	Toggle the compare tab as this should also be closed
  		slider.tween("top", this.sliderHeight);
  		
  	}
  	else {
  		//	Animate height
  		container.tween("height", this.containerHeight);
  		
  		//	Has to be chained here so that the overflow doesn't show during the tween
  		diagram.tween("height", this.diagramHeight).retrieve('tween').chain( function() {
  			diagram.setStyle("overflow", "");
  		});
  		
  		diagram.removeClass("close-toggle");
  		toggleLink.set("html", this.toggleLinkHtmlOpen);
  		this.diagramOpen = true;
  		
  		slider.tween("top", this.sliderTop);
  		
  	}
  
  
  }
  
});


//	New class for scrollable captions first introduced on Louis Bourgeois

MoMA.scrollableCaption = new Class({

	initialize: function(el, page) {

		this.el = el;

        this.setHeight();

		if (el.getElement('div#scrollable-caption-outer')) {
			this.addMoreLink();
        }

        var me = this;

        // Update caption area height when SOV main image changes.
        page.addEvent('sovMainImageResize', function(){me.setHeight();});

	},

    // Set the height of the captions container based on the main SOV image.
    setHeight: function() {

		// set height so we know what height to open compare container to even when the scroller is opened
		rightColContainerHeight = $$('div.right-column')[0].getSize().y;
		leftColContainerHeight = $$('div.left-column')[0].getSize().y;

        // If the left and right boxes are not the same height
        // change the initial size of the scrollable area.

        // Store the difference between the two containers.
        var diff = leftColContainerHeight - rightColContainerHeight;
		this.scrollInner = this.el.getElement("div#scrollable-caption");

        var initialHeight = this.scrollInner.getStyle("height").toInt();
        this.adjustedHeight = initialHeight + diff;

        // Only update the height if the scroll container is closed.
        var scrollOuter = this.el.getElement('div#scrollable-caption-outer');
        if (!scrollOuter.getParent().hasClass('open-caption')) {
            this.scrollInner.setStyle("height", this.adjustedHeight);
        }

    },

	addMoreLink: function() {

		var scrollOuter = this.el.getElement('div#scrollable-caption-outer'),
            scrollInner = this.scrollInner,
            adjustedHeight = this.adjustedHeight,
		    linkContainer = scrollOuter.getParent();

		//	If no scroll content don't add the button to expand		
		if (scrollInner.getScrollSize().y <= adjustedHeight) {
			return false;
		}
		
		//	Create the link
		var link = new Element("a", {
			id: "full-caption-link",
			"title": "full-caption-link",
			"href": "#",
			"html": "More"
		});

		//	Inject the link into the page
		link.inject(linkContainer);
		//	Add the click event
        var me = this;

		link.addEvent("click", function(e) {
			//	Stop default link behaviour
			new Event(e).stop();
			//	Is caption already open?
			if (linkContainer.hasClass("open-caption")){
				//	already open so shrink and remove class
				scrollInner.tween('height', me.adjustedHeight).retrieve("tween").chain(function(){
					linkContainer.removeClass("open-caption");	
					link.innerHTML = "More";
				});
				
			}
			else {
				//	Closed so expand to full height and add open class
				scrollInner.tween('height', scrollInner.getScrollSize().y).retrieve("tween").chain(function(){					
					linkContainer.addClass("open-caption");	
					link.innerHTML = "Less";
				});
			
			}
		
		});
				
	}

});


// This class will handle drop down menu behaviour for the content
MoMA.SectionMenu = new Class({

	initialize: function(el) {
		this.el = el;
		
		if (el.getElement('select#contents-list'))
		    this.dropDownLinks(el.getElement('select#contents-list'))
	    
	},
	
	dropDownLinks: function(tableOfContent) {
		// on click of the option, go to it's value - the GET variable which gets appended to the url
	    tableOfContent.addEvent('change', function(){
	    	var selectedOption = tableOfContent.getSelected();
	    	location.href = selectedOption.getProperty('value');
		}.bind(this));
	}
	
});

//The Class to swap in the second Images once their links have been clicked on
MoMA.SecondaryImages = new Class({
	
	initialize: function(el, page) {
	
	
		this.el = el;
		this.secondImageLinks = el.getElements('ul.pages li a');
		var imageSource = el.getElement('div.holder');
		var controls = el.getElement('div.controls');
		this.secondImageLinks.each(function(link){

			 link.addEvent('click', function(){
				var linkID = link.getProperty('id');
				var imageID = linkID.replace("secondImage",'');

				for (key in imageArray){
					if(key == (imageID-1)){
						
						var src = imageArray[key]['src'];
						var width = imageArray[key]['width'];
						var height = imageArray[key]['height'];
						var alt = imageArray[key]['alt'];
						//set the html of the div.holder to include the image source. this replaces the flash object when zoomify is there instead.
						imageSource.set('html','<p id="mainImage"><img src="'+src+'" width="'+width+'" height="'+height+'" alt="'+alt+'" /></p>');

						if(imageArray[key]['zoom']){
							
							controls.set('html','<div id="zoomifyDiv"></div>');
							
							if (swfobject.hasFlashPlayerVersion('6'))
							{
								if (BrowserDetect.browser == 'Opera' || BrowserDetect.browser == 'Chrome')
								{
									var fullscreenMode = 'false';
								}
								else
								{
									var fullscreenMode = 'true';
								}
								//add the zoomify links to the div.controls
								addZoomifyLinks(imageArray[key]['zoom'], 'zoomifyDiv', '', '', '', fullscreenMode, function(){page.fireEvent('sovMainImageResize');});
							}
							else {
								clearZoomifyLink('zoomifyDiv');
							}
						}
						else {
							clearZoomifyLink('zoomifyDiv');
						}
					}
				}

                // Fire resize event.
                page.fireEvent('sovMainImageResize');

                return false;
			 });
		});
		
	},

	swapImage: function(link, imageSource) { 	
		
		imageSource.getElementgetProperty('src') = link.getProperty('href');
		return false;
    }
});

// This Class will handle the onclick values of the tabs, hiding and showing the relevant content
MoMA.SectionContentTabs = new Class({

	initialize: function(el) {
		this.el = el;
		// Grab all the content tab links
		this.listItems = el.getElements('div.tabs ul li a');
		
		// Loop through all tab links
		this.listItems.each(function(listItem){
	    	// Grab all the content where the class is the same as the ID of the tab link
			var relatedContent = el.getElements('div.' + listItem.id);

			// Check if the link has an ID and there is related content
			if (listItem.id.length > 0 && relatedContent.length > 0) {
				
				// When a tab link is clicked...
				listItem.addEvent('click', function() {
					// Hide all the content...
					el.getElements('div.content').setStyle('display', 'none');
					relatedContent.each(function(relatedContentItem) {
						/// and unhide the related content
						relatedContentItem.setStyle('display', 'block');
						
						// Unselect all the tabs, and highlight the clicked tab
						el.getElements('div.tabs ul li a').removeClass('selected');
						listItem.addClass('selected');
					});
					return false;
				});
			}
	    });
	}
});

// The Class which handles the browser filter transitions
MoMA.FilterTransitions = new Class({
    
  initialize: function(el) {
    // Grab content that needs to be changed
    this.el = el;
    
    // Get the height of the mainContent, and create a content cover of the same size
    this.coverContent = el.getElement('div#coverContent');
    // Calculate height of the popover style content covering div
	var mainContentDims = el.getElement('div#middle').getSize();
	//var collectionDims = el.getElement('div#collection').getSize();
    var footerDims = el.getElement('div#bottomContent').getSize();
    if (mainContentDims.y < minContentHeight) {
    	this.minContentHeight = minContentHeight;
    	mainContentDims.y = minContentHeight;
    }
    this.contentCoverHeight = mainContentDims.y + footerDims.y;
    this.coverContent.setStyle('height', this.contentCoverHeight);
    
    this.filterBar = el.getElement('form.browseFilter');
    this.filterLists = this.filterBar.getElements('ul');
    
	this.toggleFilterBar = el.getElement('div#toggleFilter div#filterOptions');
    this.advancedLink = el.getElement('a.advancedOptions');
    this.fileDropDown = el.getElement('.extendedFilter');
    this.closeFilter = el.getElement('a#closeFilter');
    if(typeof germex != 'undefined'){
    this.closeSearchFilters = el.getElement('a#closeSearchFilters');
    }
    this.filterStatus = el.getElement('a#filterStatus');
    this.tabbedInfo = el.getElement('#middle.object .text .content');
    this.thumbnailSlider = el.getElement('div.thumbnail_images');
    this.collectionNav = el.getElement('div#collection-nav');
    this.middleContent = el.getElement('div#middle');

    this.coverFilterContent = el.getElements('div#coverFilterOptions');
    this.bottomContent = el.getElement('div#bottomContent');

    
    //TODO: Add functionality to move popover to middle of screen, set overflow: hidden and activate close button
    this.noSearchResults = el.getElement('div#errorMessage');
    
    if (el.getElement('div.untoggleable') != "") {	
    	this.toggleFilterBar.addEvent('click', function(evt){
    		new Event(evt).stop();
    	});
    }	
    
   //if there is no search results then output an error in the middle of the screen, hiding other content
    if (this.noSearchResults) {
    	this.coverNoResults = el.getElement('div#coverNoResults')
    	this.coverNoResults.setStyle('display', 'block');
    	this.noSearchResults.set('html', '<p id="errorHeader">Sorry, your search criteria didn\'t return any results.</p><p>You may want to broaden your search and try again.</p><a href="#"><img id="close_message" src="images/collection/error_message_close_icon.gif" alt="close" /></a>');
    	this.filterBar.setStyle('display', 'block');
    	
    	//for when the user clicks the close icon
    	this.noSearchResults.addEvent('click', function() {
    		this.filterBar.setStyle('display', 'block');
			this.noSearchResults.setStyle('display', 'none');
			this.coverNoResults.setStyle('display', 'none');
			return false;	
		}.bind(this))
		
		//for when the user clicks on the background.
		this.coverNoResults.addEvent('click', function() {
			this.filterBar.setStyle('display', 'block');
			this.noSearchResults.setStyle('display', 'none');
			this.coverNoResults.setStyle('display', 'none');
		}.bind(this))
		
    }
    
    // TRANSITION OPTIONS
    // Set properties for tweening the filter drop down
    this.fileDropDown.set('tween', {
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut,
      onComplete: function(e) {
		if (this.toggleFilterBar.className.indexOf(strFilterToggle) != -1) {
		    el.getElements('form.browseFilter ul').setStyle('overflow', 'auto');
		    if (typeof germex === 'undefined' && typeof lb === "undefined"){
		    	
		    	el.getElement('div#coverContent').setStyle('display', 'block');
		    }
		} else {
			if (lteIE7) {
				if (this.middleContent.getElements('select') != "")
					this.middleContent.getElements('select').setStyle('display', 'inline');
				
				if (this.bottomContent.getElements('select') != "")
					this.bottomContent.getElements('select').setStyle('display', 'inline');
			}
				
		}
      }.bind(this)
    });
	
	// If you click the filter bar, the content covering div or the 'advanced' search link,
	// the browse filter menu will drop down
	
	// Only toggle filter bar if not on the stand alone search page
	if (el.getElements('div.toggleable') != "") {
	    this.toggleFilterBar.addEvent('click', this.toggleMainFilter.bind(this));	    
	    this.closeFilter.addEvent('click', this.toggleMainFilter.bind(this));
	    if(typeof germex != 'undefined') {
	    this.closeSearchFilters.addEvent('click', this.toggleMainFilter.bind(this));
	    }
	   // this.advancedLink.addEvent('click', this.toggleAdvancedFilter.bind(this));
	   
	    this.coverContent.addEvent('click', this.toggleFilter.bind(this));
	    
	    // TODO: Not opening main options
	    // this.coverFilterContent.addEvent('click', this.toggleMainFilter.bind(this));
	}
  },
    
  // Function that toggle the filter drop down menu, and
  // hides the rest of the website behind a semi opaque div
  toggleFilter: function() {
	// Use toggle class to keep track of whether the filter bar is expand or not
	this.toggleFilterBar.toggleClass(strFilterToggle);

	// If the drop down is closed, then show it and hide the main content
	// Else close the drop down and show the main content
	if (this.toggleFilterBar.className.indexOf(strFilterToggle) != -1) {
		if (typeof germex === 'undefined' && typeof lb === 'undefined') {
			this.coverContent.setStyle('display', 'block');
		}
		// Elements that may not appear on the page
		if (this.tabbedInfo) {
			this.tabbedInfo.setStyle('overflow', 'hidden');
		}
	    //if (this.thumbnailSlider) {
	    	//this.thumbnailSlider.setStyle('overflow', 'hidden');
	    //}
	    

	    // Animate the browse filter to its preset height
	    this.fileDropDown.tween('height', browseFilterHeight);
   		this.fileDropDown.removeClass("hide-borders");
	    // IE6 bug fix: Hide drop downs when the browse filter is expanded
		if (lteIE7) {
		    if (this.minContentHeight != "") {
		    	if (typeof germex === 'undefined' && typeof lb === 'undefined') {
		    		this.middleContent.setStyle('height', this.minContentHeight);
		    	}
			}
			if (this.middleContent.getElements('select') != "")
				this.middleContent.getElements('select').setStyle('display', 'none');
				
			if (this.bottomContent.getElements('select') != "")
				this.bottomContent.getElements('select').setStyle('display', 'none');
		}

	    this.filterStatus.addClass('open');
	    this.filterStatus.removeClass('closed');
	} else {
		this.coverContent.setStyle('display', 'none');
	    this.filterLists.setStyle('overflow', 'hidden');
	    // Elements that may not appear on the page
	    if (this.tabbedInfo) {
	    	this.tabbedInfo.setStyle('overflow', 'auto');
	    }
	   // if (this.thumbnailSlider) {
	    //	this.thumbnailSlider.setStyle('overflow', 'auto');
	    //}

		// Close up the browse filter
		this.fileDropDown.tween('height', 0);
	    this.fileDropDown.addClass("hide-borders");	    
	    this.filterStatus.addClass('closed');
	    this.filterStatus.removeClass('open');
		// If mainContent height has been fixed, then revert back to 'auto'
		if ((lteIE7) && (this.middleContent.getStyle('height').toInt() == minContentHeight))
			this.middleContent.setStyle('height', 'auto');

	}

  },
  
  // Function that sets the browse filter behaviour based if the art terms header button is pressed
  toggleAdvancedFilter: function(e) {
    e = new Event(e);
    e.preventDefault();
    
	this.toggleFilter();
  },
  
 
  
  // Function that sets the browse filter behaviour based if the main filter bar is pressed
  toggleMainFilter: function(e) {
    e = new Event(e);
    e.preventDefault();

	if (this.fileDropDown.getStyle('height') == "0px") {
		this.toggleFilter();
	} else if ((this.coverFilterContent.getStyle('display') == "none") && (this.toggleFilterBar.getProperty('class').indexOf("selected") != -1)) {
		this.toggleFilter();
	}
	
	if (this.toggleFilterBar.getProperty('class').indexOf("selected") == -1) {
		this.toggleFilterBar.setProperty('class',this.toggleFilterBar.getProperty('class') + ' selected');
	}
	// this.artTermsBar.removeClass('selected');	
  }
  
  
  
    
});

// Class that deals with the collection nav search form behavior
MoMA.Search = new Class({
	initialize: function(el) {
		this.el = el;
		this.searchField = el.getElement('input#searchAll');
		
		this.searchFieldBehaviour(this.searchField);

	},
	
	searchFieldBehaviour: function(rollOverItem) {
		this.searchField.setAttribute('value', searchFieldValue);
		this.searchField.addEvent('focus', function(){
			$(this).setAttribute('value', '')
		});
		
		this.searchField.addEvent('blur', function(){
			if ($(this).getAttribute('value') == "") {
				$(this).setAttribute('value', searchFieldValue)
			}
		});
	}
	
	
});

MoMA.RollOverStates = new Class({

	initialize: function(el) {
		if (lteIE7) {
		    // Grab content for IE6
		    this.el = el;
		    if (el.getElements('div.tabs ul li.dropdown') != "")
			    this.rollOverIE(el.getElements('div.tabs ul li.dropdown'))
			    
			if (el.getElements('ul#thumbnail-view-items li') != "")
			    this.rollOverIE(el.getElements('ul#thumbnail-view-items li'))
			
			if (el.getElements('ul#list-view-items li') != "")
			    this.rollOverIE(el.getElements('ul#list-view-items li'))
			    
			if (el.getElements('ul.list-view-items li') != "")
			    this.rollOverIE(el.getElements('ul.list-view-items li'))
			    
			if (el.getElements('div#filterOptions') != "")
			    this.rollOverIE(el.getElements('div#filterOptions'))
		}

		this.imageRollOver = el.getElements('ul#thumbnail-view-items li div.shadow div.description a img');
		this.imageRollOverUncropped = el.getElements('ul#thumbnail-view-items li a img');
		this.verticalAlignment(this.imageRollOver);
		this.verticalAlignment(this.imageRollOverUncropped);
		// Grab Content
		if (el.getElement('input#filterSubmit') != "")
		    this.rollOverImageSubmit(el.getElement('input#filterSubmit'), "images/collection/search.gif");
	},
	
	// Function that adds class on hover for IE6 styles
	rollOverIE: function(rollOverItems) { 	
		rollOverItems.each(function(thumbnail){
	    	thumbnail
		  	.addEvent('mouseover', function() {
				this.addClass('hoverState');
			})
		    .addEvent('mouseout', function() {
		    	this.removeClass('hoverState');
		    })
		});
    },
    
   	// Function that takes an image submit button, and changes its source on rollover
    rollOverImageSubmit: function(rollOverButton, rollOverSource) { 	
    	var oldSrc = rollOverButton.getAttribute('src');
    	rollOverButton
		.addEvent('mouseover', function() {
			this.setAttribute('src', rollOverSource);
		})
		.addEvent('mouseout', function() {
		  	this.setAttribute('src', oldSrc);
		})
    },
    
	verticalAlignment: function(images) {
        	images.each(function(image){
        		var remainder_height = 170 - image.get('height');
        		image.setStyle('margin-top', remainder_height / 2);
        		image.setStyle('margin-bottom', remainder_height / 2);
        	});
        }
   
});

// Class that deals with any functionality for link behavior
MoMA.LinkFunctions = new Class({
	initialize: function(el) {
		if ($chk(el.getElements('ul#list-view-items li'))) {
    		this.listViewItems = el.getElements('ul#list-view-items li');
		    this.blockLink(this.listViewItems, 0);
	    }
	    
	    if ($chk(el.getElements('ul.list-view-items li'))) {
    		this.listViewItems = el.getElements('ul.list-view-items li');
		    this.blockLink(this.listViewItems, 0);
	    }
	    
		if ($chk(el.getElements('ul#thumbnail-view-items li'))) {
    		this.thumbnailViewItems = el.getElements('ul#thumbnail-view-items li');
		    this.blockLink(this.thumbnailViewItems, 1);
	    }
	},
	
	// Function that makes an entire element linkable,
	// based on a specific link within that div
	blockLink: function(linkItems, linkNumber) {
		linkItems.setStyle('cursor','pointer');
		
		linkItems.each(function(linkItem){
			var primaryLink = linkItem.getElements('a')[linkNumber];
			linkItem.addEvent('click', function() {
				document.location = primaryLink.getAttribute('href');
			});
		});
	}
});

// Class that deals with any functionality for link behavior
MoMA.Banner = new Class({
	initialize: function(el) {
		
		if ($chk(el.getElements('div.banner_info'))) {
			
    		this.listViewItems = el.getElements('div.banner_info');
    		this.listViewItems.setStyle("display", "block");
    		
    		
		    this.listViewItems.getElement("a").addEvent('mouseover', function() {
		    	this.listViewItems.getElement("p").setStyle('visibility', 'visible');
		    }.bind(this));
		    
		    this.listViewItems.getElement("p").addEvent('mouseout', function() {
		    	this.listViewItems.getElement("p").setStyle('visibility', 'hidden');
		    }.bind(this));
	    }
	}
});

// Class that determines whether or not to show the 'Find related products at MoMAstore.org' button on single object pages
MoMA.StoreRelatedProducts = new Class({
	initialize: function(el) {
		var query = onlineStoreQuery;

		var req = new Request({
			url: "get_moma_store.php",
			data: { "q": query },
			method: "get",
			headers: { "Accept": "text/xml" }
		});

		req.onSuccess = function(txt, doc) {
			// Determine whether or not to display button
			var numberOfProducts = doc.getElementsByTagName("product").length;
			if (numberOfProducts > 0) $$('.shop_link').setStyle('display','block');
		}
		
		req.send();
	}
});


/* 
	DEFER: May reinstate for the 'about this department' popover
	MoMA.PopOvers = new Class({

	initialize: function(el) {
	    // Grab content
	    this.el = el;

	    this.showContent(
	    	el.getElement('.readText'),
	    	el.getElement('.info_box_wrap'),
	    	el.getElement('div.close_box a')
	    );
	},
	
	// Take in an activate button, a revealing element and an optional close element
	showContent: function(activateLink, showItem, closeButton) {	
		activateLink.addEvent('click', function() {
			if (showItem.getStyle('display') == "none") {
				showItem.setStyle('display', 'block');
			} else {
				showItem.setStyle('display', 'none');
			}
		});
		
		closeButton.addEvent('click', function() {
			showItem.setStyle('display', 'none');
		});
    }
   
}); */
