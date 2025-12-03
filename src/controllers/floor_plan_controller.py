from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6 import QtCore
from models.smoke_detector import SmokeDetector, IOBox, CallPoint
from views.floor_plan_view import FloorPlanView
import json
from pathlib import Path
from PyQt6.QtCore import QPointF
from PyQt6.QtCore import QTimer
import base64
import math

class FloorPlanController:
    def __init__(self, parent):
        self.scene = QGraphicsScene()
        self.view = FloorPlanView(self.scene, parent)
        # expose controller to the view so it can read scale for coordinate conversion
        try:
            self.view.controller = self
        except Exception:
            pass
        self.detectors = []
        self.lines = []  # list of {'item': QGraphicsLineItem, 'start': detector, 'end': detector}
        self._line_start = None
        self.scale = 1.0  # meters per pixel
        self.parent = parent
        # Whether detector range circles should be visible
        self.show_ranges = True
        self._calibrating = False
        self._calibration_points = []
        
        # Track current device type being added
        self._device_type_to_add = "Detector"
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Connect view's calibration signal to the controller
        try:
            self.view.calibration_point_requested.connect(self._on_calibration_point)
        except Exception:
            # Defensive: if the view doesn't have the signal (older versions), ignore
            pass
    
    def load_floor_plan(self, image_path, pdf_page=None):
        """Load a floor plan from an image or PDF file.
        
        Args:
            image_path: Path to image file, PDF file, or raw image bytes
            pdf_page: If image_path is a PDF, the page number to load (0-based)
        """
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtWidgets import QGraphicsPixmapItem
        from pathlib import Path

        pix = QPixmap()
        
        # Handle different input types
        if isinstance(image_path, (bytes, bytearray)):
            # Raw image data
            loaded = pix.loadFromData(bytes(image_path))
            if not loaded:
                raise ValueError("Could not load image from binary data")
            self.floorplan_path = None
            self.floorplan_blob = bytes(image_path)
            self.pdf_page = None
        else:
            # Path-like input - check for PDF
            path = Path(str(image_path))
            if path.suffix.lower() == '.pdf':
                # Convert PDF page to PNG
                from utils import pdf_tools
                png_data = pdf_tools.pdf_page_to_pixmap(str(path), pdf_page or 0)
                if not pix.loadFromData(png_data):
                    raise ValueError(f"Failed to convert PDF page to image: {image_path}")
                self.floorplan_path = str(image_path)
                self.floorplan_blob = png_data
                self.pdf_page = pdf_page
            else:
                # Regular image file - store its content for portability
                pix = QPixmap(str(image_path))
                if pix.isNull():
                    raise ValueError(f"Could not load image: {image_path}")
                # Save the image data to ensure project portability
                ba = QtCore.QByteArray()
                buffer = QtCore.QBuffer(ba)
                buffer.open(QtCore.QBuffer.OpenModeFlag.WriteOnly)
                pix.save(buffer, "PNG")
                self.floorplan_blob = bytes(ba.data())
                self.floorplan_path = str(image_path)
                self.pdf_page = None

        # Remove any existing floor plan items
        for item in list(self.scene.items()):
            # Keep detector items (they are SmokeDetector instances) but remove pixmaps
            from PyQt6.QtWidgets import QGraphicsPixmapItem as _GPI
            if isinstance(item, _GPI):
                self.scene.removeItem(item)

        self.floor_plan_item = QGraphicsPixmapItem(pix)
        # Place the floor plan at the origin
        self.floor_plan_item.setZValue(-10)
        self.scene.addItem(self.floor_plan_item)
        # Fit view to the image bounds if view is available
        try:
            self.view.fitInView(self.floor_plan_item, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception:
            pass

    def to_dict(self):
        """Serialize the current project state to a dictionary."""
        data = {
            "floorplan_path": getattr(self, 'floorplan_path', None),
            "floorplan_blob": None,
            "floorplan_name": None,
            "pdf_page": getattr(self, 'pdf_page', None),
            "scale": self.scale,
            "detectors": [],
            "lines": [],
        }

        # Always include the image blob if we have one (ensures project portability)
        if getattr(self, 'floorplan_blob', None):
            data['floorplan_blob'] = base64.b64encode(self.floorplan_blob).decode('ascii')
            data['floorplan_name'] = Path(getattr(self, 'floorplan_path', '') or '').name or None
            
        # Include original path for reference
        data['floorplan_path'] = getattr(self, 'floorplan_path', None)

        # Collect detectors
        for d in self.detectors:
            pos = d.pos()
            data["detectors"].append({
                "x": pos.x(),
                "y": pos.y(),
                "model": getattr(d, 'model', ''),
                "range": getattr(d, 'range', 0),
                "bus_number": getattr(d, 'bus_number', ''),
                "group": getattr(d, 'group', ''),
                "address": getattr(d, 'address', ''),
                "full_address_label": getattr(d, 'get_full_address_label', lambda: '')(),
                "serial_number": getattr(d, 'serial_number', ''),
                "room_id": getattr(d, 'room_id', ''),
                "qr_data": getattr(d, 'qr_data', ''),
                "brand": getattr(d, 'brand', ''),
                "paired_sn": getattr(d, 'paired_sn', ''),
                "device_type": getattr(d, 'device_type', 'Detector'),
            })

        # Include the stored floorplan path if available
        # Serialize lines as detector index pairs
        for ln in self.lines:
            try:
                s = self.detectors.index(ln['start'])
                e = self.detectors.index(ln['end'])
                data['lines'].append([s, e])
            except Exception:
                continue

        return data

    def from_dict(self, data: dict):
        """Load project state from a dictionary (reverse of to_dict)."""
        # Clear existing detectors
        for d in list(self.detectors):
            try:
                self.remove_detector(d)
            except Exception:
                pass

        # Load floorplan
        # If we have an embedded image blob, use it directly
        if data.get('floorplan_blob'):
            try:
                blob = base64.b64decode(data['floorplan_blob'])
                # Keep original path for reference
                self.floorplan_path = data.get('floorplan_path')
                try:
                    # Load the blob with PDF page if specified
                    self.load_floor_plan(blob, data.get('pdf_page'))
                except Exception:
                    # Just store the blob if loading fails
                    self.floorplan_blob = blob
                    self.pdf_page = data.get('pdf_page')
            except Exception:
                pass
        else:
            # No blob, try to load from path
            fp = data.get('floorplan_path')
            if fp:
                self.floorplan_path = fp
                try:
                    # Load from file with PDF page if specified
                    self.load_floor_plan(fp, data.get('pdf_page'))
                except Exception:
                    # Path load failed - ignore, caller may handle
                    pass

        # Set scale
        if 'scale' in data:
            try:
                self.set_scale(data['scale'])
            except Exception:
                self.scale = data['scale']

        # Recreate detectors
        for item in data.get('detectors', []):
            try:
                x = float(item.get('x', 0))
                y = float(item.get('y', 0))
                # Get device type and create the appropriate object
                dev_type = item.get('device_type', 'Detector')
                d = self.add_detector(QPointF(x, y), dev_type)
                d.model = item.get('model', '')
                d.bus_number = item.get('bus_number', '')
                d.group = item.get('group', '')
                d.address = item.get('address', '')
                d.room_id = item.get('room_id', '')
                d.serial_number = item.get('serial_number', '')
                d.qr_data = item.get('qr_data', '')
                d.brand = item.get('brand', '')
                # paired_sn only for detectors
                if hasattr(d, 'paired_sn'):
                    d.paired_sn = item.get('paired_sn', '')
                # range only for detectors
                if hasattr(d, 'range'):
                    r = item.get('range', 0)
                    try:
                        self.set_detector_range(d, float(r))
                    except Exception:
                        d.set_range(r, pixels_per_meter=None)
                try:
                    d.update_address_label()
                except Exception:
                    pass
            except Exception:
                continue

        # Recreate lines after detectors are created
        for pair in data.get('lines', []):
            try:
                s_idx, e_idx = pair
                s = self.detectors[int(s_idx)]
                e = self.detectors[int(e_idx)]
                self.add_line(s, e)
            except Exception:
                continue

        # Update colors based on serial uniqueness
        try:
            self.update_detector_colors()
        except Exception:
            pass

    def validate_project(self):
        """Validate project for common errors prior to export.

        Returns (errors, warnings) where each is a list of strings.
        """
        errors = []
        warnings = []

        # Missing serial numbers
        missing_serial = [d for d in self.detectors if not (getattr(d, 'serial_number', '') or '').strip()]
        if missing_serial:
            errors.append(f"{len(missing_serial)} detector(s) missing serial number(s).")

        # Duplicate serial numbers
        sn_map = {}
        for d in self.detectors:
            sn = (getattr(d, 'serial_number', '') or '').strip()
            if sn:
                sn_map.setdefault(sn, []).append(d)
        dup_sns = {sn: items for sn, items in sn_map.items() if len(items) > 1}
        if dup_sns:
            for sn, items in dup_sns.items():
                labels = [getattr(i, 'get_full_address_label', lambda: '')() or f"@{i.pos().x():.0f},{i.pos().y():.0f}" for i in items]
                errors.append(f"Duplicate serial '{sn}' found on detectors: {', '.join(labels)}")

        # Duplicate address labels
        addr_map = {}
        for d in self.detectors:
            lbl = ''
            try:
                lbl = d.get_full_address_label()
            except Exception:
                lbl = ''
            if lbl:
                addr_map.setdefault(lbl, []).append(d)
        dup_addrs = {lbl: items for lbl, items in addr_map.items() if len(items) > 1}
        if dup_addrs:
            for lbl, items in dup_addrs.items():
                poslist = [f"@{i.pos().x():.0f},{i.pos().y():.0f}" for i in items]
                errors.append(f"Duplicate address label '{lbl}' on detectors at: {', '.join(poslist)}")

        # Spacing check (requires numeric self.scale which is meters-per-pixel)
        if isinstance(self.scale, (int, float)) and float(self.scale) > 0:
            for i in range(len(self.detectors)):
                for j in range(i + 1, len(self.detectors)):
                    a = self.detectors[i]
                    b = self.detectors[j]
                    dx = a.pos().x() - b.pos().x()
                    dy = a.pos().y() - b.pos().y()
                    pix = math.hypot(dx, dy)
                    meters = pix * float(self.scale)
                    if meters < 0.5:
                        la = getattr(a, 'get_full_address_label', lambda: '')() or f"@{a.pos().x():.0f},{a.pos().y():.0f}"
                        lb = getattr(b, 'get_full_address_label', lambda: '')() or f"@{b.pos().x():.0f},{b.pos().y():.0f}"
                        errors.append(f"Detectors too close (<0.5m): {la} and {lb} (distance {meters:.2f} m)")
        else:
            warnings.append("Project scale is not a numeric meters-per-pixel value; spacing checks were skipped. Calibrate project to enable spacing validation.")

        return errors, warnings
    
    def add_detector(self, pos, device_type="Detector"):
        """Add a device at the given position.
        
        Args:
            pos: QPointF position
            device_type: "Detector", "IO", or "CallPoint"
        """
        if device_type == "IO":
            device = IOBox(pos, controller=self)
        elif device_type == "CallPoint":
            device = CallPoint(pos, controller=self)
        else:
            # Default to smoke detector
            device = SmokeDetector(pos, controller=self)
        
        self.detectors.append(device)
        self.scene.addItem(device)
        # update coloring for serial uniqueness
        try:
            self.update_detector_colors()
        except Exception:
            pass
        return device

    def find_detectors(self, query):
        """Find detectors matching a serial number, full address label, or containing the query.

        Returns a list of detector objects (may be empty).
        """
        q = (str(query) or '').strip()
        if not q:
            return []
        ql = q.lower()
        results = []
        for d in self.detectors:
            try:
                sn = (getattr(d, 'serial_number', '') or '')
                full = ''
                try:
                    full = d.get_full_address_label() or ''
                except Exception:
                    full = ''
                room = (getattr(d, 'room_id', '') or '')

                if q == sn or q == full:
                    results.append(d)
                    continue
                if ql in sn.lower() or ql in full.lower() or ql in room.lower():
                    results.append(d)
            except Exception:
                continue
        return results

    def highlight_detector(self, detector, duration_ms=1500):
        """Center on and temporarily highlight a detector.

        Sets the detector as selected, centers the view on it, and briefly changes
        its brush color and pen (outline) before restoring the original.
        """
        try:
            # center view
            try:
                self.view.centerOn(detector)
            except Exception:
                pass

            # select
            try:
                detector.setSelected(True)
            except Exception:
                pass

            # temporarily change brush and pen for highlight
            try:
                orig_brush = detector.brush()
                orig_pen = detector.pen()
                
                # Set bright yellow background with thick black outline
                detector.setBrush(QBrush(QColor(255, 255, 0)))
                highlight_pen = QPen(QColor(0, 0, 0))
                highlight_pen.setWidth(3)
                detector.setPen(highlight_pen)

                def _restore():
                    try:
                        detector.setBrush(orig_brush)
                        detector.setPen(orig_pen)
                    except Exception:
                        pass

                QTimer.singleShot(duration_ms, _restore)
            except Exception:
                pass
        except Exception:
            pass

    def add_line(self, start_detector, end_detector):
        """Add a visual line connecting two detectors and track it."""
        from PyQt6.QtWidgets import QGraphicsLineItem

        line = QGraphicsLineItem(start_detector.pos().x(), start_detector.pos().y(), end_detector.pos().x(), end_detector.pos().y())
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(2)
        line.setPen(pen)
        line.setZValue(1)
        self.scene.addItem(line)
        self.lines.append({'item': line, 'start': start_detector, 'end': end_detector})
        return line

    def handle_line_click(self, detector):
        """Called when a detector is clicked while in line-mode. Creates a line between two consecutive clicks."""
        if self._line_start is None:
            self._line_start = detector
            return
        if detector is self._line_start:
            # clicked same detector, reset
            self._line_start = None
            return
        # create line
        try:
            self.add_line(self._line_start, detector)
        except Exception:
            pass
        self._line_start = None

    def start_calibration(self):
        """Enter calibration mode: user will click two points on the plan and enter the real-world distance."""
        self._calibrating = True
        self._calibration_points = []
        try:
            self.view.set_calibrate_mode(True)
        except Exception:
            pass
        try:
            QMessageBox.information(self.parent, "Calibration", "Click two points on the floor plan that correspond to a known real-world distance (e.g., a corridor length).")
        except Exception:
            pass

    def _on_calibration_point(self, pos: QPointF):
        if not self._calibrating:
            return
        self._calibration_points.append(pos)
        if len(self._calibration_points) < 2:
            return

        p1, p2 = self._calibration_points[:2]
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        pixel_distance = math.hypot(dx, dy)

        # Ask user for real-world distance in meters
        try:
            meters, ok = QInputDialog.getDouble(self.parent or None, "Calibration", "Enter the real-world distance between the two points (meters):", 1.0, 0.0001, 1e6, 4)
        except Exception:
            meters, ok = (0.0, False)

        # Exit calibration mode regardless
        self._calibrating = False
        try:
            self.view.set_calibrate_mode(False)
        except Exception:
            pass

        if not ok or meters <= 0 or pixel_distance <= 0:
            try:
                QMessageBox.warning(self.parent, "Calibration", "Calibration cancelled or invalid. No changes made.")
            except Exception:
                pass
            return

        meters_per_pixel = float(meters) / float(pixel_distance)
        # store scale as meters_per_pixel
        try:
            self.set_scale(meters_per_pixel)
        except Exception:
            self.scale = meters_per_pixel

        # Reapply ranges so circles draw using the new scale
        for d in list(self.detectors):
            try:
                self.set_detector_range(d, getattr(d, 'range', 0))
            except Exception:
                pass

        try:
            QMessageBox.information(self.parent, "Calibration", f"Calibration complete. Computed meters-per-pixel: {meters_per_pixel:.6f}")
        except Exception:
            pass

    def update_detector_colors(self):
        """Set detectors to green when their serial number is unique, otherwise red."""
        counts = {}
        for d in self.detectors:
            sn = getattr(d, 'serial_number', '') or ''
            counts[sn] = counts.get(sn, 0) + 1

        for d in self.detectors:
            sn = getattr(d, 'serial_number', '') or ''
            try:
                if sn and counts.get(sn, 0) == 1:
                    d.setBrush(QBrush(QColor(0, 200, 0)))  # Green for unique serial
                else:
                    d.setBrush(QBrush(QColor(255, 140, 0)))  # Orange for non-unique or empty serial
            except Exception:
                pass

    def update_range_visibility(self):
        """Show or hide range circles for all detectors based on controller setting."""
        for d in self.detectors:
            try:
                if getattr(d, 'range_circle', None):
                    d.range_circle.setVisible(bool(self.show_ranges))
            except Exception:
                pass

    def set_detector_range(self, detector, range_meters):
        """Set detector range in meters and update visual if possible.

        If the controller has a numeric `self.scale` (meters_per_pixel), compute
        pixels_per_meter = 1 / meters_per_pixel and pass to the detector. If
        the scale is not numeric (e.g. stored as '1:100'), the visual range
        cannot be determined without calibration; the detector will store the
        numeric range but no visual circle will be drawn.
        """
        # store numeric range on the detector
        try:
            if isinstance(self.scale, (int, float)) and self.scale > 0:
                pixels_per_meter = 1.0 / float(self.scale)
                detector.set_range(range_meters, pixels_per_meter)
            else:
                # unknown pixels_per_meter — set range value but don't draw
                detector.set_range(range_meters, pixels_per_meter=None)
        except Exception:
            # fallback: set without drawing
            detector.set_range(range_meters, pixels_per_meter=None)
    
    def remove_detector(self, detector):
        if detector in self.detectors:
            # Remove any lines connected to this detector
            for ln in list(self.lines):
                try:
                    if ln.get('start') is detector or ln.get('end') is detector:
                        try:
                            self.scene.removeItem(ln.get('item'))
                        except Exception:
                            pass
                        try:
                            self.lines.remove(ln)
                        except Exception:
                            pass
                except Exception:
                    pass

            self.detectors.remove(detector)
            try:
                self.scene.removeItem(detector)
            except Exception:
                pass

            # update colors after removal
            try:
                self.update_detector_colors()
            except Exception:
                pass
    
    def set_scale(self, meters_per_pixel):
        # The API accepts either a numeric meters_per_pixel or a string like "1:100".
        if isinstance(meters_per_pixel, str):
            text = meters_per_pixel.strip()
            if text.startswith("1:"):
                # Store the ratio string for now; precise pixel-based scaling requires calibration
                self.scale = text
                return
            else:
                try:
                    val = float(text)
                    self.scale = val
                except ValueError:
                    # keep as raw string
                    self.scale = text
        else:
            self.scale = meters_per_pixel
        # TODO: Update visual elements based on new scale (requires converting between pixels and meters)
    
    def export_to_pdf(self, file_path):
        """Export the floor plan and detector details to PDF."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from PyQt6.QtCore import QBuffer, QByteArray
        from PyQt6.QtGui import QImage
        import io
        from datetime import datetime

        pagesize = landscape(A4)
        page_w, page_h = pagesize
        doc = SimpleDocTemplate(file_path, pagesize=pagesize)
        story = []
        styles = getSampleStyleSheet()

        # Validate project before exporting
        try:
            errors, warnings = self.validate_project()
        except Exception:
            errors, warnings = ([], [])

        if errors:
            try:
                QMessageBox.critical(self.parent, "Validation Errors", "\n".join(errors))
            except Exception:
                pass
            return

        if warnings:
            try:
                msg = "Warnings found:\n" + "\n".join(warnings) + "\n\nContinue with PDF export?"
                resp = QMessageBox.question(self.parent, "Validation Warnings", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if resp != QMessageBox.StandardButton.Yes:
                    return
            except Exception:
                # if the dialog cannot be shown, continue
                pass

        # Front page: project/title/metadata + optional logo
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=32,
            spaceAfter=20
        )
        project_name = getattr(self.parent, 'project_name', 'Untitled Project')
        story.append(Paragraph(f"{project_name}", title_style))

        # Add current date and calibration/project metadata
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray
        )
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", date_style))

        # Calibration/scale info
        try:
            scale_info = ''
            if isinstance(self.scale, (int, float)) and float(self.scale) > 0:
                scale_info = f"Scale: {self.scale:.6f} meters/pixel"
            else:
                scale_info = f"Scale: {str(self.scale)}"
            story.append(Paragraph(scale_info, styles['Normal']))
        except Exception:
            pass

        # Project floorplan path and detector count
        try:
            fp = getattr(self, 'floorplan_path', None) or ''
            story.append(Paragraph(f"Floorplan: {fp}", styles['Normal']))
        except Exception:
            pass
        try:
            story.append(Paragraph(f"Detectors: {len(self.detectors)}", styles['Normal']))
        except Exception:
            pass

        # Optional logo (look in repository resources/logo.png)
        try:
            logo_path = Path('resources') / 'logo.png'
            if logo_path.exists():
                logo_img = Image(str(logo_path))
                logo_img.drawWidth = 4 * cm
                logo_img.drawHeight = 4 * cm
                story.append(Spacer(1, 12))
                story.append(logo_img)
        except Exception:
            pass

        story.append(PageBreak())

        # Floor Plan (on its own page)
        if hasattr(self, 'floor_plan_item') and self.floor_plan_item:
            # Create QImage from the scene. QImage requires integer dimensions.
            scene_rect = self.scene.sceneRect()
            w = max(1, int(math.ceil(scene_rect.width())))
            h = max(1, int(math.ceil(scene_rect.height())))

            image = QImage(w, h, QImage.Format.Format_ARGB32)
            # Fill with white using a Qt color (reportlab.colors.white is not compatible)
            image.fill(QColor(255, 255, 255))

            painter = QPainter(image)
            # Render the scene into the QImage
            try:
                self.scene.render(painter)
            finally:
                painter.end()

            # Convert QImage to PNG bytes via QBuffer
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            image.save(buffer, "PNG")
            image_data = bytes(buffer.data())

            # Add floor plan image to PDF
            img = Image(io.BytesIO(image_data))
            # Compute available area on the page (leave margins and space for header/footer)
            available_w = page_w - 2*cm
            available_h = page_h - 6*cm
            scene_w = max(1.0, float(scene_rect.width()))
            scene_h = max(1.0, float(scene_rect.height()))
            scale = min(available_w / scene_w, available_h / scene_h)
            img.drawWidth = float(scene_w) * scale
            img.drawHeight = float(scene_h) * scale
            story.append(img)
            story.append(Spacer(1, 20))

        # Group detectors by bus number
        bus_groups = {}
        for d in self.detectors:
            bus_num = getattr(d, 'bus_number', '') or 'Unassigned'
            if bus_num not in bus_groups:
                bus_groups[bus_num] = []
            bus_groups[bus_num].append(d)

        # Sort detectors within each bus by address
        for bus in bus_groups.values():
            bus.sort(key=lambda d: getattr(d, 'address', ''))

        # Create detector tables for each bus; each bus starts on a new page
        for bus_index, bus_num in enumerate(sorted(bus_groups.keys())):
            # Start each bus on a new page (skip before the first bus since the floor plan already had its page)
            
            story.append(PageBreak())

            # Bus header
            story.append(Paragraph(f"Bus {bus_num}", styles['Heading2']))
            story.append(Spacer(1, 10))

            # Detector table with columns: Full address label, Serial number, Room ID, QR data, Paired Detector SN, Type
            header = ['Full\naddress', 'Serial number', 'Room ID', 'QR data', 'Paired\nDetector SN', 'Type']
            data = [header]
            for d in bus_groups[bus_num]:
                full_label = ''
                try:
                    full_label = getattr(d, 'get_full_address_label', lambda: '')() or ''
                except Exception:
                    full_label = ''

                qr_para = Paragraph((getattr(d, 'qr_data', '') or '').replace('\n', '<br />'), styles['Normal'])

                row = [
                    full_label,
                    getattr(d, 'serial_number', ''),
                    getattr(d, 'room_id', ''),
                    qr_para,
                    getattr(d, 'paired_sn', ''),
                    getattr(d, 'device_type', 'Detector')
                ]
                data.append(row)

            # Column widths: allocate space to QR data and Paired SN where Bus/Group/Address used to be
            colWidths = [2*cm, 4.5*cm, 3*cm, 8*cm, 3.5*cm, 2*cm]
            table = Table(data, colWidths=colWidths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(table)
            story.append(Spacer(1, 20))

        # Add page numbers and project info in footer
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            # Project name in bottom left
            canvas.drawString(cm, 0.75 * cm, project_name)
            # Page numbers in bottom right
            page_num = canvas.getPageNumber()
            canvas.drawRightString(page_w - cm, 0.75 * cm, f"Page {page_num}")
            canvas.restoreState()

        # Build PDF with footer
        doc.build(story, onFirstPage=footer, onLaterPages=footer)