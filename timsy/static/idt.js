function calculateTotalDuration() {
    let totalHours = 0;
    let totalMinutes = 0;
    const rows = document.querySelectorAll('.record-row');
    
    rows.forEach(row => {
        const durationInput = row.querySelector('input[id^="id_duration"]');
        if (durationInput && durationInput.value) {
            const durationParts = durationInput.value.split(':');
            if (durationParts.length === 2) {
                const hours = parseInt(durationParts[0], 10) || 0;
                const minutes = parseInt(durationParts[1], 10) || 0;
                totalHours += hours;
                totalMinutes += minutes;
            } else if (durationParts.length === 1) {
                // Handle case where only minutes are provided
                totalMinutes += parseInt(durationParts[0], 10) || 0;
            }
        }
    });

    // Convert excess minutes to hours
    totalHours += Math.floor(totalMinutes / 60);
    totalMinutes = totalMinutes % 60;

    // Update display
    document.getElementById('total-duration').textContent = 
        `${String(totalHours).padStart(2, '0')}:${String(totalMinutes).padStart(2, '0')}`;
    
    // Calculate remaining time
    let remainingHours = 24 - totalHours;
    let remainingMinutes = 0;
    
    if (totalMinutes > 0) {
        remainingHours -= 1;
        remainingMinutes = 60 - totalMinutes;
    }

    document.getElementById('remaining-time').textContent = 
        `${String(remainingHours).padStart(2, '0')}:${String(remainingMinutes).padStart(2, '0')}`;

    // Show warning if total duration exceeds 24 hours
    const warning = document.getElementById('duration-warning');
    if (totalHours >= 24 && totalMinutes > 0) {
        warning.style.display = 'inline';
    } else {
        warning.style.display = 'none';
    }

    return { hours: totalHours, minutes: totalMinutes };
}

function populateSelectOptions(index) {
    // Populate parent options
    const parentSelect = document.getElementById(`id_parent${index}`);
    const parentSelected = parentSelect.dataset.selected;
    // Add empty option first
    const emptyOption = document.createElement('option');
    emptyOption.value = '';
    emptyOption.textContent = '---------';
    parentSelect.appendChild(emptyOption);
    // Add other options
    selectOptions.parent.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option.value;
        optionElement.textContent = option.text;
        if (option.value === parentSelected) {
            optionElement.selected = true;
        }
        parentSelect.appendChild(optionElement);
    });

    // Populate importance options
    const importanceSelect = document.getElementById(`id_importance${index}`);
    const importanceSelected = importanceSelect.dataset.selected;
    // Add empty option first
    const emptyOption2 = document.createElement('option');
    emptyOption2.value = '';
    emptyOption2.textContent = '---------';
    importanceSelect.appendChild(emptyOption2);
    // Add other options
    selectOptions.importance.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option.value;
        optionElement.textContent = option.text;
        if (option.value === importanceSelected) {
            optionElement.selected = true;
        }
        importanceSelect.appendChild(optionElement);
    });

    // Populate urgency options
    const urgencySelect = document.getElementById(`id_urgency${index}`);
    const urgencySelected = urgencySelect.dataset.selected;
    // Add empty option first
    const emptyOption3 = document.createElement('option');
    emptyOption3.value = '';
    emptyOption3.textContent = '---------';
    urgencySelect.appendChild(emptyOption3);
    // Add other options
    selectOptions.urgency.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option.value;
        optionElement.textContent = option.text;
        if (option.value === urgencySelected) {
            optionElement.selected = true;
        }
        urgencySelect.appendChild(optionElement);
    });
}

function deleteRow(index) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (row) {
        // Instead of removing the row, clear its values
        const inputs = row.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            input.value = '';
        });
        const selects = row.querySelectorAll('select');
        selects.forEach(select => {
            select.selectedIndex = 0;
        });
        updateAllStartTimes();
        calculateTotalDuration();
    }
}

function updateAllStartTimes() {
    const rows = document.querySelectorAll('.record-row');
    let currentTime = new Date();
    currentTime.setHours(0, 0, 0, 0);

    rows.forEach((row, index) => {
        const startInput = row.querySelector('input[id^="id_start"]');
        const durationInput = row.querySelector('input[id^="id_duration"]');
        
        if (startInput) {
            startInput.value = `${String(currentTime.getHours()).padStart(2, '0')}:${String(currentTime.getMinutes()).padStart(2, '0')}`;
        }

        if (durationInput && durationInput.value) {
            const [hours, minutes] = durationInput.value.split(':').map(Number);
            currentTime.setHours(currentTime.getHours() + (hours || 0));
            currentTime.setMinutes(currentTime.getMinutes() + (minutes || 0));
        }
    });

    calculateTotalDuration();
}

function focusFirstEmptyRecord() {
    const rows = document.querySelectorAll('.record-row');
    for (let i = 0; i < rows.length; i++) {
        const durationInput = rows[i].querySelector('input[id^="id_duration"]');
        if (durationInput && !durationInput.value) {
            // Update start time based on previous record
            if (i > 0) {
                const prevRow = rows[i - 1];
                const prevStartInput = prevRow.querySelector('input[id^="id_start"]');
                const prevDurationInput = prevRow.querySelector('input[id^="id_duration"]');
                
                if (prevStartInput && prevDurationInput && prevDurationInput.value) {
                    const [prevHours, prevMinutes] = prevStartInput.value.split(':').map(Number);
                    const [durationHours, durationMinutes] = prevDurationInput.value.split(':').map(Number);
                    
                    let newHours = prevHours + durationHours;
                    let newMinutes = prevMinutes + durationMinutes;
                    
                    if (newMinutes >= 60) {
                        newHours += Math.floor(newMinutes / 60);
                        newMinutes = newMinutes % 60;
                    }
                    
                    const startInput = rows[i].querySelector('input[id^="id_start"]');
                    if (startInput) {
                        startInput.value = `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
                    }
                }
            }
            
            // Set focus to the duration input
            durationInput.focus();
            break;
        }
    }
}

// Add event listeners for duration changes
document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('records-table');
    if (table) {
        table.addEventListener('input', function(e) {
            if (e.target.id.startsWith('id_duration')) {
                calculateTotalDuration();
            }
        });
        
        // Initial calculation
        calculateTotalDuration();

        // Focus on first empty record
        focusFirstEmptyRecord();
    }
}); 