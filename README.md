# Smoke Detector Planner

A desktop application for planning smoke detector installations on floor plans.

## Features

- Load and view floor plans
- Add and configure smoke detectors
- Draw connections between detectors
- Set detector properties (model, range, bus number, address, serial number)
- Save project files
- Export to PDF with detector layout and configuration details

## Installation

1. Create a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
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

## Development

To run tests:
```powershell
pytest tests/
```