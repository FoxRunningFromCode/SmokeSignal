# Smoke Detector Planner

A desktop application for planning smoke detector installations on floor plans — load floor plans, place detectors, configure addresses and ranges, and export layouts to PDF. 🔧🗺️

## Features

- Load and view floor plans
- Add, move, and configure smoke detectors (model, range, bus, address, serial)
- Draw connections between detectors
- Save projects and export detector layouts to PDF

## Installation

### Quick start (user)
- If you have the Windows installer, run it to install Smoke Detector Planner.
- If running from source:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

### Developer setup
1. Create & activate virtualenv (see above).
2. Install dev/test dependencies:
```powershell
pip install -r requirements.txt
```
3. Run the app from source:
```powershell
python src/main.py
```

## Usage

1. Run the application:
```powershell
python src/main.py
```

2. Use the File menu to:
   - Create a new project
   - Open an existing project
   - Save your project
   - Export to PDF

3. In the main window:
   - Left-click to add smoke detectors
   - Click and drag detectors to move them
   - Right-click detectors to edit their properties
   - Use Ctrl + Mouse wheel to zoom
   - Click and drag to pan the view

## Project Files

- `src/main.py` - Application entry point
- `src/views/` - GUI components
- `src/models/` - Data models
- `src/controllers/` - Application logic
- `src/utils/` - Helper functions
- `resources/` - Application resources
- `tests/` - Unit tests

## Build & Packaging 🔧
- PyInstaller spec file is `SmokeSignal.spec` — used to build the bundled executable.
- Windows installer files: see `installer/SmokeSignal.iss` and `tools/build_windows_installer.ps1`.
- Typical build steps:
  1. Create build with PyInstaller: `pyinstaller SmokeSignal.spec`
  2. Run the PowerShell packaging script: `.\tools\build_windows_installer.ps1`

## Development

To run tests:
```powershell
pytest tests/
```

## Contributing 🤝
- Fork the repo, create a branch, implement changes, and open a PR with a description and tests.
- Please keep changes small and focused.

## License & Contact
- Add your license text here (e.g., MIT).
- Contact: add maintainer email or GitHub handle.