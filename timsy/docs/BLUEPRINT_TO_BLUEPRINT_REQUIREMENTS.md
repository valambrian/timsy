# Blueprint-to-Blueprint Application Feature Requirements

## Overview
Extend the blueprint editor to allow blueprints to copy entries from other blueprints, similar to how daily plans can apply blueprints. This enables blueprint composition and reusability through simple entry copying without tracking origins.

## Functional Requirements

### 1. User Interface Integration

#### 1.1 Blueprint Panel Addition
- **Location**: Add blueprint panel to `blueprint_edit.html` on the right side
- **Layout**: Mirror the daily plan editor layout with flex display
- **Panel specifications**:
  - **Width**: 300px (consistent with daily plan)
  - **Title**: "Available Blueprints"
  - **Styling**: Match existing blueprint panel styling from daily plan
  - **Position**: Right side of the form, adjacent to main blueprint table

#### 1.2 Blueprint Selection Interface
- **Available blueprints list**: Show all active blueprints except current blueprint
- **Visual states**:
  - **Enabled**: Green background, clickable (start time matches)
  - **Disabled**: Gray background, not clickable (time mismatch)
- **Blueprint display format**:
  - **Blueprint name**: Bold text
  - **Start time**: Smaller gray text showing "Starts: HH:MM"
  - **Entry count**: Show number of entries (optional)

#### 1.3 Real-time Panel Updates
- **Auto-refresh**: Update panel when blueprint entries change
- **Start time tracking**: Recalculate available blueprints when first empty row changes
- **Status updates**: Reflect blueprint availability as user modifies current blueprint

### 2. Blueprint Application Logic

#### 2.1 Application Mechanism
- **Trigger**: Click on enabled blueprint in panel
- **API call**: Fetch blueprint entries via existing `/timsy/api/blueprints/{blueprint_id}/entries/` endpoint
- **Entry insertion**: Add fetched entries starting from first empty row
- **Field mapping**: Copy all entry fields (duration, place, abbreviation, description, parent, importance, urgency)
- **No origin tracking**: Copied entries become independent, no connection to source blueprint

#### 2.2 Start Time Calculation
- **Base time**: Use start time of first empty row in current blueprint
- **Sequential calculation**: Each applied entry's start time = previous entry start + previous entry duration
- **Time formatting**: Maintain HH:MM format consistency
- **Automatic updates**: Recalculate all subsequent start times after application

#### 2.3 Row Management
- **Sufficient rows**: Ensure enough empty rows for applied entries + 5 buffer rows
- **Dynamic creation**: Add new rows if needed using existing `createNewRow()` function
- **Row indexing**: Maintain proper form field naming (duration0, duration1, etc.)

### 3. Blueprint Selection Logic

#### 3.1 Available Blueprints
- **Include**: All active blueprints
- **Exclude**: Only the current blueprint being edited
- **No dependency tracking**: All blueprints are available regardless of previous applications
- **Time compatibility**: Filter by start time matching first empty row

#### 3.2 Validation Rules
- **Start time matching**: Blueprint start time must match first empty row time
- **Blueprint existence**: Target blueprint must exist and be active

### 4. Backend Requirements

#### 4.1 API Endpoints
- **Existing endpoint**: Reuse `/timsy/api/blueprints/{blueprint_id}/entries/`
- **Filter logic**: Exclude only current blueprint from available blueprints list
- **Error handling**: Return appropriate errors for time mismatches or capacity issues

#### 4.2 Blueprint Context in Views
- **Blueprint edit view**: Pass available blueprints to template
- **JSON serialization**: Ensure blueprint data is properly formatted for JavaScript
- **Simple filtering**: Only exclude current blueprint ID

### 5. Frontend Implementation

#### 5.1 JavaScript Integration
- **Copy blueprint panel logic** from `daily_plan_edit.html`
- **Modify for blueprint context**: Adapt functions to work with blueprints instead of daily plans
- **Event handlers**: Set up click handlers for blueprint selection
- **AJAX calls**: Handle asynchronous blueprint entry fetching

#### 5.2 Key JavaScript Functions
```javascript
// Adapt from daily_plan_edit.html
function updateBlueprintPanelForBlueprint()
function addBlueprintEntriesToBlueprint(blueprintId, startRowIndex)
function checkBlueprintCompatibility(blueprint)
function calculateFirstEmptyRowInBlueprint()
```

**checkBlueprintCompatibility(blueprint) Logic:**
```javascript
function checkBlueprintCompatibility(blueprint) {
    // 1. Exclude current blueprint being edited
    if (blueprint.id === currentBlueprintId) {
        return { compatible: false, reason: 'current' };
    }
    
    // 2. Check if blueprint is active
    if (!blueprint.active) {
        return { compatible: false, reason: 'inactive' };
    }
    
    // 3. Get start time of first empty row in current blueprint
    const firstEmptyRowTime = calculateFirstEmptyRowTime();
    
    // 4. Compare with blueprint's start time
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

**Return Values:**
- `compatible: true` → Show blueprint with green background (clickable)
- `compatible: false` → Show blueprint with gray background (disabled)
- `reason` field helps determine the visual state and error messages

#### 5.3 DOM Manipulation
- **Panel injection**: Add blueprint panel to blueprint edit template
- **Row creation**: Ensure new rows are properly created and indexed
- **Form field management**: Maintain proper form field naming and validation

### 6. Template Requirements

#### 6.1 Blueprint Edit Template Updates
- **Add blueprint panel**: Include blueprint selection panel HTML
- **Flex layout**: Modify layout to accommodate panel (main content + sidebar)
- **JavaScript inclusion**: Add blueprint panel JavaScript logic
- **CSS styling**: Include blueprint panel styles

#### 6.2 Template Structure
```html
<div style="display: flex; gap: 20px;">
    <div style="flex: 1;">
        <!-- Existing blueprint table -->
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
```

### 7. Validation Requirements

#### 7.1 Pre-Application Validation
- **Start time compatibility**: Ensure blueprint start time matches insertion point
- **Blueprint existence**: Confirm target blueprint exists and is active

#### 7.2 Error Handling
- **User-friendly messages**:
  - "Blueprint start time (HH:MM) doesn't match current position (HH:MM)"
  - "Blueprint not found or inactive"

### 8. User Experience Requirements

#### 8.1 Visual Feedback
- **Success confirmation**: Brief success message when blueprint applied
- **Error display**: Non-intrusive error messages
- **Visual updates**: Immediate UI updates reflecting applied entries

#### 8.2 Interaction Flow
1. **User opens blueprint editor**
2. **Blueprint panel loads** showing available blueprints
3. **User modifies blueprint** → panel updates in real-time
4. **User clicks available blueprint** → entries are copied
5. **Start times recalculate** → subsequent entries update
6. **Panel refreshes** → shows current state

### 9. Performance Considerations

#### 9.1 UI Responsiveness
- **Asynchronous operations**: All blueprint applications happen async
- **Non-blocking UI**: Interface remains responsive during operations
- **Progressive enhancement**: Core functionality works without JavaScript
- **Debounced updates**: Limit frequency of panel updates

#### 9.2 Entry Copying Performance
- **Efficient copying**: Minimize DOM manipulation during entry insertion
- **Batch operations**: Copy multiple entries efficiently
- **Memory management**: Clean up temporary data after copying

### 10. Business Logic Requirements

#### 10.1 Blueprint Composition Strategy
- **Additive composition**: Applied blueprint entries are added, not replaced
- **Insertion point**: Always insert at first empty row
- **Time continuity**: Maintain chronological sequence of entries
- **No conflicts**: Insertion at empty rows prevents data conflicts
- **Independent entries**: Copied entries have no connection to source blueprint

#### 10.2 Blueprint Reusability Patterns
- **Template blueprints**: Small, focused blueprints for common sequences
- **Composite blueprints**: Complex blueprints built from copied entries
- **Modular design**: Encourage creation of reusable blueprint components
- **Copy-and-modify**: Users can copy entries and then customize them

### 11. Integration Requirements

#### 11.1 Existing Functionality Preservation
- **No breaking changes**: All existing blueprint functionality must continue working
- **Form submission**: Blueprint saving logic remains unchanged
- **Drag and drop**: Existing drag/drop functionality must work with copied entries
- **Validation**: Existing blueprint validation rules still apply

#### 11.2 Daily Plan Integration
- **Consistency**: Blueprint-to-blueprint behavior should match daily plan blueprint application
- **Shared code**: Reuse JavaScript functions where possible
- **Similar UX**: User experience should be familiar to daily plan users

### 12. Success Criteria

#### 12.1 Functional Success
- **Blueprints can copy entries from other blueprints** without data corruption
- **Start times calculate correctly** for all copied entries
- **Form submission works** with copied blueprint entries
- **Multiple applications work** without conflicts

#### 12.2 User Experience Success
- **Intuitive interface** that mirrors daily plan experience
- **Real-time feedback** shows available blueprints accurately
- **Fast performance** with responsive UI during operations
- **Clear error handling** guides users through issues

#### 12.3 Technical Success
- **No breaking changes** to existing functionality
- **Maintainable code** that follows established patterns
- **Scalable architecture** that handles growth in blueprint usage
- **Simple implementation** without complex dependency tracking 