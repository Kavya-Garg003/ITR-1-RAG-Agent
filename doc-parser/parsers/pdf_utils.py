import pdfplumber
import re

try:
    import fitz   # PyMuPDF — better for complex layouts
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


def pdf_to_structured_text(pdf_path: str) -> str:
    """
    Converts a PDF into a structured 'Markdown-ish' text format that preserves 
    table relationships, making it much easier for LLMs to process.
    
    Uses BOTH pdfplumber (good for tables) AND PyMuPDF (good for text flow) 
    to maximize extraction coverage. Merges results from both extractors.
    """
    structured_content = []
    
    # ── Method 1: pdfplumber (best for tables) ─────────────────────────────────
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_content = []
                page_content.append(f"--- Page {i+1} ---")
                
                # 1. Extract text with layout preservation hints
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    page_content.append(text)
                
                # 2. Extract text with different settings for fallback
                if not text or len(text.strip()) < 50:
                    text2 = page.extract_text(x_tolerance=5, y_tolerance=5)
                    if text2 and len(text2.strip()) > len((text or "").strip()):
                        page_content.append(text2)
                
                # 3. Extract tables and format as Markdown tables
                tables = page.extract_tables()
                if tables:
                    page_content.append("\n[Tables found on this page]:")
                    for table in tables:
                        if not table or not any(table): 
                            continue
                        
                        # Normalize row lengths
                        max_cols = max(len(row) for row in table if row)
                        
                        # Build Markdown table
                        md_table = []
                        for row_idx, row in enumerate(table):
                            if not row: 
                                continue
                            # Pad row if needed
                            row = list(row) + [""] * (max_cols - len(row))
                            # Clean cells
                            cells = [str(c or "").replace("\n", " ").strip() for c in row]
                            md_table.append("| " + " | ".join(cells) + " |")
                            
                            # Add separator after header
                            if row_idx == 0:
                                md_table.append("| " + " | ".join(["---"] * max_cols) + " |")
                        
                        structured_content.append("\n".join(md_table))
                        structured_content.append("") # Spacer
                
                # 4. Try extracting words with positions for structured data
                try:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    if words and not text:
                        # Group words by line (y position)
                        lines = {}
                        for w in words:
                            y_key = round(w["top"] / 5) * 5  # Group by ~5pt bands
                            if y_key not in lines:
                                lines[y_key] = []
                            lines[y_key].append((w["x0"], w["text"]))
                        
                        # Sort lines and words within lines
                        word_text = []
                        for y in sorted(lines.keys()):
                            line_words = sorted(lines[y], key=lambda x: x[0])
                            word_text.append(" ".join(w[1] for w in line_words))
                        
                        if word_text:
                            page_content.append("\n[Word-level extraction]:\n" + "\n".join(word_text))
                except Exception:
                    pass
                
                structured_content.extend(page_content)
    except Exception as e:
        print(f"pdfplumber extraction error: {e}")
    
    # ── Method 2: PyMuPDF (better text flow for complex layouts) ───────────────
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(pdf_path)
            pymupdf_content = []
            for i, page in enumerate(doc):
                # Standard text extraction
                text = page.get_text("text")
                if text and text.strip():
                    pymupdf_content.append(f"--- Page {i+1} (PyMuPDF) ---\n{text.strip()}")
                
                # Dict-based extraction for structured data
                try:
                    blocks = page.get_text("dict")["blocks"]
                    for block in blocks:
                        if block.get("type") == 0:  # text block
                            for line in block.get("lines", []):
                                line_text = ""
                                for span in line.get("spans", []):
                                    line_text += span.get("text", "")
                                # Look for key-value patterns (label: value)
                                if ":" in line_text and len(line_text) < 200:
                                    pymupdf_content.append(f"  KV: {line_text.strip()}")
                except Exception:
                    pass
            
            doc.close()
            
            # If PyMuPDF extracted significantly more text, add it
            pymupdf_text = "\n\n".join(pymupdf_content)
            plumber_text = "\n\n".join(structured_content)
            
            if len(pymupdf_text) > len(plumber_text) * 0.3:
                structured_content.append("\n\n=== PYMUPDF ENHANCED EXTRACTION ===\n")
                structured_content.extend(pymupdf_content)
        except Exception as e:
            print(f"PyMuPDF extraction error: {e}")
    
    result = "\n\n".join(structured_content)
    
    # ── Method 3: OCR fallback if very little text extracted ───────────────────
    if len(result.strip()) < 200:
        try:
            import pytesseract
            from PIL import Image
            import io
            
            print("[pdf_utils] Very little text extracted, trying OCR...")
            if HAS_PYMUPDF:
                doc = fitz.open(pdf_path)
                ocr_texts = []
                for i in range(min(10, len(doc))):
                    pix = doc[i].get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(img, lang="eng")
                    if ocr_text.strip():
                        ocr_texts.append(f"--- Page {i+1} (OCR) ---\n{ocr_text.strip()}")
                doc.close()
                if ocr_texts:
                    result += "\n\n=== OCR EXTRACTION ===\n" + "\n\n".join(ocr_texts)
        except ImportError:
            print("[pdf_utils] pytesseract not available for OCR fallback")
        except Exception as e:
            print(f"[pdf_utils] OCR fallback error: {e}")
    
    return result
