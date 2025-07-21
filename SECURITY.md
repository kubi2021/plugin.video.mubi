# Security Policy

## Security Level

This Kodi plugin implements **Level 2 (Filesystem Safety)** protection, which provides an optimal balance between security and user experience for local media consumption applications.

## Security Framework

### Level 2 (Filesystem Safety) - Current Implementation

**Scope**: Prevents filesystem-related issues while preserving media title readability.

#### What Level 2 Protects Against:
- ✅ **Filesystem crashes** and incompatibilities across platforms
- ✅ **Path traversal attacks** (`../../../etc/passwd`, `....`, etc.)
- ✅ **Windows reserved name conflicts** (CON, PRN, AUX, COM1, LPT1, etc.)
- ✅ **Cross-platform filename issues** (Windows/Mac/Linux/Android/Apple TV)
- ✅ **Control character injection** (null bytes, Unicode control sequences)
- ✅ **Dangerous Unicode sequences** (zero-width chars, BOM, non-characters)

#### Filesystem-Dangerous Characters Removed:
```
< > : " / \ | ? *
```

#### What Level 2 Preserves (Good User Experience):
- ✅ **Movie title readability**: `"What's Up?"`, `"2001: A Space Odyssey"`
- ✅ **International characters**: `Amélie`, `東京物語`, `Москва`, `Niño`
- ✅ **Normal punctuation**: `' & , ( ) + = @ # ~ ! $ % ^ [ ] { }`
- ✅ **Common symbols**: `*batteries not included`, `Movie & Co`
- ✅ **Director's cuts**: `Movie (Director's Cut)`
- ✅ **Series notation**: `Movie: Episode IV`

## Implementation Details

### Filename Sanitization
- **Purpose**: Ensure filesystem compatibility
- **Method**: Remove only filesystem-dangerous characters
- **Preservation**: Keep all safe punctuation and international characters

### NFO Content Sanitization  
- **Purpose**: Preserve original movie titles in metadata
- **Method**: Minimal sanitization (only control characters)
- **Preservation**: Keep original titles with all punctuation intact

### Examples

| Original Title | Sanitized Filename | NFO Content |
|---|---|---|
| `2001: A Space Odyssey` | `2001 A Space Odyssey (2023)` | `2001: A Space Odyssey` |
| `What's Up?` | `What's Up (2023)` | `What's Up?` |
| `Movie & Co` | `Movie & Co (2023)` | `Movie & Co` |
| `"Crocodile" Dundee` | `Crocodile Dundee (2023)` | `"Crocodile" Dundee` |
| `AC/DC: Live` | `ACDC Live (2023)` | `AC/DC: Live` |

## Rationale

### Why Level 2 is Appropriate for Kodi Plugins:

1. **Context**: Local media consumption, not web servers or high-stakes environments
2. **Platforms**: Personal devices (PC, Mac, Android, Apple TV) with trusted content
3. **Content**: Movie titles with legitimate punctuation and international characters
4. **User Experience**: Media enthusiasts expect readable, properly formatted titles
5. **Risk Profile**: Low attack surface, local execution, trusted content sources

### Security Levels Comparison:

| Level | Description | Use Case | Trade-offs |
|---|---|---|---|
| **Level 1** | Minimal protection | Development only | ❌ Filesystem vulnerabilities |
| **Level 2** | Filesystem safety | **Kodi plugins** ✅ | ✅ Perfect balance |
| **Level 3** | Basic injection protection | Web applications | ❌ Removes legitimate characters |
| **Level 4** | Paranoid protection | High-security environments | ❌ Poor user experience |
| **Level 5** | Maximum security | Military/financial systems | ❌ Breaks media titles |

## Testing

Our security implementation is validated through comprehensive test suites:

- ✅ **Filesystem safety tests**: Verify dangerous characters are removed
- ✅ **Preservation tests**: Ensure safe characters are kept
- ✅ **Cross-platform tests**: Validate Windows/Mac/Linux compatibility
- ✅ **Edge case tests**: Handle empty strings, reserved names, long titles
- ✅ **Real-world tests**: Test actual movie titles from various cultures
- ✅ **NFO integrity tests**: Verify metadata preservation
