---
name: kodi-logs
description: Read and triage a Kodi log for this plugin. Use only when the user asks to look at Kodi logs or pastes one. Never read the log proactively.
argument-hint: "[path to kodi.log]"
---

# Kodi log triage

## Locate

| Platform | Path |
|---|---|
| macOS | `~/Library/Logs/kodi.log` |
| Linux | `~/.kodi/temp/kodi.log` |
| Windows | `%APPDATA%\Kodi\kodi.log` |
| Android | `/sdcard/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log` |

Use `$ARGUMENTS` if given, else the platform default.

## Procedure

1. Freshness: `head -3 <log>`. If the first timestamp is not today, say so before continuing.
2. Plugin lines: `grep -in 'mubi' <log> | tail -150`.
3. Errors: `grep -inE 'error|exception|traceback' <log> | grep -i mubi | tail -50`. Read the 20 lines around each Python traceback.
4. Correlate with code: every `xbmc.log` message is a literal string; `grep -rn "<message prefix>" repo/plugin_video_mubi` finds the emitter.

Format: `YYYY-MM-DD HH:MM:SS.mmm T:<thread> <level> <component>: <message>`.

## Markers

| Text | Meaning |
|---|---|
| `running add-on script MUBI` | plugin invoked (new process each call) |
| `Starting GitHub Sync` | Fast Sync began |
| `Schema version:` | database version read |
| `MD5 verification` | integrity check result |
| `Successfully downloaded and parsed` | Fast Sync data OK |
| `Error downloading file` / `Max retries` | network |
| `Failed to parse` | schema or JSON problem |
| `Sync already in progress` | lock hit |
| `Invalid API Key` | TMDb/OMDb key rejected |

## Report

Timeline of what the user did, first error with its traceback, the emitting `file:line`, and a hypothesis. Do not fix anything unless asked. Never paste tokens or keys from the log; the plugin redacts them, but confirm.
