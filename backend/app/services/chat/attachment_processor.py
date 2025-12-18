from typing import List, Dict, Any
from app.schemas.chat import Attachment
from app.utils.pdf_utils import extract_text_from_base64_pdf
import asyncio


class AttachmentProcessor:
    async def process_attachments(self, attachments: List[Attachment]) -> List[Dict[str, Any]]:
        processed_parts: List[Dict[str, Any]] = []

        for att in attachments:
            name = (att.name or "").strip()

            if att.type == "application/pdf" or name.lower().endswith(".pdf"):
                extracted_text = await asyncio.to_thread(extract_text_from_base64_pdf, att.content)
                # Max 20k chars per pdf
                if len(extracted_text) > 20000:
                    extracted_text = extracted_text[:20000] + "... [TRUNCATED]"
                
                processed_parts.append({
                    "type": "text",
                    "text": f"--- Document Content: {name or 'document.pdf'} ---\n{extracted_text}\n--- End Document ---"
                })

            elif att.type and att.type.startswith("image"):
                url = att.content or ""
                if not url.startswith("http") and not url.startswith("data:"):
                    url = f"data:{att.type};base64,{url}"

                processed_parts.append({
                    "type": "image_url",
                    "image_url": {"url": url},
                    "mime_type": att.type
                })

            else:
                processed_parts.append({
                    "type": "text",
                    "text": att.content or ""
                })

        return processed_parts
