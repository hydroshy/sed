#!/usr/bin/env python3
"""
Cleanup script for SED project
Removes unused files, consolidates duplicates, and reorganizes structure
"""

import os
import shutil
import sys
from datetime import datetime

def confirm_action(message):
    """Ask user for confirmation"""
    response = input(f"{message} (y/n): ").lower()
    return response == 'y'

def backup_before_cleanup():
    """Create a backup before making changes"""
    backup_dir = f"cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup in {backup_dir}...")
    
    # Backup important directories
    dirs_to_backup = ['backup', 'gui/settings_panel.py'] 
    
    for item in dirs_to_backup:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.copytree(item, os.path.join(backup_dir, item))
            else:
                os.makedirs(os.path.dirname(os.path.join(backup_dir, item)), exist_ok=True)
                shutil.copy2(item, os.path.join(backup_dir, item))
    
    print(f"Backup created in {backup_dir}")
    return backup_dir

def cleanup_empty_files():
    """Remove empty and unnecessary files"""
    empty_files = [
        'gui/settings_panel.py',
        'camera/__init__.py',
        'utils/__init__.py',
        'backup/detection/__init__.py',
        'backup/detection/backup/detect_tool_job.py'
    ]
    
    print("\n=== Removing Empty Files ===")
    for file in empty_files:
        if os.path.exists(file) and os.path.getsize(file) == 0:
            os.remove(file)
            print(f"✓ Removed empty file: {file}")

def cleanup_backup_directory():
    """Remove or archive the backup directory"""
    if os.path.exists('backup'):
        print("\n=== Handling Backup Directory ===")
        if confirm_action("Remove entire backup directory? (contains old versions)"):
            shutil.rmtree('backup')
            print("✓ Removed backup directory")
        else:
            # Archive it instead
            archive_name = f"archive_backup_{datetime.now().strftime('%Y%m%d')}"
            shutil.move('backup', archive_name)
            print(f"✓ Moved backup to {archive_name}")

def organize_test_files():
    """Move test files to proper directory"""
    test_files = [
        'minimal_test.py',
        'simple_test.py',
        'test_exact_scenario.py',
        'test_saveimage_complete.py',
        'test_saveimage_fix.py',
        'test_saveimage_integration.py',
        'debug_saveimage.py',
        'run_tests.py'
    ]
    
    print("\n=== Organizing Test Files ===")
    
    # Create tests directory
    os.makedirs('tests', exist_ok=True)
    os.makedirs('tests/integration', exist_ok=True)
    os.makedirs('tests/unit', exist_ok=True)
    
    for test_file in test_files:
        if os.path.exists(test_file):
            # Determine target directory
            if 'integration' in test_file or 'complete' in test_file:
                target = 'tests/integration'
            elif 'debug' in test_file or 'run_tests' in test_file:
                target = 'tests'
            else:
                target = 'tests/unit'
            
            target_path = os.path.join(target, test_file)
            shutil.move(test_file, target_path)
            print(f"✓ Moved {test_file} to {target}/")

def consolidate_detect_tools():
    """Consolidate multiple detect_tool.py files"""
    print("\n=== Consolidating detect_tool.py Files ===")
    
    detect_files = [
        'tools/detect_tool.py',
        'tools/detection/detect_tool.py',
    ]
    
    # Check which one is more recent/complete
    sizes = {}
    for file in detect_files:
        if os.path.exists(file):
            sizes[file] = os.path.getsize(file)
    
    if sizes:
        # Keep the larger file (likely more complete)
        keep_file = max(sizes, key=sizes.get)
        print(f"Keeping {keep_file} ({sizes[keep_file]} bytes)")
        
        for file in detect_files:
            if file != keep_file and os.path.exists(file):
                os.remove(file)
                print(f"✓ Removed duplicate: {file}")

def identify_unused_imports():
    """Identify and report unused imports"""
    print("\n=== Checking for Unused Imports ===")
    
    try:
        # This would require more complex AST analysis
        # For now, just report common unused patterns
        unused_patterns = []
        
        for root, dirs, files in os.walk('.'):
            if 'backup' in root or '__pycache__' in root or '.git' in root:
                continue
            
            for fname in files:
                if fname.endswith('.py'):
                    fpath = os.path.join(root, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Check for common unused imports
                        if 'from backup' in content:
                            unused_patterns.append(f"{fpath}: imports from backup directory")
                        if 'import unused' in content:
                            unused_patterns.append(f"{fpath}: has 'unused' in import")
        
        if unused_patterns:
            print("Found potential unused imports:")
            for pattern in unused_patterns[:10]:  # Show first 10
                print(f"  - {pattern}")
        else:
            print("✓ No obvious unused imports found")
            
    except Exception as e:
        print(f"Error checking imports: {e}")

def generate_cleanup_report():
    """Generate a report of what was cleaned"""
    report = """
=== CLEANUP REPORT ===
Date: {date}

Actions Taken:
1. Removed empty files
2. Organized test files into tests/ directory  
3. Consolidated duplicate detect_tool.py files
4. Archived/removed backup directory

Recommendations for manual review:
- Check gui/job_tree_view.py vs gui/job_tree_view_simple.py
- Review gui/tool_manager.py vs gui/tool_manager_new.py
- Consider splitting large files (>50KB):
  - gui/main_window.py (78KB)
  - gui/camera_manager.py (58KB)
  - job/job_manager.py (36KB)

Next Steps:
1. Run tests to ensure nothing broke
2. Update import statements if needed
3. Consider further refactoring of large modules
""".format(date=datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    with open('CLEANUP_REPORT.txt', 'w') as f:
        f.write(report)
    
    print("\n" + report)

def main():
    print("=" * 60)
    print("SED PROJECT CLEANUP SCRIPT")
    print("=" * 60)
    
    if not confirm_action("This will modify your project structure. Continue?"):
        print("Cleanup cancelled.")
        return
    
    # Create backup first
    backup_dir = backup_before_cleanup()
    
    try:
        # Run cleanup tasks
        cleanup_empty_files()
        organize_test_files()
        consolidate_detect_tools()
        cleanup_backup_directory()
        identify_unused_imports()
        
        # Generate report
        generate_cleanup_report()
        
        print("\n" + "=" * 60)
        print("✓ CLEANUP COMPLETED SUCCESSFULLY!")
        print(f"Backup saved in: {backup_dir}")
        print("Review CLEANUP_REPORT.txt for details")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during cleanup: {e}")
        print(f"Backup is available in {backup_dir}")
        sys.exit(1)

if __name__ == "__main__":
    main()
