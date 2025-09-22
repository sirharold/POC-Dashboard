# Dashboard EPMAPS POC - Development History

## Overview
This document tracks the complete development history of the Dashboard EPMAPS POC project, including all changes, issues resolved, and technical decisions made.

## Detailed Development Log

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
```python
@st.cache_resource(ttl=60)  # Reduced from 900 to 60 seconds
def get_cross_account_boto3_client_cached(service, role_arn=None):
```

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
```python
# Clean DashboardGroup value to remove extra whitespace
dashboard_group = tags.get('DashboardGroup', 'Uncategorized').strip()
```

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
```python
# Yellow alarm detection now includes PREVENTIVA
if alarm_state == 'ALARM' and ('ALERTA' in alarm_name.upper() or 
                               'PROACTIVA' in alarm_name.upper() or 
                               'PREVENTIVA' in alarm_name.upper()):
    instance_alarms['PREVENTIVE'] += 1
```

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
```
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
```

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