# Smoke Detector Planning Tool - Project Context

## Project Overview
This is a Qt-based application for planning smoke detector placement with the following key features:
- Interactive floor plan visualization
- Click-to-add detector placement
- Detector range visualization (circles)
- QR code parsing for Autronica devices
- PDF export with landscape orientation

## Technical Stack
- **GUI Framework**: PyQt6
- **Image Processing**: Pillow
- **PDF Generation**: ReportLab
- **Dependencies**: See requirements.txt

## Core Components

### Data Model (`src/models/smoke_detector.py`)
- Extended smoke detector properties including:
  - QR data parsing
  - Group/Bus/Address fields
  - Brand and model information
  - Paired serial numbers
  - Default range: 6.2m
  - Maximum range: 25m

### Views (`src/views/detector_dialog.py`)
- Detector properties dialog with ordered fields
- QR code parsing integration
- Organized field layout for optimal user experience

### Controllers (`src/controllers/floor_plan_controller.py`)
- Scene management
- PDF export with landscape orientation
- Floor plan visualization
- Range circle toggle functionality
- Address label display ('bus-groupaddress')

## Key Features

### QR Code Parsing
- Parses Autronica device QR codes
- Extracts serial numbers, model information
- Auto-populates relevant detector fields

### Range Visualization
- Toggle-able range circles
- Default 6.2m range
- Configurable up to 25m

### PDF Export
- Landscape orientation
- Scaled floor plan on first page
- Project metadata footer
- Address labels included

## Implementation Notes
1. Detector dialog fields are ordered specifically for optimal workflow
2. Range circles can be toggled via menu option
3. Address labels appear when bus/group/address are set
4. QR parsing uses heuristics for Autronica format

## Pending Tasks
1. Add helpful startup message for missing PyQt6
2. Complete README documentation with run instructions
3. Add packaging notes

## Project Status
The project is fully functional with all major features implemented. Recent work focused on:
- Dialog field reordering
- PDF export improvements
- QR parsing refinements

This document serves as a knowledge transfer reference for any AI assistant working with this codebase in the future.