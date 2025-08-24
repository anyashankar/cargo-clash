# VS Code Setup for Cargo Clash

## Quick Start

1. **Open in VS Code:**

2. **Install Recommended Extensions:**

3. **Select Python Interpreter:**

## Running the Game

Using VS Code Tasks
- Press `Cmd+Shift+P`
- Type "Tasks: Run Task"
- Select "Start FastAPI Server"

## Game URLs
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Main API:** http://localhost:8000/

## VS Code Features Configured

### Debugging
- FastAPI server debugging
- Python file debugging
- Celery worker debugging

### Tasks
- Start FastAPI Server
- Install Dependencies
- Initialize Database
- Run Tests

### Code Quality
- Black formatting on save
- Import sorting with isort
- Pylint linting
- Type checking with Pylance

### File Structure
```
cargo-clash/
├── .vscode/              # VS Code configuration
├── backend/              # FastAPI backend
├── frontend/             # React frontend
├── venv/                 # Python virtual environment
└── cargo-clash.code-workspace  # VS Code workspace file
```
