"""Dialog for selecting pages from a PDF file."""
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDialogButtonBox,
    QPushButton,
    QApplication,
    QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from pathlib import Path
from utils import pdf_tools


class PDFPageSelector(QDialog):
    def __init__(self, pdf_path: str, parent=None):
        """Create a dialog for selecting a page from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Select PDF Page")
        self.pdf_path = str(Path(pdf_path))
        
        # Get PDF info
        self.page_count, self.page_dims = pdf_tools.get_pdf_info(self.pdf_path)
        
        # Create and load UI
        self._init_ui()
        self._load_preview()
        
        # Set minimum size
        self.setMinimumSize(900, 600)
        
    def _init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Page selector
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Page:"))
        self.page_combo = QComboBox()
        self.page_combo.addItems([f"Page {i+1} ({w}x{h}px)" 
                                for i, (w,h) in enumerate(self.page_dims)])
        self.page_combo.currentIndexChanged.connect(self._load_preview)
        page_layout.addWidget(self.page_combo)
        page_layout.addStretch()
        layout.addLayout(page_layout)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(QSize(800, 400))
        self.preview_label.setFrameStyle(QFrame.Shape.Box)
        self.preview_label.setText("Loading preview...")
        layout.addWidget(self.preview_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _load_preview(self):
        """Load the preview image for the current page."""
        try:
            # Show "loading" message and process events to update UI
            self.preview_label.setText("Loading preview...")
            QApplication.processEvents()
            
            # Get the preview image
            page_num = self.page_combo.currentIndex()
            png_data = pdf_tools.create_preview_image(self.pdf_path, page_num)
            
            # Create and display pixmap
            pixmap = QPixmap()
            pixmap.loadFromData(png_data)
            
            # Scale to fit preview area if needed
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
        except Exception as e:
            self.preview_label.setText(f"Error loading preview: {e}")
    
    def get_selected_page(self) -> int:
        """Get the currently selected page number (0-based)."""
        return self.page_combo.currentIndex()