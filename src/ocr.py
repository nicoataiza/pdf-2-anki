import base64
from dataclasses import dataclass
from pathlib import Path

import fitz
import ollama


@dataclass
class PageContent:
    page_number: int
    text: str


def extract_text_from_pdf(
    pdf_path: str, max_pages: int | None = None
) -> list[PageContent]:
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    client = ollama.Client(host="http://192.168.1.132:11435")

    results = []
    doc = fitz.open(pdf_path)
    total_pages = min(max_pages if max_pages else len(doc), len(doc))

    try:
        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            try:
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")

                response = client.generate(
                    model="ministral-3b-instruct-64k:latest",
                    prompt="Extract all text from this image. Preserve the structure and formatting as much as possible.",
                    images=[img_b64],
                    options={"num_ctx": 32768},
                )

                results.append(
                    PageContent(
                        page_number=page_num + 1,
                        text=response["response"],
                    )
                )
            finally:
                pix = None
                img_bytes = None
                img_b64 = None
    finally:
        doc.close()

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.ocr <pdf_path> [max_pages]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    pages = extract_text_from_pdf(pdf_path, max_pages)

    for page in pages:
        print(f"=== Page {page.page_number} ===")
        print(page.text)
        print()
