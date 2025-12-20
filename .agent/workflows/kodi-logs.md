---
type: "always_apply"
---

# Kodi Log Analysis Rules

## Log File Location (macOS)

The Kodi log file is located at:
```
~/Library/Logs/kodi.log
```

## When to Access Logs

- **Only look at the log when explicitly prompted by the user**
- Do NOT proactively read logs without being asked

## Timestamp Verification

Before analyzing logs for debugging purposes:

1. **Always check the timestamp** at the start of log entries
2. Compare the log timestamp with the current time
3. If the log is old (not from the current session), **warn the user** that the log may be stale
4. Debugging based on old logs provides **no meaningful information** for current issues

## Log Entry Format

Kodi log entries follow this format:
```
YYYY-MM-DD HH:MM:SS.mmm T:thread_id level <category>: message
```

Example:
```
2025-12-05 19:16:54.438 T:3733214 debug <general>: CScriptRunner: running add-on script MUBI
```

## Key Log Patterns for MUBI Plugin

- Plugin initialization: `running add-on script MUBI`
- API calls: `Making API call: GET https://api.mubi.com/v4/`
- Metadata extraction: `Using enhanced editorial content`, `Found fanart`, `Found poster`
- Errors: Look for `error` level entries related to `plugin.video.mubi`

