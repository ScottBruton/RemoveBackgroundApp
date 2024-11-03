import subprocess
import os

def build():
    # Define paths
    project_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(project_dir, 'dist')
    build_dir = os.path.join(project_dir, 'build')
    spec_file = os.path.join(project_dir, 'scripts.spec')

    # Remove previous build and dist directories if they exist
    if os.path.exists(dist_dir):
        print("Removing previous dist directory...")
        subprocess.run(['rmdir', '/S', '/Q', dist_dir], shell=True)
    if os.path.exists(build_dir):
        print("Removing previous build directory...")
        subprocess.run(['rmdir', '/S', '/Q', build_dir], shell=True)
    
    # Run PyInstaller
    print("Building the executable with PyInstaller...")
    command = [
        'pyinstaller', 
        '--onefile', 
        '--windowed', 
        '--name=scripts', 
        'scripts.py'
    ]
    
    # Use the spec file if it exists, otherwise use the script directly
    if os.path.exists(spec_file):
        command = ['pyinstaller', spec_file]
    
    # Execute the build command
    result = subprocess.run(command, shell=True)
    
    if result.returncode == 0:
        print("Build completed successfully!")
        print(f"Executable can be found in: {dist_dir}")
    else:
        print("Build failed.")

if __name__ == '__main__':
    build()
