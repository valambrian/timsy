# Timsy Application Requirements

## 1. Daily Plan Management
- Create daily plans from templates
- Edit existing daily plans
- View daily plans in a timeline format
- List all daily plans ordered by date
- Prevent duplicate daily plans for the same date and template

## 2. Activity Management
- Create and edit activities with:
  - Description
  - Abbreviation
  - Start time
  - Duration
  - Place
  - Parent activity
  - Importance level
  - Urgency level
- Validate activity data:
  - Required fields when any activity field is filled
  - Place must be a valid location
  - Duration must be in HH:MM format
  - Total duration cannot exceed 24 hours

## 3. Template Management
- Create and edit ideal day templates
- Templates can be active or inactive
- Templates contain a sequence of activities
- Templates can be used to generate daily plans

## 4. Time Management
- Automatic calculation of start times based on previous activity duration
- Total duration tracking
- Remaining time calculation
- Warning when total duration exceeds 24 hours
- Drag-and-drop reordering of activities with automatic time updates

## 5. Data Validation
- Place validation against predefined list
- Activity abbreviation validation
- Required field validation
- Time format validation
- Duration format validation

## 6. User Interface Features
- Drag-and-drop interface for reordering activities
- Real-time duration calculations
- Visual feedback for drag operations
- Delete functionality for activities
- Form validation with error messages
- Dropdown menus for:
  - Parent activities
  - Importance levels
  - Urgency levels

## 7. Data Relationships
- Activities can have parent activities
- Activities are associated with places
- Activities have importance and urgency levels
- Daily plans are created from templates
- Daily plans contain multiple activities

## 8. Technical Requirements
- Local operation without internet connection
- Plain JavaScript without external libraries
- Plain HTML without external CSS
- Relative template paths
- Form validation on both client and server side
- Proper error handling and user feedback

## 9. Performance Requirements
- Efficient handling of multiple activities
- Real-time calculations for time management
- Smooth drag-and-drop operations
- Responsive form updates

## 10. Data Integrity
- Unique constraints on daily plan date and template combinations
- Validation of all required fields
- Proper handling of time calculations
- Prevention of invalid data entry 