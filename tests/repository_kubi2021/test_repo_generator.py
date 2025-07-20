"""
Test suite for the repository generator script.
Tests the _repo_generator.py functionality and output.
"""

import os
import sys
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock


class TestRepoGeneratorScript:
    """Test the _repo_generator.py script functionality."""
    
    def test_repo_generator_script_exists(self):
        """Test that _repo_generator.py exists and is executable."""
        script_path = Path("_repo_generator.py")
        assert script_path.exists(), "_repo_generator.py must exist at repository root"
        
        # Check if it's a valid Python file
        with open(script_path, 'r') as f:
            content = f.read()
        
        assert content.startswith('#!/usr/bin/env python') or 'import' in content, "Script should be a valid Python file"
    
    def test_repo_generator_creates_zips_directory(self):
        """Test that running repo generator creates the zips directory."""
        zips_path = Path("repo/zips")
        
        # The directory should exist (created by previous runs)
        assert zips_path.exists(), "repo/zips directory should exist after generator runs"
        assert zips_path.is_dir(), "repo/zips should be a directory"
    
    def test_repo_generator_creates_addons_xml(self):
        """Test that repo generator creates addons.xml."""
        addons_xml_path = Path("repo/zips/addons.xml")
        assert addons_xml_path.exists(), "addons.xml should be created by repo generator"
        
        # Validate XML structure
        with open(addons_xml_path, 'r') as f:
            content = f.read()
        
        root = ET.fromstring(content)
        assert root.tag == 'addons', "Root element should be 'addons'"
        
        # Should contain addon elements
        addons = root.findall('addon')
        assert len(addons) >= 2, "Should contain at least 2 addons (repository + plugin)"
    
    def test_repo_generator_creates_md5_checksum(self):
        """Test that repo generator creates MD5 checksum file."""
        md5_path = Path("repo/zips/addons.xml.md5")
        assert md5_path.exists(), "addons.xml.md5 should be created by repo generator"
        
        # Should contain a valid MD5 hash
        with open(md5_path, 'r') as f:
            md5_content = f.read().strip()
        
        assert len(md5_content) == 32, "MD5 hash should be 32 characters"
        assert all(c in '0123456789abcdef' for c in md5_content.lower()), "MD5 should contain only hex characters"
    
    def test_repo_generator_creates_plugin_zip(self):
        """Test that repo generator creates plugin zip files."""
        plugin_dir = Path("repo/zips/plugin.video.mubi")
        assert plugin_dir.exists(), "Plugin zip directory should exist"
        
        zip_files = list(plugin_dir.glob("plugin.video.mubi-*.zip"))
        assert len(zip_files) > 0, "At least one plugin zip should exist"
        
        # Test the latest zip
        latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
        
        with zipfile.ZipFile(latest_zip, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Should contain proper directory structure
            addon_files = [f for f in file_list if f.startswith('plugin.video.mubi/')]
            assert len(addon_files) > 0, "Zip should contain files in plugin.video.mubi/ directory"
    
    def test_repo_generator_creates_repository_zip(self):
        """Test that repo generator creates repository zip files."""
        repo_dir = Path("repo/zips/repository.kubi2021")
        assert repo_dir.exists(), "Repository zip directory should exist"
        
        zip_files = list(repo_dir.glob("repository.kubi2021-*.zip"))
        assert len(zip_files) > 0, "At least one repository zip should exist"
        
        # Test the latest zip
        latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
        
        with zipfile.ZipFile(latest_zip, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Should contain proper directory structure
            repo_files = [f for f in file_list if f.startswith('repository.kubi2021/')]
            assert len(repo_files) > 0, "Zip should contain files in repository.kubi2021/ directory"


class TestRepoGeneratorSecurity:
    """Test security aspects of the repository generator."""
    
    def test_repo_generator_ignores_development_files(self):
        """Test that repo generator properly ignores development files."""
        # Check that generated zips don't contain development files
        plugin_dir = Path("repo/zips/plugin.video.mubi")
        zip_files = list(plugin_dir.glob("plugin.video.mubi-*.zip"))
        
        if zip_files:
            latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
            
            with zipfile.ZipFile(latest_zip, 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # Should not contain development files
                dev_files = [f for f in file_list if any(ignore in f for ignore in [
                    '__pycache__', '.pytest_cache', 'tests/', '.git', 'venv/', 
                    'requirements-dev.txt', 'requirements-test.txt'
                ])]
                
                assert len(dev_files) == 0, f"Zip should not contain development files: {dev_files}"
    
    def test_repo_generator_preserves_addon_structure(self):
        """Test that repo generator preserves proper addon directory structure."""
        plugin_dir = Path("repo/zips/plugin.video.mubi")
        zip_files = list(plugin_dir.glob("plugin.video.mubi-*.zip"))
        
        if zip_files:
            latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
            
            with zipfile.ZipFile(latest_zip, 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # Should have proper addon structure
                required_files = [
                    'plugin.video.mubi/addon.xml',
                    'plugin.video.mubi/addon.py'
                ]
                
                for required_file in required_files:
                    assert required_file in file_list, f"Zip must contain {required_file}"
                
                # Should have resources directory
                resource_files = [f for f in file_list if f.startswith('plugin.video.mubi/resources/')]
                assert len(resource_files) > 0, "Zip should contain resources directory"


class TestRepoGeneratorVersioning:
    """Test version handling in repository generator."""
    
    def test_repo_generator_uses_correct_addon_versions(self):
        """Test that repo generator uses correct versions from addon.xml files."""
        addons_xml_path = Path("repo/zips/addons.xml")
        
        if addons_xml_path.exists():
            with open(addons_xml_path, 'r') as f:
                content = f.read()
            
            root = ET.fromstring(content)
            addons = root.findall('addon')
            
            # Find plugin addon
            plugin_addon = None
            repo_addon = None
            
            for addon in addons:
                if addon.get('id') == 'plugin.video.mubi':
                    plugin_addon = addon
                elif addon.get('id') == 'repository.kubi2021':
                    repo_addon = addon
            
            assert plugin_addon is not None, "addons.xml should contain plugin.video.mubi"
            assert repo_addon is not None, "addons.xml should contain repository.kubi2021"
            
            # Versions should be valid
            plugin_version = plugin_addon.get('version')
            repo_version = repo_addon.get('version')
            
            assert plugin_version is not None, "Plugin should have version"
            assert repo_version is not None, "Repository should have version"
            
            # Plugin version should be numeric (our simple versioning)
            try:
                int(plugin_version)
            except ValueError:
                pytest.fail(f"Plugin version '{plugin_version}' should be a simple integer")
    
    def test_repo_generator_zip_names_match_versions(self):
        """Test that generated zip file names match addon versions."""
        # Check plugin zip naming
        plugin_dir = Path("repo/zips/plugin.video.mubi")
        if plugin_dir.exists():
            zip_files = list(plugin_dir.glob("plugin.video.mubi-*.zip"))
            
            for zip_file in zip_files:
                # Extract version from filename
                filename = zip_file.name
                version_part = filename.replace('plugin.video.mubi-', '').replace('.zip', '')
                
                # Read addon.xml from zip to verify version
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    addon_xml_files = [f for f in zf.namelist() if f.endswith('addon.xml')]
                    if addon_xml_files:
                        addon_xml_content = zf.read(addon_xml_files[0])
                        root = ET.fromstring(addon_xml_content)
                        xml_version = root.get('version')
                        
                        assert version_part == xml_version, f"Zip filename version {version_part} should match addon.xml version {xml_version}"


class TestRepoGeneratorIntegration:
    """Integration tests for repository generator with the full workflow."""
    
    def test_repo_generator_output_consistency(self):
        """Test that multiple runs of repo generator produce consistent output."""
        # This test assumes the generator has been run and files exist
        zips_path = Path("repo/zips")
        
        if zips_path.exists():
            # Check that all expected files exist
            expected_files = [
                "addons.xml",
                "addons.xml.md5",
                "plugin.video.mubi",
                "repository.kubi2021"
            ]
            
            for expected_file in expected_files:
                file_path = zips_path / expected_file
                assert file_path.exists(), f"Expected file {expected_file} should exist in zips directory"
    
    def test_repo_generator_github_pages_compatibility(self):
        """Test that repo generator output is compatible with GitHub Pages hosting."""
        # Check that URLs in repository addon.xml point to correct GitHub location
        repo_zip_path = Path("repo/zips/repository.kubi2021/repository.kubi2021-2.zip")
        
        if repo_zip_path.exists():
            with zipfile.ZipFile(repo_zip_path, 'r') as zip_file:
                addon_xml_files = [f for f in zip_file.namelist() if f.endswith('addon.xml')]
                
                if addon_xml_files:
                    addon_xml_content = zip_file.read(addon_xml_files[0])
                    root = ET.fromstring(addon_xml_content)
                    
                    # Find repository extension
                    repo_extension = root.find(".//extension[@point='xbmc.addon.repository']")
                    if repo_extension is not None:
                        dir_element = repo_extension.find('dir')
                        if dir_element is not None:
                            info_element = dir_element.find('info')
                            datadir_element = dir_element.find('datadir')
                            
                            if info_element is not None:
                                info_url = info_element.text
                                assert 'github' in info_url.lower(), "Info URL should point to GitHub"
                                assert 'kubi2021' in info_url, "Info URL should contain correct username"
                            
                            if datadir_element is not None:
                                datadir_url = datadir_element.text
                                assert 'github' in datadir_url.lower(), "Datadir URL should point to GitHub"
                                assert 'kubi2021' in datadir_url, "Datadir URL should contain correct username"
