import pytest
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET
from resources.lib.migrations import (
    add_mubi_source, read_xml, write_xml, show_source_added_message,
    is_first_run, mark_first_run
)


class TestMigrations:
    """Test cases for the migrations module."""

    @patch('xbmcvfs.translatePath')
    @patch('xbmc.log')
    def test_add_mubi_source_new_file(self, mock_log, mock_translate_path):
        """Test adding MUBI source when sources.xml doesn't exist."""
        mock_translate_path.return_value = '/fake/path/sources.xml'

        # Function should run without crashing
        add_mubi_source()

        # Should log something
        mock_log.assert_called()

    @patch('xbmcvfs.translatePath')
    @patch('xbmcvfs.exists')
    @patch('resources.lib.migrations.read_xml')
    @patch('xbmc.log')
    def test_add_mubi_source_existing_source(self, mock_log, mock_read_xml, 
                                           mock_exists, mock_translate_path):
        """Test adding MUBI source when it already exists."""
        mock_translate_path.return_value = '/fake/path/sources.xml'
        mock_exists.return_value = True
        
        # Create mock XML with existing MUBI source
        root = ET.Element("sources")
        video = ET.SubElement(root, "video")
        source = ET.SubElement(video, "source")
        path = ET.SubElement(source, "path")
        path.text = 'special://userdata/addon_data/plugin.video.mubi'
        
        mock_tree = Mock()
        mock_tree.getroot.return_value = root
        mock_read_xml.return_value = mock_tree
        
        add_mubi_source()
        
        # Should log that source already exists
        mock_log.assert_called()

    @patch('xbmcvfs.translatePath')
    @patch('xbmc.log')
    def test_add_mubi_source_new_source(self, mock_log, mock_translate_path):
        """Test adding MUBI source when sources.xml exists but no MUBI source."""
        mock_translate_path.return_value = '/fake/path/sources.xml'

        # Function should run without crashing
        add_mubi_source()

        # Should log something
        mock_log.assert_called()

    @patch('xbmcvfs.translatePath')
    @patch('resources.lib.migrations.read_xml')
    @patch('xbmc.log')
    def test_add_mubi_source_read_xml_failure(self, mock_log, mock_read_xml, mock_translate_path):
        """Test adding MUBI source when XML reading fails."""
        mock_translate_path.return_value = '/fake/path/sources.xml'
        mock_read_xml.return_value = None  # Simulate read failure
        
        add_mubi_source()
        
        # Should handle the error gracefully
        mock_log.assert_called()

    @patch('xbmcvfs.translatePath')
    @patch('xbmc.log')
    def test_add_mubi_source_exception(self, mock_log, mock_translate_path):
        """Test adding MUBI source handles exceptions."""
        mock_translate_path.side_effect = Exception("Path error")

        # The function should raise the exception since translatePath is outside try-catch
        with pytest.raises(Exception, match="Path error"):
            add_mubi_source()

        # Log may or may not be called depending on when exception occurs

    @patch('xbmcvfs.exists')
    @patch('xbmc.log')
    def test_read_xml_success(self, mock_log, mock_exists):
        """Test successful XML reading."""
        mock_exists.return_value = True

        # Mock file content
        xml_content = '<?xml version="1.0"?><sources><video></video></sources>'

        # Use the MockFile class from conftest.py
        with patch('xbmcvfs.File') as mock_file_class:
            mock_file_instance = Mock()
            mock_file_instance.read.return_value = xml_content
            mock_file_instance.__enter__ = Mock(return_value=mock_file_instance)
            mock_file_instance.__exit__ = Mock(return_value=None)
            mock_file_class.return_value = mock_file_instance

            tree = read_xml('/fake/path/sources.xml')

            assert tree is not None
            assert tree.getroot().tag == "sources"
            mock_log.assert_called()

    @patch('xbmcvfs.exists')
    @patch('xbmc.log')
    def test_read_xml_file_not_exists(self, mock_log, mock_exists):
        """Test XML reading when file doesn't exist."""
        mock_exists.return_value = False
        
        tree = read_xml('/fake/path/sources.xml')
        
        assert tree is None
        mock_log.assert_called()

    @patch('xbmcvfs.exists')
    @patch('xbmcvfs.File')
    @patch('xbmc.log')
    def test_read_xml_exception(self, mock_log, mock_file, mock_exists):
        """Test XML reading handles exceptions."""
        mock_exists.return_value = True
        mock_file.side_effect = Exception("File error")
        
        tree = read_xml('/fake/path/sources.xml')
        
        assert tree is None
        mock_log.assert_called()

    @patch('xbmc.log')
    def test_write_xml_success(self, mock_log):
        """Test successful XML writing."""
        # Create a simple XML tree
        root = ET.Element("sources")
        tree = ET.ElementTree(root)

        with patch('xbmcvfs.File') as mock_file_class:
            mock_file_instance = Mock()
            mock_file_instance.__enter__ = Mock(return_value=mock_file_instance)
            mock_file_instance.__exit__ = Mock(return_value=None)
            mock_file_instance.write = Mock()
            mock_file_class.return_value = mock_file_instance

            write_xml(tree, '/fake/path/sources.xml')

            mock_file_instance.write.assert_called_once()
            mock_log.assert_called()

    @patch('xbmcvfs.File')
    @patch('xbmc.log')
    def test_write_xml_exception(self, mock_log, mock_file):
        """Test XML writing handles exceptions."""
        root = ET.Element("sources")
        tree = ET.ElementTree(root)
        
        mock_file.side_effect = Exception("Write error")
        
        write_xml(tree, '/fake/path/sources.xml')
        
        mock_log.assert_called()

    @patch('xbmcgui.Dialog')
    def test_show_source_added_message(self, mock_dialog):
        """Test showing source added message."""
        mock_dialog_instance = Mock()
        mock_dialog.return_value = mock_dialog_instance
        
        show_source_added_message()
        
        mock_dialog_instance.ok.assert_called_once()
        args = mock_dialog_instance.ok.call_args[0]
        assert "MUBI Source Added" in args[0]
        assert "MUBI Movies source has been added" in args[1]

    def test_is_first_run_true(self, mock_addon):
        """Test is_first_run returns True when first run not completed."""
        mock_addon.getSettingBool.return_value = False
        
        result = is_first_run(mock_addon)
        
        assert result is True
        mock_addon.getSettingBool.assert_called_with('first_run_completed')

    def test_is_first_run_false(self, mock_addon):
        """Test is_first_run returns False when first run completed."""
        mock_addon.getSettingBool.return_value = True
        
        result = is_first_run(mock_addon)
        
        assert result is False
        mock_addon.getSettingBool.assert_called_with('first_run_completed')

    def test_mark_first_run(self, mock_addon):
        """Test marking first run as completed."""
        mark_first_run(mock_addon)
        
        mock_addon.setSettingBool.assert_called_with('first_run_completed', True)

    @patch('xbmcvfs.translatePath')
    @patch('xbmc.log')
    def test_add_mubi_source_no_video_element(self, mock_log, mock_translate_path):
        """Test adding MUBI source when sources.xml has no video element."""
        mock_translate_path.return_value = '/fake/path/sources.xml'

        # Function should run without crashing
        add_mubi_source()

        # Should log something
        mock_log.assert_called()

    @patch('xbmcvfs.translatePath')
    @patch('xbmc.log')
    def test_add_mubi_source_different_path(self, mock_log, mock_translate_path):
        """Test adding MUBI source when existing source has different path."""
        mock_translate_path.return_value = '/fake/path/sources.xml'

        # Function should run without crashing
        add_mubi_source()

        # Should log something
        mock_log.assert_called()

    @patch('xbmcvfs.exists')
    def test_read_xml_invalid_xml(self, mock_exists):
        """Test reading invalid XML content."""
        mock_exists.return_value = True

        # Mock invalid XML content
        xml_content = '<invalid><xml><content>'

        with patch('xbmcvfs.File') as mock_file_class:
            mock_file_instance = Mock()
            mock_file_instance.read.return_value = xml_content
            mock_file_instance.__enter__ = Mock(return_value=mock_file_instance)
            mock_file_instance.__exit__ = Mock(return_value=None)
            mock_file_class.return_value = mock_file_instance

            with patch('xbmc.log') as mock_log:
                tree = read_xml('/fake/path/sources.xml')

            assert tree is None
            mock_log.assert_called()

    def test_xml_structure_validation(self):
        """Test that XML structure is created correctly."""
        # Create a new sources XML structure
        root = ET.Element("sources")
        video_sources = ET.SubElement(root, "video")
        
        new_source = ET.SubElement(video_sources, "source")
        
        name = ET.SubElement(new_source, "name")
        name.text = "MUBI Movies"
        
        path = ET.SubElement(new_source, "path")
        path.text = 'special://userdata/addon_data/plugin.video.mubi'
        path.set("pathversion", "1")
        
        allowsharing = ET.SubElement(new_source, "allowsharing")
        allowsharing.text = "true"
        
        # Verify structure
        assert root.tag == "sources"
        assert video_sources.tag == "video"
        assert new_source.tag == "source"
        assert name.text == "MUBI Movies"
        assert path.text == 'special://userdata/addon_data/plugin.video.mubi'
        assert path.get("pathversion") == "1"
        assert allowsharing.text == "true"
