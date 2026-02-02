// Export functionality - covers email, print, RIS-format data
// Created 10/23/08 by Ken Mitchell


// Variables used to construct proper urls
// Note that the email and sms urls MUST be the same as the webapp server to support the ajax calls between the webapp
// and the email/sms functions

var emailApplicationURL = "markeditems"; 
var smsApplicationURL = "markeditems";
var refWorksAutoLoginURL = "http://www.refworks.com/refworks/autologin.asp";
var errorMessage = "We're sorry, but there appears to be a problem with sending information.  Please try again later, or contact us using the 'Contact Us' link.\n\nWe apologize for the inconvenience.";

/* The generatePopUpBox() function is a relatively simple function that preps the intended linkID to become a "lightbox"-style popup box link.  It assumes that the link has an href that includes an achor portion, and that anchor portion points to the id of a non-visible element on the page (this is how fancybox works with inline elements).  */
function generatePopUpBox(selectorName, frameWidth, frameHeight) {
	if (selectorName != null) {
		$(document).on("click", selectorName, function(){
			var targetElementID = this.href;
			var anchorPortionRegExp = new RegExp("^[^#]+(#.+)$");
			targetElementID = targetElementID.replace(anchorPortionRegExp, "$1");
			this.setAttribute("targetElementID", targetElementID);
			$(targetElementID).dialog({
				height : frameHeight? frameHeight : 'auto',
				width: frameWidth? frameWidth : 500,
				modal: true,
				dialogClass: "fancy",
				show: {effect: 'fade', duration: 250}
			});
			return false;
		});
	}
}

// activateEmailForm is a relatively simple function that assigns a couple of properties/attributes on the passed0in form(s).  Ideally, it should also set the onSubmit method for the form, but it appears that the fancyBox plugin (or something in the structure of the SearchTRLN pages) is blocking that, so the onSubmit is manually set in the jsp page (not ideal...).
function activateEmailForm(formClassName) {
	if (formClassName != null) {
		$("." + formClassName).each(function() {
			var emailForm = this;
			// get the record/page title
			emailForm.setAttribute("emailTitle", $(".title", emailForm).text());
			emailForm.action = emailApplicationURL;
			
		});
	}
}

// compileEmailFormEventListener is a legacy function from attempts to set the onSubmit programmatically rather than manually.
function compileEmailFormEventListener(e) {
	if (this != null) {
		compileEmailForm(this);
	}
}

// compileEmailForm() provides the main data-retrieval methods for the email form.  The basic idea is that when a user clicks on "Submit", the page retrieves the e-mail data (if it's not already there) and adds it to the email form.  Then the form is submitted.
function compileEmailForm(formObject) {
	if (formObject != null) {
		// make sure there aren't already textareas in the email form (if so, then just try to post the form rather than add the data...
		var postingData = {"email":formObject.email.value, "export": "email"};
		if ($("textarea", formObject).length > 0) {
			postingData.subject = formObject.subject.value;
			postingData.message = formObject.message.value;
			postExportData(formObject, errorMessage, postingData, "e-mail", postingData.email);
		} else {
			var $submitButton = $(formObject).find("input[type='submit']");
			$submitButton.attr("disabled", "disabled");
			// add a subject
			var subjectLine = "UNC-CH Catalog information";
			var formSubject = formObject.emailSubject.value;
			var formTitle = formObject.getAttribute("emailTitle");
			
			if ((formSubject != null) && (formSubject.length >0)) {
				if (formSubject.length > 128)
					subjectLine = formSubject.substring(0,128);
				else subjectLine = formSubject;
			} else {
				if ((formTitle != null) && (formTitle.length >0))
					subjectLine += " for '" + formTitle + "'";
			}
			$(formObject).append('<textarea name="subject">' + subjectLine + '</textarea>');
			postingData.subject = formObject.subject.value;
			// add a message with the contents of the desired record(s)
			var recordID = formObject.getAttribute("recordID");
			var emailMessage = "No information is available for your request.";
			var formContentsURL = formObject.getAttribute("contentsURL");
			if ((formContentsURL!= null) && (recordID != null) && (formContentsURL.length > 0) && (recordID.length > 0)) {
				// define the needed ajax options
				var requestMethod = "GET";
				var requestURL = formObject.getAttribute("contentsURL");
				var requestData = {'output-format':'export', 'export-option':'email', 'format': 'email'};
				// for the data, we need to check if the recordID is "markeditems", which indicates a shopping-cart export.  This means that rather than passing "id=xxx", we'll want to pass "op=list"...
				if (recordID == "markeditems") {
					requestData.op = "list";
				} else {
					requestData.R = recordID;
				}
				var requestReturnType = "text";
				var requestReturnContentType = "text/plain; charset=utf-8";
				var successFunction = function(data, status) {
						emailMessage = data;
						$(formObject).append('<textarea name="message">' + emailMessage + '</textarea>');
						postingData.message = formObject.message.value;
						postExportData(formObject, errorMessage, postingData, "e-mail", postingData.email);
					};
				var errorFunction = function(xhpObject, status, error) {
						// alert("failure! status: " + status + ", error: " + error + ", XMLHTTPREQUEST: " + xhpObject.getAllResponseHeaders() + ", responseXML: " + xhpObject.responseXML);
						$(".formcontents", formObject).hide("normal", function() {
							$(formObject).prepend('<div class="exportresults">' + errorMessage + '</div>');
						});
						return false;
					};
				// process the ajax function
				performAJAXCall(requestMethod, requestURL, requestData, requestReturnType, successFunction, errorFunction, requestReturnContentType);
				// show a loader (just to indicate progress....)
				$(formObject).prepend('<div class="exportresults"><img src="images/ajax-loader.gif" alt="(loading)" /> <span class="resultsaction">compiling email...</span></div>');
			}
		}
		return false;
	} else {
		return false;
	}
}

function compileReservesForm(formObject){
	if (formObject != null) {
		var formIncomplete = false;
		$(formObject).find(".required_fields input:hidden, .required_fields input:text, select").each(function(){
			if ($(this).val() == null || $.trim($(this).val()).length == 0)
				formIncomplete = true;
		});
		
		if (formIncomplete){
			$(".reserves_form_errors").html("Please fill in all fields not labeled as optional.");
			$(".reserves_form_errors").show();
			return false;
		} else {
			var re = /[^@]+@[^@.]+\.[^@]+/;
			if (!$(formObject).find("input[name='email']").val().match(re)){
				$(".reserves_form_errors").html("Please enter a valid email address.");
				$(".reserves_form_errors").show();
				return false;
			}
			$(".reserves_form_errors").hide();
		}
		
		var $submitButton = $(formObject).find("input[type='submit']");
		$submitButton.attr("disabled", "disabled");
		
		var requestData = {"export": "reserves"};
		
		$(formObject).find("input:hidden, input:radio:checked, input:text, textarea").each(function(){
			if ($(this).val() != null)
				requestData[$(this).attr("name")] = $(this).val();
		});
		
		requestData['course_id'] = requestData.course_subject + requestData.course_number;
		requestData['contact'] = $(formObject).find("select[name='contact']").val().split("|")[0];
		
		var contactEmail = $(formObject).find("select[name='contact']").val().split("|")[1];
		var contactName = $(formObject).find("select[name='contact'] option:selected").text();
		
		$.ajax({
			type : 'POST',
			url : formObject.action,
			data : requestData,
			success : function(data, status){
				if (data.error != null){
					$(formObject).html("<h1>Course Reserves Request</h1>\n<br/><div style='text-align: center'>" +
							data.error + "</div>");
				} else {
					$(formObject).html("<h1>Course Reserves Request</h1>\n<br/><div style='text-align: center'>" +
							"Your reserves request has been sent to the " + contactName + " Reserves Department. " +
							"Reserves can also be contacted at <a href=\"mailto:" + contactEmail + "\">" + contactEmail + "</a>. "
							+ "You will receive a confirmation email when your materials are " +
							"available at the " + contactName + "; typical processing time is 5-7 business days. " +
							"Please <a href='mailto:" + contactEmail + "'>contact us</a> if you have any comments " +
							"or questions.</div>");
				}
				
				ga('unc.send', 'event', requestData['contact'], 'course reserves submission');
			},
			error : function(xhpObject, status, error){
				$(formObject).prepend('<div class="exportresults">We were unable to complete the request.  Please try again or contact us directly.' +
						error + '<br/>' + status + '</div>');
			}
		});
	}
	return false;
}

// compileSMSForm is similar to the compileEmailForm above, but using the SMS data.  Both of these functions post data to the same type of PHP script (although with different names).  Much of the functionality has been derived from Derek's work in a previosu version.
function compileSMSForm(formObject) {
	var frm = formObject; // get the SMS form
	var phone = frm.phone.value; // get the phone #
	phone = phone.replace(/[^\d]/ig,""); // remove all non-digit characters
	if (phone.length == 11)
		phone = phone.substring(1);
	if (phone.length == 10) { // if 10 chars, we're good
		formObject.action = smsApplicationURL;
		var postingData = {
				"number": phone, 
				"export": "sms", 
				"provider": frm.provider.options[frm.provider.selectedIndex].value,
				"item" : $("input[name='item']:checked").val()
		};
		// now post the data
		return postExportData(formObject, errorMessage, postingData, "sms", frm.phone.value);
	} else {
		alert('please enter a valid phone #');
		return false;
	}
}

// postExportData does an AJAX-based submission of the passed-in email/sms form.  (Note that the fields that are passed along are manually cited below.)
function postExportData(formObject, errorMessage, postingData, postType, recipient) {
	if ((formObject != null) && (postingData != null)) {
		var postingType = "e-mail";
		if (postType != null) {
			postingType = postType;
		}
		// first check to see if any exportresults content exists, and if so, clear it.
		$(".exportresults", formObject).remove();
		// adjust the form object to suppress display of the form contents and display a generator message
		$(formObject).prepend('<div class="exportresults"><img src="images/ajax-loader.gif" alt="loading" /> <span class="resultsaction">Sending ' + postingType + '</span></div>');
		$(".formcontents", formObject).hide("normal");
		// compile the AJAX-based information
		postingData.returnstyle = "json";
		var requestMethod = "POST";
		var requestURL = formObject.action;
		var requestData = postingData;
		var requestReturnType = "json";
		var successFunction = function(receivedData, status) {
			// now that the data has been sent (and received), check to see if any errors.  If so, display them.  If not, then display success message
			// alert(data.result);
			var resultsMessage = postingType + " successfully sent to " + recipient;
			if (receivedData.result != "success") {
				resultsMessage = "Error: ";
				if (receivedData.messages) {
					resultsMessage += receivedData.messages;
					$(".formcontents", formObject).show("normal");
					$(formObject).find("input[type='submit']").attr("disabled", "");
				} else {
					resultsMessage += errorMessage;
				}
			}
			$(".exportresults", formObject).hide("normal", function() {
				$(this).html(resultsMessage).show("normal");
			});
		};
		var errorFunction = function(xhpObject, status, error) {
			// alert("failure! status: " + status + ", error: " + error + ", XMLHTTPREQUEST: " + xhpObject.getAllResponseHeaders() + ", responseXML: " + xhpObject.responseXML);
			$(".formcontents", formObject).hide("normal", function() {
				$(formObject).prepend('<div class="exportresults">' + errorMessage + '</div>');
			});
			return false;
		};
		// process the ajax function
		performAJAXCall(requestMethod, requestURL, requestData, requestReturnType, successFunction, errorFunction);
	} else {
		alert(errorMessage);
	}
	return false;
}

// performAJAXCall() is a generic-style function that performs an AJAX call according to the requested parameters.  Nothing is returned, as the desired actions are executed via the success/failure components.  the $.ajax JQuery method is preferred rather than the simpler .get, .post or .load, as we want to provide some level of error-handling.
function performAJAXCall(requestMethod, requestURL, requestData, requestReturnType, successFunction, errorFunction, requestReturnContentType) {
	if ((requestMethod != null) && (requestURL != null) && (requestData != null) && (requestReturnType != null) && (successFunction != null) && (errorFunction != null)) {
		// compile ajax options
		var ajaxOptions = { type:requestMethod, url:requestURL, data:requestData, dataType:requestReturnType, success:successFunction, error:errorFunction};
		//var ajaxOptions = { type:requestMethod, url:requestURL, data:requestData, dataType:requestReturnType, success:successFunction, error:errorFunction};
		
		if (requestReturnContentType != null) {
			ajaxOptions.contentType = requestReturnContentType;
		}
		$.ajax(ajaxOptions);
	}
}

// activatePrintLink() is a simple function that sets the onClick action of any relevant links to produce a popup (smaller) window
function activatePrintLink(linkClassName) {
	$("." + linkClassName + "[href]").click(function() {
		var targetURL = this.href;
		window.open(targetURL, "printwindow", 'toolbar=no,width=800,height=600,dependent=yes,menubar=no,resizable=yes,scrollbars=yes');
		return false;
	});
}

function activateEADLink(linkClassName) {
	$("." + linkClassName + "[href]").click(function() {
		var targetURL = this.href;
		window.open(targetURL, "eadwindow", 'toolbar=no,width=800,height=600,resizable=yes,menubar=yes,scrollbars=yes');
		return false;
	});
}

// activateExportSelect() finds the desired form by name and sets it to automatically open a new window (refworks) or produce the file (endnote), depending on the option selected in the select
function activateExportSelect(exportFormID) {
	var exportForm = document.forms[exportFormID];
	if (exportForm != null) {
		var refWorksExpressImportWindowName = "RefWorksMain"; // all refworks imports need to be done in a window with this name
		var id = exportForm.id.value;
		var baseurl = "?vendor=SearchUNC&filter=RIS%20Format&encoding=65001&url=";
		var webServicesEncodingString = "&output-format=export&export-option=ris";
		var searchString = "?";
		if (id == "markeditems") {
			var recordIDList = exportForm.recordids.value;
			if (recordIDList != null) {
				searchString += "R=" + recordIDList; 
			}
		} else {
			searchString += "R=" + id; 
		}
		var documentLocation = document.location;
		var recordUrl = documentLocation.protocol + "//" + documentLocation.host + documentLocation.pathname; // doesn't appear to need a "/" between host and pathname...
		// make sure to replace "markeditems" servlet pointer with "search" pointer
		var markedItemsStringIndex = recordUrl.indexOf("markeditems");
		if (markedItemsStringIndex > -1) {
			recordUrl = recordUrl.substr(0, markedItemsStringIndex) + "search";
		}
		var callbackurl = recordUrl + searchString + webServicesEncodingString;
		var refworksurl = baseurl + encodeURIComponent(callbackurl);
		// set the onchange for the select to submit the form
		$("select", exportForm).change(function() {
			// determine what option has been selected, and adjust any values as needed (main condition is to see if RefWorks is being requested, and adjust target name for the form)
			var selectedOptionArray = $("option:selected", this);
			if (selectedOptionArray.length > 0) {
				var selectedOption = selectedOptionArray[0];
				if (selectedOption != null) {
					$.get("./search", {op: "log", exportType: selectedOption.value}, null, "xml" );
					if (selectedOption.value == "text"){
						if (id == "markeditems")
							window.open("markeditems?op=list&output-format=export&export-option=email",'_self','location=1,top=0,left=0,width=850,height=600,menubar=1,toolbar=1,scrollbars=1,resizable=1');
						else window.open("search?R=" + id + "&output-format=export&export-option=email",'_self','location=1,top=0,left=0,width=850,height=600,menubar=1,toolbar=1,scrollbars=1,resizable=1');
					} else {
						var refworksRegExp = new RegExp("^(Refworks-)(.*)$");
						var refWorksInstitution = selectedOption.value.replace(refworksRegExp, "$2");
						var finalurl = null;
						switch (refWorksInstitution)  {
							case "unaffiliated":
							case "duke":
							case "nccu":
								finalurl = "http://www.refworks.com/express/ExpressImport.asp" + refworksurl;
								break;
							case "unc":
								finalurl = "http://www.refworks.com.libproxy.lib.unc.edu/express/ExpressImport.asp" + refworksurl;
								break;
							case "ncsu":
								// callback url must be double-encoded to survive ncsu proxy scripts
								finalurl = "http://www.lib.ncsu.edu/cgi-bin/proxy.pl?server=www.refworks.com/express/ExpressImport.asp" + baseurl + encodeURIComponent(encodeURIComponent(callbackurl));
								break;
							case "ris":
								if (id == "markeditems")
									finalurl = "search" + searchString+"&output-format=export&export-option=ris";
								else finalurl = "search?R="+id+"&output-format=export&export-option=ris";
								document.location = finalurl;
								return;
								break;
						}
						if (finalurl != null) {
							window.open(finalurl,'RefworksMain','resizable=yes,width=900,height=600, top=10, left=10');
						}
					}
				}
			
			}
			
		});
	}
}

function generateLightBox(className, optionsHash) {
	if (className != null) {
		var targetLink = $("." + className + " a"), targetSrc = targetLink.attr("href");
		targetLink.click(function(e){
			var dialogContent = $("<img src='" + targetSrc + "'/>");
			dialogContent.load(function(){
				$(this).dialog({
					height : 'auto',
					width: 'auto',
					modal: true,
					dialogClass: "image_popup",
					show: {effect: 'fade', duration: 300},
					open: function() {
						var self = this;
						$('.ui-widget-overlay').add(self).bind('click', function() {
							dialogContent.dialog('close');
							return false;
						});
					}
				});
			});
			return false;
		});
	}
}

$(document).ready(function() {
	generatePopUpBox(".emaillink"); // includes email and sms links
	generatePopUpBox(".course_reserves_link", 580, 500);
	activateEmailForm("emailform");
	activatePrintLink("printlink");
	activateEADLink("eadlink");
	activateExportSelect("exportform");
	$(".reservesContacts").live("change", function(){
		if ($(this).val().indexOf("ul|") == 0 || $(this).val().indexOf("sils|") == 0){
			$("input.loan_period_1day").attr("disabled", false);
			$("span.loan_period_1day").removeClass("disabled");
		} else {
			$("input.loan_period_1day").attr("disabled", true);
			$("span.loan_period_1day").addClass("disabled");
		}
	}).trigger("change");
});