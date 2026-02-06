"""
Typed Kodi Stubs for Testing

These stubs provide realistic API behavior matching real Kodi modules.
They replace MagicMock to catch type errors and provide predictable behavior.

Reference: https://codedocs.xyz/xbmc/xbmc/
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Callable, Optional
from unittest.mock import Mock


# =============================================================================
# xbmcaddon Stubs
# =============================================================================

class AddonStub:
    """Typed stub for xbmcaddon.Addon.
    
    Real behavior:
    - getSetting() returns empty string for unknown keys
    - getSettingBool() returns False for unknown keys
    - getSettingInt() returns 0 for unknown keys
    """
    
    def __init__(self, addon_id: str = "plugin.video.mubi"):
        self._addon_id = addon_id
        self._settings: dict[str, str] = {}
        self._addon_info: dict[str, str] = {
            "path": "/tmp/mock_addon",
            "profile": "/tmp/mock_addon/userdata",
            "id": addon_id,
            "name": "MUBI",
            "version": "1.0.0",
        }
    
    def getSetting(self, key: str) -> str:
        """Returns setting value or empty string if not set."""
        if not isinstance(key, str):
            raise TypeError(f"key must be str, not {type(key).__name__}")
        return self._settings.get(key, "")
    
    def setSetting(self, key: str, value: str) -> None:
        """Sets a setting value."""
        if not isinstance(key, str):
            raise TypeError(f"key must be str, not {type(key).__name__}")
        if not isinstance(value, str):
            raise TypeError(f"value must be str, not {type(value).__name__}")
        self._settings[key] = value
    
    def getSettingBool(self, key: str) -> bool:
        """Returns setting as boolean. Returns False if not set."""
        val = self.getSetting(key).lower()
        return val in ("true", "1", "yes")
    
    def setSettingBool(self, key: str, value: bool) -> None:
        """Sets a boolean setting."""
        self._settings[key] = "true" if value else "false"
    
    def getSettingInt(self, key: str) -> int:
        """Returns setting as integer. Returns 0 if not set or invalid."""
        try:
            return int(self.getSetting(key))
        except (ValueError, TypeError):
            return 0
    
    def setSettingInt(self, key: str, value: int) -> None:
        """Sets an integer setting."""
        self._settings[key] = str(value)
    
    def getAddonInfo(self, key: str) -> str:
        """Returns addon info. Keys: id, name, version, path, profile, etc."""
        return self._addon_info.get(key, "")
    
    def openSettings(self) -> None:
        """Opens addon settings dialog (no-op in tests)."""
        pass
    
    def getLocalizedString(self, string_id: int) -> str:
        """Returns localized string by ID."""
        return f"[String:{string_id}]"


# =============================================================================
# xbmcvfs Stubs
# =============================================================================

class VFSStub:
    """Typed stub for xbmcvfs module functions.
    
    Provides realistic filesystem operations using temp directories.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        self._base_path = base_path or tempfile.mkdtemp(prefix="kodi_test_")
        self._files: dict[str, bytes] = {}  # Virtual filesystem
    
    def translatePath(self, path: str) -> str:
        """Translates special:// paths to real paths."""
        if path.startswith("special://"):
            # Map common special paths
            if "profile" in path:
                return os.path.join(self._base_path, "userdata")
            elif "home" in path:
                return self._base_path
            else:
                return self._base_path
        return path
    
    def exists(self, path: str) -> bool:
        """Check if path exists (real or virtual)."""
        real_path = self.translatePath(path)
        return os.path.exists(real_path) or path in self._files
    
    def mkdirs(self, path: str) -> bool:
        """Create directory tree."""
        try:
            os.makedirs(self.translatePath(path), exist_ok=True)
            return True
        except OSError:
            return False
    
    def mkdir(self, path: str) -> bool:
        """Create single directory."""
        try:
            os.makedirs(self.translatePath(path), exist_ok=True)
            return True
        except OSError:
            return False
    
    def rmdir(self, path: str) -> bool:
        """Remove directory."""
        try:
            os.rmdir(self.translatePath(path))
            return True
        except OSError:
            return False
    
    def delete(self, path: str) -> bool:
        """Delete file."""
        try:
            os.remove(self.translatePath(path))
            return True
        except OSError:
            return False
    
    def copy(self, source: str, destination: str) -> bool:
        """Copy file."""
        import shutil
        try:
            shutil.copy(self.translatePath(source), self.translatePath(destination))
            return True
        except OSError:
            return False
    
    def listdir(self, path: str) -> tuple[list[str], list[str]]:
        """List directory contents. Returns (dirs, files) tuple."""
        real_path = self.translatePath(path)
        if not os.path.isdir(real_path):
            return ([], [])
        
        dirs = []
        files = []
        for item in os.listdir(real_path):
            if os.path.isdir(os.path.join(real_path, item)):
                dirs.append(item)
            else:
                files.append(item)
        return (dirs, files)


class VFSFileStub:
    """Stub for xbmcvfs.File context manager."""
    
    def __init__(self, path: str, mode: str = "r"):
        self._path = path
        self._mode = mode
        self._content = b""
        self._position = 0
        
        # Read existing content if opening for read
        if "r" in mode and os.path.exists(path):
            with open(path, "rb") as f:
                self._content = f.read()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Write content if opened for write
        if "w" in self._mode:
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
            with open(self._path, "wb") as f:
                f.write(self._content)
        return False
    
    def read(self, num_bytes: int = -1) -> bytes:
        """Read bytes from file."""
        if num_bytes == -1:
            data = self._content[self._position:]
            self._position = len(self._content)
        else:
            data = self._content[self._position:self._position + num_bytes]
            self._position += len(data)
        return data
    
    def readBytes(self, num_bytes: int = -1) -> bytes:
        """Alias for read() for Kodi compatibility."""
        return self.read(num_bytes)
    
    def write(self, data: bytes | str) -> bool:
        """Write data to file."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._content += data
        return True
    
    def seek(self, position: int) -> int:
        """Seek to position."""
        self._position = min(max(0, position), len(self._content))
        return self._position
    
    def size(self) -> int:
        """Get file size."""
        return len(self._content)
    
    def close(self) -> None:
        """Close file (no-op, handled by context manager)."""
        pass


# =============================================================================
# xbmcgui Stubs  
# =============================================================================

class DialogStub:
    """Typed stub for xbmcgui.Dialog."""
    
    def __init__(self):
        self._last_notification: Optional[tuple] = None
        self._last_ok: Optional[tuple] = None
        self._select_return = -1
        self._yesno_return = False
        self._input_return = ""
    
    def notification(self, heading: str, message: str, icon: str = "", time: int = 5000, sound: bool = True) -> None:
        """Show notification."""
        self._last_notification = (heading, message, icon, time, sound)
    
    def ok(self, heading: str, message: str) -> bool:
        """Show OK dialog."""
        self._last_ok = (heading, message)
        return True
    
    def yesno(self, heading: str, message: str, nolabel: str = "", yeslabel: str = "", autoclose: int = 0) -> bool:
        """Show Yes/No dialog."""
        return self._yesno_return
    
    def select(self, heading: str, options: list, autoclose: int = 0, preselect: int = -1, useDetails: bool = False) -> int:
        """Show select dialog. Returns selected index or -1 if cancelled."""
        return self._select_return
    
    def input(self, heading: str, default: str = "", type: int = 0, option: int = 0, autoclose: int = 0) -> str:
        """Show input dialog."""
        return self._input_return


class DialogProgressStub:
    """Typed stub for xbmcgui.DialogProgress."""
    
    def __init__(self):
        self._created = False
        self._heading = ""
        self._message = ""
        self._percent = 0
        self._cancelled = False
    
    def create(self, heading: str, message: str = "") -> None:
        """Create progress dialog."""
        self._created = True
        self._heading = heading
        self._message = message
    
    def update(self, percent: int, message: str = "") -> None:
        """Update progress."""
        self._percent = percent
        if message:
            self._message = message
    
    def close(self) -> None:
        """Close dialog."""
        self._created = False
    
    def iscanceled(self) -> bool:
        """Check if user cancelled."""
        return self._cancelled


class ListItemStub:
    """Typed stub for xbmcgui.ListItem."""
    
    def __init__(self, label: str = "", label2: str = "", path: str = "", offscreen: bool = False):
        self._label = label
        self._label2 = label2
        self._path = path
        self._info: dict[str, dict[str, Any]] = {}
        self._art: dict[str, str] = {}
        self._properties: dict[str, str] = {}
        self._stream_info: dict[str, list] = {}
        self._is_folder = False
        self._content_lookup = True
        self._mime_type = ""
    
    def setLabel(self, label: str) -> None:
        self._label = label
    
    def getLabel(self) -> str:
        return self._label
    
    def setLabel2(self, label2: str) -> None:
        self._label2 = label2
    
    def setPath(self, path: str) -> None:
        self._path = path
    
    def getPath(self) -> str:
        return self._path
    
    def setInfo(self, type: str, infoLabels: dict) -> None:
        self._info[type] = infoLabels
    
    def getInfo(self, type: str) -> dict:
        return self._info.get(type, {})
    
    def setArt(self, art: dict) -> None:
        self._art.update(art)
    
    def setProperty(self, key: str, value: str) -> None:
        self._properties[key] = value
    
    def getProperty(self, key: str) -> str:
        return self._properties.get(key, "")
    
    def addStreamInfo(self, type: str, values: dict) -> None:
        if type not in self._stream_info:
            self._stream_info[type] = []
        self._stream_info[type].append(values)
    
    def setIsFolder(self, is_folder: bool) -> None:
        self._is_folder = is_folder
    
    def setContentLookup(self, lookup: bool) -> None:
        self._content_lookup = lookup
    
    def setMimeType(self, mime_type: str) -> None:
        self._mime_type = mime_type


# =============================================================================
# xbmcplugin Stubs
# =============================================================================

class PluginStub:
    """Typed stub for xbmcplugin module functions.
    
    Tracks plugin state for assertions in tests.
    """
    
    # Constants
    SORT_METHOD_NONE = 0
    SORT_METHOD_TITLE = 1
    SORT_METHOD_DATE = 2
    SORT_METHOD_SIZE = 3
    
    def __init__(self):
        self._directory_items: list[tuple] = []
        self._content_type: Optional[str] = None
        self._sort_methods: list[int] = []
        self._resolved_url: Optional[tuple] = None
        self._ended = False
    
    def addDirectoryItem(self, handle: int, url: str, listitem: ListItemStub, isFolder: bool = False, totalItems: int = 0) -> bool:
        """Add item to directory listing."""
        self._directory_items.append((handle, url, listitem, isFolder))
        return True
    
    def addDirectoryItems(self, handle: int, items: list, totalItems: int = 0) -> bool:
        """Add multiple items to directory listing."""
        for url, listitem, isFolder in items:
            self._directory_items.append((handle, url, listitem, isFolder))
        return True
    
    def endOfDirectory(self, handle: int, succeeded: bool = True, updateListing: bool = False, cacheToDisc: bool = True) -> None:
        """End directory listing."""
        self._ended = True
    
    def setContent(self, handle: int, content: str) -> None:
        """Set plugin content type (movies, tvshows, etc)."""
        self._content_type = content
    
    def addSortMethod(self, handle: int, sortMethod: int) -> None:
        """Add sort method."""
        self._sort_methods.append(sortMethod)
    
    def setResolvedUrl(self, handle: int, succeeded: bool, listitem: ListItemStub) -> None:
        """Set resolved URL for playback."""
        self._resolved_url = (handle, succeeded, listitem)


# =============================================================================
# Factory Functions
# =============================================================================

def create_mock_modules(base_path: Optional[str] = None) -> dict:
    """Create all mock modules with typed stubs.
    
    Returns dict that can be used to update sys.modules.
    """
    addon = AddonStub()
    vfs = VFSStub(base_path)
    plugin = PluginStub()
    
    # Create module-like objects
    xbmcaddon = Mock()
    xbmcaddon.Addon = lambda *args, **kwargs: addon
    
    xbmcvfs = Mock()
    xbmcvfs.translatePath = vfs.translatePath
    xbmcvfs.exists = vfs.exists
    xbmcvfs.mkdirs = vfs.mkdirs
    xbmcvfs.mkdir = vfs.mkdir
    xbmcvfs.rmdir = vfs.rmdir
    xbmcvfs.delete = vfs.delete
    xbmcvfs.copy = vfs.copy
    xbmcvfs.listdir = vfs.listdir
    xbmcvfs.File = VFSFileStub
    
    xbmcgui = Mock()
    xbmcgui.Dialog = DialogStub
    xbmcgui.DialogProgress = DialogProgressStub
    xbmcgui.ListItem = ListItemStub
    
    xbmcplugin = Mock()
    xbmcplugin.addDirectoryItem = plugin.addDirectoryItem
    xbmcplugin.addDirectoryItems = plugin.addDirectoryItems
    xbmcplugin.endOfDirectory = plugin.endOfDirectory
    xbmcplugin.setContent = plugin.setContent
    xbmcplugin.addSortMethod = plugin.addSortMethod
    xbmcplugin.setResolvedUrl = plugin.setResolvedUrl
    xbmcplugin.SORT_METHOD_NONE = PluginStub.SORT_METHOD_NONE
    
    return {
        'xbmcaddon': xbmcaddon,
        'xbmcvfs': xbmcvfs,
        'xbmcgui': xbmcgui,
        'xbmcplugin': xbmcplugin,
        '_addon': addon,
        '_vfs': vfs,
        '_plugin': plugin,
    }
