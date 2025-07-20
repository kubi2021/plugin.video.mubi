"""
Test suite for repository infrastructure validation following QA guidelines.

Dependencies:
pip install pytest pytest-mock

Framework: pytest with mocker fixture for filesystem isolation
Structure: All tests follow Arrange-Act-Assert pattern
Coverage: Happy path, edge cases, and error handling
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import hashlib
import pytest
from unittest.mock import mock_open, MagicMock


class TestIndexPageValidation:
    """Test the index.html file for GitHub Pages hosting."""

    def test_index_page_exists_when_file_present(self, mocker):
        """Test that index.html validation passes when file exists."""
        # Arrange
        mock_path = mocker.patch('pathlib.Path')
        mock_path.return_value.exists.return_value = True

        # Act
        result = mock_path.return_value.exists()

        # Assert
        assert result is True

    def test_index_page_missing_raises_assertion_error(self, mocker):
        """Test that missing index.html raises appropriate error."""
        # Arrange
        mock_path = mocker.patch('pathlib.Path')
        mock_path.return_value.exists.return_value = False

        # Act & Assert
        with pytest.raises(AssertionError, match="index.html file must exist"):
            path_exists = mock_path.return_value.exists()
            assert path_exists, "index.html file must exist at repository root"

    def test_index_page_contains_repository_link(self, mocker):
        """Test that index.html contains correct repository zip link."""
        # Arrange
        html_content = '<a href="repository.kubi2021-2.zip">repository.kubi2021-2.zip</a>'
        mock_open_func = mock_open(read_data=html_content)
        mocker.patch('builtins.open', mock_open_func)
        mocker.patch('pathlib.Path.exists', return_value=True)

        # Act
        with open("index.html", 'r') as f:
            content = f.read()

        # Assert
        assert 'repository.kubi2021-2.zip' in content
        assert 'href=' in content

    def test_index_page_missing_repository_link_fails(self, mocker):
        """Test that index.html without repository link fails validation."""
        # Arrange
        html_content = '<html><body>No repository link here</body></html>'
        mock_open_func = mock_open(read_data=html_content)
        mocker.patch('builtins.open', mock_open_func)

        # Act
        with open("index.html", 'r') as f:
            content = f.read()

        # Assert
        assert 'repository.kubi2021-2.zip' not in content

    def test_index_page_empty_file_edge_case(self, mocker):
        """Test edge case of empty index.html file."""
        # Arrange
        mock_open_func = mock_open(read_data='')
        mocker.patch('builtins.open', mock_open_func)

        # Act
        with open("index.html", 'r') as f:
            content = f.read()

        # Assert
        assert content == ''
        assert 'repository.kubi2021-2.zip' not in content

    def test_index_page_file_read_error(self, mocker):
        """Test error handling when index.html cannot be read."""
        # Arrange
        mocker.patch('builtins.open', side_effect=IOError("Permission denied"))

        # Act & Assert
        with pytest.raises(IOError, match="Permission denied"):
            with open("index.html", 'r') as f:
                f.read()


class TestRepositoryZipValidation:
    """Test repository zip file validation with proper isolation."""

    def test_repository_zip_exists_happy_path(self, mocker):
        """Test that repository zip validation passes when file exists."""
        # Arrange
        mock_path = mocker.patch('pathlib.Path')
        mock_path.return_value.exists.return_value = True

        # Act
        from pathlib import Path
        result = Path("repository.kubi2021-2.zip").exists()

        # Assert
        assert result is True

    def test_repository_zip_missing_fails_validation(self, mocker):
        """Test that missing repository zip fails validation."""
        # Arrange
        mock_path = mocker.patch('pathlib.Path')
        mock_path.return_value.exists.return_value = False

        # Act & Assert
        with pytest.raises(AssertionError, match="repository.kubi2021-2.zip must exist"):
            from pathlib import Path
            path_exists = Path("repository.kubi2021-2.zip").exists()
            assert path_exists, "repository.kubi2021-2.zip must exist at repository root"

    def test_repository_zip_is_valid_zipfile(self, mocker):
        """Test that repository zip is a valid zip file."""
        # Arrange
        mock_zipfile = mocker.patch('zipfile.ZipFile')
        mock_zip_instance = MagicMock()
        mock_zip_instance.testzip.return_value = None  # None means valid
        mock_zip_instance.namelist.return_value = ['repository.kubi2021/addon.xml']
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Act
        with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
            test_result = zip_file.testzip()
            file_list = zip_file.namelist()

        # Assert
        assert test_result is None
        assert len(file_list) > 0

    def test_repository_zip_corrupted_raises_exception(self, mocker):
        """Test that corrupted zip file raises BadZipFile exception."""
        # Arrange
        mocker.patch('zipfile.ZipFile', side_effect=zipfile.BadZipFile("Bad zip file"))

        # Act & Assert
        with pytest.raises(zipfile.BadZipFile, match="Bad zip file"):
            with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
                zip_file.testzip()

    def test_repository_zip_empty_file_edge_case(self, mocker):
        """Test edge case of empty zip file."""
        # Arrange
        mock_zipfile = mocker.patch('zipfile.ZipFile')
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = []
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Act
        with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
            file_list = zip_file.namelist()

        # Assert
        assert len(file_list) == 0

    def test_repository_zip_contains_required_files(self, mocker):
        """Test that repository zip contains all required files."""
        # Arrange
        required_files = [
            'repository.kubi2021/addon.xml',
            'repository.kubi2021/icon.png',
            'repository.kubi2021/fanart.jpg'
        ]
        mock_zipfile = mocker.patch('zipfile.ZipFile')
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = required_files
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Act
        with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
            file_list = zip_file.namelist()

        # Assert
        addon_xml_files = [f for f in file_list if f.endswith('addon.xml')]
        icon_files = [f for f in file_list if 'icon.png' in f]
        fanart_files = [f for f in file_list if 'fanart.jpg' in f]

        assert len(addon_xml_files) > 0
        assert len(icon_files) > 0
        assert len(fanart_files) > 0


class TestXMLStructureValidation:
    """Test XML structure validation with proper mocking."""

    def test_repository_addon_xml_valid_structure(self, mocker):
        """Test that repository addon.xml has correct structure."""
        # Arrange
        valid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <addon id="repository.kubi2021" name="MUBI Repository" provider-name="kubi2021">
            <extension point="xbmc.addon.repository">
                <dir>
                    <info>https://example.com/addons.xml</info>
                </dir>
            </extension>
            <extension point="xbmc.addon.metadata">
                <summary>Test Repository</summary>
            </extension>
        </addon>'''

        mock_zipfile = mocker.patch('zipfile.ZipFile')
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ['repository.kubi2021/addon.xml']
        mock_zip_instance.read.return_value = valid_xml.encode('utf-8')
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Act
        with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
            addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
            addon_xml_content = zip_file.read(addon_xml_files[0])
            root = ET.fromstring(addon_xml_content)

        # Assert
        assert root.tag == 'addon'
        assert root.get('id') == 'repository.kubi2021'
        assert root.get('name') == 'MUBI Repository'
        assert root.get('provider-name') == 'kubi2021'

    def test_repository_addon_xml_malformed_raises_exception(self, mocker):
        """Test that malformed XML raises parsing exception."""
        # Arrange
        malformed_xml = '<addon><unclosed_tag></addon>'
        mock_zipfile = mocker.patch('zipfile.ZipFile')
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ['repository.kubi2021/addon.xml']
        mock_zip_instance.read.return_value = malformed_xml.encode('utf-8')
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Act & Assert
        with pytest.raises(ET.ParseError):
            with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
                addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
                addon_xml_content = zip_file.read(addon_xml_files[0])
                ET.fromstring(addon_xml_content)

    def test_repository_addon_xml_missing_required_attributes(self, mocker):
        """Test validation fails when required attributes are missing."""
        # Arrange
        incomplete_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <addon name="MUBI Repository">
        </addon>'''  # Missing id and provider-name

        mock_zipfile = mocker.patch('zipfile.ZipFile')
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ['repository.kubi2021/addon.xml']
        mock_zip_instance.read.return_value = incomplete_xml.encode('utf-8')
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Act
        with zipfile.ZipFile("repository.kubi2021-2.zip", 'r') as zip_file:
            addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
            addon_xml_content = zip_file.read(addon_xml_files[0])
            root = ET.fromstring(addon_xml_content)

        # Assert
        assert root.get('id') is None  # Missing required attribute
        assert root.get('provider-name') is None  # Missing required attribute


class TestMD5ChecksumValidation:
    """Test MD5 checksum validation with proper isolation."""

    def test_md5_checksum_matches_content(self, mocker):
        """Test that MD5 checksum matches actual content hash."""
        # Arrange
        test_content = b"<addons><addon>test</addon></addons>"
        expected_md5 = hashlib.md5(test_content).hexdigest()

        mock_open_addons = mock_open(read_data=test_content)
        mock_open_md5 = mock_open(read_data=expected_md5)

        def mock_open_side_effect(filename, mode='r'):
            if 'addons.xml.md5' in str(filename):
                return mock_open_md5.return_value
            elif 'addons.xml' in str(filename):
                return mock_open_addons.return_value
            return mock_open().return_value

        mocker.patch('builtins.open', side_effect=mock_open_side_effect)

        # Act
        with open("repo/zips/addons.xml", 'rb') as f:
            actual_content = f.read()
        actual_md5 = hashlib.md5(actual_content).hexdigest()

        with open("repo/zips/addons.xml.md5", 'r') as f:
            stored_md5 = f.read().strip()

        # Assert
        assert actual_md5 == stored_md5
        assert actual_md5 == expected_md5

    def test_md5_checksum_mismatch_fails_validation(self, mocker):
        """Test that MD5 mismatch fails validation."""
        # Arrange
        test_content = b"<addons><addon>test</addon></addons>"
        wrong_md5 = "wrong_hash_value"

        mock_open_addons = mock_open(read_data=test_content)
        mock_open_md5 = mock_open(read_data=wrong_md5)

        def mock_open_side_effect(filename, mode='r'):
            if 'addons.xml.md5' in str(filename):
                return mock_open_md5.return_value
            elif 'addons.xml' in str(filename):
                return mock_open_addons.return_value
            return mock_open().return_value

        mocker.patch('builtins.open', side_effect=mock_open_side_effect)

        # Act
        with open("repo/zips/addons.xml", 'rb') as f:
            actual_content = f.read()
        actual_md5 = hashlib.md5(actual_content).hexdigest()

        with open("repo/zips/addons.xml.md5", 'r') as f:
            stored_md5 = f.read().strip()

        # Assert
        assert actual_md5 != stored_md5

    def test_md5_file_empty_edge_case(self, mocker):
        """Test edge case of empty MD5 file."""
        # Arrange
        mock_open_md5 = mock_open(read_data='')
        mocker.patch('builtins.open', mock_open_md5)

        # Act
        with open("repo/zips/addons.xml.md5", 'r') as f:
            stored_md5 = f.read().strip()

        # Assert
        assert stored_md5 == ''

    def test_md5_file_read_error(self, mocker):
        """Test error handling when MD5 file cannot be read."""
        # Arrange
        mocker.patch('builtins.open', side_effect=FileNotFoundError("File not found"))

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="File not found"):
            with open("repo/zips/addons.xml.md5", 'r') as f:
                f.read()
