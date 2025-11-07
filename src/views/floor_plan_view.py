from PyQt6.QtWidgets import QGraphicsView, QLabel
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QFont

class FloorPlanView(QGraphicsView):
    # Emitted when the user requests adding a detector; sends a QPointF (scene coordinates)
    add_detector_requested = pyqtSignal(object)
    # Emitted when the user clicks a point in calibration mode
    calibration_point_requested = pyqtSignal(object)
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.scale_factor = 1.2
        # If True, left-clicking will add a detector at the clicked scene position.
        self.add_mode = False
        # If True, left-clicking will register calibration points
        self.calibrate_mode = False
        # If True, clicking items is used for linking lines
        self.add_line_mode = False

        # Enable mouse tracking to receive mouseMoveEvent without press
        try:
            self.setMouseTracking(True)
        except Exception:
            pass

        # Coordinate label in top-right corner
        try:
            self.coord_label = QLabel(self)
            self.coord_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.coord_label.setStyleSheet("background-color: rgba(255,255,255,200); padding: 3px; border-radius: 4px;")
            f = QFont()
            f.setPointSize(9)
            self.coord_label.setFont(f)
            self.coord_label.setText("")
            self.coord_label.adjustSize()
            self.coord_label.show()
        except Exception:
            self.coord_label = None

    def set_add_mode(self, enabled: bool):
        """Enable or disable add-detector mode."""
        self.add_mode = bool(enabled)

    def set_add_line_mode(self, enabled: bool):
        self.add_line_mode = bool(enabled)

    def set_calibrate_mode(self, enabled: bool):
        self.calibrate_mode = bool(enabled)
        
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.scale(self.scale_factor, self.scale_factor)
            else:
                self.scale(1 / self.scale_factor, 1 / self.scale_factor)
        else:
            super().wheelEvent(event)
    
    def resizeEvent(self, event):
        # Ensure coordinate label stays in the top-right of the viewport
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        try:
            if getattr(self, 'coord_label', None):
                self.coord_label.adjustSize()
                w = self.viewport().width()
                lbl_w = self.coord_label.width()
                # 10 px margin from right and 8 px from top
                x = max(0, w - lbl_w - 10)
                self.coord_label.move(x, 8)
        except Exception:
            pass

    def mousePressEvent(self, event):
        """Handle mouse press events for adding detectors and panning.

        If `add_mode` is enabled, left-click (no modifiers) will emit
        `add_detector_requested` with the scene position. Otherwise, default
        behavior (panning, selection) is preserved.
        """
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not event.modifiers()
        ):
            pos = self.mapToScene(event.pos())
            if self.add_mode:
                self.add_detector_requested.emit(pos)
                return
            if self.calibrate_mode:
                self.calibration_point_requested.emit(pos)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Update coordinate label with scene coordinates; if controller has a numeric scale,
        # also show converted meters (meters-per-pixel stored in controller.scale)
        try:
            pos = self.mapToScene(event.pos())
            x = pos.x()
            y = pos.y()
            text = f"X: {x:.1f}, Y: {y:.1f}"
            try:
                ctr = getattr(self, 'controller', None)
                if ctr and isinstance(getattr(ctr, 'scale', None), (int, float)) and float(ctr.scale) > 0:
                    meters_x = x * float(ctr.scale)
                    meters_y = y * float(ctr.scale)
                    text += f"   ({meters_x:.2f} m, {meters_y:.2f} m)"
            except Exception:
                pass
            if getattr(self, 'coord_label', None):
                self.coord_label.setText(text)
                self.coord_label.adjustSize()
                # reposition so it remains top-right
                try:
                    w = self.viewport().width()
                    lbl_w = self.coord_label.width()
                    xmove = max(0, w - lbl_w - 10)
                    self.coord_label.move(xmove, 8)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            super().mouseMoveEvent(event)
        except Exception:
            pass