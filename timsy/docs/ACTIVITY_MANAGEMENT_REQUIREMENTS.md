# Activity Management Feature Requirements

## Overview
Add CRUD (Create, Read, Update, Delete) functionality for activities that belong to a parent category, excluding the "ALL" category to keep the scope manageable.

## Current System Analysis
- **Existing Models**: Activity model already exists with relationships to Parent, Importance, and Urgency
- **Current Functionality**: Activities are created automatically via `find_or_create()` method during daily plan entry
- **Missing**: Direct activity management interface for users

## Functional Requirements

### 1. Activity List View
- **URL Pattern**: `/activities/` and `/activities/<parent_id>/`
- **Functionality**:
  - Display all activities (excluding those with parent="ALL")
  - Filter activities by parent category
  - Show activity details: abbreviation, description, parent, importance, urgency
  - Provide links to edit/delete each activity
  - Include "Create New Activity" button
  - Support sorting by sort_order, then by description

### 2. Activity Detail View
- **URL Pattern**: `/activities/<activity_id>/`
- **Functionality**:
  - Display full activity information
  - Show related information (parent, importance, urgency details)
  - Provide edit and delete action buttons
  - Show usage statistics (how many times used in plans/records)

### 3. Activity Create View
- **URL Pattern**: `/activities/create/` and `/activities/create/<parent_id>/`
- **Functionality**:
  - Form with fields: abbreviation, description, parent, importance, urgency, sort_order
  - Exclude parents with id="ALL" from parent dropdown
  - Pre-select parent if accessed via parent-specific URL
  - Validate abbreviation uniqueness
  - Validate description uniqueness within parent
  - Auto-assign sort_order if not provided (max + 1)

### 4. Activity Edit View
- **URL Pattern**: `/activities/<activity_id>/edit/`
- **Functionality**:
  - Pre-populated form with current activity data
  - Same validation as create view
  - Warning if activity is used in existing plans/records
  - Option to update all existing references or create new activity

### 5. Activity Delete View
- **URL Pattern**: `/activities/<activity_id>/delete/`
- **Functionality**:
  - Confirmation page showing activity details
  - List of dependent records (daily plans, activity records)
  - Soft delete option (mark as inactive) vs hard delete
  - Prevent deletion if activity has dependencies (due to PROTECT constraint)

## Technical Requirements

### 1. URL Configuration
```python
# Add to timsy/urls.py
path('activities/', activity_views.activity_list, name='activity_list'),
path('activities/<slug:parent_id>/', activity_views.activity_list_by_parent, name='activity_list_by_parent'),
path('activities/detail/<int:activity_id>/', activity_views.activity_detail, name='activity_detail'),
path('activities/create/', activity_views.activity_create, name='activity_create'),
path('activities/create/<slug:parent_id>/', activity_views.activity_create_with_parent, name='activity_create_with_parent'),
path('activities/<int:activity_id>/edit/', activity_views.activity_edit, name='activity_edit'),
path('activities/<int:activity_id>/delete/', activity_views.activity_delete, name='activity_delete'),
```

### 2. View Functions
- Create `activity_views.py` in the views directory
- Follow existing patterns from `daily_plan_views.py` and `blueprint_views.py`
- Use function-based views for consistency with existing codebase
- Implement proper error handling and validation

### 3. Templates
- `activity_list.html` - List all activities with filtering
- `activity_detail.html` - Show activity details
- `activity_form.html` - Shared form for create/edit
- `activity_delete.html` - Confirmation page for deletion
- Follow existing template patterns and inherit from `base.html`

### 4. Model Enhancements
- Add `active` field to Activity model (similar to Parent model)
- Add method to check if activity has dependencies
- Add method to get usage statistics
- Create migration for new fields

## Data Requirements

### 1. Filtering Logic
- Exclude activities where `parent.id = "ALL"`
- Support filtering by active/inactive status
- Support filtering by parent category

### 2. Validation Rules
- Abbreviation: max 10 characters, optional, unique if provided
- Description: max 200 characters, required, unique within parent
- Parent: required, cannot be "ALL"
- Importance: required, must exist
- Urgency: required, must exist
- Sort_order: optional, auto-assign if not provided

### 3. Business Rules
- Cannot delete activities that are referenced in daily plans or activity records
- When editing activities used in existing records, offer option to:
  - Update all references (risky)
  - Create new activity with changes (safer)
- Maintain sort_order for consistent display

## UI/UX Requirements

### 1. Navigation
- Add "Activities" link to main navigation
- Breadcrumb navigation: Home > Activities > [Parent] > [Action]
- Back buttons on all forms

### 2. List Display
- Tabular format with sortable columns
- Parent filter dropdown
- Search functionality (by abbreviation or description)
- Pagination for large datasets
- Action buttons (Edit/Delete) for each row

### 3. Forms
- Use existing form styling patterns
- Dropdown for parent selection (exclude "ALL")
- Dropdown for importance/urgency selection
- Auto-complete for abbreviation field
- Client-side validation for required fields

### 4. Responsive Design
- Follow existing responsive patterns
- Mobile-friendly forms and lists
- Touch-friendly buttons and links

## Security Requirements

### 1. Access Control
- Follow existing authentication patterns
- No additional authorization needed (same as daily plans)

### 2. Data Protection
- Validate all input data
- Prevent SQL injection through proper ORM usage
- CSRF protection on all forms

## Performance Requirements

### 1. Database Optimization
- Use select_related() for parent, importance, urgency relationships
- Add database indexes on frequently queried fields
- Limit query results with pagination

### 2. Caching
- Follow existing caching patterns if any
- Cache parent/importance/urgency choices for forms

## Integration Requirements

### 1. Existing Functionality
- Maintain compatibility with `Activity.find_or_create()` method
- Ensure daily plan creation still works
- Update admin interface if needed

### 2. Future Extensibility
- Design views to support additional filtering options
- Structure templates for easy customization
- Consider API endpoints for future mobile app

## Testing Requirements

### 1. Unit Tests
- Test all CRUD operations
- Test validation rules
- Test business logic (dependency checking)

### 2. Integration Tests
- Test form submissions
- Test navigation flows
- Test error handling

## Implementation Priority

### Phase 1 (Core CRUD)
1. Model enhancements (add active field)
2. Activity list view with basic filtering
3. Activity create view
4. Activity edit view
5. Basic templates

### Phase 2 (Enhanced Features)
1. Activity detail view with usage statistics
2. Activity delete view with dependency checking
3. Advanced filtering and search
4. Navigation integration

### Phase 3 (Polish)
1. Responsive design improvements
2. Performance optimizations
3. Comprehensive testing
4. Documentation updates

## Success Criteria
- Users can view all activities filtered by parent (excluding "ALL")
- Users can create new activities with proper validation
- Users can edit existing activities safely
- Users can delete activities when no dependencies exist
- All functionality integrates seamlessly with existing daily plan workflow
- Performance remains acceptable with large datasets
- UI follows existing design patterns and is mobile-friendly 