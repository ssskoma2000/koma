import subprocess
import sys
import os

def install_requirements():
    # Virtual environment tekshiruvi
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Virtual environment detected. Installing packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    else:
        print("Please run this script inside a virtual environment!")
        print("Create one with: python3 -m venv venv")
        print("Activate with: source venv/bin/activate")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
    print("Setup complete!")
