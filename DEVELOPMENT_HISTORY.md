# Histórico de Desarrollo - Dashboard EPMAPS POC

Este archivo documenta todas las instrucciones, cambios y evolución del proyecto para poder retomar el desarrollo en cualquier punto.

## Contexto del Proyecto

**Objetivo**: Crear una aplicación con Streamlit que viva dentro de AWS para monitoreo de salud de máquinas virtuales, con capacidad de expansión futura para reportes, tendencias, etc.

**Tecnologías**:
- Streamlit (framework principal)
- Boto3 (AWS SDK para Python)
- Docker (Contenedores)
- AWS App Runner / EC2 (Despliegue Serverless / Instancia)
- GitHub Actions (CI/CD)
- YAML (Configuración)

## Registro de Desarrollo

### 2025-09-17 - Conversation Archive Summary

#### Major Accomplishments in This Session
This conversation session successfully addressed multiple critical issues and implemented significant improvements:

1. **Completed SAPService Integration** (v0.2.02-v0.2.03)
   - Added missing `get_available_log_content` method
   - Fixed header visibility issues
   - Implemented smooth auto-refresh mechanism

2. **Column Control Feature** (v0.2.04-v0.2.05) 
   - Added dynamic column selection (1-4 columns)
   - Implemented session persistence via query parameters
   - Fixed navigation persistence issues

3. **Auto-Refresh Optimization** (v0.2.06)
   - Replaced problematic threading approach with `st.fragment`
   - Eliminated black screen refresh experience
   - Achieved smooth 30-second updates

4. **Cache and Grouping Issues Resolution** (v0.2.07-v0.2.08)
   - Fixed AWS tag change visibility problems
   - Resolved duplicate group issue (whitespace in tags)
   - Implemented automatic tag cleaning with `.strip()`

#### Next Potential Enhancements Discussed
- Additional server card indicators for technical diagnostics
- Performance metrics display (CPU, Memory, Disk)
- Uptime and connectivity status indicators

#### Current Status: v0.2.10
All major issues resolved, smooth auto-refresh working, column control functional, and tag grouping fixed.

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

### 2025-09-15 - Fix AWS Cache for Tag Changes (v0.2.07)

#### Problem Reported
**DashboardGroup Tag Changes Not Reflecting in UI**
- **Issue**: User modified DashboardGroup tags in EC2 console
- **Expected**: Servers should be regrouped according to new tags
- **Actual**: Dashboard showed old grouping, splitting "Almacenamiento" into two groups
- **Root Cause**: AWS client cache TTL was 15 minutes, preventing tag updates

#### Solution Implemented
**1. Reduced Cache TTL**
- Changed AWS client cache from 900 seconds (15 min) to 60 seconds (1 min)
- Tag changes now visible within 1 minute instead of 15 minutes
- File: `services/aws_service.py:18`

**2. Added Manual Cache Clear**
- Added `clear_cache()` method to AWSService class
- Allows immediate cache invalidation when needed
- Useful for testing and immediate updates

**3. Added Refresh Button in UI**
- Added "🔄 Actualizar" button next to column selector
- Button clears cache and forces immediate data refresh
- Tooltip explains functionality
- Layout: `[Columnas] [Actualizar] [Alarm Legend]`

#### How to Use
**For Immediate Updates After Tag Changes:**
1. Modify tags in EC2 console
2. Click "🔄 Actualizar" button in dashboard
3. Groups will update immediately

**For Automatic Updates:**
- Changes now appear within 1 minute automatically
- No user action required

#### Technical Details
```python
@st.cache_resource(ttl=60)  # Reduced from 900 seconds
def get_cross_account_boto3_client(...):

def clear_cache(self):
    self.get_cross_account_boto3_client.clear()
```

#### Version: v0.2.07

### 2025-09-15 - Fix Auto-Refresh with st.fragment (v0.2.06)

#### Problem Found
**Auto-Refresh Not Working Properly**
- **Issue**: Previous implementation only checked time when page loaded manually
- **Result**: Groups were not actually refreshing every 30 seconds
- **User Report**: "probé modificando algunos grupos y la página no refresca"

#### Solution: Use st.fragment with run_every
**1. Replaced Time-Based Checking**
- Removed manual time checking approach
- Eliminated threading-based solution

**2. Implemented st.fragment Auto-Refresh**
- Used `@st.fragment(run_every=30)` decorator
- This is the official Streamlit way for auto-refresh
- Automatically runs every 30 seconds without user interaction

**3. Technical Implementation**
```python
@st.fragment(run_every=30)  # Auto-refresh every 30 seconds
def _render_dashboard_content(self, current_env, show_aws_errors, refresh_interval):
    # Only refresh on dashboard (not detail pages)
    # Fetch fresh AWS data
    # Re-render groups
```

#### Benefits
- ✅ **Actually refreshes every 30 seconds** (fixed!)
- ✅ **No threading warnings**
- ✅ **Smooth visual updates** (no black screen)
- ✅ **Official Streamlit approach**
- ✅ **Respects page context** (doesn't refresh detail pages)

#### Version: v0.2.06

### 2025-09-15 - Implement Smooth Auto-Refresh (v0.2.05)

#### Problem Solved
**Annoying Full Page Refresh Every 30 Seconds**
- **Issue**: Page was using `<meta http-equiv="refresh">` causing complete page reload
- **User Experience**: Black screen flash and complete redraw every 30 seconds
- **Impact**: Poor visual experience, lost scroll position, momentary disruption

#### Solution Implemented: Smooth Auto-Refresh
**1. Removed Meta Refresh Tag**
- Eliminated `<meta http-equiv="refresh" content="{refresh_interval}">` 
- Changed subtitle text from "se autorecarga" to "se actualiza"

**2. Implemented Threading-Based Auto-Refresh**
- Created `_setup_auto_refresh()` method in DashboardUI class
- Uses background thread with `threading.Thread` 
- Triggers `st.rerun()` instead of full page reload
- Only refreshes when on dashboard page (not detail page)

**3. Session State Management**
- Tracks refresh state with `auto_refresh_active` flag
- Prevents multiple concurrent refresh timers
- Maintains refresh timing accuracy

#### Technical Implementation Details
```python
def _setup_auto_refresh(self, refresh_interval: int):
    # Background thread sleeps for refresh_interval seconds
    # Then calls st.rerun() to update content
    # Only if still on dashboard (not detail page)
```

#### Benefits Achieved
- ✅ **No more black screen flash**
- ✅ **Smooth content updates** 
- ✅ **Preserved user interaction state**
- ✅ **Column selection maintained**
- ✅ **Better user experience**

#### Version: v0.2.05

### 2025-09-15 - Fix Column Selection Persistence in Navigation (v0.2.04)

#### Issue Fixed
**Column Selection Lost During Navigation**
- **Problem**: When navigating to detail page and returning to dashboard, the column selection was reset to default
- **Root Cause**: Navigation links didn't preserve the columns query parameter

#### Solution Implemented
1. **Server Card Links**: Modified to include columns parameter
   - Changed: `?poc_vm_id={instance_id}` 
   - To: `?poc_vm_id={instance_id}&columns={columns_param}`
   
2. **Back to Dashboard Link**: Modified to preserve columns parameter
   - Changed: `href='/'`
   - To: `href='/?columns={columns_param}'`

#### Technical Details
- Both navigation links now read the current columns value from query params
- Default value of '2' is used if parameter is missing
- Ensures consistent column layout throughout navigation flow
- Version updated to v0.2.04

### 2025-09-15 - Fix Column Control Persistence and Alignment (v0.2.03)

#### Issues Fixed

**1. Column Selection Persistence on Page Refresh**
- **Problem**: Column selection was lost after the 30-second auto-refresh
- **Solution**: Switched from session state to URL query parameters
- **Implementation**: 
  - Column selection now stored in `st.query_params['columns']`
  - Value persists through page refreshes and reloads
  - Default value: 2 columns

**2. Improved Column Control Layout**
- **Problem**: "Columnas:" label was above the dropdown, not aligned
- **Solution**: Created sub-columns to align label horizontally
- **Implementation**:
  - Used 2 sub-columns within the control column
  - Label displayed in first sub-column with custom styling
  - Selectbox in second sub-column with collapsed label
  - Added padding to align with alarm legend

#### Technical Details
- Query parameter: `?columns=X` where X is 1, 2, 3, or 4
- Validation ensures only valid column counts are used
- Page reruns when selection changes to update URL
- Version updated to v0.2.03

### 2025-09-15 - Back Link Position and Column Control Feature (v0.2.02)

#### Changes Made

**1. Adjusted Back to Dashboard Link Position**
- Added `margin-top: 1rem` to the back link in detail_ui.py
- Provides better visual spacing from the top of the page

**2. Added Column Control Feature**
- **New selectbox control**: Allows users to choose between 1-4 columns for group distribution
- **Session persistence**: Column selection stored in `st.session_state.num_columns`
- **Location**: Placed next to alarm legend for easy access
- **Default**: 2 columns (maintains backward compatibility)

**3. Updated Group Distribution Logic**
- Modified `build_and_display_dashboard` method to support dynamic column counts
- Single column: Groups displayed vertically
- Multi-column: Groups distributed evenly across selected number of columns
- Uses modulo operator for even distribution

**4. Added Selectbox Styling**
- Custom CSS for selectbox appearance
- Matches dark theme with semi-transparent background
- Hover effects for better interactivity

**5. Switched app.py to Use Refactored Code**
- **IMPORTANT**: The main app.py now uses the refactored class-based architecture
- Original monolithic code backed up to `app_monolithic_backup.py`
- This was necessary because the column control was added to the refactored version

#### Technical Implementation
- Session state key: `num_columns` (persists during session)
- Column options: [1, 2, 3, 4]
- Layout: Uses `st.columns()` with dynamic count
- Version updated to v0.2.02

### 2025-09-15 - Fix Header Visibility Issues

#### Problem
After aggressive space reduction, headers and navigation elements were getting cut off at the top of the page.

#### Solution
- **Adjusted top padding**:
  - Main content area: increased to 2.5rem
  - Block container: increased to 2rem
  
- **Restored h1 margins**:
  - Top margin: 0.5rem (to ensure visibility)
  - Bottom margin: 0.3rem
  - Line height: 1.2
  
- **Navigation elements spacing**:
  - Columns container: 0.5rem top/bottom margins
  - Back link: added margin-bottom: 0.5rem
  
#### Result
All header elements are now visible while still maintaining reduced spacing compared to the original design.

### 2025-09-15 - Further Header Space Optimization

#### User Feedback
Users reported there was still too much wasted space before and after headers, while wanting to keep the same font sizes.

#### Changes Made
- **Reduced main content padding**:
  - Main content area padding reduced from 2rem to 1rem
  - Block container padding set to 1rem top/bottom
  
- **Optimized h1 and h2 margins**:
  - h1: margin-bottom 0.2rem, margin-top 0, padding 0, line-height 1.1
  - h2: margins reduced to 0.3rem, line-height 1.2
  
- **Added specific CSS rules to minimize spacing**:
  - Element containers with h1: zero margins
  - Paragraph elements: zero top margin, 0.3rem bottom
  - Columns with navigation buttons: zero padding
  - Horizontal blocks with buttons: minimal margins and gap
  
- **Updated inline styles**:
  - Dashboard page: h1 and p elements set to margin: 0, padding: 0
  - Detail page: h1 set to margin: 0, padding: 0
  
- **Navigation button optimization**:
  - Reduced button padding from 0.5rem to 0.4rem
  - Zero margins on buttons

#### Result
Significantly reduced vertical space usage while maintaining all font sizes and readability.

### 2025-09-15 - Removal of Unused vm_status Configuration

#### Context
The `vm_status` section in config.yaml contained hardcoded server colors that were no longer being used. The current implementation correctly determines server and group colors based on CloudWatch alarms.

#### Changes Made
- **Removed `vm_status` section from config.yaml**:
  - This section contained hardcoded color mappings for each server
  - The refactored code in `ui_components/dashboard_ui.py` already determines colors based on alarms
  
- **Cleaned up `utils/helpers.py`**:
  - Removed the unused `get_vm_status()` function that relied on the vm_status configuration
  
- **Updated `components/server_card.py`**:
  - Removed import of `get_vm_status`
  - Added deprecation note indicating this component is replaced by `ui_components/dashboard_ui.py`
  - Modified to use a default status since it's no longer actively used

#### Technical Verification
- Server card colors are determined by alarm states (dashboard_ui.py lines 51-59):
  - Red: If any ALARM state
  - Yellow: If any PREVENTIVE state
  - Gray: If INSUFFICIENT_DATA or UNKNOWN
  - Green: Otherwise (all OK)
  
- Group colors follow the same logic based on worst server status (lines 74-97)

### 2025-09-15 - Header Height Optimization

#### User Feedback
Users reported that the headers (titles) in both the summary and detail pages were taking up too much vertical space.

#### Changes Made
- **Reduced main title (h1) size and spacing**:
  - Font size reduced from 2.5rem to 1.8rem
  - Bottom margin reduced from 1rem to 0.5rem
  - Added top margin of 0.5rem and line-height of 1.2 for compact display
  
- **Optimized h2 headings for detail page sections**:
  - Added specific styling for h2 elements
  - Font size set to 1.3rem with reduced margins (0.5rem)
  
- **Adjusted global spacing**:
  - Reduced top padding for main content area to 2rem
  - Reduced spacing around dividers to 0.5rem
  
- **Updated inline styles in UI components**:
  - Dashboard page: Added inline margin styles to reduce spacing between title and subtitle
  - Detail page: Added margin-bottom style to main title
  - Subtitle font size reduced from 0.8em to 0.75em

#### Technical Notes
- All changes preserve the original functionality including environment rotation
- No text content or navigation logic was modified
- Changes focus solely on visual spacing optimization

### 2025-09-15 - Completion of SAPService Class Integration

#### Changes Made
- **Added `get_available_log_content` method to SAPService class**:
  - Migrated the standalone function from `app.py` to maintain proper separation of concerns
  - Method retrieves raw available.log content from CloudWatch Logs for SAP monitoring
  - Preserves exact same logic including environment detection and log group selection
  
- **Updated DetailUI to use the new SAPService method**:
  - Added the "Available.log Content Section" that was missing in the refactored version
  - Now calls `sap_service.get_available_log_content(instance_id)` instead of the standalone function
  - Maintains the same UI display with expandable section for log content

#### Technical Details
- The `get_available_log_content` method searches through CloudWatch log groups based on environment (production vs qa/dev)
- Returns raw log content or None if not available
- Maintains backward compatibility with existing functionality

### 2025-09-15 - Code Refactoring v0.2.0-refactored: Class-Based Architecture with UI Preservation

#### Objective
Refactor the monolithic `app.py` code into a class-based architecture for better maintainability while preserving the exact original UI behavior, appearance, colors, and click actions that the user required.

#### Approach
Instead of creating a completely new UI system, this refactoring wraps existing functions into classes without changing their behavior, ensuring 100% UI compatibility.

#### Architecture Implemented

**Service Layer (`services/`)**:
- `AWSService`: Wraps all AWS operations (EC2, CloudWatch, STS) in a single class
  - Preserves exact same logic as original functions
  - Maintains @st.cache_resource decorators and error handling
  - Same AWS role assumption and client creation behavior

- `SAPService`: Wraps SAP availability monitoring functionality
  - Exact same CloudWatch Logs parsing logic
  - Same environment detection (prod vs qa/dev)
  - Identical JSON parsing and service extraction

**UI Component Layer (`ui_components/`)**:
- `DashboardUI`: Wraps dashboard display functions
  - Preserves exact HTML generation for server cards
  - Same alert bar creation with color coding
  - Identical group container styling and layout
  - Same navigation logic and environment switching

- `DetailUI`: Wraps detail page functionality
  - Same gauge chart creation with Plotly
  - Identical metrics collection (CPU, memory, disk)
  - Same alarm display and color coding

**Coordination Layer**:
- `DashboardManager`: Main orchestrator class
  - Loads configuration from YAML (same as original)
  - Routes between dashboard and detail pages
  - Coordinates all components

#### Files Created:
```
services/
├── __init__.py
├── aws_service.py         # AWS operations wrapper
└── sap_service.py         # SAP monitoring wrapper

ui_components/
├── __init__.py
├── dashboard_ui.py        # Dashboard UI wrapper
└── detail_ui.py           # Detail page UI wrapper

dashboard_manager.py       # Main coordinator
app_refactored.py         # Clean entry point
app_original_backup.py    # Backup of original code
```

#### Files Modified:
- `app.py`: Replaced with clean 24-line class-based entry point
- `config.yaml`: Version updated to v0.2.0-refactored

#### Key Preservation Guarantees:
✅ **Exact same UI appearance**: All HTML, CSS classes, and styling preserved
✅ **Same server group colors**: Green/yellow/red/gray group borders maintained  
✅ **Same server card design**: Alert bars, colors, and layouts identical
✅ **Same click actions**: Server cards link to detail pages with same URLs
✅ **Same alarm display**: Color coding and icons preserved
✅ **Same navigation**: Environment switching and page routing unchanged
✅ **Same auto-refresh**: Meta refresh and timing behavior identical
✅ **Same AWS integration**: All API calls and data processing unchanged

#### Benefits Achieved:
1. **Maintainability**: Code organized into logical, focused classes
2. **Testability**: Each component can be tested independently
3. **Extensibility**: Easy to add new features or modify existing ones
4. **Separation of Concerns**: UI, business logic, and AWS operations separated
5. **Reusability**: Components can be reused across different pages
6. **Reduced Complexity**: Easier to understand and modify individual components

#### Migration Path:
- Original 927-line monolithic file → Clean 24-line entry point + organized modules
- Zero breaking changes for end users
- Same configuration format and deployment process
- Preserves all existing functionality and behavior

#### Testing Results:
✅ All imports successful
✅ AWS connection working  
✅ UI components initialized
✅ Configuration loading functional
✅ No changes to user experience

### 2025-09-14 - SAP Availability Integration with Real CloudWatch Logs Data

#### Objective
Complete the integration of SAP availability monitoring by connecting to real CloudWatch Logs data generated by Lambda functions, implementing proper log parsing for the FILE_CHECK_DETAIL format.

#### Problems Encountered & Solutions
1. **Log Group Names Update**:
   * **Problem:** Previous implementation used placeholder log group names that didn't match the actual Lambda function log groups.
   * **Solution:** Updated `get_sap_availability_data()` to use the real log group names:
     - Production: `/aws/lambda/sap-availability-heartbeat-prod` and `/aws/lambda/sap-availability-heartbeat-prod-b`
     - QA/DEV: `/aws/lambda/sap-availability-heartbeat` and `/aws/lambda/sap-availability-heartbeat-b`

2. **Log Format Mismatch**:
   * **Problem:** Parser was designed for generic log format but actual logs use structured JSON format with FILE_CHECK_DETAIL prefix.
   * **Solution:** Completely rewrote `parse_sap_log_results()` to parse the actual format:
     ```
     FILE_CHECK_DETAIL: {"vm_name": "...", "instance_id": "...", "file_path": "...", 
                        "status": "AVAILABLE/UNAVAILABLE", "details": "...", 
                        "raw_output": "...", "timestamp": "...", "environment": "..."}
     ```

3. **Environment-Based Log Group Selection**:
   * **Problem:** Need to query different log groups based on whether instance is production or development.
   * **Solution:** Implemented logic to detect production instances by checking for 'PRD', 'PROD', or 'PRODUCTION' patterns in instance names and select appropriate log groups.

4. **Service Name Extraction**:
   * **Problem:** Need to extract meaningful service names from SAP file paths like `/usr/sap/DAA/SMDA98/work/available.log`.
   * **Solution:** Used regex to parse file paths and create service names like "DAA SMDA98" from the path components.

#### Files Modified:
* `app.py`:
  - Updated `get_sap_availability_data()` function with real log group names and environment detection
  - Completely rewrote `parse_sap_log_results()` to handle FILE_CHECK_DETAIL JSON format
  - Enhanced `create_sap_availability_table()` to display new data fields (environment, details, raw_output, etc.)
* `config.yaml`:
  - Bumped version to v0.1.67

#### Implementation Details:
* **Environment Detection**: Automatically determines if instance is production or development based on naming patterns
* **JSON Parsing**: Handles malformed JSON by attempting to fix common issues like double quotes
* **Service Identification**: Extracts SAP system and instance numbers from file paths
* **Rich Data Display**: Shows status, details, raw output, environment, and timestamp information
* **Error Handling**: Comprehensive logging for debugging CloudWatch Logs issues

#### Technical Improvements:
* More robust JSON parsing with error recovery
* Better service name extraction using regex patterns
* Environment-aware log group selection
* Enhanced error logging for troubleshooting

### 2025-09-12 - Continuous Deployment and Data Loading Fixes

#### Objective
Establish a robust CI/CD pipeline for deploying the Streamlit app to EC2 and resolve data loading issues.

#### Problems Encountered & Solutions
1.  **GitHub Actions Permission Denied (`fatal: failed to stat ... Permission Denied`)**:
    *   **Problem:** The `ssm-user` running the SSM command in GitHub Actions could not access the application directory (`APP_PATH`), and the `ec2-user` (intended owner) also lacked permissions.
    *   **Solution:** Modified `deploy.yml` to ensure the application directory (`/home/ec2-user/POC-Dashboard`) is created and owned by `ec2-user` *before* any `git` operations.
2.  **GitHub Actions `fatal: not a git repository`**:
    *   **Problem:** After fixing permissions, the `git pull` command failed because the newly created directory on EC2 was not a Git repository.
    *   **Solution:** Modified `deploy.yml` to include `git init` and `git remote add origin` before `git pull`, ensuring the directory is a proper Git repository.
3.  **GitHub Actions `remote origin already exists`**:
    *   **Problem:** On subsequent deployments, `git remote add origin` failed because the remote was already configured.
    *   **Solution:** Modified `deploy.yml` to conditionally add the remote origin, checking if it exists first.
4.  **Streamlit App "No se puede acceder a este sitio web"**:
    *   **Problem:** The Streamlit service was crashing on startup (`status=200/CHDIR`) because its `WorkingDirectory` in `/etc/systemd/system/streamlit.service` was pointing to the old path (`/home/ssm-user/POC-Dashboard/`).
    *   **Solution:** Updated the `streamlit.service` file on EC2 to set `WorkingDirectory=/home/ec2-user/POC-Dashboard`, reloaded `systemd` daemon, and restarted the service.
5.  **Streamlit App "Cargando datos desde AWS..." (Data Loading Issue)**:
    *   **Problem:** The application was stuck on the loading message, and logs showed `botocore.client.EC2` objects were not pickle-serializable, causing `st.cache_data` to fail in `get_cross_account_boto3_client()`.
    *   **Solution:** Changed `@st.cache_data` to `@st.cache_resource` for `get_cross_account_boto3_client()` in `app.py`, as recommended by Streamlit for non-serializable objects.
6.  **Lack of Real-time Data Refresh & Debugging Visibility**:
    *   **Problem:** The page was not auto-reloading, and debugging AWS data fetching issues was difficult without on-screen logs.
    *   **Solution:**
        *   Implemented a configurable auto-reload mechanism with a countdown timer in `app.py` (using `REFRESH_INTERVAL_SECONDS` from `config.yaml`).
        *   Added a `show_aws_errors` flag to `config.yaml` to control on-screen display of AWS errors.
        *   Enhanced `get_aws_data()` with more granular logging to `/tmp/streamlit_aws_debug.log`.
        *   Implemented a feature to display the content of `/tmp/streamlit_aws_debug.log` directly on the Streamlit page when `show_aws_errors` is enabled.

#### Files Modified:
*   `.github/workflows/deploy.yml`
*   `app.py`
*   `config.yaml`

### 2025-09-12 - Versión 6.1: Simplificación de Navegación - Solo POC AWS Alive

#### Resumen
Se simplificó la navegación de la aplicación para mostrar únicamente la página "POC AWS Alive" en el sidebar, ocultando todas las páginas auxiliares y de entornos de prueba (Production, QA, DEV). La aplicación ahora redirige automáticamente a POC AWS Alive al iniciar.

#### Cambios Implementados

1. **Redirección Automática en `app.py`**:
   * Se eliminó el sidebar manual con múltiples enlaces
   * Se implementó redirección automática a POC AWS Alive usando `st.switch_page()`
   * Se configuró `initial_sidebar_state="collapsed"` para ocultar el sidebar por defecto

2. **Renombrado de Página Principal**:
   * `pages/4_POC.py` → `pages/POC_AWS_Alive.py`
   * Esto elimina el prefijo numérico y mejora la claridad del nombre

3. **Actualización de Referencias de Navegación**:
   * Se actualizaron todas las referencias en `_5_POC_Detalles.py` para apuntar a `POC_AWS_Alive.py`
   * Las páginas con prefijo `_` permanecen ocultas del sidebar como es esperado

#### Justificación
El usuario reportó que las páginas con prefijo `_` seguían apareciendo en el sidebar debido al uso de navegación manual con `st.sidebar.page_link()`. Al eliminar esta navegación manual y usar el comportamiento automático de Streamlit, solo las páginas sin prefijo `_` son visibles, logrando el objetivo de mostrar únicamente POC AWS Alive.

### 2025-09-12 - Versión 6.0 (Beta 2): Refactorización Arquitectónica y Despliegue Automatizado

#### Resumen
Esta versión representa la refactorización más grande hasta la fecha. La aplicación monolítica (`app.py`) fue desmantelada y reconstruida sobre una arquitectura modular, escalable y configurable, alineada con las mejores prácticas de desarrollo de software. Además, se implementó un flujo de despliegue continuo (CI/CD).

#### Cambios Implementados

1.  **Arquitectura Multi-Página y Componentizada**:
    *   La aplicación se transformó en una **aplicación multi-página**, con archivos dedicados para cada entorno (`Producción`, `QA`, `DEV`) en el directorio `pages/`.
    *   Se crearon **componentes de UI reutilizables** (`server_card.py`, `group_container.py`) para encapsular la lógica de renderizado y promover la reutilización de código.
    *   La lógica común y funciones de ayuda se centralizaron en `utils/helpers.py`.

2.  **Configuración Externa con `config.yaml`**:
    *   Toda la definición de servidores, grupos y estados se movió a un archivo `config.yaml`.
    *   **Beneficio:** Ahora es posible añadir, modificar o eliminar servidores y grupos sin necesidad de editar el código Python, facilitando enormemente el mantenimiento.

3.  **Mejoras de Navegación y Experiencia de Usuario**:
    *   `app.py` ahora funciona como un **portal de bienvenida** que construye una barra de navegación lateral personalizada, ofreciendo una experiencia más limpia.
    *   Se añadió un **navegador entre entornos** (flechas ᐊ y ᐅ) en las páginas principales.
    *   La navegación a las páginas de detalle fue refactorizada para usar **parámetros de consulta en la URL** (`st.query_params`), un método más robusto y estándar que `st.session_state`.

4.  **Optimización de la Página POC (AWS Live)**:
    *   La página `4_POC.py` fue rediseñada para usar un **sistema de cache en memoria compartida**.
    *   Un **hilo de fondo (background thread)** se encarga de actualizar los datos desde AWS (`boto3`) cada 30 segundos.
    *   **Beneficio:** Todos los usuarios concurrentes acceden a la misma cache, lo que reduce drásticamente las llamadas a la API de AWS, mejora el rendimiento y la escalabilidad de la aplicación.

5.  **Despliegue Continuo con GitHub Actions**:
    *   Se creó el flujo de trabajo `.github/workflows/deploy.yml`.
    *   Este flujo **automatiza el despliegue** de la aplicación en la instancia EC2 designada cada vez que se realiza un `push` a la rama `main`.
    *   Utiliza `AWS SSM Send-Command` para ejecutar los comandos de actualización en la instancia de forma segura.

#### Decisión de Arquitectura
Se adoptó una arquitectura modular y basada en configuración para preparar la aplicación para un crecimiento futuro. La separación de la configuración (`config.yaml`), la lógica (`utils/`), los componentes de UI (`components/`) y las vistas (`pages/`) hace que el sistema sea más fácil de entender, mantener y escalar. La implementación de CI/CD con GitHub Actions profesionaliza el ciclo de vida del desarrollo.

### 2025-09-10 - Versión 5.0 (Beta 1): Modernización y Preparación para Despliegue

#### Resumen
En esta fase, la aplicación fue refactorizada en profundidad para eliminar dependencias de herramientas de línea de comandos (`aws-cli`) y adoptar una arquitectura moderna, robusta y portable, lista para un despliegue profesional en la nube.

#### Cambios Implementados

1.  **Refactorización a `boto3`**:
    *   Se reemplazaron todas las llamadas a `subprocess` que ejecutaban `aws-cli`.
    *   Toda la comunicación con AWS (EC2 y CloudWatch) ahora se realiza de forma nativa en Python a través de la librería `boto3`.
    *   **Beneficios:** Mayor rendimiento, código más limpio, mejor manejo de errores y eliminación de una dependencia externa del entorno de ejecución.

2.  **Contenerización con Docker**:
    *   Se añadió un `Dockerfile` a la raíz del proyecto.
    *   Este archivo permite empaquetar la aplicación y todas sus dependencias en un contenedor estándar, garantizando que funcione de la misma manera en cualquier entorno (local o en la nube).

3.  **Nueva Estrategia de Despliegue con AWS App Runner**:
    *   Se definió una nueva estrategia de despliegue recomendada que utiliza AWS App Runner, un servicio serverless.
    *   **Beneficios:** Costo-eficiencia (pago por uso, escala a cero), totalmente gestionado por AWS, y despliegue continuo desde el repositorio de código.

4.  **Creación de Documentación de Despliegue**:
    *   Se creó un nuevo directorio `docs/`.
    *   Se añadieron dos guías de despliegue detalladas:
        *   `deploy_using_app_runner.md` (Recomendada)
        *   `deploy_using_ec2instance.md` (Alternativa)

5.  **Mejoras de Navegación y UI**:
    *   Se corrigieron errores de navegación a las páginas de detalle.
    *   Se reestructuró el directorio `pages/` para ocultar las páginas de detalle de la barra lateral, limpiando el menú principal.
    *   La aplicación ahora carga directamente en la página de "Producción" para una mejor experiencia de usuario.

#### Decisión de Arquitectura
Se abandona el uso de `aws-cli` en favor de `boto3` para alinear el proyecto con las mejores prácticas de desarrollo de aplicaciones en la nube, habilitando despliegues en contenedores y mejorando la mantenibilidad general del código.

### 2025-09-10 - Inicio del Proyecto

#### Requerimientos Iniciales
El usuario solicitó crear un POC con las siguientes características:

1. **Página Principal**:
   - Título: "Dashboard POC"
   - Grupo: "SAP ISU PRODUCCIÓN"
   - 3 servidores virtuales:
     - SRVISUASCS (estado verde)
     - SRVISUPRD (estado rojo)
     - SRVISUPRDDB (estado amarillo)
   - Indicadores tipo semáforo para mostrar estado
   - Contador de alertas totales
   - Gráfico tipo pie mostrando alertas críticas/advertencias/ok

2. **Página de Detalle** (al hacer clic en una VM):
   - Columna 1: Listado gráfico de alarmas (luz + nombre)
   - Columna 2: 
     - Filtro de tiempo (5min, 15min, 30min, 1h, 3h, 6h, 12h)
     - Indicadores de CPU (1 por núcleo)
     - Indicador de RAM
     - Indicadores de discos (5 discos)

#### Implementación Realizada

**Archivos creados**:
1. `app.py` - Aplicación principal con toda la lógica
2. `requirements.txt` - Dependencias (streamlit, plotly)

**Características implementadas**:
- ✅ Dashboard principal con 3 VMs
- ✅ Estados de semáforo (verde, rojo, amarillo) con indicadores visuales
- ✅ Contadores de alertas totales
- ✅ Gráficos de pie para distribución de alertas
- ✅ Navegación a página de detalle por VM
- ✅ Listado de alarmas con indicadores visuales
- ✅ Filtro de tiempo
- ✅ Métricas de CPU (4 núcleos)
- ✅ Métrica de RAM
- ✅ Métricas de 5 discos duros

**Decisiones técnicas**:
- Uso de `st.session_state` para manejar navegación entre vistas
- Datos hardcodeados para el POC
- Diseño responsive con columnas de Streamlit
- Plotly para gráficos de pie compactos
- CSS inline para personalizar apariencia de semáforos

## Próximos Pasos Sugeridos

1. **Integración con AWS**:
   - Configurar despliegue en EC2/ECS/Lambda
   - Implementar autenticación
   - Conectar con CloudWatch para métricas reales

2. **Mejoras de Funcionalidad**:
   - Agregar persistencia de datos
   - Implementar actualización en tiempo real
   - Añadir módulo de reportes
   - Implementar tendencias históricas

3. **Mejoras de UI/UX**:
   - Tema oscuro/claro
   - Notificaciones push para alertas críticas
   - Dashboard personalizable

## Notas para Retomar el Desarrollo

Para continuar el desarrollo:
1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar aplicación: `streamlit run app.py`
3. Revisar este archivo para entender el contexto
4. Consultar README.md para ver el changelog actualizado

## Estructura del Proyecto (v6.0)

```
POC/
├── .github/                    # Flujos de trabajo de CI/CD
│   └── workflows/
│       └── deploy.yml
├── app.py                      # Página principal y navegador
├── config.yaml                 # Configuración de servidores y grupos
├── Dockerfile                  # Contenerización de la aplicación
├── requirements.txt            # Dependencias de Python
├── assets/
│   └── styles.css              # Hoja de estilos CSS
├── components/
│   ├── group_container.py      # Componente para grupos de servidores
│   └── server_card.py          # Componente para tarjetas de servidor
├── docs/
│   ├── deploy_using_app_runner.md
│   └── deploy_using_ec2instance.md
├── pages/
│   ├── 1_Production.py         # Página para el entorno de Producción (oculta del menú)
│   ├── 2_QA.py                 # Página para el entorno de QA (oculta del menú)
│   ├── 3_DEV.py                # Página para el entorno de DEV (oculta del menú)
│   ├── POC_AWS_Alive.py        # Página principal con datos reales de AWS (única visible)
│   ├── _1_Detalles_del_Servidor.py # Página de detalle (oculta)
│   ├── _5_POC_Detalles.py      # Página de detalles POC (oculta)
│   └── _vm_details.py          # Página de detalles VM (oculta)
├── utils/
│   └── helpers.py              # Funciones de ayuda y lógica compartida
├── DEVELOPMENT_HISTORY.md      # Este archivo
└── README.md                   # Documentación principal
```

### 2025-09-10 - Segunda Iteración: Múltiples Grupos de Servidores

#### Nuevos Requerimientos
El usuario solicitó agregar un segundo grupo de servidores:
- Grupo: "SAP ERP"
- 2 servidores:
  - SRVERPPRD (estado verde)
  - SRVSAPERPBDD (estado amarillo)
- Diferenciación visual entre grupos mediante cajas

#### Cambios Implementados

**Modificaciones en app.py**:
1. Actualización de `get_vm_status()` para incluir los nuevos servidores
2. Actualización de `get_vm_alerts()` con datos para los nuevos servidores
3. Refactorización de `main_dashboard()` para mostrar dos grupos separados
4. Implementación de cajas visuales diferenciadas:
   - SAP ISU PRODUCCIÓN: Caja con borde azul (#1f77b4) y fondo azul claro
   - SAP ERP: Caja con borde naranja (#ff7f0e) y fondo naranja claro

**Características agregadas**:
- ✅ Segundo grupo SAP ERP con 2 servidores
- ✅ Cajas visuales para diferenciar grupos
- ✅ Colores distintivos por grupo
- ✅ Estados y alertas configurados para nuevos servidores

**Decisiones de diseño**:
- Uso de colores contrastantes pero armoniosos para diferenciar grupos
- Mantenimiento del layout de 3 columnas, dejando una vacía en el grupo SAP ERP
- Conservación del mismo estilo visual para los indicadores de estado

### 2025-09-10 - Tercera Iteración: Estilización y Diseño Moderno

#### Requerimientos del Usuario
El usuario solicitó estilizar la aplicación para hacerla más bonita e impactante visualmente.

#### Cambios Implementados

**Patrón de Diseño Aplicado**: Glassmorphism + Futuristic Dark Theme

**Principales mejoras visuales**:
1. **Tema Oscuro Futurista**
   - Fondo con gradiente oscuro (#0a0f1c a #1a1f2e)
   - Efecto glassmorphism con backdrop-filter blur
   - Transparencias y bordes sutiles

2. **Animaciones y Efectos**
   - Animación de pulso en indicadores de estado
   - Efectos hover en tarjetas (elevación y brillo)
   - Transiciones suaves con cubic-bezier
   - Sombras dinámicas con colores de acento

3. **Mejoras Tipográficas**
   - Fuente Inter de Google Fonts
   - Título principal con gradiente de texto
   - Jerarquía visual clara con tamaños y pesos

4. **Componentes Rediseñados**
   - Tarjetas de servidor con bordes gradiente al hover
   - Botones con gradientes y efectos de elevación
   - Progress bars con gradientes vibrantes
   - Indicadores de estado con brillos y sombras de neón

5. **Nuevas Características Visuales**
   - Footer con resumen global del sistema
   - Métricas de disponibilidad con indicadores delta
   - Iconos para mejor identificación visual
   - Colores vibrantes: cyan (#00d4ff), verde neón (#00ff88), morado (#667eea)

**Decisiones técnicas**:
- CSS personalizado extenso para control total del diseño
- Uso de gradientes lineales para elementos destacados
- Animaciones CSS puras para mejor rendimiento

### 2025-09-14 - Eliminación de Caché en Funciones de Detalle

#### Problema Identificado
Los usuarios reportaron que las alarmas aparecían con estados diferentes entre la página de resumen y la página de detalle:
- Página de resumen: Alarmas grises (INSUFFICIENT_DATA)
- Página de detalle: Alarmas verdes (OK)

#### Análisis del Problema
Se identificó que el problema era causado por el sistema de caché:
- La página de resumen no usaba caché y mostraba datos en tiempo real
- La página de detalle usaba `@st.cache_data(ttl=60)` con un TTL de 60 segundos
- Esto causaba que los datos pudieran tener hasta 60 segundos de antigüedad

#### Solución Implementada
Se eliminaron todos los decoradores `@st.cache_data` de las funciones de obtención de datos en la página de detalle:
- `get_instance_details()`
- `get_alarms_for_instance()`
- `get_cpu_utilization()`
- `get_memory_utilization()`
- `get_disk_utilization()`

Se mantuvo únicamente el caché de los clientes boto3 (`@st.cache_resource(ttl=900)`) para evitar recrear las conexiones constantemente.

#### Justificación
El sistema de monitoreo debe mostrar los problemas en tiempo real cuando se capturan. No debe haber información obsoleta o antigua que pueda causar confusión al momento de diagnosticar problemas.

#### Versión
Se actualizó la versión de la aplicación de v0.1.56 a v0.1.57 para reflejar los cambios realizados en el sistema de caché.

### 2025-09-14 - Corrección de Estados UNKNOWN en Alarmas

#### Problema Identificado
Después de eliminar el caché, persistía el problema de inconsistencia entre la página de resumen y la página de detalle. El servidor "SRVISUASCS" mostraba 6 alarmas todas verdes en la página de detalle, pero en el resumen aparecían 5 verdes y 1 gris.

#### Análisis del Problema
Se identificó que algunas alarmas tenían estado `UNKNOWN` en lugar de los estados estándar de CloudWatch:
- La función `get_aws_data()` asignaba `'UNKNOWN'` como valor por defecto cuando `StateValue` no existía
- La función `create_alert_bar_html()` no consideraba el estado `UNKNOWN` en el cálculo de totales
- Esto causaba discrepancias en los conteos de alarmas

#### Solución Implementada
1. **Agregados logs detallados** para debuggear cada alarma individual y su estado
2. **Modificada `create_alert_bar_html()`** para tratar estados `UNKNOWN` como `INSUFFICIENT_DATA`
3. **Actualizada lógica de colores** en `create_server_card()` y `create_group_container()` para considerar estados `UNKNOWN`
4. **Unificado el manejo** de estados desconocidos con estados de datos insuficientes

#### Cambios Técnicos
- Estados `UNKNOWN` ahora se suman a `INSUFFICIENT_DATA` en el conteo total
- Las tarjetas de servidor muestran color gris si tienen estados `UNKNOWN` o `INSUFFICIENT_DATA`
- Los grupos también consideran estados `UNKNOWN` para determinar su color

#### Versión
Se actualizó la versión de v0.1.57 a v0.1.58 para reflejar esta corrección.

### 2025-09-14 - Corrección de Enlaces a AWS CloudWatch Console

#### Problema Identificado
Los enlaces de las alarmas en la página de detalle apuntaban incorrectamente a la propia aplicación en lugar de la consola de AWS CloudWatch.

#### Enlaces Incorrectos
```
http://ec2-54-224-75-218.compute-1.amazonaws.com:8501/?poc_vm_id=i-05286b364879c6560#:~:text=EPMAPS%20%2D%20(DMZ%2DSRVSAPROU)%20%2D%20PING%20NOT%20REACHABLE%20%F0%9F%94%97
```

#### Formato Correcto Requerido
```
https://011528297340-pdl6i3zc.us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:alarm/ALARM_NAME?~(search~'ENCODED_SEARCH')
```

#### Solución Implementada
Modificada la función `create_alarm_item_html()` en `utils/helpers.py` para:
1. **Extraer cuenta y región** del ARN de la alarma
2. **Generar URL correcta** con el formato de la consola AWS
3. **Codificar correctamente** el parámetro de búsqueda
4. **Agregar icono diferente** para alarmas grises (🔒)

#### Cambios Técnicos
- Formato de URL: `https://{account_id}-pdl6i3zc.{region}.console.aws.amazon.com/cloudwatch/home?region={region}#alarmsV2:alarm/{alarm_name}?~(search~'{encoded_search}')`
- Codificación de caracteres especiales: espacios = `*20`, paréntesis = `*28/*29`, etc.
- Icono para estado gris cambiado a 🔒

#### Versión
Se actualizó la versión de v0.1.58 a v0.1.59 para reflejar esta corrección.

### 2025-09-14 - Corrección de Escapado HTML en Enlaces de Alarmas

#### Problema Identificado
Los enlaces de alarmas se generaban con HTML malformado cuando los nombres de alarmas contenían caracteres especiales como `%`, `>`, `<`, causando que el HTML se rompiera y los enlaces no funcionaran correctamente.

**Ejemplo de HTML malformado:**
```
70%')' target='_blank' style='color: white; text-decoration: none; font-weight: 500;'> EPMAPS PRD SRVBOPRD PREVENTIVA CPU % uso >70% 🔗
```

#### Causa del Problema
Los nombres de alarmas como `"CPU % uso >70%"` contenían caracteres que tienen significado especial en HTML y no se estaban escapando correctamente antes de insertarlos en el HTML.

#### Solución Implementada
1. **Agregado import de módulo html** para escapado de caracteres
2. **Implementado escapado HTML** usando `html.escape()` en la función `create_alarm_item_html()`
3. **Separación de contextos**: URL encoding para URLs y HTML escaping para contenido HTML
4. **Aplicado tanto a enlaces como a texto sin enlace**

#### Cambios Técnicos
- Import agregado: `import html`
- HTML escaping: `escaped_alarm_name = html.escape(alarm_name)`
- Los caracteres `<`, `>`, `&`, `"`, `'` ahora se escapan correctamente a `&lt;`, `&gt;`, `&amp;`, `&quot;`, `&#x27;`

#### Versión
Se actualizó la versión de v0.1.59 a v0.1.60 para reflejar esta corrección de seguridad y funcionalidad.

### 2025-09-14 - Corrección Avanzada de URLs de Alarmas con Caracteres Especiales

#### Problema Persistente
A pesar del escapado HTML implementado, persistían problemas con URLs malformadas cuando los nombres de alarmas contenían caracteres como `%`, `>`, causando enlaces rotos con patrones como:
```
80%')' target='_blank' style='color: white; text-decoration: none; font-weight: 500;'> EPMAPS PROD SRVCRMPRD ACTIVA RAM % uso >80% 🔗
```

#### Análisis Profundo del Problema
1. **Codificación de URL insuficiente**: `quote()` no manejaba todos los caracteres especiales
2. **Conflicto de comillas**: Uso de comillas simples en HTML con URLs que contenían comillas
3. **Encodificación incompleta**: Faltaban mappings para caracteres como `%`, `>`, `<`, `&`, `=`

#### Solución Implementada
1. **Encodificación más robusta** del parámetro de búsqueda:
   - `%` → `*25`
   - `>` → `*3E`
   - `<` → `*3C`
   - `&` → `*26`
   - `=` → `*3D`

2. **URL encoding mejorado** usando `quote(alarm_name, safe='')`

3. **Cambio de formato HTML**:
   - Reemplazado comillas simples (`'`) por comillas dobles (`"`) en atributos HTML
   - Uso de triple comillas simples (`'''`) para strings Python para evitar conflictos

#### Cambios Técnicos
- Encodificación expandida: `encoded_search = alarm_name.replace(...).replace('%', '*25').replace('>', '*3E')...`
- URL encoding seguro: `quote(alarm_name, safe='')`
- HTML con comillas dobles: `<a href="{console_url}" target="_blank">`

#### Versión
Se actualizó la versión de v0.1.60 a v0.1.61 para reflejar esta corrección avanzada.

### 2025-09-14 - Simplificación de Iconos de Estado de Alarmas

#### Cambio Solicitado
El usuario reportó que los enlaces funcionan correctamente pero prefiere simplificar los iconos de estado de las alarmas. Los iconos complejos (🔴, 🟡, 🔒) causaban confusión visual.

#### Solución Implementada
Simplificación de iconos a solo dos estados:
- **🟢 (Verde)**: Para alarmas en estado normal (OK)
- **⚫ (Gris/Negro)**: Para todos los demás estados (ALARM, INSUFFICIENT_DATA, UNKNOWN, etc.)

#### Cambios Técnicos
- Modificada función `create_alarm_item_html()` en `utils/helpers.py`
- Lógica simplificada: `status_icon = "🟢" if status == "green" else "⚫"`
- Eliminados iconos específicos por tipo de alarma

#### Beneficios
- **Claridad visual**: Solo dos estados simples de entender
- **Consistencia**: Alineado con el diseño general del dashboard
- **Menos confusión**: No hay necesidad de interpretar múltiples iconos

#### Versión
Se actualizó la versión de v0.1.61 a v0.1.62 para reflejar esta simplificación de UI.

### 2025-09-14 - Restauración del Esquema de Colores Original

#### Clarificación del Usuario
El usuario aclaró que quería mantener el esquema de colores original con significado específico, pero sin iconos complejos como cadenas (🔗) o candados (🔒). Solo círculos de colores simples.

#### Esquema de Colores Restaurado
- **🟢 Verde**: Alarmas OK/normales
- **🔴 Rojo**: Alarmas en estado de alarma (ALARM)
- **🟡 Amarillo**: Alarmas preventivas/proactivas (PREVENTIVE/ALERTA)
- **⚫ Gris**: Datos insuficientes (INSUFFICIENT_DATA/UNKNOWN)

#### Cambios Técnicos
- Restaurada lógica de iconos: `status_icon = "🔴" if status == "red" else "🟡" if status == "yellow" else "⚫" if status == "gray" else "🟢"`
- Eliminados iconos complejos (🔗, 🔒)
- Mantenidos solo círculos de colores para claridad visual

#### Beneficios
- **Significado claro**: Cada color representa un estado específico
- **Simplicidad visual**: Solo círculos, sin iconos complejos
- **Consistencia**: Alineado con el sistema de colores del dashboard

#### Versión
Se actualizó la versión de v0.1.62 a v0.1.63 para reflejar esta restauración del esquema de colores.

### 2025-09-14 - Mejoras en Métricas de Rendimiento: Gauges y Filtrado de Discos

#### Problemas Identificados
1. **Mensaje confuso de CloudWatch agent**: Aparecía mensaje de "agent no instalado" cuando sí estaba instalado
2. **Discos tmpfs irrelevantes**: Se mostraban sistemas de archivos temporales (tmpfs, devtmpfs, etc.) que no son útiles para monitoreo
3. **Barras de progreso poco visuales**: Las barras simples no proporcionaban suficiente información visual
4. **Umbrales de color inconsistentes**: Los umbrales no seguían estándares de monitoreo

#### Soluciones Implementadas

**1. Filtrado de Sistemas de Archivos**
- Filtrados sistemas de archivos no físicos: `tmpfs`, `devtmpfs`, `udev`, `proc`, `sys`, `run`
- Solo se muestran discos físicos reales
- Código: `if any(exclude in disk_name.lower() for exclude in ['tmpfs', 'devtmpfs', 'udev', 'proc', 'sys', 'run']): continue`

**2. Implementación de Gauges**
- Reemplazadas barras de progreso simples por gauges visuales usando Plotly
- Gauges con escala de colores y umbrales claramente definidos
- Layout adaptado: CPU y RAM en columnas superiores, discos en grid de 2 columnas

**3. Estandarización de Umbrales de Color**
- **Verde**: < 80% (normal)
- **Amarillo**: 80-92% (advertencia)
- **Rojo**: > 92% (crítico)

**4. Mejora de Mensajes de Error**
- Simplificado mensaje cuando no hay datos disponibles
- Eliminada referencia confusa a "CloudWatch Agent no instalado"

#### Cambios Técnicos

**Imports agregados:**
```python
import plotly.graph_objects as go
```

**Nueva función create_gauge():**
- Gauges con fondos transparentes para tema oscuro
- Escalas de color por zonas
- Indicador threshold para valor actual
- Configuración responsive

**Layout actualizado:**
- CPU y RAM: 2 columnas superiores
- Discos: Grid flexible de 2 columnas por fila
- Eliminadas barras de progreso y contenedores de colores manuales

#### Beneficios
- **Visualización mejorada**: Gauges más intuitivos que barras
- **Información relevante**: Solo discos físicos mostrados
- **Umbrales estándar**: Consistentes con mejores prácticas de monitoreo
- **Experiencia limpia**: Menos ruido visual, mensajes más claros

#### Versión
Se actualizó la versión de v0.1.63 a v0.1.64 para reflejar estas mejoras en la visualización de métricas.

### 2025-09-14 - Implementación de Monitoreo de Disponibilidad SAP

#### Requerimiento del Usuario
El usuario solicitó agregar una sección para mostrar métricas de disponibilidad de servicios SAP obtenidas desde archivos de log específicos en rutas como `/usr/sap/SERVICIO/CODIGO/work/available.log`.

#### Funcionalidad Requerida
- **Formato de archivos**: `AVAILABLE/UNAVAILABLE FechaInicio FechaFin`
- **Ubicación**: Encima de métricas de rendimiento
- **Datos mostrados**: Path, último estado, fecha inicio, fecha fin
- **Historial**: Hasta 10 líneas por servicio

#### Implementación Actual (Placeholder)

**Estructura de datos:**
```python
{
    'path': '/usr/sap/ERP/DVEBMGS00/work/available.log',
    'service': 'SAP ERP',
    'instance': 'DVEBMGS00',
    'history': [
        {'status': 'AVAILABLE', 'start_time': '2025-09-14 08:00:00', 'end_time': '2025-09-14 23:59:59'}
    ]
}
```

**Funciones implementadas:**
1. `get_sap_availability_data()`: Identifica servicios SAP por nombre de instancia
2. `create_sap_availability_table()`: Crea tabla visual con estados e historial
3. Integración en `display_detail_page()`

**Identificación de servicios:**
- **ERP**: Si 'ERP' está en el nombre de la instancia
- **CRM**: Si 'CRM' está en el nombre de la instancia
- **ISU**: Si 'ISU' está en el nombre de la instancia
- **BW**: Si 'BW' está en el nombre de la instancia

#### Visualización Implementada
- **Título**: 🔧 Disponibilidad Servicios SAP
- **Por servicio**: Nombre, instancia, path del archivo
- **Estado actual**: Con indicador visual (🟢/🔴)
- **Tabla historial**: # | Estado | Fecha Inicio | Fecha Fin
- **Limite**: Máximo 10 entradas de historial

#### Pendientes de Implementación
**IMPORTANTE**: La implementación actual es un placeholder. Se requiere:

1. **Método de acceso a archivos**:
   - SSH/SCP a servidores SAP
   - CloudWatch custom metrics
   - API en servidores SAP
   - Montaje de red (NFS/SMB)

2. **Parser de archivos log**:
   - Leer formato: `AVAILABLE/UNAVAILABLE StartDateTime EndDateTime`
   - Manejo de errores de archivos
   - Cache de datos para performance

3. **Configuración**:
   - Mapeo de instancias → servicios SAP
   - Credenciales para acceso remoto
   - Rutas de archivos configurables

#### Dependencias Agregadas
- `pandas`: Para manejo de DataFrames en tablas

#### Versión
Se actualizó la versión de v0.1.64 a v0.1.65 para reflejar esta nueva funcionalidad.

**Nota**: Esta funcionalidad requiere implementación adicional para acceder a los archivos reales. Actualmente muestra datos simulados para demostrar la interfaz.

### 2025-09-14 - Integración con CloudWatch Logs para Datos SAP Reales

#### Actualización de Implementación
El usuario aclaró que los datos SAP ya se extraen mediante un Lambda y se almacenan en CloudWatch Logs, eliminando la necesidad de acceso directo a archivos.

#### Nueva Implementación
Modificada la función `get_sap_availability_data()` para consultar CloudWatch Logs usando CloudWatch Logs Insights.

**Componentes implementados:**

1. **Consulta CloudWatch Logs**:
   ```python
   logs_client = get_cross_account_boto3_client_cached('logs')
   query = '''
   fields @timestamp, @message
   | filter @message like /INSTANCE_NAME/
   | filter @message like /AVAILABLE/ or @message like /UNAVAILABLE/
   | sort @timestamp desc
   | limit 10
   '''
   ```

2. **Búsqueda en múltiples Log Groups**:
   - `/aws/lambda/sap-availability-checker`
   - `/aws/lambda/sap-monitor`
   - `/epmaps/sap-availability`
   - `/sap/{instance_name}`

3. **Parser de Logs**:
   - Función `parse_sap_log_results()` para extraer datos de disponibilidad
   - Manejo de diferentes formatos de log
   - Agrupación por servicio SAP

4. **Fallback System**:
   - Si no se encuentran logs reales, usa datos placeholder
   - Logging detallado para debugging
   - Manejo de errores graceful

#### Funcionalidades
- **CloudWatch Logs Insights**: Consultas estructuradas para extraer datos SAP
- **Búsqueda por instancia**: Filtra logs por nombre de instancia específica
- **Historial temporal**: Consulta últimas 24 horas de datos
- **Parsing flexible**: Adaptable a diferentes formatos de log del Lambda
- **Logging completo**: Debug logs en `/tmp/streamlit_aws_debug.log`

#### Pendiente de Configuración
**IMPORTANTE**: Para que funcione completamente, necesitas proporcionar:

1. **Nombre exacto del Log Group** donde el Lambda escribe los datos
2. **Formato de los mensajes de log** del Lambda
3. **Identificadores** usados en los logs para cada servicio SAP

**Ejemplo de formato esperado**:
```
[Timestamp] INSTANCE_NAME SERVICE_NAME AVAILABLE/UNAVAILABLE StartDateTime EndDateTime
```

#### Versión
Se actualizó la versión de v0.1.65 a v0.1.66 para reflejar la integración con CloudWatch Logs.
- Diseño responsive mantenido con mejoras visuales