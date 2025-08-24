#!/usr/bin/env python3
"""
VS Code setup script for Cargo Clash project.
Run this script to configure VS Code properly.
"""

import json
import os
import subprocess
import sys

def main():
    project_root = "/Users/anyashankar/cargo-clash"
    venv_python = f"{project_root}/venv/bin/python"
    
    print("🚀 Setting up VS Code for Cargo Clash...")
    
    # Check if virtual environment exists
    if not os.path.exists(venv_python):
        print("❌ Virtual environment not found!")
        print(f"Expected: {venv_python}")
        return False
    
    # Test imports
    print("✅ Testing Python imports...")
    try:
        subprocess.run([venv_python, "-c", "from pydantic_settings import BaseSettings; print('pydantic_settings: OK')"], check=True)
        subprocess.run([venv_python, "-c", "from sqlalchemy import create_engine; print('sqlalchemy: OK')"], check=True)
        subprocess.run([venv_python, "-c", "from sqlalchemy.ext.asyncio import AsyncSession; print('sqlalchemy.ext.asyncio: OK')"], check=True)
        subprocess.run([venv_python, "-c", "from sqlalchemy.orm import DeclarativeBase; print('sqlalchemy.orm: OK')"], check=True)
        print("✅ All imports working correctly!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Import test failed: {e}")
        return False
    
    print("\n📝 VS Code Configuration:")
    print(f"   Python Interpreter: {venv_python}")
    print(f"   Project Root: {project_root}")
    print(f"   Backend Path: {project_root}/backend")
    
    print("\n🔧 Next Steps:")
    print("1. Open VS Code")
    print("2. Install 'code' command: Cmd+Shift+P → 'Shell Command: Install code command in PATH'")
    print("3. Open project: code /Users/anyashankar/cargo-clash/cargo-clash.code-workspace")
    print("4. Select Python interpreter: Cmd+Shift+P → 'Python: Select Interpreter'")
    print(f"5. Choose: {venv_python}")
    print("6. Reload window: Cmd+Shift+P → 'Developer: Reload Window'")
    
    print("\n🎮 Game Status:")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ Cargo Clash server is running!")
            print("   📚 API Docs: http://localhost:8000/docs")
            print("   ❤️  Health: http://localhost:8000/health")
        else:
            print("⚠️  Server responded with error")
    except:
        print("⚠️  Server not running. Start with:")
        print("   cd /Users/anyashankar/cargo-clash")
        print("   source venv/bin/activate")
        print("   cd backend")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
