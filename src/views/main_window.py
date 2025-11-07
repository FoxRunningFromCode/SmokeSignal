from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QMenuBar, QMenu, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt
from controllers.floor_plan_controller import FloorPlanController
import json
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smoke Detector Planner")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Initialize floor plan controller
        self.floor_plan_controller = FloorPlanController(self)
        layout.addWidget(self.floor_plan_controller.view)
        
        # Create menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = file_menu.addAction("New Project")
        new_action.triggered.connect(self.new_project)
        
        open_action = file_menu.addAction("Open Project")
        open_action.triggered.connect(self.open_project)
        
        save_action = file_menu.addAction("Save Project")
        save_action.triggered.connect(self.save_project)
        
        export_action = file_menu.addAction("Export to PDF")
        export_action.triggered.connect(self.export_to_pdf)

        # Tools menu for interactive modes
        tools_menu = menubar.addMenu("Tools")
        self.add_detector_action = tools_menu.addAction("Add Detector Mode")
        self.add_detector_action.setCheckable(True)
        self.add_detector_action.toggled.connect(self._on_add_detector_toggled)
        self.add_line_action = tools_menu.addAction("Add Line Mode")
        self.add_line_action.setCheckable(True)
        self.add_line_action.toggled.connect(self._on_add_line_toggled)
        calibrate_action = tools_menu.addAction("Calibrate Project")
        calibrate_action.triggered.connect(self._on_calibrate_project)

        # Toggle to show/hide detection range circles
        self.show_ranges_action = tools_menu.addAction("Show Range Circles")
        self.show_ranges_action.setCheckable(True)
        self.show_ranges_action.setChecked(True)
        self.show_ranges_action.toggled.connect(self._on_show_ranges_toggled)

    def _on_add_detector_toggled(self, checked: bool):
        # Toggle add mode on the view
        try:
            self.floor_plan_controller.view.set_add_mode(checked)
        except Exception:
            pass

    def _on_add_line_toggled(self, checked: bool):
        try:
            self.floor_plan_controller.view.set_add_mode(False)
            # Set a dedicated line mode flag on the controller/view
            self.floor_plan_controller.line_mode = bool(checked)
            self.floor_plan_controller.view.set_add_line_mode(bool(checked))
        except Exception:
            pass

    def _on_calibrate_project(self):
        try:
            # Start calibration flow in the controller (will ask for points and distance)
            self.floor_plan_controller.start_calibration()
        except Exception as e:
            QMessageBox.critical(self, "Calibration error", f"Failed to start calibration: {e}")

    def _on_show_ranges_toggled(self, checked: bool):
        try:
            # Store on controller and update visuals
            self.floor_plan_controller.show_ranges = bool(checked)
            try:
                self.floor_plan_controller.update_range_visibility()
            except Exception:
                pass
        except Exception:
            pass
    
    def new_project(self):
        # Ask for a project name
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if not ok or not name:
            return

        # Ask user to select a floor plan image
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select floor plan image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if not image_path:
            QMessageBox.information(self, "No image selected", "Project was created without a floor plan image.")

        # Ask for drawing scale (accepts formats like "1:100" or a numeric value)
        scale_text, ok = QInputDialog.getText(self, "Drawing Scale", "Enter drawing scale (e.g. 1:100) or meters-per-pixel (numeric):")
        if not ok:
            return

        # Save project meta locally on the window instance for now
        self.project_name = name
        self.project_floorplan = image_path
        self.project_scale_text = scale_text

        # Try to load the floor plan into the controller (if provided)
        if image_path:
            try:
                self.floor_plan_controller.load_floor_plan(image_path)
            except Exception as e:
                QMessageBox.critical(self, "Load error", f"Failed to load floor plan: {e}")

        # Apply scale to controller if parsable — controller will decide how to interpret it
        try:
            self.floor_plan_controller.set_scale(scale_text)
        except Exception:
            # Non-fatal — controller may accept string scales for later processing
            pass
    
    def open_project(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Project Files (*.sdp);;All Files (*)"
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # give the controller the data
                self.floor_plan_controller.from_dict(data)
                # set local metadata if present
                self.project_name = data.get('project_name', Path(file_name).stem)
                self.project_floorplan = data.get('floorplan_path')
                self.project_scale_text = data.get('scale')
                QMessageBox.information(self, "Project loaded", f"Loaded project: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Load error", f"Failed to load project: {e}")
    
    def save_project(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "Project Files (*.sdp);;All Files (*)"
        )
        if file_name:
            # Ensure extension
            p = Path(file_name)
            if p.suffix.lower() != '.sdp':
                p = p.with_suffix('.sdp')

            try:
                data = self.floor_plan_controller.to_dict()
                # include some top-level metadata
                data['project_name'] = getattr(self, 'project_name', p.stem)
                # ensure floorplan_path reflects what the controller has, if any
                if hasattr(self.floor_plan_controller, 'floorplan_path'):
                    data['floorplan_path'] = str(self.floor_plan_controller.floorplan_path)

                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)

                QMessageBox.information(self, "Saved", f"Project saved to: {p}")
            except Exception as e:
                QMessageBox.critical(self, "Save error", f"Failed to save project: {e}")
    
    def export_to_pdf(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export to PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if file_name:
            # Ensure .pdf extension
            p = Path(file_name)
            if p.suffix.lower() != '.pdf':
                p = p.with_suffix('.pdf')
            
            try:
                self.floor_plan_controller.export_to_pdf(str(p))
                QMessageBox.information(self, "Export Complete", f"Project exported to PDF: {p}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export to PDF: {e}")