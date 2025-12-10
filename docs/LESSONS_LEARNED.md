# Lessons Learned: Kodi API Compatibility Issues

## Incident Summary

During the development of the external metadata feature for the MUBI Kodi addon, a critical compatibility issue was discovered with Kodi API usage. The issue involved the use of deprecated Kodi APIs that were removed in Kodi 19, causing the addon to fail on newer Kodi versions.

## What Went Wrong

### The Problem
The `MetadataCache` class in `external_metadata/cache.py` was initially using `xbmc.translatePath()` to resolve addon profile paths. This API was deprecated in Kodi 19 and replaced with `xbmcvfs.translatePath()`.

### Root Cause
- **API Deprecation**: `xbmc.translatePath()` was deprecated in Kodi 19 (Matrix) in favor of `xbmcvfs.translatePath()`
- **Lack of Testing**: No automated tests existed to detect deprecated API usage
- **Version Assumptions**: Code was written assuming Kodi 18 API compatibility without forward compatibility checks

### Impact
- Addon would crash on Kodi 19+ with import/attribute errors
- Users on newer Kodi versions unable to use external metadata features
- Silent failures in cache initialization leading to degraded performance

## What We Fixed

### Immediate Fix
- Replaced `xbmc.translatePath()` with `xbmcvfs.translatePath()` in `MetadataCache.__init__()`
- Ensured all path resolution uses the correct Kodi 19+ compatible API

### Long-term Improvements
- Added comprehensive test suite for external metadata module
- Implemented Kodi API compatibility scanning in tests
- Created guidelines for future Kodi API usage

## Kodi API Compatibility Guidelines

### Kodi Version Support
- **Target**: Kodi 19 (Matrix) and later
- **Minimum**: Kodi 19.0
- **Legacy**: No support for Kodi 18 or earlier

### Deprecated APIs to Avoid

#### Path Handling
- ❌ `xbmc.translatePath(path)` - Deprecated in Kodi 19
- ✅ `xbmcvfs.translatePath(path)` - Correct for Kodi 19+

#### Cache Operations
- ❌ `xbmc.getCacheThumbName(path)` - Deprecated
- ✅ `xbmcvfs.translatePath('special://temp/') + filename` - Use temp directory

#### Info Labels
- ❌ `xbmc.getInfoLabel('System.BuildVersion')` - Deprecated patterns
- ✅ `xbmc.getInfoLabel('System.Version')` - Use correct labels

### Best Practices

#### 1. Import Correct Modules
```python
import xbmcvfs  # For file operations
import xbmcaddon  # For addon info
import xbmc  # For logging and basic functions
```

#### 2. Path Resolution
```python
# Correct
addon = xbmcaddon.Addon()
profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))

# Incorrect (deprecated)
profile_path = xbmc.translatePath(addon.getAddonInfo("profile"))
```

#### 3. File Operations
```python
# Use xbmcvfs for all file operations
with open(xbmcvfs.translatePath(path), 'r') as f:
    data = f.read()
```

#### 4. Error Handling
```python
try:
    # Kodi API calls
    pass
except Exception as e:
    xbmc.log(f"Error: {e}", xbmc.LOGERROR)
```

## Testing Requirements

### Automated Testing
- All Kodi API usage must be tested with proper mocking
- Tests must verify correct API usage (xbmcvfs vs xbmc)
- Compatibility tests must scan for deprecated API patterns

### Test Coverage
- Cache initialization and file operations
- Path resolution with xbmcvfs.translatePath
- Error handling for API failures
- Version compatibility across Kodi versions

### CI/CD Integration
- Run compatibility scanner on all commits
- Fail builds using deprecated APIs
- Maintain test coverage above 90%

## Development Checklist

### Before Implementing New Features
- [ ] Review Kodi API documentation for target version
- [ ] Check for deprecated APIs in implementation
- [ ] Add unit tests with proper Kodi API mocking
- [ ] Test on multiple Kodi versions if possible

### Code Review Checklist
- [ ] No usage of `xbmc.translatePath()`
- [ ] All file operations use `xbmcvfs`
- [ ] Proper error handling for API calls
- [ ] Logging uses appropriate levels
- [ ] Tests cover all Kodi API interactions

### Release Checklist
- [ ] Run full test suite including compatibility tests
- [ ] Verify addon.xml Kodi version requirements
- [ ] Test on Kodi 19+ environments
- [ ] Update documentation for any API changes

## Future Considerations

### Kodi Version Evolution
- Monitor Kodi API changes in upcoming versions
- Plan migration paths for breaking changes
- Consider abstraction layers for API differences

### Testing Infrastructure
- Expand compatibility test coverage
- Add integration tests for Kodi environments
- Implement automated Kodi version testing

### Documentation
- Maintain API compatibility guide
- Document breaking changes and migration steps
- Keep examples updated with current best practices

## Key Takeaways

1. **Test Early, Test Often**: Automated tests caught this issue before production deployment
2. **API Compatibility is Critical**: Kodi API changes can break addons silently
3. **Version Targeting**: Clearly define supported Kodi versions and test against them
4. **Defensive Coding**: Use proper error handling and logging for API operations
5. **Continuous Monitoring**: Regularly audit codebase for deprecated API usage

## References

- [Kodi API Documentation](https://codedocs.xyz/xbmc/xbmc/)
- [Kodi 19 Migration Guide](https://kodi.wiki/view/Migration_to_Kodi_19)
- [Addon Development Guidelines](https://kodi.wiki/view/Add-on_development)