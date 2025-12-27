from PyQt6.QtWidgets import QGraphicsView, QLabel
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QFont, QColor

class FloorPlanView(QGraphicsView):
    # Emitted when the user requests adding a detector; sends a QPointF (scene coordinates)
    add_detector_requested = pyqtSignal(object)
    # Emitted when the user clicks a point in calibration mode
    calibration_point_requested = pyqtSignal(object)
    # Emitted when the user clicks a point while in measure mode
    measure_point_requested = pyqtSignal(object)
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
        # If True, clicking will register measure points
        self.measure_mode = False

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

    def set_measure_mode(self, enabled: bool):
        """Enable or disable measure mode and update cursor."""
        self.measure_mode = bool(enabled)
        try:
            if self.measure_mode:
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                # restore default cursor
                self.unsetCursor()
        except Exception:
            pass
        
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
            if self.measure_mode:
                # emit measure point and let controller handle drawing
                self.measure_point_requested.emit(pos)
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

    def drawForeground(self, painter, rect):
        """Draw overlay elements such as the scale legend in the top-right corner."""
        try:
            super().drawForeground(painter, rect)
        except Exception:
            pass

        try:
            ctr = getattr(self, 'controller', None)
            if not ctr or not getattr(ctr, 'show_scale_legend', False):
                return

            # Save painter state and work in device coordinates for consistent sizing
            painter.save()
            painter.resetTransform()

            vw = self.viewport().width()
            margin = 10
            max_width = 140  # max pixel length for largest segment
            # scale legend area
            bg_w = max_width + 2 * margin
            bg_h = 90
            # ensure we stay within the viewport even if it's smaller than the legend
            x0 = max(margin, vw - bg_w - margin)
            y0 = 8

            # background (semi-transparent white)
            painter.setOpacity(0.95)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.drawRoundedRect(x0, y0, bg_w, bg_h, 6, 6)
            painter.setOpacity(1.0)

            # Text header
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(x0 + margin, y0 + 16, "Scale")

            # Prepare values to show
            lengths_m = [0.5, 1.0, 2.0, 5.0]
            ppm = None
            scaled_flag = False
            try:
                if isinstance(getattr(ctr, 'scale', None), (int, float)) and float(ctr.scale) > 0:
                    # pixels-per-meter in SCENE coordinates
                    pixels_per_meter_scene = 1.0 / float(ctr.scale)
                else:
                    pixels_per_meter_scene = None
            except Exception:
                pixels_per_meter_scene = None

            # Draw each bar with label
            y_bar_start = y0 + 28
            for i, lm in enumerate(lengths_m):
                label = f"{lm:g} m"

                # Compute scene-length in scene pixels (scene coords)
                if pixels_per_meter_scene:
                    scene_len = lm * pixels_per_meter_scene
                    # Convert scene length to device (viewport) pixels using mapFromScene
                    try:
                        p0 = self.mapFromScene(QPointF(0, 0))
                        p1 = self.mapFromScene(QPointF(scene_len, 0))
                        px_len = abs(p1.x() - p0.x())
                    except Exception:
                        px_len = None
                else:
                    px_len = None

                if px_len is None:
                    # fallback: relative sizing to max width
                    px_len = max_width * (lm / max(lengths_m)) * 0.6
                else:
                    # ensure it fits in the legend area
                    if px_len > max_width:
                        scale_factor = max_width / px_len
                        px_len = px_len * scale_factor
                        scaled_flag = True

                bx = x0 + margin
                by = y_bar_start + i * 18
                # Draw line
                pen = painter.pen()
                pen.setWidth(3)
                painter.setPen(pen)
                painter.drawLine(bx, by + 8, bx + int(px_len), by + 8)
                # Draw end ticks
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawLine(bx, by + 4, bx, by + 12)
                painter.drawLine(bx + int(px_len), by + 4, bx + int(px_len), by + 12)

                # Label to the right
                font2 = painter.font()
                font2.setPointSize(8)
                font2.setBold(False)
                painter.setFont(font2)
                painter.drawText(bx + int(px_len) + 6, by + 11, label)

            # If we had to scale, indicate scaled legend
            if scaled_flag:
                font3 = painter.font()
                font3.setPointSize(7)
                painter.setFont(font3)
                painter.drawText(x0 + margin, y_bar_start + len(lengths_m) * 18 + 6, "(scaled to fit)")

            if pixels_per_meter_scene is None:
                font4 = painter.font()
                font4.setPointSize(8)
                painter.setFont(font4)
                painter.drawText(x0 + margin, y_bar_start + len(lengths_m) * 18 + 22, "No numeric scale")

            painter.restore()
        except Exception:
            pass