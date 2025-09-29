"""
Script to update imports from config_loader to utils.config_loader
"""
import os
import re
from pathlib import Path

# Find all Python files in the src directory
def find_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

FILES_TO_UPDATE = find_python_files('src') + ['test_config_loader.py']

def update_file(file_path):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Store original content to check if changes were made
        original_content = content
        
        # Replace imports
        updated = False
        
        # Replace 'from config_loader import' with 'from utils.config_loader import'
        content = content.replace(
            'from config_loader import',
            'from utils.config_loader import'
        )
        
        # Replace 'from .config_loader import' with 'from .utils.config_loader import'
        content = content.replace(
            'from .config_loader import',
            'from .utils.config_loader import'
        )
        
        # Replace 'from ..config_loader import' with 'from ..utils.config_loader import'
        content = content.replace(
            'from ..config_loader import',
            'from ..utils.config_loader import'
        )
        
        # Replace 'import config_loader' with 'from utils import config_loader'
        content = re.sub(
            r'^import config_loader$',
            'from utils import config_loader',
            content,
            flags=re.MULTILINE
        )
        
        # Check if content changed
        updated = (content != original_content)
        
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
