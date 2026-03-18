function createRequest() {
  let request;
  try {
    request = new XMLHttpRequest();
  } catch (tryMS) {
    try {
      request = new ActiveXObject("Msxml2.XMLHTTP");
    } catch (otherMS) {
      try {
        request = new ActiveXObject("Microsoft.XMLHTTP");
      } catch (failed) {
          request = null;
      }
    }
  }
  return request;
}

function showTime(element_id, hours, minutes){
   if (minutes >= 60) {
     minutes -= 60;
     hours = hours + 1;
    }
    hours = hours.toString();
    if (minutes < 10) {
      minutes = "0" + minutes.toString();
    }
    else {
      minutes = minutes.toString();
    }
  document.getElementById(element_id).value = hours + ":" + minutes;
}

function formatTimeField(element_id){
   const time = document.getElementById(element_id).value.split(":");
   const hours = parseInt(time[0]);
   const minutes = parseInt(time[1]);
   showTime(element_id, hours, minutes);
}

