# VS Code Setup for Cargo Clash

## Quick Start

1. **Open in VS Code:**
   ```bash
   code /Users/anyashankar/cargo-clash/cargo-clash.code-workspace
   ```

2. **Install Recommended Extensions:**
   - VS Code will prompt you to install recommended extensions
   - Or press `Cmd+Shift+P` → "Extensions: Show Recommended Extensions"

3. **Select Python Interpreter:**
   - Press `Cmd+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose `/Users/anyashankar/cargo-clash/venv/bin/python`

## Running the Game

### Method 1: Using VS Code Tasks
- Press `Cmd+Shift+P`
- Type "Tasks: Run Task"
- Select "Start FastAPI Server"

### Method 2: Using Debug Configuration
- Go to Run and Debug (Cmd+Shift+D)
- Select "FastAPI Server" configuration
- Press F5 or click the play button

### Method 3: Using Integrated Terminal
```bash
cd /Users/anyashankar/cargo-clash
source venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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

## Troubleshooting

### If imports show errors:
1. Ensure Python interpreter is set to `./venv/bin/python`
2. Reload VS Code window: `Cmd+Shift+P` → "Developer: Reload Window"

### If server won't start:
1. Check if port 8000 is already in use: `lsof -ti:8000`
2. Kill existing process: `pkill -f uvicorn`
3. Restart from VS Code
