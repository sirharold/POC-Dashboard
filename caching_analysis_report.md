# Caching System Analysis Report

## Executive Summary

The application uses multiple caching mechanisms with different TTL (Time To Live) values for the summary dashboard and detail pages. This analysis reveals potential inconsistencies that could lead to the summary page showing different alarm states than the detail page.

## Caching Mechanisms Overview

### 1. Summary Page (Dashboard) Caching

The summary page **does not use Streamlit's @st.cache decorators** for AWS data. Instead, it uses:

- **Session State Caching**: Data is stored in `st.session_state.data_cache`
- **Manual Refresh**: Page auto-refreshes every 30 seconds using HTML meta refresh tag
- **Data Fetching**: `get_aws_data()` is called directly without caching decorator
- **AWS Client Caching**: Uses cached boto3 clients via `get_cross_account_boto3_client_cached()`

### 2. Detail Page Caching

The detail page uses **aggressive caching with @st.cache_data decorators**:

- **Instance Details**: `@st.cache_data(ttl=60)` - 60 seconds TTL
- **Alarms for Instance**: `@st.cache_data(ttl=60)` - 60 seconds TTL
- **CPU Utilization**: `@st.cache_data(ttl=60)` - 60 seconds TTL
- **Memory Utilization**: `@st.cache_data(ttl=60)` - 60 seconds TTL
- **Disk Utilization**: `@st.cache_data(ttl=60)` - 60 seconds TTL

### 3. AWS Client Caching

- **Boto3 Client**: `@st.cache_resource(ttl=900)` - 15 minutes TTL
- This caches the AWS credentials and client objects

## Key Differences Between Summary and Detail Pages

### Data Sources
1. **Summary Page (`get_aws_data()`)**:
   - Fetches ALL alarms at once using pagination
   - Processes alarms for all instances in a single operation
   - More efficient approach for bulk data retrieval

2. **Detail Page (`get_alarms_for_instance()`)**:
   - Fetches ALL alarms again but filters for specific instance
   - Less efficient as it retrieves all alarms just to filter for one instance
   - Uses the same CloudWatch API but with different caching

### Caching Behavior
1. **Summary Page**:
   - No function-level caching
   - Data refreshed every 30 seconds (page reload)
   - Always shows fresh data on page load

2. **Detail Page**:
   - 60-second cache on all data functions
   - Data can be up to 60 seconds old
   - Cache persists across user navigation

## Potential Issues Identified

### 1. Data Inconsistency
- **Scenario**: User views summary page, then clicks on an instance
- **Problem**: Detail page may show cached data up to 60 seconds old while summary was fresh
- **Impact**: Alarm states might differ between views

### 2. Preventive Alarm Logic Duplication
Both pages check for preventive alarms but with slightly different implementations:
- Summary: `if alarm_state == 'ALARM' and ('ALERTA' in alarm_name.upper() or 'PROACTIVA' in alarm_name.upper())`
- Detail: Same logic but applied during rendering

### 3. Inefficient Data Retrieval in Detail Page
- Detail page fetches ALL alarms just to filter for one instance
- This is inefficient and could be optimized using CloudWatch dimension filters

### 4. Different Refresh Mechanisms
- Summary: HTML meta refresh (full page reload)
- Detail: Streamlit cache TTL (partial data refresh)

## Recommendations

### 1. Harmonize Caching Strategy
- Consider using consistent TTL values across pages
- Either cache both or cache neither for consistency

### 2. Optimize Detail Page Queries
```python
# Current approach (inefficient)
def get_alarms_for_instance(instance_id: str):
    # Gets ALL alarms then filters
    
# Recommended approach
def get_alarms_for_instance(instance_id: str):
    cloudwatch = get_cross_account_boto3_client('cloudwatch')
    paginator = cloudwatch.get_paginator('describe_alarms')
    pages = paginator.paginate(
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
    )
```

### 3. Add Cache Invalidation
- Provide a manual refresh button on detail page
- Consider using `st.cache_data.clear()` when needed

### 4. Unify Alarm Processing Logic
- Create a shared function for preventive alarm detection
- Ensure consistent alarm categorization across pages

### 5. Consider Real-time Updates
- Implement WebSocket or polling for real-time alarm updates
- Use Streamlit's experimental features for auto-refresh without page reload

## Conclusion

The caching system shows a clear disparity between the summary and detail pages. The summary page prioritizes freshness with 30-second refreshes and no function caching, while the detail page prioritizes performance with 60-second caches. This can lead to inconsistent alarm states between views, particularly when alarms change state within the 60-second cache window of the detail page.