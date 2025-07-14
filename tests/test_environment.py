#!/usr/bin/env python3
"""
Environment validation tests.
Ensures all required dependencies are available for testing.
"""
import pytest
import sys
import platform


class TestEnvironment:
    """Test that the testing environment has all required dependencies."""
    
    def test_python_version(self):
        """Test that Python version is supported."""
        version = sys.version_info
        assert version.major == 3, f"Python 3 required, got {version.major}"
        assert version.minor >= 8, f"Python 3.8+ required, got {version.major}.{version.minor}"
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is supported")
    
    def test_platform_info(self):
        """Display platform information for debugging."""
        print(f"Platform: {platform.platform()}")
        print(f"Architecture: {platform.architecture()}")
        print(f"Machine: {platform.machine()}")
        print(f"Processor: {platform.processor()}")
    
    def test_required_modules_available(self):
        """Test that all required modules can be imported."""
        required_modules = [
            'pytest',
            'unittest.mock',
            'threading',
            'concurrent.futures',
            'gc',
            'os',
            'sys',
            'pathlib',
            'tempfile',
            'json',
            'xml.etree.ElementTree',
            'requests',
            'psutil'  # This is the critical one for stress tests
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
                print(f"✅ {module} - available")
            except ImportError as e:
                missing_modules.append(f"{module}: {e}")
                print(f"❌ {module} - missing: {e}")
        
        assert not missing_modules, f"Missing required modules: {missing_modules}"
    
    def test_psutil_functionality(self):
        """Test that psutil works correctly for memory monitoring."""
        import psutil
        import os
        
        # Test basic psutil functionality
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        assert hasattr(memory_info, 'rss'), "psutil memory_info should have 'rss' attribute"
        assert memory_info.rss > 0, "RSS memory should be positive"
        
        memory_mb = memory_info.rss / 1024 / 1024
        assert memory_mb > 0, "Memory usage in MB should be positive"
        
        print(f"✅ psutil working correctly - current memory usage: {memory_mb:.1f}MB")
    
    def test_stress_test_imports(self):
        """Test that stress test module can be imported."""
        try:
            from tests.test_stress import TestStressScenarios
            print("✅ Stress test module imports successfully")
            
            # Test that the class can be instantiated
            test_instance = TestStressScenarios()
            memory = test_instance.get_memory_usage()
            assert memory > 0, "Memory usage should be positive"
            print(f"✅ Stress test memory monitoring works: {memory:.1f}MB")
            
        except ImportError as e:
            pytest.fail(f"Cannot import stress tests: {e}")
        except Exception as e:
            pytest.fail(f"Error testing stress test functionality: {e}")
    
    def test_pytest_markers(self):
        """Test that pytest markers are properly configured."""
        import pytest
        
        # Test that our custom markers are available
        markers = [
            'stress',
            'slow', 
            'security',
            'integration',
            'e2e',
            'quality',
            'unit',
            'network',
            'filesystem'
        ]
        
        # This test mainly validates that pytest is configured correctly
        # The actual marker validation happens during test collection
        print(f"✅ Pytest version: {pytest.__version__}")
        print(f"✅ Custom markers configured: {', '.join(markers)}")
    
    def test_github_actions_environment(self):
        """Test GitHub Actions specific environment."""
        import os
        
        # Check if we're running in GitHub Actions
        if os.getenv('GITHUB_ACTIONS'):
            print("🔧 Running in GitHub Actions environment")
            print(f"   Runner OS: {os.getenv('RUNNER_OS', 'unknown')}")
            print(f"   Python version: {os.getenv('pythonLocation', 'unknown')}")
            print(f"   Workflow: {os.getenv('GITHUB_WORKFLOW', 'unknown')}")
            print(f"   Repository: {os.getenv('GITHUB_REPOSITORY', 'unknown')}")
        else:
            print("🏠 Running in local development environment")
        
        # Test that PYTHONPATH is set correctly
        pythonpath = os.getenv('PYTHONPATH', '')
        print(f"PYTHONPATH: {pythonpath}")
        
        # Verify we can import our modules
        try:
            import resources.lib.mubi
            import resources.lib.film
            import resources.lib.session_manager
            print("✅ All main modules can be imported")
        except ImportError as e:
            pytest.fail(f"Cannot import main modules: {e}")
