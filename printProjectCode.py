import os
import json
import ast

def extract_methods_and_code(file_path):
    """Extracts methods and the full code from a Python file."""
    methods = []
    code_content = ""
    
    with open(file_path, 'r') as file:
        code_content = file.read()
        tree = ast.parse(code_content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.append(node.name)
    
    return methods, code_content

def get_project_structure(directory):
    """Generates a dictionary with the project structure, code files, methods, and code."""
    project_data = {
        "project_structure": [],
        "code_files": {}
    }
    
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name.endswith(".py") and name != "printProjectCode.py":
                file_path = os.path.join(root, name)
                relative_path = os.path.relpath(file_path, directory)
                project_data["project_structure"].append(relative_path)
                
                methods, code_content = extract_methods_and_code(file_path)
                project_data["code_files"][relative_path] = {
                    "methods": methods,
                    "code": code_content
                }
    
    return project_data

def save_project_data(directory):
    """Saves the project data as a JSON file in the given directory."""
    project_data = get_project_structure(directory)
    json_file_path = os.path.join(directory, "project_structure.json")
    
    with open(json_file_path, 'w') as json_file:
        json.dump(project_data, json_file, indent=4)
    print(f"Project structure and code saved to {json_file_path}")

if __name__ == "__main__":
    save_project_data(os.path.dirname(os.path.abspath(__file__)))
