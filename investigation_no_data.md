# Investigation: Streamlit App Not Displaying Data

## Date: September 13, 2025

## Problem Statement:
The Streamlit application, deployed on an EC2 instance, consistently displays "Cargando datos desde AWS..." (Loading data from AWS...) but fails to render any actual instance data (groups or server cards). No explicit error messages are shown on the Streamlit UI, even when `SHOW_AWS_ERRORS` is enabled.

## Initial State & Context:
*   `debug_aws.py` script (run manually on EC2) successfully found 56 EC2 instances with the `DashboardGroup` tag, confirming AWS connectivity and data availability from the EC2 instance.
*   Application uses `boto3` for AWS interaction.
*   Deployment is managed via GitHub Actions (`deploy.yml`).
*   `app.py` is the main Streamlit application file.
*   `config.yaml` stores application settings.

## Debugging Steps & Observations:

### Phase 1: Initial Data Loading Issue & `st.cache_data` Serialization Error
*   **Observation:** App stuck on "Cargando datos...".
*   **Tool:** `debug_aws.py` output provided by user.
*   **Log (`/tmp/streamlit_aws_debug.log`):** Showed `Cannot serialize the return value (of type `botocore.client.EC2`) in `get_cross_account_boto3_client()`. `st.cache_data` uses `pickle`... use `st.cache_resource` instead.`
*   **Hypothesis:** `st.cache_data` was incorrectly used for `boto3` clients.
*   **Action:** Changed `@st.cache_data` to `@st.cache_resource` for `get_cross_account_boto3_client()` in `app.py`.
*   **Result:** User reported "deploy is working", but still "Cargando datos..." and no errors. Subsequent `cat /tmp/streamlit_aws_debug.log` showed the *same* serialization error, indicating the `app.py` change was not effectively deployed or applied.

### Phase 2: Deployment & Service Restart Issues
*   **Problem:** GitHub Actions `fatal: failed to stat ... Permission Denied` and `fatal: not a git repository`.
*   **Hypothesis:** Incorrect directory permissions/ownership and missing Git repo initialization on EC2.
*   **Action:** Modified `deploy.yml` to:
    *   Create `/home/ec2-user/POC-Dashboard` and `chown` to `ec2-user`.
    *   Include `git init` and `git remote add origin` before `git pull`.
    *   Conditionally add remote (`if ! git remote get-url origin`).
*   **Problem:** Streamlit app "No se puede acceder a este sitio web" (site unreachable).
*   **Hypothesis:** `systemd` service `WorkingDirectory` was incorrect.
*   **Action:** Updated `streamlit.service` on EC2 to `WorkingDirectory=/home/ec2-user/POC-Dashboard/`, reloaded daemon, restarted service.
*   **Result:** Site became accessible, but still "Cargando datos...".

### Phase 3: Debugging Data Loading (Post-Deployment Fixes)
*   **Observation:** App still "Cargando datos...", no errors on screen.
*   **Hypothesis:** `get_aws_data()` returning empty list without exception, or `SHOW_AWS_ERRORS` not working.
*   **Action:**
    *   Added `show_aws_errors: false` to `config.yaml` (later set to `true` by user).
    *   Enhanced `get_aws_data()` with granular logging to `/tmp/streamlit_aws_debug.log`.
    *   Implemented `display_debug_log()` to show log content on Streamlit page.
    *   Modified `get_aws_data()` to explicitly set `st.session_state.data_cache["error_message"]` on role assumption failure.
*   **Observation:** User reported "Estado de Conexión AWS: Desconocido. Detalles: None" on screen.
*   **Hypothesis:** Background thread not updating `_data_cache` or `_data_cache` not visible to main thread.
*   **Action:** Added logging to `update_cache_in_background` to confirm execution.
*   **Log (`/tmp/streamlit_aws_debug.log`):** Showed `Background thread: AWS Connection Status: Conexión AWS OK, Error: None` and `Found 56 instances with DashboardGroup tag.` from background thread. BUT `Main thread: _data_cache instances count: 0, connection_status: Desconocido` from main thread.
*   **Conclusion:** Background thread *is* fetching data, but main thread *not* seeing updates.

### Phase 4: Streamlit State Management & Threading Issues
*   **Hypothesis:** `st.session_state` not correctly updated/persisted across reruns when modified by background thread.
*   **Action:**
    *   Moved `_data_cache` initialization into `st.session_state` (`st.session_state.data_cache`).
    *   Replaced all `_data_cache` references with `st.session_state.data_cache`.
    *   Removed `_lock` from `update_cache_in_background` (relying on `st.session_state` thread-safety).
    *   Removed `_lock` from `build_and_display_dashboard` (direct access to `st.session_state.data_cache`).
    *   Added `time.sleep(0.1)` after `st.session_state.data_cache` updates in background thread (as a long shot for timing).
*   **Observation:** Log still showed `Main thread: _data_cache instances count: 0, connection_status: Desconocido`.
*   **Hypothesis:** `threading.Thread` directly modifying `st.session_state` is problematic in Streamlit. The background thread seems to hang/crash after its initial log.

### Phase 5: Attempt to Simplify (Remove Background Thread)
*   **Problem:** Persistent issues with `threading.Thread` in Streamlit.
*   **Action:** Attempted to remove `_data_cache` global, `get_aws_data` function, `update_cache_in_background` function, and background thread initialization.
*   **Observation:** `replace` commands failed repeatedly due to `old_string` not matching content on EC2. This indicates `app.py` on EC2 is *not* being updated as expected by the `deploy.yml` process, or my `replace` commands are too brittle.

## Current State of `app.py` on EC2 (as of last `cat`):
The `app.py` on the EC2 instance *still* contains the `_data_cache` global variable and the background thread initialization, despite multiple attempts to remove them. This means the `replace` commands are not effectively updating the file on the remote.

## Unresolved Issues:
1.  **Streamlit App Not Displaying Data:** The core problem persists. The main thread is not seeing the data fetched by the background thread (or the background thread is not fully executing).
2.  **`bump_version.yml` Error:** The "Invalid workflow file" error on line 62 of `bump_version.yml` persists, indicating a YAML parsing issue that I have been unable to resolve.
3.  **`app.py` Update Failure:** The `replace` commands are not reliably updating `app.py` on the EC2 instance, leading to a mismatch between local changes and deployed code.

## Next Steps for Investigation:
*   **Focus on `app.py` deployment reliability:** Before any further debugging of the Streamlit app, ensure that `app.py` is *actually* being updated on the EC2 instance with every deployment. This might require a more robust file transfer mechanism or direct verification after deployment.
*   **Re-evaluate Streamlit background task strategy:** If `app.py` deployment is confirmed, and the data loading issue persists, consider alternative patterns for background data fetching in Streamlit (e.g., queue-based communication, or fetching data directly in the main thread on refresh, as initially planned in Phase 5).
*   **Address `bump_version.yml` separately:** This is a CI/CD issue that needs to be resolved independently.

This document summarizes the current state and provides a clear path forward.
