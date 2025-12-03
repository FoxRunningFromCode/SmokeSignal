from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QMenuBar, QMenu, QFileDialog, QInputDialog, QMessageBox, QDialog
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
        
        # Track which device type is currently being added
        self.device_type_to_add = "Detector"
        
        # Connect the add_detector_requested signal from the view to our method
        try:
            self.floor_plan_controller.view.add_detector_requested.connect(self._on_add_device_requested)
        except Exception:
            pass
        
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
        
        # Device type selection (Detector, IO, Call Point)
        devices_menu = tools_menu.addMenu("Add Device")
        self.detector_action = devices_menu.addAction("Smoke Detector")
        self.detector_action.setCheckable(True)
        self.detector_action.setChecked(True)
        self.detector_action.triggered.connect(self._on_select_device_type)
        
        self.io_action = devices_menu.addAction("IO Box")
        self.io_action.setCheckable(True)
        self.io_action.triggered.connect(self._on_select_device_type)
        
        self.callpoint_action = devices_menu.addAction("Call Point")
        self.callpoint_action.setCheckable(True)
        self.callpoint_action.triggered.connect(self._on_select_device_type)
        
        self.add_device_action = tools_menu.addAction("Add Device Mode")
        self.add_device_action.setCheckable(True)
        self.add_device_action.toggled.connect(self._on_add_device_toggled)
        
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
        
        # Find device action
        find_action = tools_menu.addAction("Find Device")
        find_action.triggered.connect(self._on_find_device)

    def _on_select_device_type(self):
        """Handle device type selection from menu."""
        if self.sender() == self.detector_action:
            self.device_type_to_add = "Detector"
            self.io_action.setChecked(False)
            self.callpoint_action.setChecked(False)
            self.detector_action.setChecked(True)
        elif self.sender() == self.io_action:
            self.device_type_to_add = "IO"
            self.detector_action.setChecked(False)
            self.callpoint_action.setChecked(False)
            self.io_action.setChecked(True)
        elif self.sender() == self.callpoint_action:
            self.device_type_to_add = "CallPoint"
            self.detector_action.setChecked(False)
            self.io_action.setChecked(False)
            self.callpoint_action.setChecked(True)
    
    def _on_add_device_toggled(self, checked: bool):
        """Toggle add-device mode on the view."""
        try:
            self.floor_plan_controller.view.set_add_mode(checked)
            # Set device type on controller
            self.floor_plan_controller._device_type_to_add = self.device_type_to_add
        except Exception:
            pass

    def _on_add_detector_toggled(self, checked: bool):
        # Legacy - for backwards compatibility if needed
        try:
            self.floor_plan_controller.view.set_add_mode(checked)
        except Exception:
            pass
    
    def _on_add_device_requested(self, pos):
        """Handle add device request from the view."""
        try:
            self.floor_plan_controller.add_detector(pos, self.device_type_to_add)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add device: {e}")

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

    def _on_find_device(self):
        try:
            text, ok = QInputDialog.getText(self, "Find Device", "Enter serial number or full address label:")
        except Exception:
            text, ok = ('', False)
        if not ok or not text:
            return

        try:
            results = self.floor_plan_controller.find_detectors(text)
        except Exception as e:
            QMessageBox.critical(self, "Find Error", f"Search failed: {e}")
            return

        if not results:
            QMessageBox.information(self, "Not found", f"No detectors match '{text}'.")
            return

        if len(results) == 1:
            try:
                self.floor_plan_controller.highlight_detector(results[0])
            except Exception:
                pass
            return

        # Multiple results: ask user to pick one
        try:
            items = []
            for d in results:
                lbl = ''
                try:
                    lbl = d.get_full_address_label() or ''
                except Exception:
                    lbl = ''
                desc = f"{getattr(d, 'serial_number', '')} - {lbl}"
                items.append(desc)
            choice, ok2 = QInputDialog.getItem(self, "Multiple matches", "Select detector:", items, 0, False)
            if not ok2:
                return
            idx = items.index(choice)
            sel = results[idx]
            try:
                self.floor_plan_controller.highlight_detector(sel)
            except Exception:
                pass
        except Exception:
            # fallback: highlight first
            try:
                self.floor_plan_controller.highlight_detector(results[0])
            except Exception:
                pass
    
    def new_project(self):
        # Ask for a project name
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if not ok or not name:
            return

        # Ask user to select a floor plan image or PDF
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select floor plan image or PDF",
            "",
            "Floor Plan Files (*.png *.jpg *.jpeg *.bmp *.pdf);;Image Files (*.png *.jpg *.jpeg *.bmp);;PDF Files (*.pdf);;All Files (*)"
        )
        if not image_path:
            QMessageBox.information(self, "No file selected", "Project was created without a floor plan.")
            return

        pdf_page = None
        if Path(image_path).suffix.lower() == '.pdf':
            # Show PDF page selector dialog
            from .pdf_page_dialog import PDFPageSelector
            dialog = PDFPageSelector(image_path, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                QMessageBox.information(self, "Cancelled", "PDF page selection was cancelled.")
                return
            pdf_page = dialog.get_selected_page()

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
                self.floor_plan_controller.load_floor_plan(image_path, pdf_page)
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