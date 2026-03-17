function setNextStartField(row, total) {
  var current_id = parseInt(row, 10);
  var next_id = current_id + 1;
  var start = document.getElementById("id_start" + current_id).value.split(":");
  var duration = document.getElementById("id_duration" + current_id).value.split(":");
  var hours = 0;
  var minutes = 0;
  if (isNaN(duration[1])) { // no hours entered, just minutes
    if (document.getElementById("id_duration" + current_id).value == "") {
      duration[0] = 0;
    }
    hours = parseInt(start[0], 10);
    minutes = parseInt(start[1], 10) + parseInt(duration[0], 10);
    showTime("id_duration" + current_id, 0, parseInt(duration[0], 10));
  }
  else {
    hours = parseInt(start[0], 10) + parseInt(duration[0], 10);
    minutes = parseInt(start[1], 10) + parseInt(duration[1], 10);
   }
  if (current_id < parseInt(total, 10)) {
    showTime("id_start" + next_id, hours, minutes);
  }  
}

function start() {
  getLastActivity();
}

function checkAbbreviation(row, total) {
  var abbreviation = document.getElementById("id_abbreviation" + parseInt(row, 10)).value;
  request = createRequest();
  if (request == null) {
    alert("Unable to create request");
    return;
  }
  var url = "/timsy/requests/activity/" + abbreviation;
  request.open("GET", url, true);
  request.onreadystatechange = function() { displayActivityDetail(row, total); };
  request.send(null);
}

function displayActivityDetail(row, total) {
  if (request.readyState == 4) {
    if (request.status == 200) {
      var record = eval('(' + request.responseText + ')');
      if (record.description) {
        document.getElementById("id_description" + row).value = record.description;
        var parent = document.getElementById("id_parent" + row);
        for (var index=0; index < parent.length; index = index + 1) {
          if (parent.options[index].text == record.parent) {
            parent.selectedIndex = index;
          }
        } 
        var importance = document.getElementById("id_importance" + row);
        for (var index=0; index < importance.length; index = index + 1) {
          if (importance.options[index].text == record.importance) {
            importance.selectedIndex = index;
          }
        } 
        var urgency = document.getElementById("id_urgency" + row);
        for (var index=0; index < urgency.length; index = index + 1) {
          if (urgency.options[index].text == record.urgency) {
            urgency.selectedIndex = index;
          }
        } 
        var next_id = row + 1;
        document.getElementById("id_duration" + next_id).focus();
      }
    }
  }
}

function getLastActivity() {
  request = createRequest();
  if (request == null) {
    alert("Unable to create request");
    return;
  }
  var url = "/timsy/requests/last";
  request.open("GET", url, true);
  request.onreadystatechange = displayLastActivity;
  request.send(null);
}

function displayLastActivity() {
  if (request.readyState == 4) {
    if (request.status == 200) {
      var record = eval('(' + request.responseText + ')');
      document.getElementById("date").innerHTML = record.date;
      showTime("id_start0", record.start_hour, record.start_minute);
      showTime("id_duration0", record.duration_hour, record.duration_minute);
      document.getElementById("id_place0").value = record.place;
      document.getElementById("id_abbreviation0").value = record.abbreviation;
      document.getElementById("id_description0").value = record.description;
      document.getElementById("id_parent0").value = record.parent;
      document.getElementById("id_importance0").value = record.importance;
      document.getElementById("id_urgency0").value = record.urgency;
      setNextStartField(0, 1);
      document.getElementById("id_duration1").focus();
    }
  }
}

window.onload=start
