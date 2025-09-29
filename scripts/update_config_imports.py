"""
Script to update imports from src.config to src.config_loader
"""
import os
import re
from pathlib import Path

# Files that need to be updated
FILES_TO_UPDATE = [
    "src/utils/utils.py",
    "src/utils/selenium_utils.py",
    "src/storage/json_storage.py",
    "src/models.py",
    "src/driver_manager/web_driver_manager.py",
    "src/driver_manager/firefox_driver.py",
    "src/driver_manager/driver_installer.py",
    "src/driver.py",
    "src/data/verifier/h2h_data_verifier.py",
    "src/data/loader/test_loader.py",
    "src/data/loader/results_data_loader.py",
    "src/data/loader/odds_data_loader.py",
    "src/data/loader/match_data_loader.py",
    "src/data/loader/h2h_data_loader.py",
    "src/data/extractor/h2h_data_extractor.py",
    "src/core/url_verifier.py",
    "src/cli/cli_manager.py"
]

def update_file(file_path):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace imports
        updated = False
        
        # Replace 'from src.config import CONFIG' with 'from src.config_loader import CONFIG'
        if 'from src.config import' in content:
            content = content.replace(
                'from src.config import',
                'from src.config_loader import'
            )
            updated = True
            
        # Replace 'from src.config import CONFIG, ' with 'from src.config_loader import CONFIG, '
        if 'from src.config import ' in content:
            content = content.replace(
                'from src.config import ',
                'from src.config_loader import '
            )
            updated = True
        
        # Replace 'from ..config import' with 'from ..config_loader import'
        if 'from ..config import' in content:
            content = content.replace(
                'from ..config import',
                'from ..config_loader import'
            )
            updated = True
        
        # If we made changes, write the file back
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {file_path}")
            return True
            
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
    
    return False

def main():
    """Main function to update all files"""
    updated_count = 0
    
    for file_path in FILES_TO_UPDATE:
        if os.path.exists(file_path):
            if update_file(file_path):
                updated_count += 1
    
    print(f"\nUpdated {updated_count} files.")

if __name__ == "__main__":
    main()
