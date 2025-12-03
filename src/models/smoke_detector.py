from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QGraphicsRectItem, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPixmap
from pathlib import Path


class BaseDevice(QGraphicsItem):
    """Base class for all fire safety devices (detectors, IO boxes, call points)."""
    
    ICON_FILE = "M_s.png"  # Override in subclasses
    
    def __init__(self, pos, controller=None):
        super().__init__()
        self.setPos(pos)

        # Visual composition: a colored background square and an icon pixmap on top
        self._icon_pixmap = None
        self._pixmap_item = None
        self._background = None

        # Load bundled icon
        try:
            icon_path = Path(__file__).resolve().parent / self.ICON_FILE
            pix = QPixmap(str(icon_path))
            if not pix.isNull():
                self._icon_pixmap = pix
        except Exception:
            self._icon_pixmap = None

        # Default padding around the icon so background is a bit larger
        self._pad = 10  # pixels per side

        # Create background rect and pixmap item if we have an icon
        if self._icon_pixmap is not None:
            w = self._icon_pixmap.width()
            h = self._icon_pixmap.height()
            # background rect centered at (0,0)
            rect = QRectF(-w/2 - self._pad, -h/2 - self._pad, w + 2 * self._pad, h + 2 * self._pad)
            self._background = QGraphicsRectItem(rect, parent=self)
            self._background.setBrush(QBrush(QColor(255, 0, 0)))
            self._background.setPen(QPen(Qt.PenStyle.NoPen))
            self._background.setZValue(0)

            # Pixmap item centered
            self._pixmap_item = QGraphicsPixmapItem(self._icon_pixmap, parent=self)
            self._pixmap_item.setOffset(-w/2, -h/2)
            self._pixmap_item.setZValue(1)
        else:
            # Fall back to small bbox
            self._pad = 5
            self._background = None

        # Generic device properties
        self.model = ""
        self.bus_number = ""
        self.group = ""
        self.address = ""
        self.room_id = ""
        self.device_type = "Device"  # Override in subclasses
        self.serial_number = ""
        self.qr_data = ""
        self.brand = ""

        # Reference to the controller (FloorPlanController) for callbacks
        self.controller = controller

        # Range circle (gray area) - only for detectors
        self.range_circle = None
        # Room label (above) and Address label (below) shown near device
        try:
            # Room label (shows `room_id` when present)
            self.room_label = QGraphicsTextItem("", parent=self)
            self.room_label.setDefaultTextColor(QColor(0, 0, 0))
            self.room_label.setZValue(3)
            try:
                rf = self.room_label.font()
                rsize = rf.pointSizeF()
                if not rsize or rsize <= 0:
                    rsize = 8.0
                rf.setPointSizeF(rsize * 2.0)
                self.room_label.setFont(rf)
            except Exception:
                pass
            try:
                # Position room label above the icon (offset depends on icon height)
                y_off = - (self._icon_pixmap.height() / 2 + 80) if self._icon_pixmap else -20
                self.room_label.setPos(-64, y_off)
            except Exception:
                pass

            # Address label shown below room label
            self.address_label = QGraphicsTextItem("", parent=self)
            self.address_label.setDefaultTextColor(QColor(0, 0, 0))
            self.address_label.setZValue(3)
            # Make the label at least 2x the default text size (fall back to a sensible size)
            try:
                f = self.address_label.font()
                size = f.pointSizeF()
                if not size or size <= 0:
                    # some environments may return -1; choose a reasonable default base size
                    size = 8.0
                f.setPointSizeF(size * 3.0)
                self.address_label.setFont(f)
            except Exception:
                # if anything goes wrong, try a fixed larger font
                try:
                    f2 = QFont()
                    f2.setPointSizeF(14.0)
                    self.address_label.setFont(f2)
                except Exception:
                    pass

            # position offset relative to device
            try:
                y_off = - (self._icon_pixmap.height() / 2 + 60) if self._icon_pixmap else -6
                self.address_label.setPos(-64, y_off)
            except Exception:
                pass
        except Exception:
            self.room_label = None
            self.address_label = None

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def boundingRect(self):
        """Return the bounding rectangle for this device item."""
        if self._icon_pixmap is not None:
            w = self._icon_pixmap.width()
            h = self._icon_pixmap.height()
            return QRectF(-w/2 - self._pad, -h/2 - self._pad, w + 2 * self._pad, h + 2 * self._pad)
        else:
            return QRectF(-8, -8, 16, 16)

    def paint(self, painter, option, widget):
        """Paint method - child items (background rect and pixmap) handle the actual drawing."""
        # Nothing to paint at this level; child items handle drawing
        pass

    def mousePressEvent(self, event):
        """Handle selection and editing - right-click menu, line mode."""
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
        """Open the device properties dialog on double click."""
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
                # Dialog applies changes directly to the device via controller or device methods
                # After editing, ask controller to update colors/visuals
                try:
                    if self.controller is not None:
                        self.controller.update_detector_colors()
                except Exception:
                    pass
        except Exception:
            # If anything goes wrong, ignore to keep the app responsive
            pass

    def update_address_label(self):
        """Update the small address label shown next to the device.

        Format: bus-groupaddress (e.g. 01-2015 or similar). Only shown when
        bus, group and address are available.
        """
        try:
            if not getattr(self, 'address_label', None):
                return
            bus = str(getattr(self, 'bus_number', '') or '').strip()
            group = str(getattr(self, 'group', '') or '').strip()
            addr = str(getattr(self, 'address', '') or '').strip()
            room = str(getattr(self, 'room_id', '') or '').strip()

            # Update room label first
            try:
                if getattr(self, 'room_label', None):
                    if room:
                        self.room_label.setPlainText(room)
                        self.room_label.setVisible(True)
                    else:
                        self.room_label.setPlainText("")
                        self.room_label.setVisible(False)
            except Exception:
                pass

            if bus and group and addr:
                # Prefer numeric formatting: bus -> 2 digits, group -> as-is (single digit), address -> 3 digits
                try:
                    bus_i = int(bus)
                    group_i = int(group)
                    addr_i = int(addr)
                    label = f"{bus_i:02d}-{group_i}{addr_i:03d}"
                except Exception:
                    # fallback to raw concatenation if values aren't numeric
                    label = f"{bus}-{group}{addr}"
                try:
                    if getattr(self, 'address_label', None):
                        self.address_label.setPlainText(label)
                        self.address_label.setVisible(True)
                except Exception:
                    pass
            else:
                # hide if incomplete
                try:
                    if getattr(self, 'address_label', None):
                        self.address_label.setPlainText("")
                        self.address_label.setVisible(False)
                except Exception:
                    pass
                
        except Exception:
                    pass

    def get_full_address_label(self):
        """Return the formatted full address label (same format used for display) or empty string."""
        try:
            bus = str(getattr(self, 'bus_number', '') or '').strip()
            group = str(getattr(self, 'group', '') or '').strip()
            addr = str(getattr(self, 'address', '') or '').strip()
            if bus and group and addr:
                try:
                    bus_i = int(bus)
                    group_i = int(group)
                    addr_i = int(addr)
                    return f"{bus_i:02d}-{group_i}{addr_i:03d}"
                except Exception:
                    return f"{bus}-{group}{addr}"
        except Exception:
            pass
        return ""
    
    # Compatibility helpers so controller code that calls setBrush/setPen continues to work
    def setBrush(self, brush):
        """Set the brush (background color) of the device."""
        try:
            if self._background is not None:
                self._background.setBrush(brush)
            else:
                # no background; no-op
                pass
        except Exception:
            pass

    def brush(self):
        """Return the current brush of the background rectangle."""
        try:
            if self._background is not None:
                return self._background.brush()
        except Exception:
            pass
        return QBrush()

    def setPen(self, pen):
        """Set the pen (border) of the device background."""
        try:
            if self._background is not None:
                self._background.setPen(pen)
        except Exception:
            pass

    def pen(self):
        """Return the current pen of the background rectangle."""
        try:
            if self._background is not None:
                return self._background.pen()
        except Exception:
            pass
        return QPen()


class SmokeDetector(BaseDevice):
    """Smoke detector with range circle capability."""
    
    ICON_FILE = "M_s.png"
    
    def __init__(self, pos, controller=None):
        super().__init__(pos, controller)
        # Smoke detector specific properties
        self.range = 6.2  # default range in meters (max 25)
        self.paired_sn = ""
        self.device_type = "Detector"

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

class IOBox(BaseDevice):
    """Input/Output module with no range capability."""
    
    ICON_FILE = "IO64.png"
    
    def __init__(self, pos, controller=None):
        super().__init__(pos, controller)
        self.device_type = "IO"


class CallPoint(BaseDevice):
    """Manual call point (break glass) with no range capability."""
    
    ICON_FILE = "C_P64.png"
    
    def __init__(self, pos, controller=None):
        super().__init__(pos, controller)
        self.device_type = "CallPoint"
