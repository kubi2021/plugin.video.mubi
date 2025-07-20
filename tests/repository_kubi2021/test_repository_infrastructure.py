"""
Test suite for repository infrastructure validation.
Tests GitHub Pages setup, repository files, and overall consistency.
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import hashlib
import pytest
from unittest.mock import patch, mock_open


class TestIndexPage:
    """Test the index.html file for GitHub Pages hosting."""
    
    def test_index_page_exists(self):
        """Test that index.html exists at repository root."""
        index_path = Path("index.html")
        assert index_path.exists(), "index.html file must exist at repository root"
    
    def test_index_page_has_correct_link(self):
        """Test that index.html contains the correct repository zip link."""
        index_path = Path("index.html")
        with open(index_path, 'r') as f:
            content = f.read()
        
        # Should contain a link to the repository zip
        assert 'repository.kubi2021-2.zip' in content, "index.html must link to repository.kubi2021-2.zip"
        assert 'href=' in content, "index.html must contain an href link"
    
    def test_index_page_is_minimal(self):
        """Test that index.html is minimal and focused."""
        index_path = Path("index.html")
        with open(index_path, 'r') as f:
            content = f.read()
        
        # Should be simple HTML
        assert '<!DOCTYPE html>' in content, "index.html should have proper DOCTYPE"
        # Should not be overly complex
        assert len(content) < 1000, "index.html should be minimal for Kodi compatibility"


class TestRepositoryZipAtRoot:
    """Test the repository zip file at the root level."""
    
    def test_repository_zip_exists_at_root(self):
        """Test that repository zip exists at repository root."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        assert repo_zip_path.exists(), "repository.kubi2021-2.zip must exist at repository root"
    
    def test_repository_zip_is_valid(self):
        """Test that repository zip is a valid zip file."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        
        try:
            with zipfile.ZipFile(repo_zip_path, 'r') as zip_file:
                # Test that zip can be opened and read
                zip_file.testzip()
                file_list = zip_file.namelist()
                assert len(file_list) > 0, "Repository zip should not be empty"
        except zipfile.BadZipFile:
            pytest.fail("repository.kubi2021-2.zip is not a valid zip file")
    
    def test_repository_zip_contains_required_files(self):
        """Test that repository zip contains required files."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        
        with zipfile.ZipFile(repo_zip_path, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Should contain addon.xml
            addon_xml_files = [f for f in file_list if f.endswith('addon.xml')]
            assert len(addon_xml_files) > 0, "Repository zip must contain addon.xml"
            
            # Should contain icon and fanart
            icon_files = [f for f in file_list if 'icon.png' in f]
            fanart_files = [f for f in file_list if 'fanart.jpg' in f]
            assert len(icon_files) > 0, "Repository zip must contain icon.png"
            assert len(fanart_files) > 0, "Repository zip must contain fanart.jpg"
    
    def test_repository_zip_size_reasonable(self):
        """Test that repository zip size is reasonable."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        file_size = repo_zip_path.stat().st_size
        
        # Should be between 10KB and 1MB (reasonable for a repository)
        assert 10 * 1024 < file_size < 1024 * 1024, f"Repository zip size {file_size} bytes seems unreasonable"


class TestRepositoryZipContents:
    """Test the XML structure and contents of repository zip."""
    
    def test_repository_addon_xml_structure(self):
        """Test that repository addon.xml has correct structure."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        
        with zipfile.ZipFile(repo_zip_path, 'r') as zip_file:
            # Find addon.xml in the zip
            addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
            assert len(addon_xml_files) > 0, "Repository zip must contain addon.xml"
            
            # Read and parse addon.xml
            addon_xml_content = zip_file.read(addon_xml_files[0])
            root = ET.fromstring(addon_xml_content)
            
            # Validate basic structure
            assert root.tag == 'addon', "Root element must be 'addon'"
            assert root.get('id') == 'repository.kubi2021', "Repository ID must be 'repository.kubi2021'"
            assert root.get('name') == 'MUBI Repository', "Repository name must be 'MUBI Repository'"
            assert root.get('provider-name') == 'kubi2021', "Provider name must be 'kubi2021'"
    
    def test_repository_addon_xml_extensions(self):
        """Test that repository addon.xml has required extensions."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        
        with zipfile.ZipFile(repo_zip_path, 'r') as zip_file:
            addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
            addon_xml_content = zip_file.read(addon_xml_files[0])
            root = ET.fromstring(addon_xml_content)
            
            # Find extensions
            extensions = root.findall('extension')
            assert len(extensions) >= 2, "Repository should have at least 2 extensions"
            
            # Check for repository extension
            repo_extension = None
            metadata_extension = None
            
            for ext in extensions:
                if ext.get('point') == 'xbmc.addon.repository':
                    repo_extension = ext
                elif ext.get('point') == 'xbmc.addon.metadata':
                    metadata_extension = ext
            
            assert repo_extension is not None, "Repository must have xbmc.addon.repository extension"
            assert metadata_extension is not None, "Repository must have xbmc.addon.metadata extension"
    
    def test_repository_addon_xml_urls(self):
        """Test that repository addon.xml has correct GitHub URLs."""
        repo_zip_path = Path("repository.kubi2021-2.zip")
        
        with zipfile.ZipFile(repo_zip_path, 'r') as zip_file:
            addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
            addon_xml_content = zip_file.read(addon_xml_files[0])
            root = ET.fromstring(addon_xml_content)
            
            # Find repository extension
            repo_extension = root.find(".//extension[@point='xbmc.addon.repository']")
            assert repo_extension is not None
            
            # Check URLs
            dir_element = repo_extension.find('dir')
            assert dir_element is not None, "Repository extension must have dir element"
            
            info_element = dir_element.find('info')
            checksum_element = dir_element.find('checksum')
            datadir_element = dir_element.find('datadir')
            
            assert info_element is not None, "Repository must have info element"
            assert checksum_element is not None, "Repository must have checksum element"
            assert datadir_element is not None, "Repository must have datadir element"
            
            # Validate URLs point to correct GitHub location
            base_url = "https://raw.githubusercontent.com/kubi2021/plugin.video.mubi/main/repo/zips/"
            assert info_element.text == base_url + "addons.xml", "Info URL must point to addons.xml"
            assert checksum_element.text == base_url + "addons.xml.md5", "Checksum URL must point to addons.xml.md5"
            assert datadir_element.text == base_url, "Datadir URL must point to zips directory"


class TestRepositoryConsistency:
    """Test overall repository consistency and integrity."""
    
    def test_generated_zips_directory_exists(self):
        """Test that generated zips directory exists and has content."""
        zips_path = Path("repo/zips")
        assert zips_path.exists(), "repo/zips directory must exist"
        assert zips_path.is_dir(), "repo/zips must be a directory"
        
        # Should contain addons.xml and md5
        addons_xml = zips_path / "addons.xml"
        addons_md5 = zips_path / "addons.xml.md5"
        assert addons_xml.exists(), "repo/zips/addons.xml must exist"
        assert addons_md5.exists(), "repo/zips/addons.xml.md5 must exist"
    
    def test_addons_xml_md5_consistency(self):
        """Test that addons.xml.md5 matches actual addons.xml hash."""
        zips_path = Path("repo/zips")
        addons_xml = zips_path / "addons.xml"
        addons_md5 = zips_path / "addons.xml.md5"
        
        # Calculate actual MD5 of addons.xml
        with open(addons_xml, 'rb') as f:
            actual_md5 = hashlib.md5(f.read()).hexdigest()
        
        # Read stored MD5
        with open(addons_md5, 'r') as f:
            stored_md5 = f.read().strip()
        
        assert actual_md5 == stored_md5, f"MD5 mismatch: actual {actual_md5} != stored {stored_md5}"
    
    def test_addons_xml_contains_both_addons(self):
        """Test that addons.xml contains both repository and plugin addons."""
        addons_xml_path = Path("repo/zips/addons.xml")
        
        with open(addons_xml_path, 'r') as f:
            content = f.read()
        
        root = ET.fromstring(content)
        addons = root.findall('addon')
        
        # Should contain both addons
        addon_ids = [addon.get('id') for addon in addons]
        assert 'repository.kubi2021' in addon_ids, "addons.xml must contain repository.kubi2021"
        assert 'plugin.video.mubi' in addon_ids, "addons.xml must contain plugin.video.mubi"
    
    def test_plugin_zip_exists_and_valid(self):
        """Test that plugin zip exists and is valid."""
        # Find the latest plugin zip
        plugin_zips_dir = Path("repo/zips/plugin.video.mubi")
        assert plugin_zips_dir.exists(), "Plugin zips directory must exist"
        
        zip_files = list(plugin_zips_dir.glob("plugin.video.mubi-*.zip"))
        assert len(zip_files) > 0, "At least one plugin zip must exist"
        
        # Test the latest zip
        latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with zipfile.ZipFile(latest_zip, 'r') as zip_file:
                zip_file.testzip()
                file_list = zip_file.namelist()
                
                # Should contain addon.xml and addon.py
                addon_xml_files = [f for f in file_list if f.endswith('addon.xml')]
                addon_py_files = [f for f in file_list if f.endswith('addon.py')]
                
                assert len(addon_xml_files) > 0, "Plugin zip must contain addon.xml"
                assert len(addon_py_files) > 0, "Plugin zip must contain addon.py"
        except zipfile.BadZipFile:
            pytest.fail(f"Plugin zip {latest_zip} is not valid")
    
    def test_root_and_generated_repo_zips_match(self):
        """Test that repository zip at root matches generated one."""
        root_zip = Path("repository.kubi2021-2.zip")
        generated_zip = Path("repo/zips/repository.kubi2021/repository.kubi2021-2.zip")
        
        assert root_zip.exists(), "Root repository zip must exist"
        assert generated_zip.exists(), "Generated repository zip must exist"
        
        # Compare file sizes (should be identical)
        root_size = root_zip.stat().st_size
        generated_size = generated_zip.stat().st_size
        
        assert root_size == generated_size, f"Repository zip sizes don't match: root {root_size} != generated {generated_size}"
        
        # Compare MD5 hashes (should be identical)
        with open(root_zip, 'rb') as f:
            root_md5 = hashlib.md5(f.read()).hexdigest()
        
        with open(generated_zip, 'rb') as f:
            generated_md5 = hashlib.md5(f.read()).hexdigest()
        
        assert root_md5 == generated_md5, f"Repository zip hashes don't match: root {root_md5} != generated {generated_md5}"
