# Root conftest.py - must be loaded before pytest tries to traverse directories
# This handles macOS SIP/permission errors on protected files

def pytest_ignore_collect(collection_path):
    """Ignore files that cannot be stat'd due to macOS SIP or permission issues."""
    try:
        # Just try to stat the path - if it fails, ignore it
        collection_path.stat()
    except PermissionError:
        return True
    
    # Always ignore certain known problematic files
    ignored_patterns = ['.env', '.coverage', '.DS_Store', '.bak']
    name = str(collection_path.name)
    for pattern in ignored_patterns:
        if pattern in name:
            return True
    
    return None
