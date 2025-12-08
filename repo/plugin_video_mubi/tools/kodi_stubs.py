"""
Kodi Stubs for Standalone Execution

Provides mock implementations of Kodi modules (xbmc, xbmcaddon, xbmcgui, etc.)
so that plugin code can run outside of Kodi for development/analysis tools.
"""

import sys
from types import ModuleType


# ============================================================================
# xbmc module stub
# ============================================================================
class XbmcStub(ModuleType):
    """Mock xbmc module."""

    # Log levels
    LOGDEBUG = 0
    LOGINFO = 1
    LOGWARNING = 2
    LOGERROR = 3
    LOGFATAL = 4

    # Log level names for output
    _LOG_NAMES = {0: 'DEBUG', 1: 'INFO', 2: 'WARNING', 3: 'ERROR', 4: 'FATAL'}

    # Control verbosity
    _verbose = False

    @staticmethod
    def log(message, level=1):
        """Print log messages to stdout when verbose."""
        if XbmcStub._verbose or level >= XbmcStub.LOGWARNING:
            level_name = XbmcStub._LOG_NAMES.get(level, 'INFO')
            print(f"[{level_name}] {message}")

    @staticmethod
    def translatePath(path):
        """Return path as-is."""
        return path

    @staticmethod
    def getCondVisibility(condition):
        """Return False for all conditions."""
        return False

    @staticmethod
    def executebuiltin(command):
        """No-op for executebuiltin."""
        pass

    @staticmethod
    def sleep(ms):
        """Sleep for milliseconds."""
        import time
        time.sleep(ms / 1000.0)


# ============================================================================
# xbmcaddon module stub
# ============================================================================
class AddonStub:
    """Mock Addon class."""

    _settings = {}

    def __init__(self, addon_id=None):
        self.addon_id = addon_id or 'plugin.video.mubi'

    def getSetting(self, key):
        """Return empty string for all settings."""
        return AddonStub._settings.get(key, '')

    def setSetting(self, key, value):
        """Store setting in memory."""
        AddonStub._settings[key] = value

    def getAddonInfo(self, info_type):
        """Return addon info."""
        info = {
            'id': self.addon_id,
            'name': 'MUBI',
            'version': '1.0.0',
            'path': '/tmp/plugin.video.mubi',
            'profile': '/tmp/plugin.video.mubi/userdata',
        }
        return info.get(info_type, '')

    def getLocalizedString(self, string_id):
        """Return placeholder string."""
        return f"String_{string_id}"


class XbmcaddonStub(ModuleType):
    """Mock xbmcaddon module."""

    Addon = AddonStub


# ============================================================================
# xbmcgui module stub
# ============================================================================
class DialogStub:
    """Mock Dialog class."""

    def ok(self, heading, message):
        print(f"[DIALOG] {heading}: {message}")
        return True

    def yesno(self, heading, message):
        return False

    def notification(self, heading, message, icon=None, time=5000):
        print(f"[NOTIFICATION] {heading}: {message}")


class DialogProgressStub:
    """Mock DialogProgress class."""

    def __init__(self):
        self._cancelled = False

    def create(self, heading, message=''):
        print(f"[PROGRESS] {heading}: {message}")

    def update(self, percent, message=''):
        pass

    def close(self):
        pass

    def iscanceled(self):
        return self._cancelled


class XbmcguiStub(ModuleType):
    """Mock xbmcgui module."""

    Dialog = DialogStub
    DialogProgress = DialogProgressStub


# ============================================================================
# xbmcplugin module stub
# ============================================================================
class XbmcpluginStub(ModuleType):
    """Mock xbmcplugin module."""

    @staticmethod
    def setContent(handle, content):
        pass

    @staticmethod
    def addDirectoryItem(handle, url, listitem, isFolder=False):
        pass

    @staticmethod
    def endOfDirectory(handle, succeeded=True):
        pass


# ============================================================================
# xbmcvfs module stub
# ============================================================================
class XbmcvfsStub(ModuleType):
    """Mock xbmcvfs module."""

    @staticmethod
    def exists(path):
        import os
        return os.path.exists(path)

    @staticmethod
    def mkdir(path):
        import os
        os.makedirs(path, exist_ok=True)
        return True

    @staticmethod
    def mkdirs(path):
        import os
        os.makedirs(path, exist_ok=True)
        return True

    @staticmethod
    def translatePath(path):
        return path


# ============================================================================
# inputstreamhelper module stub
# ============================================================================
class InputStreamHelperStub:
    """Mock InputStreamHelper class."""

    def __init__(self, protocol, drm=None):
        self.protocol = protocol
        self.drm = drm

    def check_inputstream(self):
        return True


class InputstreamhelperStub(ModuleType):
    """Mock inputstreamhelper module."""

    Helper = InputStreamHelperStub

