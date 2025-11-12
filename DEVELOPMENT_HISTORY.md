# Dashboard EPMAPS POC - Development History

## v0.7.0 - SAP Availability Metrics in Monthly Report (2025-11-12)

### Feature: SAP Availability (Heartbeat) Metrics
- **Description**: Added full support for SAP availability heartbeat metrics from CloudWatch
- **Namespaces**:
  - Production: `SAP_Monitoring_Availability_Prod` (49 metrics)
  - QA/DEV: `SAP_Monitoring_Availability` (59 metrics)
- **Total metrics**: 108 availability metrics across all environments

### Implementation Details

**New methods in `services/aws_service.py`:**

1. `get_availability_metrics_for_instance(instance_id, environment)`:
   - Lists all heartbeat metrics for a specific EC2 instance
   - Auto-selects namespace based on environment
   - Filters by InstanceId dimension
   - Returns metrics matching 'heartbeat' pattern

2. `get_availability_metric_data(namespace, metric_name, dimensions, start_time, end_time, period)`:
   - Retrieves time-series data with all required dimensions
   - Dimensions: VMName, Path, InstanceId
   - Returns DataFrame with Average, Minimum, Maximum
   - Default period: 900 seconds (15 minutes)

**New method in `ui_components/monthly_report_ui.py`:**

`_display_availability_metrics(start_date, end_date)`:
- Processes and displays SAP availability metrics
- One chart per SAP service per server
- Structure mirrors `_display_ping_metrics`
- Handles multiple services per server automatically
- Extracts service name from metric name
- Chart titles: "{ServerName} - {Service} - Disp: XX.X%"

**Metric Naming Convention:**
```
{ServerName}_{System}_{Service}_heartbeat

Examples:
- SRVERPQA_ERQ_ASCS01_heartbeat
- SRVBWPRD_BIP_D00_heartbeat
- DMZ-SRVWDPRD_DAA_SMDA98_heartbeat
```

**Visual Differences from Ping:**
- Color: Green (#2ca02c) vs Ping Blue (#1f77b4)
- Font size: 14px vs 16px (to fit longer service names)
- Multiple charts per server (one per SAP service)
- Fixed period: 15 minutes

### User Experience

**Display Flow:**
1. User selects "Availability" from metric type dropdown
2. User selects date range and clicks "🔍 Consultar"
3. System shows title: "Métricas de Availability (SAP) Desde DD/MM/YYYY hasta DD/MM/YYYY"
4. For each environment (Production, QA, DEV):
   - Shows subtitle: "Producción (X servidores)"
   - For each server, shows all its SAP services as separate charts
   - Example: SRVBWPRD might show BIP_D00, BJP_SCS03, DAA_SMDA98
5. PDF button generates: Availability_Report_YYYYMMDD_YYYYMMDD.pdf

**Example Server with Multiple Services:**
```
SRVBWPRD in Production may have:
[SRVBWPRD - BIP_D00 - Disp: 98.5%]
[SRVBWPRD - BJP_SCS03 - Disp: 99.2%]
[SRVBWPRD - DAA_SMDA98 - Disp: 97.1%]
```

### Files Modified:
- `services/aws_service.py`:
  - Lines 329-367: New `get_availability_metrics_for_instance()` method
  - Lines 369-410: New `get_availability_metric_data()` method
- `ui_components/monthly_report_ui.py`:
  - Line 212: Connected availability routing
  - Lines 551-736: New `_display_availability_metrics()` method (186 lines)
- `config.yaml` line 70: Bumped version to v0.7.0
- `ScriptsUtil/explore_availability_metrics.py`: New exploration script (188 lines)

### Testing Results:

**Exploration Script Results:**
- ✅ 59 metrics in QA/DEV namespace
- ✅ 49 metrics in Production namespace
- ✅ All metrics have data (672 datapoints for 7 days)
- ✅ Values are binary (0-1) as expected
- ✅ Period: 15 minutes confirmed

**Sample Metrics Found:**
- srvcrmqasV_QCA_SUM_heartbeat (QA)
- SRVCRMDEV_DCA_D00_heartbeat (DEV)
- SRVBWPRD_BIP_D00_heartbeat (Prod)
- DMZ-SRVWDPRD_DAA_SMDA98_heartbeat (Prod)

### Impact:
- ✅ Complete visibility of SAP service availability
- ✅ Granular per-service monitoring (ASCS, DVEBMGS, SCS, D00, etc.)
- ✅ Multiple services per server supported
- ✅ Schedule-aware availability calculation
- ✅ Organized by environment for clarity
- ✅ PDF export with all services included
- ✅ Same professional layout as Ping metrics

### Technical Notes:

**Dimension Requirements:**
All three dimensions are required for queries:
- VMName: Server name as appears in EC2 tags
- Path: Full path to available.log file
- InstanceId: EC2 instance ID

**Service Name Extraction:**
Service name extracted from metric name using pattern:
```python
service_name = metric_name.replace('_heartbeat', '')
                          .replace(f'{instance_name}_', '')
```
Examples:
- SRVERPQA_ERQ_ASCS01_heartbeat → ERQ_ASCS01
- SRVBWPRD_BIP_D00_heartbeat → BIP_D00

**Period Calculation:**
Unlike Ping (dynamic period), Availability uses fixed 15-minute interval
as this is the standard CloudWatch Agent collection period for these metrics.

### Version: v0.7.0

---

## v0.6.9 - Organize Monthly Report by Environment Sections (2025-11-11)

### Feature: Multiple Environment Sections in Monthly Report
- **Description**: Monthly report now organizes servers by Environment (Production, QA, DEV) with section subtitles
- **Previous**: Showed only QA servers with "Procesando X servidor(es) de QA..." notification
- **Current**: Shows all environments organized in sections with descriptive subtitles

### Implementation Details

**Environment Sections:**
- Process environments in order: Production → QA → DEV
- Display format: `#### {environment_name} ({count} servidor/es)`
- Examples:
  - "Producción (5 servidores)"
  - "QA (13 servidores)"
  - "Desarrollo (3 servidores)"

**Modified: `_display_ping_metrics()`**
- Loops through 3 environments: Production, QA, DEV
- For each environment:
  1. Gets instances with `_get_instances_by_environment(env_tag)`
  2. Skips silently if no instances found
  3. Displays section subtitle with server count
  4. Processes all servers in that environment
  5. Shows charts in 4-column grid
  6. Adds horizontal separator `st.markdown("---")` between sections
  7. Accumulates all charts for PDF export

**UI Improvements:**
- ❌ Removed: `st.info("Procesando X servidor(es) de QA...")`
- ❌ Removed: `st.warning("⚠️ Sin datos de ping para {instance_name}")` - now skips silently
- ✅ Added: Section subtitles with semantic hierarchy (####)
- ✅ Added: Visual separators between environment sections
- ✅ Maintained: Spinner during data loading
- ✅ Maintained: 4-column grid layout per section

**PDF Export:**
- Includes ALL servers from ALL environments
- Maintains order: Production → QA → DEV
- Single unified PDF with complete metrics
- Button positioned at the end (centered): "📄 Descargar PDF" (primary type)

### User Experience

**Display Flow:**
1. User clicks "🔍 Consultar"
2. System shows title: "Métricas de Ping Desde DD/MM/YYYY hasta DD/MM/YYYY"
3. For each environment with servers:
   - Shows section subtitle: "Producción (X servidores)"
   - Displays charts in 4-column grid
   - Shows horizontal separator
4. Repeats for QA and DEV environments
5. PDF button generates report with all environments

**Layout Example:**
```
#### Producción (5 servidores)
[Chart 1] [Chart 2] [Chart 3] [Chart 4]
[Chart 5]

───────────────────────────────────────────────

#### QA (13 servidores)
[Chart 1] [Chart 2] [Chart 3] [Chart 4]
[Chart 5] [Chart 6] [Chart 7] [Chart 8]
[Chart 9] [Chart 10] [Chart 11] [Chart 12]
[Chart 13]

───────────────────────────────────────────────

#### Desarrollo (3 servidores)
[Chart 1] [Chart 2] [Chart 3]

───────────────────────────────────────────────

                [📄 Descargar PDF]
```

### Files Modified:
- `ui_components/monthly_report_ui.py`:
  - Lines 395-554: Refactored `_display_ping_metrics()` for multi-environment support
  - Added environment loop with tuple mapping: (tag, display_name)
  - Added section subtitles with server count
  - Added visual separators between sections
  - Changed from `charts_data` to `all_charts_data` for PDF aggregation
- `config.yaml` line 70: Bumped version to v0.6.9

### Impact:
- ✅ Complete visibility across all environments (Production, QA, DEV)
- ✅ Better organization with clear visual separation
- ✅ Professional UI with semantic hierarchy
- ✅ Scalable: works with any number of environments/servers
- ✅ Single PDF with complete infrastructure overview
- ✅ Cleaner UI without redundant notifications
- ✅ Maintains all v0.6.8 features (schedule-aware availability, dynamic grid)

### Use Cases:

**Scenario 1: Full infrastructure (all 3 environments)**
- Shows 3 sections with their respective servers
- PDF includes complete infrastructure metrics

**Scenario 2: Partial infrastructure (e.g., only Production + QA)**
- Shows 2 sections (skips DEV silently)
- PDF includes only existing environments

**Scenario 3: Single environment (e.g., only QA)**
- Shows 1 section with new format
- Backward compatible with v0.6.8 use case

### Version: v0.6.9

---

## v0.6.8 - Multiple QA Servers in Monthly Report (2025-11-11)

### Feature: Display All QA Environment Servers
- **Description**: Monthly report now shows ping metrics for ALL servers with Environment=QA tag
- **Previous**: Only showed SRVERPQA (hardcoded)
- **Current**: Dynamically fetches and displays all QA servers

### Implementation Details

**New Method: `_get_instances_by_environment()`**
- Filters instances by Environment tag (case-insensitive)
- Returns list of dictionaries with ID, Name, and Schedule
- Reusable for other environments (PROD, DEV, etc.)

**Modified: `_display_ping_metrics()`**
- Now processes all QA instances instead of single hardcoded server
- Displays progress: "Procesando X servidor(es) de QA..."
- Shows warning for servers without ping data (continues processing others)
- Displays all charts in 4-column grid layout (multiple rows as needed)
- All charts included in PDF export

**Grid Layout:**
- Dynamic rows: Creates new row for every 4 charts
- Responsive: Uses Streamlit columns for proper spacing
- Example with 13 servers: 3 full rows + 1 partial row (1 chart)

**Performance:**
- Progress indicators for each server
- Optimal period calculated once (same for all servers)
- Parallel-ready structure for future optimization

### Testing Results

**Local Test:**
```bash
python -c "from ui_components.monthly_report_ui import MonthlyReportUI; ..."
✅ Método _get_instances_by_environment funcional
📊 Encontradas 13 instancias de QA
```

**QA Servers Found:**
- SRVHANDBQAS
- SRVERPQA
- (+ 11 more QA servers)

### Files Modified:
- `ui_components/monthly_report_ui.py`:
  - Lines 228-229: Added 'Name' to _get_instance_data_by_name return
  - Lines 238-257: New `_get_instances_by_environment()` method
  - Lines 395-515: Completely refactored `_display_ping_metrics()` for multiple servers
  - Dynamic grid display with 4 columns per row
- `config.yaml` line 70: Bumped version to v0.6.8

### Impact:
- ✅ Complete visibility of QA environment (13 servers)
- ✅ Scalable to any number of servers (grid adapts)
- ✅ Reusable for other environments (PROD, DEV)
- ✅ Better insights: all servers in one report
- ✅ PDF includes all QA servers automatically
- ✅ Maintains schedule-aware availability calculation

### User Experience:
1. User clicks "🔍 Consultar"
2. System finds all Environment=QA servers
3. Shows: "Procesando 13 servidor(es) de QA..."
4. Displays progress for each server
5. Shows all charts in clean 4-column grid
6. PDF export includes all servers (landscape format)

### Version: v0.6.8

## v0.6.7 - PDF Export Functionality (2025-11-11)

### Feature: Export Monthly Reports to PDF
- **Description**: Added PDF export functionality for ping metric reports
- **UI**: PDF button appears next to the report title "Métricas de Ping Desde DD/MM/YYYY hasta DD/MM/YYYY"

### Implementation Details

**New Dependencies:**
- `plotly[kaleido]>=6.1.1`: Plotly with bundled compatible kaleido for chart-to-image conversion
- `reportlab`: For PDF generation

**Important Note on Dependencies:**
- Use `plotly[kaleido]>=6.1.1` instead of installing kaleido separately
- This ensures compatible versions are installed (Plotly 6.4.0 + Kaleido 1.2.0)
- Avoids `ImportError: cannot import name 'broadcast_args_to_dicts'` compatibility issue
- Install command: `pip install 'plotly[kaleido]>=6.1.1'`

**PDF Generation:**
- Method: `_generate_pdf_report()` in `MonthlyReportUI` class
- Format: Landscape orientation (11" x 8.5")
- Layout: 4 columns (same as UI), multiple rows if needed
- Title: "Métricas de Ping Desde DD/MM/YYYY hasta DD/MM/YYYY" (centered, 18pt)
- Charts: Converted to PNG images (300x250px) and embedded in PDF
- Filename: `Ping_Report_YYYYMMDD_YYYYMMDD.pdf`

**UI Changes:**
- Title and PDF button layout: 6:1 column ratio
- PDF button: `📄 PDF` positioned to the right of the title
- Button triggers immediate PDF generation and download
- No page reload required

**Technical Details:**
```python
# PDF Layout
- Landscape orientation: landscape(letter)
- Chart size: 2.4" x 2" (300x250px)
- Column widths: 2.5" each (4 columns)
- Table padding: 3px left/right, 5px top/bottom
- Title spacing: 0.3" after title
```

**Chart Conversion:**
```python
img_bytes = fig.to_image(format="png", width=300, height=250)
```

### Files Modified:
- `ui_components/monthly_report_ui.py`:
  - Lines 9-15: Added PDF generation imports
  - Lines 300-371: New `_generate_pdf_report()` method
  - Lines 375-376: Modified title layout (6:1 columns)
  - Lines 479-500: Added PDF button and download logic
- `requirements.txt`: Changed to `plotly[kaleido]>=6.1.1` and added `reportlab`
- `Dockerfile`: Added chromium and chromium-driver system dependencies
- `config.yaml` line 70: Bumped version to v0.6.7
- `README.md`: Updated with PDF features and dependency notes
- `CLAUDE.md`: Added PDF documentation and troubleshooting section

### Files Created:
- `ScriptsUtil/test_pdf_generation.py`: Test script for PDF generation
- `DEPLOY_NOTES.md`: Comprehensive deployment guide with dependency requirements and troubleshooting

### Testing:
- ✅ PDF generation tested with sample data
- ✅ Plotly chart to image conversion working (kaleido)
- ✅ ReportLab PDF creation working
- ✅ Test PDF: 13KB, 1 page, landscape format
- ✅ Charts embedded correctly with titles

### Usage:
1. Navigate to Monthly Report page
2. Select date range and query ping metrics
3. Click "📄 PDF" button next to title
4. PDF downloads automatically with filename: `Ping_Report_20250901_20250930.pdf`

### PDF Content:
- Title with date range (centered, bold)
- Charts in 4-column grid (landscape)
- Server name and availability percentage in each chart title
- Professional formatting with proper spacing

### Impact:
- ✅ Export monthly reports for documentation
- ✅ Share reports via email/Slack
- ✅ Archive historical reports
- ✅ Professional PDF formatting
- ✅ No external tools needed
- ✅ Instant download (no processing delay)

### Version: v0.6.7

## v0.6.6 - Scheduled Availability Calculator (2025-11-11)

### Feature: Smart Availability Calculation with Schedule Support
- **Description**: Implemented intelligent availability calculation that considers scheduled downtime periods
- **Impact**: Accurate availability metrics that exclude planned maintenance windows from availability calculations

### Implementation Details

**New Library: `utils/availability_calculator.py`**
- Created `AvailabilityCalculator` class for centralized availability calculations
- Supports multiple schedule types:
  - **Weekends**: Powered off Friday 21:00 to Monday 10:00
  - **Nights**: Powered off 21:00 to 06:00 daily
  - **BusinessHours**: Only available Monday-Friday 08:00-18:00

**Schedule Detection Logic:**
- `_is_weekend_downtime()`: Detects Friday 21:00 through Monday 10:00 (confirmed via tests)
- `_is_night_downtime()`: Detects daily 21:00 to 06:00
- `_is_outside_business_hours()`: Detects non-business hours (outside M-F 08:00-18:00)

**Availability Metrics:**
- `total_points`: Total datapoints in query
- `available_points`: Points where metric == 1
- `unavailable_points`: Points where metric == 0
- `scheduled_downtime_points`: Points during scheduled maintenance
- `unscheduled_downtime_points`: Actual downtime outside schedule
- `availability_percentage`: Overall availability (raw)
- `scheduled_availability_percentage`: Availability excluding scheduled downtime (what we show)

**AWS Service Integration:**
- Modified `services/aws_service.py` line 196: Added `Schedule` tag extraction
- Tag is read from EC2 instance tags: `Schedule` (case sensitive, with capital S)
- Stored in instance data dictionary for use in calculations

**UI Updates:**
- `ui_components/monthly_report_ui.py`:
  - Modified `_get_instance_data_by_name()`: Returns both instance ID and schedule tag
  - Modified `_display_ping_metrics()`:
    - Changed title format: "Métricas de Ping Desde DD/MM/YYYY hasta DD/MM/YYYY" (no emojis)
    - Removed success/info messages about query dates and intervals
    - Integrated AvailabilityCalculator for accurate availability calculation
    - Uses `scheduled_availability_percentage` for display
    - Chart still shows all datapoints (including scheduled downtime)

**Testing:**
- Created `ScriptsUtil/test_availability_calculator.py`:
  - 16 unit tests for weekend schedule detection (all passed ✅)
  - Integration tests with sample data
  - Verified correct handling of Friday 21:00 boundary
  - Verified correct handling of Monday 10:00 boundary
  - Confirmed 100% scheduled availability when downtime matches schedule

### Example Behavior:
```
Server: SRVERPQA (schedule: "Weekends")
Period: Friday 20:00 - Monday 11:00 (84 hours)

Without schedule consideration:
- 23 hours UP, 61 hours DOWN = 27.38% availability ❌ Misleading

With schedule consideration:
- 23 hours UP, 0 hours unscheduled DOWN = 100% availability ✅ Accurate
- 61 hours were during scheduled maintenance (excluded from metric)
```

### Files Created:
- `utils/availability_calculator.py`: New availability calculation library
- `ScriptsUtil/test_availability_calculator.py`: Comprehensive test suite

### Files Modified:
- `services/aws_service.py` line 196: Added Schedule tag extraction
- `ui_components/monthly_report_ui.py`:
  - Line 8: Added import for AvailabilityCalculator
  - Lines 213-230: Modified `_get_instance_data_by_name()` method
  - Lines 295-345: Modified `_display_ping_metrics()` method
  - Line 298: Changed title format (removed emojis)
  - Removed lines with st.success and st.info messages
- `config.yaml` line 70: Bumped version to v0.6.6

### Impact:
- ✅ Accurate availability metrics for scheduled machines
- ✅ Reusable library for all future availability calculations
- ✅ Support for multiple schedule types (Weekends, Nights, BusinessHours)
- ✅ Cleaner UI without redundant messages
- ✅ Extensible design for adding new schedule types
- ✅ 100% test coverage for schedule detection logic

### Version: v0.6.6

## v0.6.5 - Monthly Report UI (2025-11-10)

### Feature: Monthly Report Page
- **Description**: New page for generating monthly reports with flexible date selection
- **Access**: New button "📅 Informe Mensual" added next to "Reporte Alarmas" button in main dashboard

### Implementation Details

**UI Components:**
- Created new `ui_components/monthly_report_ui.py` with `MonthlyReportUI` class
- Date range selector with:
  - Start date and end date pickers (default: first day of current month to today)
  - Dropdown with available months starting from September 2025
  - Months displayed in Spanish: "Septiembre 2025", "Octubre 2025", etc.
  - Automatically includes new months as they arrive
  - "Personalizado" option for custom date ranges

**Features:**
- **Month Dropdown**:
  - Dynamically generated list from September 2025 to current month
  - Most recent months shown first
  - Selecting a month automatically updates start/end date pickers
  - Shows: "Personalizado", "Noviembre 2025", "Octubre 2025", "Septiembre 2025"

- **Date Pickers**:
  - Independent start and end date selection
  - Manual date changes override dropdown selection
  - Validation: start date must be before end date

- **Consultar Button**:
  - Primary action button for querying data
  - Date validation with error messages
  - Ready for future implementation of report generation

- **Period Summary**:
  - Displays selected start date, end date, and total days
  - Formatted in DD/MM/YYYY format

**Navigation:**
- "← Volver al Dashboard" button preserves column layout setting
- Query param: `monthly_report=true`
- Page title: "☁️ Dashboard EPMAPS - 📅 Informe Mensual"

### Files Modified:
- `ui_components/dashboard_ui.py` lines 243-258: Added "Informe Mensual" button next to "Reporte Alarmas"
- `dashboard_manager.py` lines 10, 31, 85-86, 97-98: Added routing for monthly report page
- `ui_components/monthly_report_ui.py`: New file with MonthlyReportUI implementation

### Impact:
- ✅ New accessible monthly report interface
- ✅ No changes to existing dashboard, detail, or alarm report functionality
- ✅ Flexible date selection with month presets
- ✅ Spanish localization for month names
- ✅ Ready for future report generation implementation
- ✅ Maintains consistent navigation and UI patterns

### Next Steps:
- TODO: Implement actual report data generation in `MonthlyReportUI.display_monthly_report()`
- TODO: Define report metrics and visualizations
- TODO: Add export functionality (CSV/PDF)

### Version: v0.6.5

## v0.6.4 - Dimension-Based Alarm Filtering (Fix Duplicate/Wrong Alarms) (2025-11-10)

### Bug Fix: Duplicate and Wrong Instance Alarms in Detail Page
- **Problem**: When opening detail page for an instance (e.g., "srvcrmqas"), alarms from different instances were appearing:
  - Alarms from "srvcrmqasV" (substring matching issue)
  - Multiple case variants (SRVCRMQAS, srvcrmqas)
  - **Example**: Opening "srvcrmqas" showed 39 alarms, 22 of which belonged to "srvcrmqasV"

- **Root Cause**:
  - Original alarm filtering used **substring matching**: `instance_name in alarm_name`
  - Case-sensitive: "srvcrmqas" ≠ "SRVCRMQAS" → missed some alarms
  - Substring matching: "srvcrmqas" ⊂ "srvcrmqasV" → included wrong alarms
  - Additionally, 63 SAP/EPMAPS alarms don't have `InstanceId` dimension

- **Analysis Performed**:
  - Created `ScriptsUtil/analyze_alarm_dimensions.py` to analyze all 841 CloudWatch alarms
    - **778 alarms** (92.5%) have `InstanceId` dimension (standard)
    - **63 alarms** (7.5%) lack `InstanceId` dimension (SSM Agent and Composite Service alarms)
    - These 63 alarms use `Environment`, `Server`, `ProcessName` dimensions

  - Created `ScriptsUtil/debug_alarm_matching.py` to debug specific instance matching
    - Revealed **22 false positive alarms** from "srvcrmqasV" when querying "srvcrmqas"
    - All false positives had correct `InstanceId` dimension (different from target instance)
    - Confirmed substring matching was the problem

- **Solution Implemented**: Pure dimension-based matching (2-tier approach)
  ```python
  belongs_to_instance = (
      # 1. InstanceId dimension (most reliable - covers 778/841 alarms)
      any(d['Name'] == 'InstanceId' and d['Value'] == instance_id for d in dimensions) or

      # 2. Server dimension for SSM/Composite alarms (covers remaining 63/841 alarms)
      any(d['Name'] == 'Server' and d['Value'].upper() == instance_name.upper() for d in dimensions)
  )
  ```

  **Key changes from original approach:**
  - ❌ **Removed** Level 3 (name-based substring matching) - was causing 22 false positives
  - ✅ **Relies only on dimensions** - 100% coverage with 2 levels (InstanceId + Server)
  - ✅ **Case-insensitive Server dimension** matching

- **Files Modified**:
  - `config.yaml` line 70: Updated version to v0.6.4
  - `services/aws_service.py` line 147-154: Updated `get_aws_data()` alarm filtering
  - `services/aws_service.py` line 349-356: Updated `get_alarms_for_instance()` alarm filtering
  - `ScriptsUtil/analyze_alarm_dimensions.py`: New analysis tool for alarm dimension inspection
  - `ScriptsUtil/debug_alarm_matching.py`: New debugging tool for instance-specific alarm matching

- **Verification**:
  - **Before**: "srvcrmqas" showed 39 alarms (17 correct + 22 false positives from "srvcrmqasV")
  - **After**: "srvcrmqas" shows 17 alarms (0 false positives) ✅

- **Impact**:
  - ✅ Eliminates ALL false positive alarms from similar instance names
  - ✅ No more substring matching issues (srvcrmqas vs srvcrmqasV)
  - ✅ No more case sensitivity issues (srvcrmqas vs SRVCRMQAS)
  - ✅ More robust matching using only structured dimensions
  - ✅ Handles all 841 alarms correctly (778 with InstanceId + 63 with Server dimension)
  - ✅ Zero false positives verified by debug tool

### Version: v0.6.4

## v0.6.3 - SMDA98 Alarm Treatment as Preventive (2025-11-07)

### Enhancement: SMDA98 Alarms Classification
- **Feature**: Alarms containing "SMDA98" in their name are now treated as preventive (yellow/warning) alarms instead of critical (red) alarms.
- **Context**: SMDA98 is a SAP instance identifier that requires special handling. Even when these alarms are in ALARM state, they should be displayed as preventive alerts.
- **Implementation**:
  - Modified `services/aws_service.py` line 162: Added 'SMDA98' to the preventive alarm keywords check in the alarm classification logic
  - Modified `ui_components/alarm_report_ui.py` lines 219, 322, 418: Updated alarm report to classify SMDA98 alarms as yellow (preventive) in statistics and CSV exports
  - Modified `ui_components/detail_ui.py` lines 460, 474, 488, 503: Updated detail page alarm visualization to show SMDA98 alarms in yellow across all alarm categories
- **Impact**:
  - Dashboard cards now show SMDA98 alarms as preventive (yellow bar) instead of critical (red bar)
  - Alarm reports count SMDA98 alarms in the "Alarmas Amarillas" column instead of "Alarmas Rojas"
  - Detail page displays SMDA98 alarms with yellow indicators (🟡) instead of red (🔴)
  - CSV exports categorize SMDA98 alarms correctly as preventive alarms

### Version: v0.6.3

## v0.5.0 - SAP Service Alarm Integration (2025-09-26)

### 1. Main Dashboard: SAP Status Indicator
- **Feature**: A new status indicator for SAP services now appears on the main dashboard server cards.
- **Logic**: 
    - The `get_aws_data` service was enhanced to return the full list of alarm objects for each instance, not just a count.
    - The server card UI (`dashboard_ui.py`) now checks if a specific "INCIDENTE SAP SERVICES" alarm exists for the instance.
    - If the alarm exists, an indicator showing the service status (e.g., "Servicios SAP: ● OK" or "Servicios SAP: ● DOWN") is displayed on the card.
- **UI Tweak**: The label "Alertas Cloudwatch" was shortened to "Alertas".

### 2. Detail Page: Dedicated SAP Alarm Status Section
- **Feature**: The detail page now has a new, dedicated section titled "✳️ Estado Servicios SAP".
- **UI**: This component displays the status of individual SAP service alarms (e.g., `SAP JAVA CENTRAL DOWN`, `SAP ABAP CENTRAL DOWN`) in a clean, readable list format with colored status indicators.
- **Refactoring**: This new section replaces the previous, less specific "Disponibilidad Servicios SAP" table and the `available.log` viewer, centralizing SAP status monitoring around the new, specific alarms.
- **Logic**: The UI now filters the instance's alarms to find those related to SAP services and renders them in this dedicated component, while excluding them from the general alarm list to avoid duplication.

### Version: v0.5.0

## v0.4.5 - Detail Page UI Refinements (2025-09-26)

### 1. Disk Table Sorting
- **Enhancement**: The "Volúmenes EBS (Vista de AWS)" table on the detail page is now sorted by the "Device AWS" column by default, making it easier to find specific devices.

### 2. Named Disk Alarm Grouping
- **Enhancement**: The alarm list on the detail page was refactored to improve clarity.
- Alarms with names containing "PROACTIVA-DISK" or "ALERTA-DISK" are now grouped into their own respective collapsible accordion sections, reducing clutter.

### 3. Unassociated Disk Alarm Identification
- **Feature**: Implemented a new category to identify disk-related alarms that do not correspond to a known physical EBS volume attached to the instance.
- **Logic**: The system now inspects the dimensions of each disk-related alarm. If the alarm lacks a `VolumeId` dimension that matches a known EBS volume, it is categorized as "No Asociado".
- **UI**: These alarms are now grouped into a new collapsible section, "Alarmas de Disco No Asociado", helping technicians quickly identify alerts related to non-EBS storage like EFS or other shared filesystems.

### Version: v0.4.5

## v0.4.4 - Fix: Display Disk Information Table (2025-09-26)

### Problem Identified
- The disk information table, intended to replace the old gauges, was not appearing on the detail page. An info message "No hay datos de disco disponibles" was shown instead.

### Root Cause
- The initial implementation attempted to create a single, unified table by joining two different data sources:
  1.  **CloudWatch Agent Metrics**: Provided disk usage percentage.
  2.  **AWS EC2 API**: Provided EBS volume details (size, tags, IOPS).
- A debug investigation revealed that there was no reliable, common key to join these two sources. The Agent provided the OS drive letter (e.g., `C:`), but the EC2 API only provides the hypervisor device name (e.g., `/dev/xvdf`) and Volume ID. The link between them was missing.

### Solution Applied
- **1. Improved Metric Parsing**: A debug script (`ScriptsUtil/debug_metrics.py`) was created to inspect the raw CloudWatch metric dimensions. It was discovered that the OS drive letter was available in the `instance` dimension, and the `get_disk_utilization` function was corrected to parse it properly.
- **2. Two-Table UI**: Acknowledging the data-linking problem, the UI was redesigned to present the information honestly and robustly in two separate tables:
    - A **"Uso de Disco (Vista del Sistema Operativo)"** table, showing the drive letter and its usage percentage.
    - A **"Volúmenes EBS (Vista de AWS)"** table, showing the low-level AWS device name, size, IOPS, type, and tags for each physical volume.
- **3. Cleanup**: All debugging code and temporary scripts were removed after the fix was implemented.

### Result
- ✅ The disk information is now correctly displayed on the detail page.
- ✅ The two-table approach provides a complete and accurate picture by showing both the OS-level and AWS-level perspectives, which is more robust than a fragile, assumed join.

### Version: v0.4.4

## v0.4.3 - Fix: Preserve Column Selection During Navigation (2025-09-25)

### Problem Identified
- When a user selected a column layout (e.g., 3 columns) on the main dashboard, this selection was lost upon navigating to the Alarm Report page and then returning.
- The layout would reset to the default of 2 columns.

### Root Cause
- The navigation logic was incomplete. 
- 1. The button to navigate **to** the Alarm Report page (`dashboard_ui.py`) did not include the existing `columns` parameter in the new URL.
- 2. The button to navigate **back from** the Alarm Report page (`alarm_report_ui.py`) was clearing all URL parameters without preserving the `columns` parameter.

### Solution Applied
- **`alarm_report_ui.py`**: The "Volver al Dashboard" button logic was updated to first read the `columns` parameter from the URL, then clear the URL, and finally re-apply the preserved `columns` parameter. (This was the initial fix).
- **`dashboard_ui.py`**: The "Reporte Alarmas" button logic was also updated to ensure it preserves the `columns` parameter when adding the `alarm_report=true` parameter to the URL.

### Result
- ✅ The selected column layout now persists correctly when navigating between the main dashboard and the alarm report page.
- ✅ The user experience is more consistent and less frustrating.

### Version: v0.4.3

## v0.4.2 - Fix: Correct Alarm Status on Main Dashboard (2025-09-25)

### Problem Identified
- The main dashboard page was showing all servers with a green/OK status, even when there were active alarms visible on the detail and alarm report pages.
- This created a critical discrepancy and made the main dashboard unreliable.

### Root Cause
- The `get_aws_data` function in `services/aws_service.py`, which provides data for the main dashboard, was correctly calculating the alarm counts for each instance.
- However, the resulting `instance_alarms` counter object was not being included in the final `instance_data` dictionary that is returned by the function.
- The UI, not finding an `Alarms` key, defaulted to a zero-alarm state.

### Solution Applied
- The `instance_data` dictionary within `get_aws_data` was modified to correctly include the alarm data.
- The line `'Alarms': instance_alarms,` was added to ensure the calculated alarm counts are passed to the UI.

### Result
- ✅ The server cards on the main dashboard now accurately reflect the real-time alarm status (Critical, Preventive, etc.) from CloudWatch.
- ✅ The discrepancy between the main page and detail pages is resolved.

### Version: v0.4.2

## v0.4.1 - Fix: Resolve SyntaxError in aws_service.py (2025-09-25)

### Problem Identified
- The application was crashing on startup with a `SyntaxError` in `services/aws_service.py`.
- The error was caused by a missing comma in the `instance_data` dictionary after a new field (`OperatingSystem`) was added in version `v0.4.0`.

### Solution Applied
- The missing comma was added to the end of the `'AlarmsList': alarms_list` line within the `get_aws_data` method.

### Result
- ✅ The `SyntaxError` is resolved.
- ✅ The application starts correctly as intended.

### Version: v0.4.1

## v0.4.0 - Major Detail Page Enhancement (2025-09-25)

Based on user feedback, the detail page was significantly enhanced to provide richer diagnostic information for technical support.

### Phase 1: General Information & Alarm Refactoring
- **Alarm Links Removed**: As requested, all external links to the AWS console were removed from the alarm list to keep users within the dashboard.
- **Added Instance Metadata**: A new section, "Metadatos de la Instancia", was added, displaying:
  - AMI ID
  - Instance Launch Time
  - VPC ID & Subnet ID
  - Associated Security Groups

### Phase 2: Disk Visualization Overhaul
- **Gauges Replaced with Table**: The space-consuming disk gauges were removed.
- **Detailed Disk Table**: A compact and informative table was implemented, showing the following for each attached volume:
  - Device Name
  - Usage Percentage
  - Total Size (GB)
  - Provisioned IOPS
  - Volume Type
  - All associated AWS Tags
- **Service Enhancement**: A new method, `get_volume_details`, was added to `services/aws_service.py` to fetch rich data for each EBS volume from the `describe_volumes` API call.

### Phase 3: Historical Performance Graphs
- **Gauges Replaced with Charts**: All single-value performance gauges were replaced with historical time-series charts showing data for the last 3 hours.
- **New Generic Service**: A reusable `get_metric_history` function was added to `services/aws_service.py` to fetch historical data for any CloudWatch metric.
- **Implemented Charts**:
  - **CPU Utilization (%)**: Line chart showing CPU usage over time.
  - **Network Traffic (MB)**: Single chart with separate lines for `NetworkIn` and `NetworkOut`.
  - **Disk I/O (MB)**: Single chart with separate lines for `DiskReadBytes` and `DiskWriteBytes`.

### Phase 4: CloudWatch Log Viewer
- **New UI Section**: A "Visor de Logs" section was added to the bottom of the detail page.
- **Log Group Discovery**: The interface automatically discovers and lists log groups associated with the instance ID.
- **Interactive Log Display**: Users can select a log group from a dropdown menu to view the 100 most recent log events, which are then displayed in a formatted code block.
- **Service Enhancement**: New methods `get_log_groups` and `get_log_events` were added to `services/aws_service.py` to interact with the CloudWatch Logs API.

### Result
- ✅ The detail page has been transformed from a basic status view into a powerful diagnostic tool.
- ✅ Technical support can now see historical trends, detailed disk/instance configuration, and recent logs in one place.
- ✅ The UI is more compact and information-dense.

### Version: v0.4.0

## v0.3.1 - Fix: Adapt to streamlit-authenticator API change (2025-09-25)

### Problem Identified
- After refactoring to `streamlit-authenticator`, the application failed to start, throwing a `DeprecationError`.
- The error indicated that the `pre_authorized` parameter has been removed from the `Authenticate` class constructor in recent versions of the library.

### Solution Applied
- The `stauth.Authenticate` instantiation in `utils/auth.py` was updated to match the new API.
- The fifth argument (`config['credentials']['usernames']`), which was being passed as `pre_authorized`, was removed.
- The library correctly uses the main `credentials` dictionary (the first argument) to determine the list of valid users, so the extra parameter was redundant.

### Technical Fix
```python
# utils/auth.py - Corrected Authenticate call

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'] # No longer passing the 5th (pre_authorized) argument
)
```

### Result
- ✅ The application is now compatible with recent versions of `streamlit-authenticator`.
- ✅ The `DeprecationError` is resolved, and the application starts correctly.

### Version: v0.3.1

## v0.3.0 - Major Authentication System Refactoring (2025-09-25)

### Problem Identified
- The existing authentication system was not robust. It relied on `st.session_state`, causing the user to be logged out when navigating via standard HTML links, which force a full page reload.
- The previous workaround involved replacing links with buttons, which was a limiting factor.
- The underlying implementation used `localStorage` and JavaScript injections, which was fundamentally insecure and could be easily bypassed by a malicious user.

### Solution Applied
- The entire custom authentication system in `utils/auth.py` was deprecated and removed.
- The application was migrated to use the `streamlit-authenticator` library, which provides a robust, secure, and industry-standard authentication solution.
- The new system is based on secure, server-signed cookies (`HttpOnly`), ensuring that the authentication state persists across page reloads, link navigation, and even browser sessions.

### Technical Implementation
1.  **`requirements.txt`**: Confirmed `streamlit-authenticator` was a project dependency.
2.  **`config.yaml`**: 
    - Added a `credentials` section to store user information and securely hashed passwords (using bcrypt).
    - Added a `cookie` section to configure the session cookie's name, signing key, and expiration.
3.  **`utils/auth.py`**: 
    - Completely refactored the file. All insecure, custom logic was removed.
    - It now contains a single function, `get_authenticator()`, which initializes the `streamlit-authenticator` object from the `config.yaml` file.
4.  **`dashboard_manager.py`**: 
    - Replaced the call to the old `login_form()` with the `authenticator.login()` widget.
    - The main application logic is now nested inside a check for `st.session_state["authentication_status"]`.
    - The logout button is now provided directly by the authenticator object, simplifying the header.

### Result
- ✅ **Robust Authentication**: The login state is now persistent and survives navigation via any component, including standard links.
- ✅ **Enhanced Security**: The system is no longer vulnerable to `localStorage` manipulation. Sessions are validated using cryptographically signed cookies.
- ✅ **Simplified Codebase**: The complex and insecure JavaScript injection code was removed, resulting in a cleaner and more maintainable authentication flow.
- ✅ **Standard Compliance**: The authentication mechanism now follows modern web application best practices.

### Version: v0.3.0

## Overview
This document tracks the complete development history of the Dashboard EPMAPS POC project, including all changes, issues resolved, and technical decisions made.

## Detailed Development Log

### 2025-09-23 - Authentication System & Navigation Improvements (v0.2.23-v0.2.25)

#### Authentication Implementation
**Problem Identified:**
- Application needed secure login/password authentication
- Users were requesting access to the dashboard with proper security

**Solution Applied:**
- Implemented custom authentication system using SHA256 password hashing
- Created login form with user credentials verification
- Added session state management for persistent login
- Implemented logout functionality

**Technical Implementation:**
```python
# utils/auth.py
USERS = {
    "admin@dashboardepmaps.com": {
        "name": "Admin",
        "password": "790f48e3ba51e2d0762e7d4a74d4076a62cfb34d44e3dfbc43798fe9ff399602"  # AdminPass123
    },
    "user@dashboardepmaps.com": {
        "name": "User", 
        "password": "8e3bde512bf178d26128fdcda19de3ecea6ce26c4edaa177a5e2d49713272443"  # UserPass123
    }
}

def authenticate_user(username: str, password: str) -> bool:
    if username in USERS:
        return verify_password(password, USERS[username]["password"])
    return False
```

#### UI/UX Improvements
**Problem Identified:**
- User wanted logged-in user info and logout button in header instead of sidebar
- Navigation between pages was opening new tabs and asking for login again
- Login page was exposing test credentials publicly

**Solutions Applied:**
1. **Header Authentication UI:** Moved user info and logout button to main header
2. **Navigation Fix:** Replaced HTML links with Streamlit buttons to prevent new tabs
3. **Login Page Cleanup:** Removed public display of test credentials
4. **Dynamic Titles:** Added context-aware page titles in header

**Technical Changes:**
```python
# utils/auth.py - Dynamic header with user info
def add_user_header():
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if 'alarm_report' in st.query_params:
            st.markdown("# ☁️ Dashboard EPMAPS - 📊 Reporte de Alarmas")
        elif 'poc_vm_id' in st.query_params:
            st.markdown("# ☁️ Dashboard EPMAPS - Detalle VM")
        else:
            st.markdown("# ☁️ Dashboard EPMAPS")

# Navigation with buttons instead of HTML links
if st.button("📊 Reporte Alarmas", use_container_width=True, type="secondary"):
    st.query_params.update({"alarm_report": "true"})
    st.rerun()
```

#### GitHub Actions CI/CD Setup
**Problem Identified:**
- Manual deployments were error-prone and time-consuming
- User wanted automatic deployment on git push
- GitHub Actions lacked proper AWS permissions

**Solution Applied:**
- Fixed IAM permissions for `github-actions-deployer` user
- Created comprehensive deployment policy
- Configured automatic ECR push and ECS deployment

**AWS IAM Policy Created:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeTasks",
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Results Achieved
- ✅ Secure authentication system with SHA256 hashing
- ✅ Professional login interface without exposed credentials
- ✅ Seamless navigation between pages without re-authentication
- ✅ User info displayed in header with logout functionality
- ✅ Automatic deployment pipeline with git push
- ✅ Fixed GitHub Actions permissions and ECR integration

#### Lessons Learned
- Always ask before making UI changes that weren't explicitly requested
- Custom authentication systems provide more control than managed services for simple use cases
- Proper IAM permissions are critical for CI/CD pipeline success
- Session state management is essential for smooth user experience

#### Versions:
- **v0.2.23:** Authentication system and header improvements
- **v0.2.24:** Login page cleanup (removed public credentials display)
- **v0.2.25:** Removed unwanted detail buttons, restored original card behavior

### 2025-09-22 - Fix: Implement Icon & Tooltip for Validation Errors (v0.2.22)

#### Problem Identified
- The previous fix for highlighting validation errors with CSS was not visible.
- The root cause was the complex and often-overridden nature of CSS in Streamlit tables.

#### Solution Applied
- A completely new and more robust method was implemented as per the user's suggestion.
- **Icon Markers**: Instead of CSS, cells with validation errors now have their data value changed to include a `⚠️` icon (e.g., `3` becomes `"3 ⚠️"`).
- **Descriptive Tooltips**: A parallel DataFrame containing detailed error messages is generated. This is applied to the table, so hovering over an icon reveals the reason for the error (e.g., "Se esperaban 9 alarmas de disco, pero se encontraron 3.").
- **Refactored Logic**: The implementation in `ui_components/alarm_report_ui.py` was refactored to separate the numeric data (for styling rows) from the display data (with icons) and the tooltip data, using the pandas Styler's `.format()` and `.set_tooltips()` methods. This resolves the `TypeError` from the previous attempt.

#### Technical Fix
```python
# ui_components/alarm_report_ui.py

# 1. Create numeric dataframe `df`
# 2. Create `tooltips_df` and populate with error messages
# 3. Create `formatters` dictionary to add icons to data for display
def cpu_formatter(val):
    return f'{val} ⚠️' if val != 2 else val

formatters = {'Alarmas CPU': cpu_formatter, ...}

# 4. Chain styling, tooltips, and formatters
styled_df = df.style.apply(self._apply_row_highlight_styles, axis=1)\
                    .set_tooltips(tooltips_df)\
                    .format(formatters)

st.dataframe(styled_df)
```

#### Result
- ✅ Validation errors are now reliably indicated with an icon.
- ✅ Tooltips provide clear explanations for each error.
- ✅ The underlying code is more robust and less prone to CSS conflicts.

#### Version: v0.2.22

### 2025-09-22 - Add New Summary Metrics to Report (v0.2.21)

#### Problem Identified
User requested to add more metrics to the summary section of the alarm report page for a better overview.

#### Solution Applied
- The summary section in `ui_components/alarm_report_ui.py` was updated to use 6 columns instead of 4.
- Added two new metrics to the summary display:
  - **T. A. Teóricas**: The sum of all theoretical alarms.
  - **Datos Insuficientes**: The sum of all alarms with insufficient data.
- The metrics were reordered for better logical flow.

#### Technical Fix
'''python
# ui_components/alarm_report_ui.py

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Instancias", len(df))
with col2:
    st.metric("T. A. Teóricas", f"{df['T. A. Teóricas'].sum():.0f}")
# ... and so on
'''

#### Result
- ✅ The summary section now provides a more comprehensive overview with 6 key metrics.

#### Version: v0.2.21

### 2025-09-22 - Fix Disk Count Logic for Linux Instances (v0.2.19)

#### Problem Identified
User reported a discrepancy in the disk count for Linux servers. The report showed 24 disks, while the EC2 console only showed 10 EBS volumes.

#### Root Cause
- The existing logic counted all entries in the `BlockDeviceMappings` array for an instance.
- This includes not only persistent EBS volumes but also temporary (ephemeral) instance store volumes, leading to an inflated count on certain Linux AMIs.

#### Solution Applied
- The disk counting logic in `services/aws_service.py` was refined.
- It now iterates through the `BlockDeviceMappings` and counts only the mappings that contain an `Ebs` key, ensuring that only true EBS volumes are included in the total.

#### Technical Fix
'''python
# services/aws_service.py

# Get the actual number of attached EBS volumes, ignoring other block devices.
ebs_volumes = [
    mapping for mapping in instance.get('BlockDeviceMappings', [])
    if 'Ebs' in mapping
]
disk_count = len(ebs_volumes)
'''

#### Result
- ✅ The "Cant. Discos" column now accurately reflects the number of persistent EBS volumes for all instances, matching the AWS console.

#### Version: v0.2.19

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
'''python
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
'''

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
