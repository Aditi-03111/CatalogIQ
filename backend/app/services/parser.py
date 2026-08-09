import uuid
import os
import tempfile
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_content: bytes) -> Dict[str, Any]:
        """
        Parses document binary content and returns a structured intermediate representation.
        """
        pass

class DoclingParser(DocumentParser):
    def __init__(self):
        # Force docling import to fail clearly at runtime if unavailable
        try:
            import docling
            from docling.document_converter import DocumentConverter
            self._converter_class = DocumentConverter
            self.version = docling.__version__
        except ImportError as e:
            logger.error("Docling library not available at runtime.")
            raise ImportError(
                "Docling library is not installed or available at runtime. "
                "Ensure 'docling' is listed in requirements and installed."
            ) from e

    def parse(self, file_content: bytes) -> Dict[str, Any]:
        # Write binary stream to a temporary local file for Docling parser access
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            converter = self._converter_class()
            result = converter.convert(tmp_path)
            doc = result.document

            pages: List[Dict[str, Any]] = []
            if hasattr(doc, "num_pages"):
                page_count = doc.num_pages() if callable(doc.num_pages) else doc.num_pages
            else:
                page_count = 1
            
            # Pre-initialize page mappings
            for page_idx in range(1, page_count + 1):
                pages.append({
                    "page_number": page_idx,
                    "text": "",
                    "tables": [],
                    "images": []
                })

            # Process layout elements and associate them with correct page boundaries
            for element, level in doc.iterate_items():
                page_no = 1
                if hasattr(element, "prov") and element.prov:
                    page_no = element.prov[0].page_no if hasattr(element.prov[0], "page_no") else 1
 
                # Ensure page bounds in pages array
                if page_no > len(pages):
                    while len(pages) < page_no:
                        pages.append({
                            "page_number": len(pages) + 1,
                            "text": "",
                            "tables": [],
                            "images": []
                        })
                
                page_data = pages[page_no - 1]
 
                # Check element classes (handling Docling V2 standard classes)
                class_name = element.__class__.__name__
                
                if "Table" in class_name:
                    headers = []
                    rows = []
                    try:
                        df = element.export_to_dataframe(doc)
                        headers = [str(col) for col in df.columns]
                        rows = [[str(val) for val in row] for row in df.values.tolist()]
                    except Exception as df_err:
                        logger.warning(f"export_to_dataframe failed, falling back to manual cell parsing: {df_err}")
                        grid = getattr(element, "data", None)
                        if grid and hasattr(grid, "table_cells"):
                            from collections import defaultdict
                            row_cells = defaultdict(list)
                            for cell in grid.table_cells:
                                row_cells[cell.start_row_offset_idx].append(cell)
                            for r_idx in sorted(row_cells.keys()):
                                sorted_cells = sorted(row_cells[r_idx], key=lambda c: c.start_col_offset_idx)
                                row_vals = [c.text for c in sorted_cells]
                                if r_idx == 0:
                                    headers = row_vals
                                else:
                                    rows.append(row_vals)
                    page_data["tables"].append({
                        "headers": headers,
                        "rows": rows
                    })
                elif "Picture" in class_name or "Image" in class_name:
                    page_data["images"].append({
                        "image_id": str(uuid.uuid4()),
                        "page_number": page_no,
                        "label": getattr(element, "label", "image")
                    })
                else:
                    text_val = getattr(element, "text", "")
                    if text_val:
                        page_data["text"] += (text_val + "\n")

            return {
                "pages": pages,
                "metadata": {
                    "page_count": len(pages),
                    "title": getattr(doc, "title", None) or "Technical Specification Sheet"
                }
            }

        except Exception as e:
            import traceback
            logger.error(f"Error during Docling parsing: {e}\n{traceback.format_exc()}")
            raise e
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

class MockParser(DocumentParser):
    def __init__(self):
        self.version = "1.0.0"

    def parse(self, file_content: bytes) -> Dict[str, Any]:
        """
        Mock implementation explicitly injected for tests (simulating a 2-page spec).
        """
        # Quick validation check on magic bytes to verify validation triggers in tests
        if not file_content.startswith(b"%PDF"):
            raise ValueError("Invalid PDF magic bytes")

        return {
            "pages": [
                {
                    "page_number": 1,
                    "text": "Industrial Motor\nModel: MX-500\nSKU: MX500-230\n",
                    "tables": [],
                    "images": []
                },
                {
                    "page_number": 2,
                    "text": "Specifications\n",
                    "tables": [
                        {
                            "headers": ["Specification", "Value"],
                            "rows": [
                                ["Voltage", "230 V"],
                                ["Power", "5.5 kW"],
                                ["Speed", "1440 RPM"],
                                ["Weight", "32 kg"]
                            ]
                        }
                    ],
                    "images": [
                        {
                            "image_id": "mock-img-123",
                            "page_number": 2,
                            "label": "motor_wiring"
                        }
                    ]
                }
            ],
            "metadata": {
                "page_count": 2,
                "title": "Industrial Motor Specs"
            }
        }
