import pytest
import os
from src.pipelines.load_pdfs import load_pdfs

def test_load_pdfs_success(tmp_path):
    """
    Test that PDFs are correctly loaded and text is extracted.
    """
    # 1. Setup: Create a temporary PDF for testing
    # Note: In a real scenario, you'd use a small sample PDF from your data/pdfs folder
    from reportlab.pdfgen import canvas
    pdf_path = tmp_path / "test_rules.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "IWF Rule 1: Clean and Jerk must be performed.")
    c.save()
    
    pdf_folder = tmp_path
    
    # 2. Execute
    docs = load_pdfs(str(pdf_folder))
    
    # 3. Assert
    assert len(docs) == 1
    assert "IWF Rule 1" in docs[0]["text"]
    assert docs[0]["metadata"]["source"] == "test_rules.pdf"
    assert docs[0]["metadata"]["page"] == 1
