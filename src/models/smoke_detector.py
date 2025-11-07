from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor

class SmokeDetector(QGraphicsEllipseItem):
    def __init__(self, pos, controller=None):
        super().__init__()
        self.setPos(pos)
        self.setRect(QRectF(-5, -5, 20, 20))  # 10x10 pixel dot
        
        # Visual properties
        self.setBrush(QBrush(QColor(255, 0, 0)))  # Red dot
        self.setPen(QPen(Qt.PenStyle.NoPen))
        
        # Detector properties
        self.model = ""
        self.range = 6.2  # default range in meters (max 25)
        self.bus_number = ""
        self.group = ""
        self.address = ""
        self.serial_number = ""
        self.qr_data = ""
        self.brand = ""
        self.paired_sn = ""

        # Reference to the controller (FloorPlanController) for callbacks
        self.controller = controller
        
        # Range circle (gray area)
        self.range_circle = None
        # Address label shown near detector (hidden until populated)
        try:
            self.address_label = QGraphicsTextItem("", parent=self)
            self.address_label.setDefaultTextColor(QColor(0, 0, 0))
            self.address_label.setZValue(2)
            # position offset relative to detector
            try:
                self.address_label.setPos(12, -12)
            except Exception:
                pass
        except Exception:
            self.address_label = None
        
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
    def itemChange(self, change, value):
        """Update connected lines when detector is moved"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            try:
                if self.controller:
                    for line in self.controller.lines:
                        if line['start'] is self or line['end'] is self:
                            s_pos = line['start'].pos()
                            e_pos = line['end'].pos()
                            line['item'].setLine(s_pos.x(), s_pos.y(), e_pos.x(), e_pos.y())
            except Exception:
                pass
        return super().itemChange(change, value)
    
    def set_range(self, range_meters, pixels_per_meter=None):
        """Set the detection range and update the visual indicator"""
        self.range = range_meters
        # If no pixels_per_meter provided, don't draw the range circle (requires calibration)
        if pixels_per_meter is None:
            if self.range_circle:
                try:
                    self.scene().removeItem(self.range_circle)
                except Exception:
                    pass
                self.range_circle = None
            return

        range_pixels = range_meters * pixels_per_meter

        if self.range_circle:
            try:
                self.scene().removeItem(self.range_circle)
            except Exception:
                pass

        # Create a child ellipse item to represent the range
        from PyQt6.QtWidgets import QGraphicsEllipseItem

        self.range_circle = QGraphicsEllipseItem(
            -range_pixels, -range_pixels,
            range_pixels * 2, range_pixels * 2,
            parent=self
        )
        self.range_circle.setBrush(QBrush(QColor(128, 128, 128, 64)))  # Semi-transparent gray
        self.range_circle.setPen(QPen(Qt.PenStyle.NoPen))
        self.range_circle.setZValue(-1)  # Place behind the detector dot
        # Respect controller-level visibility flag if present
        try:
            visible = getattr(self.controller, 'show_ranges', True)
            self.range_circle.setVisible(bool(visible))
        except Exception:
            pass

        # Ensure address label is updated when range is (re)created
        try:
            self.update_address_label()
        except Exception:
            pass

    def update_address_label(self):
        """Update the small address label shown next to the detector.

        Format: bus-groupaddress (e.g. 1-02015 or similar). Only shown when
        bus, group and address are available.
        """
        try:
            if not getattr(self, 'address_label', None):
                return
            bus = str(getattr(self, 'bus_number', '') or '').strip()
            group = str(getattr(self, 'group', '') or '').strip()
            addr = str(getattr(self, 'address', '') or '').strip()
            if bus and group and addr:
                label = f"{bus}-{group}{addr}"
                self.address_label.setPlainText(label)
                self.address_label.setVisible(True)
            else:
                # hide if incomplete
                self.address_label.setPlainText("")
                self.address_label.setVisible(False)
        except Exception:
            pass
    
    def mousePressEvent(self, event):
        """Handle selection and editing"""
        super().mousePressEvent(event)
        # Right-click: show context menu for edit/delete
        if event.button() == Qt.MouseButton.RightButton:
            try:
                from PyQt6.QtWidgets import QMenu
                menu = QMenu()
                edit_action = menu.addAction("Edit")
                delete_action = menu.addAction("Delete")
                action = menu.exec(event.screenPos())
                if action == edit_action:
                    # open the same dialog as double-click
                    self.mouseDoubleClickEvent(event)
                elif action == delete_action:
                    if self.controller is not None:
                        try:
                            self.controller.remove_detector(self)
                        except Exception:
                            pass
                return
            except Exception:
                pass

        # Left-click in add-line mode: register for line creation
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                if self.controller is not None and getattr(self.controller, 'line_mode', False):
                    try:
                        self.controller.handle_line_click(self)
                        return
                    except Exception:
                        pass
            except Exception:
                pass

    def mouseDoubleClickEvent(self, event):
        # Open the detector properties dialog on double click
        try:
            # Lazy import to avoid circular imports
            from views.detector_dialog import DetectorDialog

            # Determine a reasonable parent for the dialog (the window containing the view)
            parent = None
            try:
                views = self.scene().views()
                if views:
                    parent = views[0].window()
            except Exception:
                parent = None

            dlg = DetectorDialog(self, controller=self.controller, parent=parent)
            if dlg.exec():
                # Dialog applies changes directly to the detector via controller or detector methods
                # After editing, ask controller to update colors/visuals
                try:
                    if self.controller is not None:
                        self.controller.update_detector_colors()
                except Exception:
                    pass
        except Exception:
            # If anything goes wrong, ignore to keep the app responsive
            pass