import sys
from unittest.mock import MagicMock

# Mock xbmc and other related modules
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
