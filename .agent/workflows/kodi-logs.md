---
description: analyzing Kodi logs for debugging
---

# Kodi Log Analysis Workflow

## Log File Locations

| Platform | Path |
|----------|------|
| **macOS** | `~/Library/Logs/kodi.log` |
| **Windows** | `%APPDATA%\Kodi\kodi.log` |
| **Linux** | `~/.kodi/temp/kodi.log` |
| **Android** | `/sdcard/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log` |

---

## Workflow Steps

### Step 1: Check Timestamp First

// turbo
```bash
# macOS - show first 5 lines to verify log freshness
head -5 ~/Library/Logs/kodi.log
```

Compare the timestamp with current time. If log is stale (old session), **warn the user** before proceeding.

### Step 2: Filter for MUBI Plugin Entries

// turbo
```bash
# macOS - grep for MUBI-related entries
grep -i "mubi\|plugin.video.mubi" ~/Library/Logs/kodi.log | tail -100
```

### Step 3: Check for Errors

// turbo
```bash
# Find error-level entries for MUBI
grep -E "(error|ERROR|Error).*mubi" ~/Library/Logs/kodi.log | tail -50
```

---

## Log Entry Format

```
YYYY-MM-DD HH:MM:SS.mmm T:thread_id level <category>: message
```

Example:
```
2025-12-05 19:16:54.438 T:3733214 debug <general>: CScriptRunner: running add-on script MUBI
```

---

## Key Patterns to Look For

| Pattern | Meaning |
|---------|---------|
| `running add-on script MUBI` | Plugin startup |
| `Starting GitHub Sync` | Sync initiated |
| `Schema version: 1` | JSON version info |
| `Successfully downloaded and parsed` | Sync completed |
| `Error downloading file` | Network/download failure |
| `MD5 verification` | Integrity check result |
| `Failed to parse` | Schema/parsing error |

---

## Important Rules

1. **Only read logs when explicitly asked** - do not proactively access
2. **Always verify timestamp** - stale logs provide no meaningful debugging info
3. **Focus on recent entries** - use `tail` to get latest entries
