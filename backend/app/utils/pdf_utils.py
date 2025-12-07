import base64
import io
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def extract_text_from_base64_pdf(base64_content: str) -> str:
    """
    Decodes a base64 string to a PDF file and extracts text from all pages.
    """
    try:
        # Check if header exists and strip it
        if "," in base64_content:
            header, encoded = base64_content.split(",", 1)
        else:
            encoded = base64_content

        pdf_bytes = base64.b64decode(encoded)
        pdf_file = io.BytesIO(pdf_bytes)
        
        reader = PdfReader(pdf_file)
        text_content = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_content.append(text)
        
        full_text = "\n\n".join(text_content)
        return full_text
    
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return f"[Error processing PDF: {str(e)}]"
