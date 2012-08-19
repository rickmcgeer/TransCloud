/* Have to see what the errors are before I can do anything meaningful here...*/
function cleanUpResponse(responseString) {
    return responseString;
}

/*
 * city = "name": "<cityName>", 
 * "processedTime": "<processed_time>",
 * "serverName": "<serverName>",
 * "imageURL":"<image_url>"
 */

function loadCity(city, index) {
    var nameID = "cityName_" + index;
    var nameElement = document.getElementById(nameID);
    nameElement.innerHTML = city.name;
    var pTimeID = "process_time_" + index;
    var pTimeElement = document.getElementById(pTimeID);
    pTimeElement.innerHTML = city.processedTime;
    var serverNameID = "serverName_" + index;
    var serverNameElement = document.getElementById(serverNameID);
    serverNameElement.innerHTML = city.serverName;
    var urlID = "city_image_" + index;
    var urlElement = document.getElementById(urlID);
    urlElement.innerHTML = '<img src="' + city.imageURL +'"/>';
}


/*
 * Get the next batch of 10 cities processed and display them
 */

function getLast10Cities() {
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
	        [
		{"name": "<cityName>", "processedTime": "<processed_time>", "serverName": "<serverName>", "imageURL":"<image_url>"}
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
    xmlhttp.open("GET", "cgi-bin/last10Cities.py", false);
    xmlhttp.send();
}

/*
 * Get the total number of cities processed
 */

function getTotalCitiesProcessed() {
    var xmlhttp;
    if (window.XMLHttpRequest) {// code for IE7+, Firefox, Chrome, Opera, Safari
       xmlhttp=new XMLHttpRequest();
     } else {// code for IE6, IE5
       xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
     }
     xmlhttp.onreadystatechange=function() {
         if (xmlhttp.readyState == 1) return;
         if ((xmlhttp.readyState == 4) &&  (xmlhttp.status==200)) {
	     var responseData=eval("("+xmlhttp.responseText+")");
	     /* responseData is of the form:
	        
		{"total": number}
	
	     */
	     var elt = document.getElementById("numCities");
             numCities.innerHTML = responseData.total;
         } else {
	     alert("Error occured getting total Number of cities");
	 }
     }
    xmlhttp.open("GET", "cgi-bin/totalCities.py", false);
    xmlhttp.send();
}