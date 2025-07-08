#!/usr/bin/env python3
"""
Test discovery validation script.
Ensures all tests are properly discoverable and organized.
"""
import subprocess
import sys
from pathlib import Path


def main():
    """Validate test discovery."""
    project_root = Path(__file__).parent.parent
    
    print("🔍 Validating test discovery...")
    
    # Run pytest collection
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "--collect-only", "-q"
    ], capture_output=True, text=True, cwd=project_root)
    
    if result.returncode != 0:
        print(f"❌ Test discovery failed:")
        print(result.stderr)
        return False
    
    # Extract test count from output
    lines = result.stdout.strip().split('\n')
    collected_line = [line for line in lines if 'collected' in line]
    
    if collected_line:
        print(f"✅ {collected_line[0]}")
    else:
        print("✅ Test discovery successful")
    
    # Check for test markers
    marker_result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "--markers"
    ], capture_output=True, text=True, cwd=project_root)
    
    markers_found = []
    if "security:" in marker_result.stdout:
        markers_found.append("security")
    if "stress:" in marker_result.stdout:
        markers_found.append("stress")
    if "quality:" in marker_result.stdout:
        markers_found.append("quality")
    if "integration:" in marker_result.stdout:
        markers_found.append("integration")
    if "e2e:" in marker_result.stdout:
        markers_found.append("e2e")
    
    if markers_found:
        print(f"✅ Test markers found: {', '.join(markers_found)}")
    
    # Test marker filtering
    for marker in ['security', 'stress', 'integration', 'e2e', 'quality']:
        marker_test = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-m", marker,
            "--collect-only", "-q"
        ], capture_output=True, text=True, cwd=project_root)
        
        if marker_test.returncode == 0:
            lines = marker_test.stdout.strip().split('\n')
            collected_line = [line for line in lines if 'collected' in line]
            if collected_line:
                count = collected_line[0].split()[0]
                print(f"✅ {marker} marker: {count} tests")
    
    print("\n🎯 Test discovery validation complete!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
