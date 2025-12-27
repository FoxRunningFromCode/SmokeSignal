"""Utility functions for handling PDF files."""
import fitz  # PyMuPDF
import io
from typing import List, Tuple
from PIL import Image
from pathlib import Path


def get_pdf_info(pdf_path: str) -> Tuple[int, List[Tuple[int, int]]]:
    """Get page count and dimensions of a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Tuple containing:
            - Number of pages
            - List of (width, height) tuples in pixels for each page
    """
    # Paper size mappings (in points)
    PAPER_SIZES = {
    "A0": (2384, 3370),
    "A1": (1684, 2384),
    "A2": (1191, 1684),
    "A3": (842, 1191),
    "A4": (595, 842),
    "A5": (420, 595),
    }
    
    doc = fitz.open(pdf_path)
    try:
        dims = []
        for i, page in enumerate(doc):
            rect = page.rect
            width_px = int(rect.width)
            height_px = int(rect.height)
            dims.append((width_px, height_px))
            
            # Determine paper size
            paper_size = "Unknown"
            for size_name, (w, h) in PAPER_SIZES.items():
                if (abs(rect.width - w) < 5 and abs(rect.height - h) < 5) or \
                   (abs(rect.width - h) < 5 and abs(rect.height - w) < 5):
                    paper_size = size_name
                    break
            
            print(f"Page {i+1}: {width_px}x{height_px} pixels ({paper_size})")
        
        return len(doc), dims
    finally:
        doc.close()


def pdf_page_to_pixmap(pdf_path: str, page_num: int, dpi: int = 300) -> bytes:
    """Convert a PDF page to a PNG image at the specified DPI.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Zero-based page number to convert
        dpi: Resolution for the output image (default 300)
        
    Returns:
        PNG image data as bytes
    """
    zoom = dpi / 72  # standard PDF dpi
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        
        # Convert pixmap to PNG bytes
        return pix.tobytes("png")
    finally:
        doc.close()


def create_preview_image(pdf_path: str, page_num: int, target_width: int = 800) -> bytes:
    """Create a lower resolution preview image of a PDF page.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Zero-based page number to convert
        target_width: Desired width of preview in pixels
        
    Returns:
        PNG image data as bytes
    """
    # First get a medium resolution version
    png_data = pdf_page_to_pixmap(pdf_path, page_num, dpi=150)
    
    # Load into PIL for resizing
    img = Image.open(io.BytesIO(png_data))
    
    # Calculate height to maintain aspect ratio
    aspect = img.height / img.width
    target_height = int(target_width * aspect)
    
    # Resize 
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Convert back to PNG bytes
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()