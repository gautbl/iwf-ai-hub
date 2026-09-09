import os
import structlog
from PyPDF2 import PdfReader
from typing import List, Dict

logger = structlog.get_logger()

def load_pdfs(pdf_folder: str) -> List[Dict[str, any]]:
    """
    Reads all PDF files in a given folder and extracts their text 
    along with basic metadata.
    
    Args:
        pdf_folder (str): Path to the directory containing IWF PDFs.
        
    Returns:
        List[Dict]: A list of dictionaries containing 'text' and 'metadata'.
    """
    documents = []
    
    if not os.path.exists(pdf_folder):
        raise FileNotFoundError(f"The directory {pdf_folder} does not exist.")

    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_folder, filename)
            try:
                reader = PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        # We store metadata to allow the agent to cite sources
                        documents.append({
                            "text": text,
                            "metadata": {
                                "source": filename,
                                "page": i + 1
                            }
                        })
            except Exception as e:
                logger.warning("pdf_processing_error", filename=filename, error=str(e))
                
    return documents
