from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter

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