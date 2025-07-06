# Debugging Hosts Navigation Issue

## Debugging Code Added

I've added comprehensive debugging code to help diagnose why hosts aren't appearing in the navigation sidebar. Here's what has been added:

### 1. Layout Component (`/frontend/src/components/layout/Layout.tsx`)
- Added console logging for React Query state (data, error, loading status)
- Added console logging when rendering the hosts section
- Added visual feedback in the UI:
  - Shows "Loading hosts..." when query is loading
  - Shows error message if query fails
  - Shows "No hosts configured" if query succeeds but returns empty array
  - Shows detailed error information if available

### 2. Hosts API (`/frontend/src/api/hosts.ts`)
- Added console logging for the request parameters
- Added console logging for the full response
- Added error catching and logging

### 3. API Client (`/frontend/src/api/client.ts`)
- Added request interceptor logging:
  - Method, URL, base URL, full URL
  - Request parameters
  - Headers (including auth token)
  - Timestamp
- Added response interceptor logging:
  - Response status and data
  - Error details if request fails
  - Timestamp

### 4. HostNavItem Component (`/frontend/src/components/navigation/HostNavItem.tsx`)
- Added console logging when rendering each host

## How to Debug

1. **Open Browser DevTools Console**
   - Look for logs starting with:
     - `[API Request]` - Shows outgoing requests
     - `[API Response]` - Shows successful responses
     - `[API Response Error]` - Shows failed requests
     - `[hostsApi.list]` - Shows hosts API specific logs
     - `[Layout]` - Shows React Query state and rendering
     - `[HostNavItem]` - Shows individual host rendering

2. **Check Network Tab**
   - Look for request to `/api/v1/hosts?active_only=true`
   - Check the response status and data
   - Verify authentication headers are present

3. **Visual Feedback**
   - The sidebar will now show:
     - Loading state while fetching
     - Error message if request fails
     - Empty state if no hosts exist
     - Actual hosts if data loads successfully

## Common Issues to Check

1. **Authentication**: Verify Bearer token is being sent
2. **API URL**: Check if the full URL is correct (baseURL + endpoint)
3. **Response Format**: Ensure API returns expected format with `items` array
4. **Permissions**: User might not have permission to view hosts
5. **Backend**: API endpoint might not be returning data

## Next Steps

After checking the console and network tabs:
1. Share any error messages you see
2. Share the network request/response details
3. Share console log output

This will help identify whether the issue is:
- Frontend query configuration
- API client configuration
- Backend API response
- Authentication/permissions
- Data format mismatch