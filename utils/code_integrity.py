import py_compile
import glob
import os

def verify_code_integrity():
    """
    Checks all Python files in the project for syntax errors.
    Returns (Success, ErrorMessage)
    """
    print("🛡️  Integrity Check: Verifying project syntax...")
    
    # Get the project root (assuming this file is in project_root/utils/code_integrity.py)
    # Adjusting to find files relative to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Files to check: all .py files in project_root and sub-folders
    search_pattern = os.path.join(project_root, "**", "*.py")
    files_to_check = glob.glob(search_pattern, recursive=True)
    
    for file_path in files_to_check:
        # Ignore virtual environments and git folders
        if any(ignored in file_path for ignored in ["venv", ".git", "__pycache__"]):
            continue
            
        try:
            # This 'compiles' the file to check for syntax errors
            py_compile.compile(file_path, doraise=True)
        except py_compile.PyCompileError as e:
            # Return the specific file and error that failed
            error_msg = f"Syntax Error in {os.path.basename(file_path)}:\n{str(e)}"
            return False, error_msg
        except Exception as e:
            return False, f"Error checking {file_path}: {str(e)}"
            
    return True, "All files compiled successfully."

if __name__ == "__main__":
    success, msg = verify_code_integrity()
    print(msg)
