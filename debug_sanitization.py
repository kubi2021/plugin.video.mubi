#!/usr/bin/env python3
"""
Debug script to understand why we're still getting double spaces.
"""

import re

def debug_sanitize_filename(filename, replacement=" "):
    """Debug version of sanitization with step-by-step output."""
    print(f"Original: '{filename}'")
    print(f"Original bytes: {filename.encode('utf-8')}")
    
    # Step 1: Replace reserved characters
    step1 = re.sub(r'[<>:"/\\|?*^%$&\'{}@!]', replacement, filename)
    print(f"After char replacement: '{step1}'")
    
    # Step 2: Remove control characters
    step2 = re.sub(r'[\x00-\x1f\x7f-\x9f]', replacement, step1)
    print(f"After control char removal: '{step2}'")
    
    # Step 3: Collapse spaces
    step3 = re.sub(r' +', ' ', step2)
    print(f"After space collapse: '{step3}'")
    
    # Step 4: Strip trailing periods and spaces
    step4 = step3.rstrip(". ")
    print(f"After rstrip: '{step4}'")
    
    # Step 5: Final strip
    final = step4.strip()
    print(f"Final result: '{final}'")
    
    # Check for double spaces in final result
    has_double_spaces = "  " in final
    print(f"Has double spaces: {has_double_spaces}")
    
    if has_double_spaces:
        print("❌ DOUBLE SPACES DETECTED!")
        # Show where the double spaces are
        for i, char in enumerate(final):
            if char == ' ' and i > 0 and final[i-1] == ' ':
                print(f"Double space at position {i-1}-{i}")
    
    return final

def test_problematic_titles():
    """Test the specific titles that are causing issues."""
    problematic_titles = [
        "Ain't Nothin' Without You",
        "Cottonpickin' Chickenpickers", 
        "David Lynch: The Art Life",
    ]
    
    print("Testing problematic titles...")
    print("=" * 80)
    
    for title in problematic_titles:
        print(f"\nTesting: {title}")
        print("-" * 40)
        
        # Test sanitization
        sanitized = debug_sanitize_filename(title)
        
        # Add year like the real code does
        with_year = f"{sanitized} (1986)"
        print(f"With year: '{with_year}'")
        
        # Check final result
        final_has_double_spaces = "  " in with_year
        print(f"Final has double spaces: {final_has_double_spaces}")
        
        if final_has_double_spaces:
            print("❌ PROBLEM FOUND!")
        else:
            print("✅ OK")
        
        print("=" * 80)

if __name__ == "__main__":
    test_problematic_titles()
