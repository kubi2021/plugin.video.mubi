#!/usr/bin/env python3
"""
Migration script to fix folder names with consecutive spaces.
This script will rename existing folders to remove double spaces.
"""

import os
import re
import shutil
from pathlib import Path

def fix_folder_name(folder_name):
    """Fix folder name by removing consecutive spaces."""
    # Collapse multiple consecutive spaces into a single space
    fixed = re.sub(r' +', ' ', folder_name)
    return fixed.strip()

def migrate_film_folders(base_path):
    """Migrate all film folders to fix consecutive spaces."""
    films_path = Path(base_path) / "films"
    
    if not films_path.exists():
        print(f"Films directory not found: {films_path}")
        return
    
    print(f"Scanning for folders with consecutive spaces in: {films_path}")
    
    folders_to_fix = []
    
    # Find all folders that need fixing
    for folder in films_path.iterdir():
        if folder.is_dir():
            folder_name = folder.name
            fixed_name = fix_folder_name(folder_name)
            
            if folder_name != fixed_name:
                folders_to_fix.append((folder, fixed_name))
    
    if not folders_to_fix:
        print("✅ No folders need fixing!")
        return
    
    print(f"Found {len(folders_to_fix)} folders that need fixing:")
    print("=" * 80)
    
    for folder, fixed_name in folders_to_fix:
        print(f"'{folder.name}' → '{fixed_name}'")
    
    print("=" * 80)
    
    # Ask for confirmation
    response = input(f"Do you want to rename these {len(folders_to_fix)} folders? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Perform the renames
    success_count = 0
    error_count = 0
    
    for folder, fixed_name in folders_to_fix:
        try:
            new_path = folder.parent / fixed_name
            
            # Check if target already exists
            if new_path.exists():
                print(f"❌ Target already exists: {fixed_name}")
                error_count += 1
                continue
            
            # Rename the folder
            folder.rename(new_path)
            print(f"✅ Renamed: '{folder.name}' → '{fixed_name}'")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error renaming '{folder.name}': {e}")
            error_count += 1
    
    print("=" * 80)
    print(f"Migration complete!")
    print(f"✅ Successfully renamed: {success_count} folders")
    if error_count > 0:
        print(f"❌ Errors: {error_count} folders")

def main():
    """Main function."""
    # Default Kodi userdata path on macOS
    default_path = os.path.expanduser("~/Library/Application Support/Kodi/userdata/addon_data/plugin.video.mubi")
    
    print("MUBI Plugin Folder Name Migration Tool")
    print("=" * 50)
    print("This script will fix folder names with consecutive spaces.")
    print()
    
    # Check if default path exists
    if os.path.exists(default_path):
        print(f"Found MUBI plugin data at: {default_path}")
        use_default = input("Use this path? (Y/n): ")
        if use_default.lower() in ['', 'y', 'yes']:
            migrate_film_folders(default_path)
            return
    
    # Ask for custom path
    custom_path = input("Enter the path to your MUBI plugin data directory: ")
    if custom_path and os.path.exists(custom_path):
        migrate_film_folders(custom_path)
    else:
        print("❌ Path not found or invalid.")

if __name__ == "__main__":
    main()
