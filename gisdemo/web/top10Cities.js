/* Have to see what the errors are before I can do anything meaningful here...*/
function cleanUpResponse(responseString) {
    return responseString;
}

/*
 * city = "name": "<cityName>", 
 * "greenspace": "<green_value>",
 */

function loadCity(city, index) {
    var nameID = "cityName_" + index;
    var nameElement = document.getElementById(nameID);
    nameElement.innerHTML = city.name;
    var greenspaceID = "green_value_" + index;
    var greenSpaceElement = document.getElementById(greenspaceID);
    greenspaceID.innerHTML = city.greenspace;
}


/*
 * Get the next batch of 10 cities processed and display them
 */

function top10Cities() {
    var xmlhttp;

    if (window.XMLHttpRequest) {// code for IE7+, Firefox, Chrome, Opera, Safari
       xmlhttp=new XMLHttpRequest();
     } else {// code for IE6, IE5
       xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
     }
     xmlhttp.onreadystatechange=function() {
         if (xmlhttp.readyState == 1) return;
         
         if ((xmlhttp.readyState == 4) && (xmlhttp.status == 200)) {
             var jsonToEval = xmlhttp.responseText;
	     var responseData=eval(jsonToEval);
	     /* responseData is of the form:
	        [		{"name": "<cityName>", "greenspace": "<green_value>"}
		...
		]
	     */
	     for(i = 0; i < 10; i++) {
		 loadCity(responseData[i], i+1);
	     }
         } else {
	     alert("Error occured getting last 10 cities");
	 }
     }
    xmlhttp.open("GET", "cgi-bin/top10Cities.py", false);
    xmlhttp.send();
}


function refreshData() {
    top10Cities();
}
    
