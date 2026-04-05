# Blueprint-to-Blueprint Implementation Plan

## Overview
This document outlines the step-by-step implementation sequence for the blueprint-to-blueprint feature that allows blueprints to copy entries from other blueprints.

## Implementation Sequence

### Phase 1: Backend Foundation

#### Step 1: Update Blueprint Edit View
**File**: `vgsite/timsy/views/blueprint_views.py`
- Add available blueprints to context (exclude current blueprint)
- Filter blueprints: `active=True`, exclude current blueprint ID
- Ensure context includes blueprint data for JavaScript consumption

**Implementation**:
```python
# In blueprint_edit view function
available_blueprints = Blueprint.objects.filter(
    active=True
).exclude(id=blueprint_id).select_related('importance')

context = {
    # ... existing context ...
    'available_blueprints': available_blueprints,
}
```

#### Step 2: Verify API Endpoint Functionality
**File**: Existing `/timsy/api/blueprints/{blueprint_id}/entries/` endpoint
- Test that blueprint entries API returns proper JSON format
- Ensure all required fields are included:
  - duration, place, abbreviation, description, parent, importance, urgency
- Verify start_time calculation and formatting

**Testing**: Use browser dev tools or test the API endpoint directly

### Phase 2: Template Structure

#### Step 3: Modify Blueprint Edit Template
**File**: `vgsite/timsy/templates/blueprint_edit.html`
- Add flex layout container around existing content
- Create blueprint panel div structure
- Maintain existing template inheritance

**Implementation**:
```html
{% extends "editor.html" %}

{% block form_content %}
<div style="display: flex; gap: 20px;">
    <div style="flex: 1;">
        <!-- Existing blueprint table content -->
        {{ block.super }}
    </div>
    <div style="width: 300px;">
        <div class="blueprint-panel">
            <h4>Available Blueprints</h4>
            <div id="blueprint-list-for-blueprint">
                <!-- Populated by JavaScript -->
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Phase 3: JavaScript Foundation

#### Step 4: Copy Blueprint Panel JavaScript
**File**: `vgsite/timsy/templates/blueprint_edit.html` (JavaScript section)
- Copy relevant functions from `daily_plan_edit.html`
- Adapt variable names for blueprint context
- Create base function structure

**Functions to create**:
```javascript
function updateBlueprintPanelForBlueprint()
function calculateFirstEmptyRowInBlueprint()
function checkBlueprintCompatibility(blueprint)
function addBlueprintEntriesToBlueprint(blueprintId, startRowIndex)
```

#### Step 5: Implement Compatibility Checking
**File**: Same as Step 4
- Implement `checkBlueprintCompatibility(blueprint)` function
- Add logic for:
  - Current blueprint exclusion
  - Active status checking
  - Start time matching
- Handle visual states (green/gray backgrounds)

**Implementation**:
```javascript
function checkBlueprintCompatibility(blueprint) {
    if (blueprint.id === currentBlueprintId) {
        return { compatible: false, reason: 'current' };
    }
    
    if (!blueprint.active) {
        return { compatible: false, reason: 'inactive' };
    }
    
    const firstEmptyRowTime = calculateFirstEmptyRowTime();
    
    if (blueprint.start_time === firstEmptyRowTime) {
        return { compatible: true, reason: 'match' };
    } else {
        return { 
            compatible: false, 
            reason: 'time_mismatch',
            expected: firstEmptyRowTime,
            actual: blueprint.start_time
        };
    }
}
```

### Phase 4: Core Functionality

#### Step 6: Implement Entry Copying Mechanism
**File**: Same as Step 4
- Create `addBlueprintEntriesToBlueprint(blueprintId, startRowIndex)` function
- Handle AJAX call to fetch blueprint entries
- Implement entry insertion logic starting from first empty row
- Use existing `createNewRow()` function for dynamic row creation

**Implementation**:
```javascript
function addBlueprintEntriesToBlueprint(blueprintId, startRowIndex) {
    fetch(`/timsy/api/blueprints/${blueprintId}/entries/`)
        .then(response => response.json())
        .then(entries => {
            entries.forEach((entry, index) => {
                const rowIndex = startRowIndex + index;
                // Ensure row exists
                ensureRowExists(rowIndex);
                // Copy entry data to form fields
                copyEntryToRow(entry, rowIndex);
            });
            // Recalculate start times
            recalculateStartTimes(startRowIndex);
            // Update panel
            updateBlueprintPanelForBlueprint();
        });
}
```

#### Step 7: Add Start Time Calculation
**File**: Same as Step 4
- Calculate sequential start times for copied entries
- Update subsequent entry start times
- Maintain HH:MM format consistency

**Implementation**:
```javascript
function recalculateStartTimes(fromRowIndex) {
    // Calculate start times based on previous entries
    // Update all subsequent rows
    // Maintain time format consistency
}
```

### Phase 5: UI Integration

#### Step 8: Panel Population and Updates
**File**: Same as Step 4
- Populate blueprint list with available blueprints
- Show blueprint names, start times, entry counts
- Implement real-time panel updates

**Implementation**:
```javascript
function updateBlueprintPanelForBlueprint() {
    const panelDiv = document.getElementById('blueprint-list-for-blueprint');
    const availableBlueprints = {{ available_blueprints|safe }};
    
    panelDiv.innerHTML = '';
    availableBlueprints.forEach(blueprint => {
        const compatibility = checkBlueprintCompatibility(blueprint);
        const blueprintDiv = createBlueprintDiv(blueprint, compatibility);
        panelDiv.appendChild(blueprintDiv);
    });
}
```

#### Step 9: Event Handlers and Interactions
**File**: Same as Step 4
- Add click handlers for blueprint selection
- Implement visual feedback for enabled/disabled states
- Add hover effects and user interaction cues

### Phase 6: Validation and Error Handling

#### Step 10: Implement Validation
**File**: Same as Step 4
- Start time compatibility checking
- Blueprint existence verification
- Error message display for time mismatches

#### Step 11: User Feedback
**File**: Same as Step 4
- Success messages when blueprints are applied
- Error messages for incompatible blueprints
- Visual updates reflecting copied entries

### Phase 7: Final Integration

#### Step 12: Testing and Refinement
- Test with various blueprint combinations
- Verify form submission works with copied entries
- Ensure no conflicts with existing functionality
- Test edge cases (empty blueprints, large blueprints)

#### Step 13: Performance Optimization
- Optimize DOM manipulation during entry copying
- Ensure smooth real-time panel updates
- Test performance with larger blueprints

## Key Dependencies

### Critical Path
1. **Phase 1 must complete first** - Backend provides the data foundation
2. **Phase 2 creates the UI structure** - Needed before JavaScript can populate it
3. **Phase 3-4 can be developed in parallel** - Core JavaScript functionality
4. **Phase 5-6 build on Phase 3-4** - UI integration requires core functions
5. **Phase 7 integrates everything** - Final testing and optimization

### Files Modified
- `vgsite/timsy/views/blueprint_views.py` - Add available blueprints context
- `vgsite/timsy/templates/blueprint_edit.html` - Add panel UI and JavaScript

### Testing Strategy
- **Incremental testing** after each phase
- **Manual testing** with browser dev tools
- **Form submission verification** after core functionality
- **Cross-browser compatibility** in final phase

## Success Indicators

### Phase Completion Criteria
- **Phase 1**: Available blueprints appear in template context
- **Phase 2**: Blueprint panel structure visible in browser
- **Phase 3**: JavaScript functions defined and callable
- **Phase 4**: Blueprint entries can be fetched and copied
- **Phase 5**: Panel shows blueprints with correct visual states
- **Phase 6**: Error handling works for incompatible blueprints
- **Phase 7**: Feature works end-to-end without issues

### Final Success
- Users can copy entries from any compatible blueprint
- Start times calculate correctly
- Form submission saves copied entries
- No breaking changes to existing functionality 