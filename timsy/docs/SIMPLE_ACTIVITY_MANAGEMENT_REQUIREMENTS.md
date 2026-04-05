# Simple Activity Management Feature Requirements

## Overview
Create a simplified activity management interface with two pages:
1. A top-level parents listing page
2. An activity editor page for each parent (similar to existing editor.html pattern)

## Functional Requirements

### 1. Top-Level Parents List Page
- **URL Pattern**: `/parents/top/`
- **Functionality**:
  - Display all top-level parents (where `id` is exactly 2 characters long)
  - Use the existing `Parent.get_direct_children("ALL")` method
  - Show parent descriptions as clickable links
  - Links should navigate to `/activities/<parent_id>/`
  - Order by `sort_order` field
  - Table format with the following columns

#### Table Columns (in order):
1. **ID** - Parent ID (primary key)
2. **Sort Order** - Display order for the parent
3. **Description** - Parent description (clickable link to activity editor)
4. **Importance** - Importance level of the parent
5. **Active** - Whether the parent is currently active ("Active" or "Inactive")

### 2. Activity Editor Page
- **URL Pattern**: `/activities/<slug:parent_id>/`
- **Functionality**:
  - Display page header with current parent description
  - **Direct Children Section** (if any exist):
    - Query direct children using `Parent.get_direct_children(current_parent_id)`
    - Display in table format with same columns as top parents list
    - Show only if direct children exist
    - Child descriptions are clickable links to their respective activity editors
  - **Activities Section**:
    - Display all activities where `activity.parent_id = parent.id`
    - Show activities in a table format with editable fields
    - Include 5 empty rows at the bottom for new activities
    - Parent field should be pre-selected to current parent for new rows
    - If user changes parent value, only display the new value (no other actions)
    - Form submission should redirect back to the same page
    - Follow the existing `editor.html` template pattern

#### Direct Children Table Columns (in order):
1. **ID** - Child parent ID (primary key)
2. **Sort Order** - Display order for the child parent
3. **Description** - Child parent description (clickable link to activity editor)
4. **Importance** - Importance level of the child parent
5. **Active** - Whether the child parent is currently active ("Active" or "Inactive")

#### Activities Table Columns (in order):
1. **Activity ID** - readonly field, auto-populated for existing activities, empty for new rows
2. **Sort Order** - editable integer field
3. **Abbreviation** - editable text field (max 10 chars)
4. **Description** - editable text field (max 200 chars)
5. **Parent** - dropdown list, pre-selected to current parent (changeable like other edit forms)
6. **Importance** - dropdown list (same as other templates)
7. **Urgency** - dropdown list (same as other templates)

## Technical Requirements

### 1. URL Configuration
```python
# Add to timsy/urls.py
path('parents/top/', activity_views.top_parents_list, name='top_parents_list'),
path('activities/<slug:parent_id>/', activity_views.activity_editor, name='activity_editor'),
```

### 2. View Functions
- Create `activity_views.py` in the views directory
- Follow existing patterns from `daily_plan_views.py`
- Use function-based views for consistency

#### top_parents_list view:
- Query: `Parent.get_direct_children("ALL")`
- Template: `top_parents_list.html`
- Context: `{'parents': top_level_parents}`

#### activity_editor view:
- Query activities: `Activity.objects.filter(parent_id=parent_id).order_by('sort_order', 'id')`
- Query direct children: `Parent.get_direct_children(parent_id)` with `select_related('importance')`
- Template: `activity_editor.html` (extends `editor.html`)
- Context: Include form data similar to `daily_plan_edit.html` plus children data
- Context variables:
  - `activities`: filtered activities for the parent
  - `parent`: current parent object
  - `children`: direct children of current parent (empty queryset if none)
  - `form`: form data with parent_list, importance_list, urgency_list
- POST handling: Validate form but redirect without saving

### 3. Templates

#### top_parents_list.html:
- Extend `base.html`
- Table format displaying parent information
- Columns: ID, Sort Order, Description, Importance, Active
- Description column contains clickable links to `/activities/<parent_id>/`
- Include page title
- Use consistent table styling with other templates

#### activity_editor.html:
- Extend `editor.html` (following existing pattern)
- Override `form_content` block
- Include table with all activity fields
- Add 5 empty rows at bottom (similar to `daily_plan_edit.html`)
- Use same dropdown patterns as existing templates
- Pre-select parent dropdown to current parent for empty rows

### 4. Form Data Structure
Follow the existing pattern from `daily_plan_edit.html`:
```python
form = {
    'parent_list': [(p.id, str(p)) for p in Parent.objects.filter(active=True)],
    'importance_list': [(i.id, str(i)) for i in Importance.objects.all()],
    'urgency_list': [(u.id, str(u)) for u in Urgency.objects.all()],
}
```

## Data Requirements

### 1. Top-Level Parents Query
- Use existing `Parent.get_direct_children("ALL")` method
- Include related importance data: `select_related('importance')`
- This returns parents with 2-character ids
- Order by `sort_order`
- Display columns: id, sort_order, description, importance.description, active

### 2. Activities Query
- Filter: `Activity.objects.filter(parent_id=parent_id)`
- Order: `order_by('sort_order', 'id')`
- Include related objects: `select_related('parent', 'importance', 'urgency')`

### 3. Form Field Naming
Follow existing pattern from `daily_plan_edit.html`:
- `activity_id{i}` - readonly (empty for new rows)
- `sort_order{i}` - editable
- `abbreviation{i}` - editable
- `description{i}` - editable
- `parent{i}` - dropdown (pre-selected to current parent)
- `importance{i}` - dropdown
- `urgency{i}` - dropdown

## UI/UX Requirements

### 1. Top-Level Parents Page
- Page title: "Activity Management - Top Level Categories" (use h3 tag)
- Table format with headers: ID, Sort Order, Description, Importance, Active
- Description column entries are clickable links to activity editor
- Table should be sortable by columns (optional enhancement)
- Use consistent table styling with other pages in the application
- Table should include `border="1"` attribute and `class="table table-striped"` for consistent styling
- No breadcrumb navigation

### 2. Activity Editor Page
- Page title: "Activities for [Parent Description]" (use h3 tag)
- No breadcrumb navigation
- **Page Layout**:
  - **Direct Children Section** (conditionally displayed):
    - Section header: "Subcategories" (h4 tag)
    - Table with same styling as top parents list
    - Only displayed if `children` queryset has results
    - Child description links navigate to `/activities/<child_id>/`
  - **Activities Section**:
    - Section header: "Activities" (h4 tag)  
    - Table with headers for all columns
    - Activity ID column should be visually distinct (readonly styling)
    - 5 empty rows at bottom with same styling as existing rows
    - Empty rows have parent pre-selected to current parent
    - Save button (even though it doesn't save yet)

### 3. Styling
- Follow existing template patterns
- Use same CSS classes as `daily_plan_edit.html`
- Tables should use `class="table table-striped"` and `border="1"` for consistent styling with other pages
- Readonly fields should use existing readonly styling from `editor.html`
- Dropdown styling should match existing dropdowns
- Page headers should use h3 or h4 tags for consistency with other pages in the application

## Form Behavior Requirements

### 1. Form Submission Processing
- **Method**: POST to same URL (redirect to self)
- **Validation Strategy**: Process and save each row independently
- **Row Processing**: Only process rows where abbreviation OR description field is not empty
- **Success Behavior**: Redirect back to the same activity editor page with success message
- **Error Behavior**: Stay on same page and display validation errors

### 2. Activity Validation Rules

#### 2.1 Abbreviation Uniqueness
- **Scope**: Abbreviations must be unique globally across all activities
- **Case Handling**: Convert to lowercase before validation and saving
- **Whitespace**: Leading/trailing whitespace is trimmed before validation
- **Empty Values**: Multiple activities may have empty/blank abbreviations
- **Existing Records**: If an existing activity's abbreviation is unchanged, consider it unique by default

#### 2.2 Required Fields (for processed rows)
- **Processing Trigger**: Row is processed if abbreviation OR description is not empty
- **If Processing Triggered**:
  - **Parent**: Required, must be valid parent ID
  - **Importance**: Required, must be valid importance ID  
  - **Urgency**: Required, must be valid urgency ID
- **Optional Fields**:
  - **Abbreviation**: Max 10 characters, globally unique (if not empty)
  - **Description**: Max 200 characters
  - **Sort Order**: Optional integer field
- **Read-Only Fields**:
  - **Activity ID**: Read-only, never updated for existing records
- **Cross-Field Validation**:
  - **If abbreviation is not blank**: Description must also be not blank

#### 2.3 Field Processing Rules
- Trim whitespace from all text fields before validation
- Convert abbreviations to lowercase before validation and saving
- Sort order defaults to 999 if empty

#### 2.4 Row Skipping Rules
- **Skip Row**: If both abbreviation AND description are empty/blank
- **Process Row**: If abbreviation OR description has any content

### 3. Database Save Logic

#### 3.1 Independent Processing
- **Strategy**: Each row is processed independently
- **Error Handling**: Errors in one row do not prevent saving other valid rows
- **Transaction Scope**: Each activity save is its own transaction

#### 3.2 Existing Activities (rows with Activity ID)
1. **ID Validation**:
   - If activity ID doesn't exist in database: ignore record and indicate error
2. **Abbreviation Uniqueness**:
   - If abbreviation is unchanged: consider unique (no validation needed)
   - If abbreviation is changed: check uniqueness against all other activities
3. **Change Detection**:
   - Compare all fields with current database values
   - If no changes detected: skip (no database operation)
4. **Update Logic**:
   - If changes detected and validation passes: update all fields
   - If validation fails: add to error list, don't save this record

#### 3.3 New Activities (rows without Activity ID)
1. **Abbreviation Validation**:
   - If abbreviation is not empty: check uniqueness against all existing activities
   - If abbreviation is empty: allow (multiple activities can have blank abbreviations)
2. **Required Field Validation**:
   - Validate parent, importance, urgency are provided and valid
3. **Creation Logic**:
   - If validation passes: create new activity with generated ID
   - If validation fails: add to error list, don't save this record

### 4. Error Handling & User Feedback

#### 4.1 Validation Error Display
- **Field-Level Errors**: Highlight specific fields with errors (red border)
- **Row-Level Messages**: Show error message near problematic rows
- **Row Numbers**: Include row numbers in error messages (1-based counting)

#### 4.2 Error Message Examples
- "Row 3: Abbreviation 'wk' already exists in another activity"
- "Row 7: Parent is required when abbreviation or description is provided"
- "Row 12: Invalid parent ID"
- "Row 5: Activity ID does not exist, record ignored"
- "Row 8: Description is required when abbreviation is provided"

#### 4.3 Success Feedback
- **Success Message**: "Activities saved successfully" (if any saves occurred)
- **Updated Data**: Display updated activity list with any new activities included
- **Form State**: Reset empty rows, preserve existing activity data

### 5. Form State Management

#### 5.1 POST Processing Flow
1. Process each non-empty row independently
2. For each row with errors:
   - Add error to error list
   - Preserve form data for that row
3. For each row that saves successfully:
   - Update database
   - Refresh data from database
4. After processing all rows:
   - If any saves occurred: show success message
   - If any errors occurred: display errors with field highlighting
   - Stay on same page (POST-redirect-GET pattern)

#### 5.2 Form Data Preservation
- **On Error**: Preserve user input data for rows with errors
- **On Success**: Show updated data from database for successful saves
- **Mixed Results**: Show database data for successful saves, preserve input for failed rows
- **Empty Rows**: Always show 5 empty rows at bottom

### 6. Database Consistency Rules

#### 6.1 Activity ID Generation
- **New Activities**: System generates unique activity ID
- **ID Format**: Follow existing activity ID pattern in database
- **Collision Handling**: Ensure generated IDs don't conflict with existing ones

#### 6.2 Related Data Validation
- **Parent Validation**: Ensure parent ID exists
- **Importance/Urgency**: Ensure IDs exist in respective tables
- **Foreign Key Constraints**: Rely on database constraints for data integrity

#### 6.3 Invalid Activity ID Handling
- **Detection**: Check if submitted activity ID exists in database
- **Action**: Ignore the record completely (no save attempt)
- **Error Message**: "Row X: Activity ID does not exist, record ignored"

#### 6.4 Performance Considerations
- **Activities Per Parent Limit**: Recommend keeping activities per parent under 150 to avoid Django's DATA_UPLOAD_MAX_NUMBER_FIELDS limit
- **Field Count Calculation**: Each activity uses 7 form fields (activity_id, sort_order, abbreviation, description, parent, importance, urgency)
- **Form Field Limit**: With 5 empty rows, the theoretical maximum is ~140 activities per parent before hitting Django's default 1000 field limit
- **Hierarchy Refactoring**: When a parent exceeds 100-150 activities, consider splitting into subcategories for better organization and performance

## Integration Requirements

### 1. Navigation
- Add link to top-level parents page in timsy.html
- Link text: "Activities"

### 2. Existing Functionality
- Don't modify existing Activity model or methods
- Don't interfere with existing `find_or_create()` functionality
- Maintain compatibility with daily plan creation

## Success Criteria
- Users can view top-level parents as clickable links
- Users can access activity editor for any parent
- Activity editor displays all existing activities for the parent
- Form includes 5 empty rows for new activities with parent pre-selected
- Activity ID field is empty for new rows, populated for existing activities
- Parent dropdown works like other edit forms (changeable, shows all active parents)
- Form validates properly
- Form redirects back to itself after submission
- UI follows existing template patterns and styling
- All functionality works without JavaScript (progressive enhancement)
