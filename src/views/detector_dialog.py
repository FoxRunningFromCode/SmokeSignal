from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QDoubleSpinBox, QLabel
)
from PyQt6.QtCore import Qt

class DetectorDialog(QDialog):
    def __init__(self, detector, controller=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detector Properties")
        self.detector = detector
        self.controller = controller

        layout = QFormLayout(self)
        # Range (first)
        self.range_spin = QDoubleSpinBox(self)
        self.range_spin.setRange(0.0, 25.0)
        self.range_spin.setSingleStep(0.1)
        self.range_spin.setSuffix(" m")
        # default to detector value or 6.2m
        self.range_spin.setValue(getattr(detector, 'range', 6.2) or 6.2)
        layout.addRow("Range:", self.range_spin)

        # QR data (scanned) - second
        self.qr_edit = QLineEdit(self)
        self.qr_edit.setText(getattr(detector, 'qr_data', ''))
        self.qr_edit.editingFinished.connect(self._parse_qr_data)
        layout.addRow("QR data:", self.qr_edit)

        # Bus
        self.bus_edit = QLineEdit(self)
        self.bus_edit.setText(getattr(detector, 'bus_number', ''))
        layout.addRow("Bus number:", self.bus_edit)

        # Group
        self.group_edit = QLineEdit(self)
        self.group_edit.setText(getattr(detector, 'group', ''))
        layout.addRow("Group:", self.group_edit)

        # Address
        self.address_edit = QLineEdit(self)
        self.address_edit.setText(getattr(detector, 'address', ''))
        layout.addRow("Address:", self.address_edit)

        # Room ID (optional)
        self.room_edit = QLineEdit(self)
        self.room_edit.setText(getattr(detector, 'room_id', ''))
        layout.addRow("Room ID:", self.room_edit)

        # Serial number
        self.serial_edit = QLineEdit(self)
        self.serial_edit.setText(getattr(detector, 'serial_number', ''))
        layout.addRow("Serial number:", self.serial_edit)

        # Brand
        self.brand_edit = QLineEdit(self)
        self.brand_edit.setText(getattr(detector, 'brand', ''))
        layout.addRow("Brand:", self.brand_edit)

        # Model
        self.model_edit = QLineEdit(self)
        self.model_edit.setText(getattr(detector, 'model', ''))
        layout.addRow("Model:", self.model_edit)

        # Paired detector serial (last)
        self.paired_edit = QLineEdit(self)
        self.paired_edit.setText(getattr(detector, 'paired_sn', ''))
        layout.addRow("Paired detector SN:", self.paired_edit)

        # Informational label for range visualization
        info = QLabel(self)
        info.setText("If the project has not been calibrated for pixels-per-meter, the range circle may not be shown correctly.")
        info.setWordWrap(True)
        layout.addRow(info)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self) -> None:
        # Apply changes to the detector
        try:
            self.detector.model = self.model_edit.text()
            new_range = float(self.range_spin.value())
            self.detector.bus_number = self.bus_edit.text()
            self.detector.address = self.address_edit.text()
            self.detector.room_id = self.room_edit.text()
            self.detector.serial_number = self.serial_edit.text()
            self.detector.group = self.group_edit.text()
            self.detector.qr_data = self.qr_edit.text()
            self.detector.brand = self.brand_edit.text()
            self.detector.paired_sn = self.paired_edit.text()

            # If a controller is provided, ask it to set the detector range so
            # it can compute pixels-per-meter. Otherwise, set without drawing.
            if self.controller is not None:
                try:
                    self.controller.set_detector_range(self.detector, new_range)
                except Exception:
                    # fallback
                    self.detector.set_range(new_range, pixels_per_meter=None)
            else:
                self.detector.set_range(new_range, pixels_per_meter=None)

            # Update colors (unique serial numbers -> green) and ranges
            try:
                if self.controller is not None:
                    self.controller.update_detector_colors()
                    try:
                        # update visibility of ranges if controller tracks that
                        self.controller.update_range_visibility()
                    except Exception:
                        pass
                # update detector address label
                try:
                    self.detector.update_address_label()
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
        super().accept()

    def _parse_qr_data(self):
        """Parse QR content heuristically and fill serial/model/brand fields.

        Expected example: "000.037.2022.223.00088_V-100_116-V-100_01"
        - serial: first underscore-separated segment
        - model: first segment that contains both letters and digits (heuristic)
        - brand: if serial looks like dotted numeric segments -> Autronica
        """
        try:
            text = self.qr_edit.text().strip()
            if not text:
                return
            parts = text.split('_')
            serial = parts[0] if parts else ''
            model_candidate = None
            # Collect segments that contain both letters and digits
            candidates = [p for p in parts[1:] if any(c.isalpha() for c in p) and any(c.isdigit() for c in p)]
            if candidates:
                # Prefer the longest candidate (e.g. prefer "116-V-100" over "V-100")
                model_candidate = max(candidates, key=len)

            # brand heuristic: dotted numeric serial
            brand = ''
            try:
                serial_plain = serial.replace('.', '')
                if serial and serial_plain.isdigit():
                    brand = 'Autronica'
            except Exception:
                brand = ''

            if serial:
                self.serial_edit.setText(serial_plain)
            if model_candidate:
                self.model_edit.setText(model_candidate)
            if brand:
                self.brand_edit.setText(brand)
        except Exception:
            pass
