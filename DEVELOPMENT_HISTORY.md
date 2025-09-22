# Dashboard EPMAPS POC - Development History

## Overview
This document tracks the complete development history of the Dashboard EPMAPS POC project, including all changes, issues resolved, and technical decisions made.

## Detailed Development Log

### 2025-09-22 - Add Sorting, New Validations, and UI Refinements (v0.2.18)

#### Problem Identified
User requested final refinements for the alarm report:
1.  **Sorting**: The table should be sorted by instance name by default.
2.  **Highlighting**: The red border highlight for validation errors was still not visible.
3.  **Column Width**: "Total" columns were too wide and needed shorter titles.

#### Solution Applied
**1. Default Sorting**
- The DataFrame is now explicitly sorted by "Nombre Instancia" before being displayed, ensuring a consistent default order.

**2. Robust Highlighting**
- The CSS property for highlighting was changed from `outline` to `box-shadow: inset 0 0 0 2px red;`. This is a more robust technique that is less likely to be overridden by other styles, ensuring the red highlight for validation errors is always visible.

**3. Abbreviated Column Titles**
- As requested, the wide column titles were abbreviated to save space:
  - `Total Alarmas Teóricas` is now `T. A. Teóricas`.
  - `Total Alarmas Actuales` is now `T. A. Actuales`.

#### Technical Fix
```python
# ui_components/alarm_report_ui.py

# Sorting
df = df.sort_values(by='Nombre Instancia').reset_index(drop=True)

# New Column Names
column_names = {
    # ...
    'total_alarms_theoretical': 'T. A. Teóricas',
    'total_alarms': 'T. A. Actuales'
}

# New Styling Logic
def _apply_validation_styles(self, row):
    # ...
    border_style = ' box-shadow: inset 0 0 0 2px red;'
    # ...
```

#### Result
- ✅ The report table now loads pre-sorted by instance name.
- ✅ Validation errors are now reliably highlighted with a red inner border.
- ✅ Column widths are more compact due to the abbreviated titles.

#### Version: v0.2.18

### 2025-09-22 - Add New Validation Rules and Theoretical Alarms Column (v0.2.17)

#### Problem Identified
User required more extensive validation rules for the alarm report and a new column to show the expected number of alarms.

#### Solution Applied
**1. Added "Total Alarmas Teóricas" Column**
- A new column was added to the report in `ui_components/alarm_report_ui.py`.
- The value is calculated based on the formula: `2 (CPU) + 1 (RAM) + (3 * Cant. Discos) + 1 (Ping)`.

**2. Renamed "Total Alarmas" Column**
- The existing "Total Alarmas" column was renamed to "Total Alarmas Actuales" for clarity.

**3. Implemented Extensive Validation Highlighting**
- The styling function `_apply_validation_styles` was enhanced to highlight cells with a red outline if they fail specific rules:
  - **Alarmas CPU**: Highlights if the value is not equal to 2.
  - **Alarmas RAM**: Highlights if the value is 0.
  - **Alarmas Disco**: Highlights if the value is not `3 * Cant. Discos`.
  - **Alarmas Ping**: Highlights if the value is 0.
- The CSS `outline` property is now used for highlighting to ensure visibility over other styles.

#### Technical Fix
'''python
# ui_components/alarm_report_ui.py

# Add new column to DataFrame
df['total_alarms_theoretical'] = 2 + 1 + (df['disk_count'] * 3) + 1

# New styling function with multiple validation rules
def _apply_validation_styles(self, row):
    # ... (row highlight logic)
    styles = [base_style] * len(row)
    border_style = ' outline: 2px solid red;'

    # CPU validation
    if row['Alarmas CPU'] != 2:
        styles[cpu_idx] += border_style

    # RAM validation
    if row['Alarmas RAM'] == 0:
        styles[ram_idx] += border_style

    # ... (and so on for Disk and Ping)
    return styles
'''

#### Result
- ✅ The report now includes a "Total Alarmas Teóricas" column for easy comparison.
- ✅ Cells with data inconsistencies according to the new rules are now clearly marked with a red outline.

#### Version: v0.2.17

### 2025-09-22 - Fix Report Styling and Update Info Text (v0.2.16)

#### Problem Identified
User reported that the disk alarm validation highlighting (red border) was not appearing correctly. Additionally, the informational text required an update.

#### Solution Applied
**1. Robust Styling Function**
- The two separate styling functions (`_highlight_rows` and `_apply_disk_alarm_validation_style`) were merged into a single, more robust function `_apply_report_styles` in `ui_components/alarm_report_ui.py`.
- This new function handles both row background highlighting and cell-specific borders in the correct order, preventing styles from overwriting each other.
- It first sets the base row background color and then appends the border style to the specific cell if the validation fails.

**2. Informational Text Update**
- The text in the `st.info` box on the report page was updated to include the new validation rules, as requested.

#### Technical Fix
'''python
# ui_components/alarm_report_ui.py

def _apply_report_styles(self, row):
    # 1. Set base style for row highlighting
    base_style = ''
    if row['Alarmas Rojas'] > 0:
        base_style = 'background-color: #ffcccc; color: black;'
    # ...
    styles = [base_style] * len(row)
    
    # 2. Apply disk alarm validation border
    if row['Cant. Discos'] > 0 and row['Alarmas Disco'] != (row['Cant. Discos'] * 3):
        disk_alarm_col_index = list(row.index).index('Alarmas Disco')
        styles[disk_alarm_col_index] += ' border: 2px solid red;' # Append style

    return styles

# Updated st.info text
st.info("Se consideran alarmas amarillas las alarmas proactivas y de alerta. Las alarmas de disco deben ser 3x la cantidad de discos. La cantidad de alertas de CPU debieran ser dos")
'''

#### Result
- ✅ The red border for disk alarm validation failures now appears correctly.
- ✅ The informational text on the report page is updated.

#### Version: v0.2.16

### 2025-09-22 - Add Disk Alarm Validation and Highlighting (v0.2.14)

#### Problem Identified
User requested a way to validate the number of disk alarms and highlight inconsistencies.
1.  **Validation Rule**: The number of alarms in the "Alarmas Disco" column should be exactly 3 times the number in the "Cant. Discos" column.
2.  **Error Highlighting**: A visual indicator was needed for rows where this validation fails.

#### Solution Applied
**1. New Validation and Styling Logic**
- A new method, `_apply_disk_alarm_validation_style`, was added to `ui_components/alarm_report_ui.py`.
- This function is applied to each row of the report table.
- It checks if `row['Alarmas Disco']` is not equal to `row['Cant. Discos'] * 3`.
- If the validation fails, it applies a `border: 2px solid red;` style specifically to the "Alarmas Disco" cell for that row.

**2. Chained Styling**
- The new cell-specific styling is chained with the existing row-level highlighting, so both styles can be applied simultaneously.

#### Technical Fix
'''python
# ui_components/alarm_report_ui.py

def _apply_disk_alarm_validation_style(self, row):
    """Apply a border to the disk alarm cell if validation fails."""
    styles = [''] * len(row)
    # Condition for the validation error
    if row['Cant. Discos'] > 0 and row['Alarmas Disco'] != (row['Cant. Discos'] * 3):
        try:
            disk_alarm_col_index = list(row.index).index('Alarmas Disco')
            styles[disk_alarm_col_index] = 'border: 2px solid red;'
        except ValueError:
            pass
    return styles

# Chained the new style in the display_alarm_report method
styled_df = df.style.apply(self._highlight_rows, axis=1).apply(self._apply_disk_alarm_validation_style, axis=1)
'''

#### Result
- ✅ The report now automatically highlights inconsistencies in the disk alarm count with a red border.
- ✅ This provides a clear and immediate visual cue for specific data validation errors without cluttering the UI.

#### Version: v0.2.14

### 2025-09-22 - Alarm Report UI & Categorization Update (v0.2.13)

#### Problem Identified
User reported several issues with the Alarm Report page:
1.  **Miscategorization**: Certain alarms (e.g., `SAP Process Running`) were not appearing in the "Otras Alarmas" category as expected.
2.  **Theme Incompatibility**: The table's row highlighting used light backgrounds, which made the default white text of dark themes unreadable.
3.  **Unnecessary Column**: The "Alarmas Disponibilidad" column was not needed.
4.  **Lack of Clarity**: The definition of a "yellow alarm" was not explicit on the page.

#### Solution Applied
**1. Simplified Alarm Categorization**
- Removed the "Alarmas Disponibilidad" category entirely from the report logic in `ui_components/alarm_report_ui.py`.
- This simplifies the classification and ensures that any alarm not matching CPU, RAM, Disk, or Ping keywords correctly falls into "Otras Alarmas".

**2. Theme-Aware Table Styling**
- Modified the `_highlight_rows` function to be compatible with both light and dark themes.
- The style now explicitly sets `color: black;` on highlighted rows, ensuring readability regardless of the user's theme.

**3. Added Informational Note**
- An `st.info` box was added below the summary metrics to clearly state: "Se consideran alarmas amarillas las alarmas proactivas y de alerta."

#### Technical Fix
'''python
# ui_components/alarm_report_ui.py

# Removed 'availability_alarms' from column_order and column_names
# Removed the elif block for 'AVAILABILITY' in _process_alarm_data

# Added info box
st.info("Se consideran alarmas amarillas las alarmas proactivas y de alerta.")

# Updated styling function for theme compatibility
def _highlight_rows(self, row):
    style = ''
    if row['Alarmas Rojas'] > 0:
        style = 'background-color: #ffcccc; color: black;'
    elif row['Alarmas Amarillas'] > 0:
        style = 'background-color: #fff4cc; color: black;'
    # ...
    return [style] * len(row)
'''

#### Result
- ✅ Alarms are now categorized more accurately, with non-specific ones correctly placed in "Otras".
- ✅ The report table is now clearly readable on both light and dark themes.
- ✅ The UI is cleaner after removing the unnecessary column.
- ✅ The page provides better context with the new informational note.

#### Version: v0.2.13

### 2025-09-22 - Use Real Data for Disk Count in Alarm Report (v0.2.12)

#### Problem Identified
**Alarm Report Showing Incorrect Disk Count**
- **Issue**: The "Cant. Discos" column in the alarm report showed an inaccurate number of disks for each instance.
- **Root Cause**: The disk count was not a real data point from AWS. It was being "inferred" by parsing alarm names and looking for numbered patterns like `DISK_0`, which is unreliable.
- **User Request**: Display real data from AWS, not inferred or "guessed" data.

#### Solution Applied
**1. Fetch Real Disk Count from AWS**
- Modified `services/aws_service.py` to get the actual number of attached block devices for each EC2 instance.
- The `get_aws_data` method now inspects the `BlockDeviceMappings` attribute from the `describe_instances` API call.
- The true disk count is now stored in a new `DiskCount` field in the instance data structure.

**2. Update Alarm Report to Use Real Data**
- Modified `ui_components/alarm_report_ui.py`.
- The logic for inferring disk count from alarm names was completely removed.
- The report now reads the `DiskCount` value directly from the data provided by `AWSService`.

#### Technical Fix
'''python
# services/aws_service.py - In get_aws_data()
# Get the actual number of attached block devices (disks)
disk_count = len(instance.get('BlockDeviceMappings', []))
instance_data['DiskCount'] = disk_count

# ui_components/alarm_report_ui.py - In _process_alarm_data()
# Get the real disk count from the instance data
disk_count = instance.get('DiskCount', 0)
'''

#### Result
- ✅ The "Cant. Discos" column in the alarm report now shows the correct number of disks as reported by the EC2 API.
- ✅ The application no longer relies on fragile name-based inference for this metric.
- ✅ Alarm categorization (CPU, RAM, etc.) still relies on keyword matching in alarm names, which is a standard practice for this kind of classification.

#### Version: v0.2.12

### 2025-09-03 - Initial POC Dashboard Creation
- Created basic Streamlit dashboard for monitoring VMs
- Integrated with AWS CloudWatch for real-time metrics
- Implemented environment switching (Production, QA, DEV)
- Added visual indicators for alarm states
- Basic CSS styling for server cards

### 2025-09-05 - AWS Integration and Deployment
- Implemented cross-account role assumption for AWS
- Created deployment scripts for AWS Fargate
- Added CloudWatch agent deployment script
- Implemented alarm creation scripts
- Added debug logging functionality

### 2025-09-10 - Major Refactoring to Class-Based Architecture
- Migrated from monolithic app.py to modular structure
- Created service classes (AWSService, SAPService)
- Created UI component classes (DashboardUI, DetailUI)
- Preserved all original functionality and appearance
- Improved code maintainability and testability

### 2025-09-12 - Header Space Optimization
- Reduced header heights in dashboard and detail pages
- Decreased h1 font size from 2.5rem to 1.8rem
- Adjusted margins and padding throughout
- Fixed navigation elements that were cut off
- Maintained all text and rotation functionality

### 2025-09-13 - Column Control Feature
- Added column selector (1-4 columns) for group distribution
- Implemented session persistence using query parameters
- Fixed column selection persistence during auto-refresh
- Fixed navigation persistence when viewing detail pages
- Aligned "Columnas:" label with dropdown control

### 2025-09-14 - Smooth Auto-Refresh Implementation
- Replaced meta refresh with st.fragment(run_every=30)
- Eliminated black screen effect during refresh
- Fixed auto-refresh not actually updating content
- Removed unnecessary manual refresh button
- Version: v0.2.06

### 2025-09-15 - Fix AWS Cache for Tag Changes (v0.2.07)

#### Problem Reported
**DashboardGroup Tag Changes Not Reflecting in UI**
- **Issue**: User modified DashboardGroup tags in EC2 console
- **Root Cause**: AWS data cached for 15 minutes (900 seconds)
- **Impact**: Users had to wait up to 15 minutes to see changes

#### Solution Applied
**Reduced Cache TTL**
- Changed from 900 seconds (15 minutes) to 60 seconds (1 minute)
- File: `services/aws_service.py:61`
- Now tag changes reflect within 1 minute

#### Technical Change
'''python
@st.cache_resource(ttl=60)  # Reduced from 900 to 60 seconds
def get_cross_account_boto3_client_cached(service, role_arn=None):
'''

#### Result
- ✅ Tag changes now visible within 1 minute
- ✅ Good balance between performance and data freshness
- ✅ Users can modify EC2 tags and see results quickly

### 2025-09-15 - Fix Duplicate Groups Issue (v0.2.08)

#### Problem Identified and Solved
**"Almacenamiento" Showing as Two Separate Groups**
- **Root Cause**: Extra whitespace in DashboardGroup tag values
- **Example**: "Almacenamiento" vs "Almacenamiento " (with trailing space)
- **Result**: AWS treated them as different group names

#### Solution Applied
**1. Automatic Tag Cleaning**
- Added `.strip()` to DashboardGroup values in AWS service
- Removes leading/trailing whitespace automatically
- File: `services/aws_service.py:159`

**2. Debug Process Used**
- Added temporary debug logging to identify the issue
- Found invisible characters in tag values
- Confirmed the fix worked correctly
- Removed debug code after verification

**3. Removed Unnecessary UI Elements**
- Removed the manual refresh button (user didn't request it)
- Restored original control layout

#### Technical Fix
'''python
# Clean DashboardGroup value to remove extra whitespace
dashboard_group = tags.get('DashboardGroup', 'Uncategorized').strip()
'''

#### Result
- ✅ All three "Almacenamiento" servers now appear in single group
- ✅ Future tag changes will automatically be cleaned
- ✅ No more duplicate groups due to whitespace
- ✅ 1-minute cache for good performance/freshness balance

#### Version: v0.2.08

### 2025-09-16 - Port 80 Preparation
- Confirmed application ready for port 80 deployment
- Fargate deployment script already configures ALB on port 80
- No code changes required

### 2025-09-17 - CloudFront Compatibility (v0.2.09)
- Analyzed WebSocket limitations with CloudFront
- Created CloudFront deployment script
- Added compatibility headers in dashboard_manager.py
- Documented deployment process
- Application works correctly with WebSocket fallbacks

### 2025-09-17 - Navigation and Threading Issues Resolved
- Fixed empty label warning with label_visibility="hidden"
- Removed threading approach causing ScriptRunContext warnings
- Improved auto-refresh reliability

#### Pending Work
- Additional server card indicators for technical diagnostics
- Performance metrics display (CPU, Memory, Disk)
- Uptime and connectivity status indicators

#### Current Status: v0.2.11
All major issues resolved, smooth auto-refresh working, column control functional, tag grouping fixed, and alarm report added.

### 2025-09-18 - Add PREVENTIVA to Yellow Alarms and CloudFront Support (v0.2.10)

#### Changes Made
**1. Extended Yellow Alarm Detection**
- Added "PREVENTIVA" to the list of keywords that trigger yellow alarms
- Now alarms are yellow when state is ALARM and name contains:
  - "ALERTA"
  - "PROACTIVA" 
  - "PREVENTIVA" (new)
- Updated in:
  - `services/aws_service.py:149`
  - `ui_components/detail_ui.py:177`

**2. CloudFront Deployment Support (v0.2.09)**
- Created `ScriptsUtil/create_cloudfront_distribution.sh` for easy CloudFront deployment
- Added CloudFront compatibility headers in `dashboard_manager.py`
- Documented deployment process in `docs/cloudfront_deployment.md`
- Application now works correctly behind CloudFront with WebSocket fallbacks

#### Technical Details
'''python
# Yellow alarm detection now includes PREVENTIVA
if alarm_state == 'ALARM' and ('ALERTA' in alarm_name.upper() or 
                               'PROACTIVA' in alarm_name.upper() or 
                               'PREVENTIVA' in alarm_name.upper()):
    instance_alarms['PREVENTIVE'] += 1
'''

#### Result
- ✅ Alarms with "PREVENTIVA" in name now show as yellow
- ✅ Application ready for CloudFront deployment
- ✅ Port 80 support confirmed via Fargate ALB

### 2025-09-18 - Add Global Alarm Report Page (v0.2.11)

#### New Feature: Global Alarm Report
**Requirements Implemented:**
1. New alarm report page accessible via link below dashboard title
2. Report shows comprehensive alarm statistics per instance
3. Filtered by environment (Production, QA, DEV) with navigation arrows
4. No Streamlit sidebar menu (clean navigation)

#### Report Columns:
- **Instance Info**: Name, Private IP, Instance ID
- **Alarm Categories**:
  - CPU Alarms (count)
  - RAM Alarms (count) 
  - Disk Alarms (count including preventive/alert/incident)
  - Disk Count (detected from alarm names)
  - Ping Alarms (count)
  - Availability Alarms (count)
  - Other Alarms (count)
- **Alarm States**:
  - Insufficient Data (count)
  - Yellow Alarms (preventive - count)
  - Red Alarms (critical - count)
  - Total Alarms (sum)

#### Technical Implementation:
1. **New Component**: `ui_components/alarm_report_ui.py`
   - Processes alarm data and categorizes by type
   - Detects disk count from alarm naming patterns
   - Color-codes rows based on alarm severity
   - Provides CSV export functionality

2. **Dashboard Updates**:
   - Added "📊 Reporte Alarmas" link below title in `dashboard_ui.py:199-202`
   - Link navigates to `?alarm_report=true`
   - Preserves environment selection across pages

3. **Routing Updates**: `dashboard_manager.py`
   - Added alarm report route handling
   - Integrated AlarmReportUI component

#### Features:
- ✅ Summary metrics at top (total instances, alarms by type)
- ✅ Sortable/filterable data table
- ✅ Row highlighting based on alarm severity
- ✅ CSV export with timestamp
- ✅ Consistent navigation with main dashboard
- ✅ No sidebar menu as requested

## Technical Architecture

### Current Structure
'''
.
├── app.py                    # Main entry point (uses DashboardManager)
├── dashboard_manager.py      # Central coordinator
├── services/
│   ├── aws_service.py       # AWS integration
│   └── sap_service.py       # SAP monitoring
├── ui_components/
│   ├── dashboard_ui.py      # Main dashboard
│   ├── detail_ui.py         # Server detail page
│   └── alarm_report_ui.py   # Alarm report page
├── utils/
│   └── helpers.py           # Shared utilities
└── components/              # Legacy components (preserved)
'''

### Key Design Decisions
1. **Modular Architecture**: Separated concerns into service and UI layers
2. **State Management**: Used Streamlit session state and query params
3. **Caching Strategy**: 60-second TTL for AWS data freshness
4. **Auto-refresh**: st.fragment for smooth updates without page reload
5. **No Sidebar**: Clean navigation through links and buttons only

## Deployment Information

### AWS Infrastructure
- **Platform**: AWS Fargate with ALB
- **Port**: 80 (via ALB)
- **CloudFront**: Supported with WebSocket fallback
- **Region**: us-east-1
- **Auto-scaling**: Configured in Fargate

### Environment Variables
- `AWS_DEFAULT_REGION`: AWS region
- `ROLE_ARN`: Cross-account role for AWS access

## Version History
- v0.1.0: Initial POC
- v0.2.0: Class-based refactoring
- v0.2.04: Column control feature
- v0.2.06: Smooth auto-refresh
- v0.2.08: Fixed duplicate groups
- v0.2.09: CloudFront support
- v0.2.10: Extended yellow alarms
- v0.2.11: Global alarm report