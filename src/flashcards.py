import csv
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

import ollama

load_dotenv()


def _get_ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _get_model() -> str:
    return os.getenv("OLLAMA_MODEL", "ministral-3b-instruct-64k:latest")


def _get_num_ctx() -> int:
    return int(os.getenv("OLLAMA_NUM_CTX", "16384"))


BLANK_PHRASES = [
    "completely blank",
    "no discernible text",
    "appears to be blank",
    "does not contain any",
    "no text to extract",
    "appears to contain no",
]

GENERIC_OCR_HEADERS = [
    "here is the extracted text",
    "here's the extracted text",
]


@dataclass
class Flashcard:
    front: str
    back: str
    card_type: str = "basic"
    tags: list[str] = field(default_factory=list)


def is_valid_page(text: str, min_chars: int = 100) -> tuple[bool, str]:
    text_lower = text.lower().strip()

    if len(text_lower) < min_chars:
        return False, f"too short ({len(text_lower)} chars)"

    for phrase in BLANK_PHRASES:
        if phrase in text_lower:
            return False, "blank page"

    text_stripped = text_lower.strip("*#- ")
    for header in GENERIC_OCR_HEADERS:
        if text_stripped == header or text_stripped.startswith(header + "\n"):
            return False, "generic OCR header"

    return True, "valid"


def generate_flashcards(
    pages: list,
    ollama_host: str | None = None,
    min_chars: int = 100,
) -> list[Flashcard]:
    host = ollama_host or _get_ollama_host()
    model = _get_model()
    num_ctx = _get_num_ctx()

    client = ollama.Client(host=host)
    flashcards = []

    for page in pages:
        is_valid, reason = is_valid_page(page.text, min_chars)
        if not is_valid:
            print(f"  Skipping page {page.page_number}: {reason}")
            continue

        prompt = f"""From the following text, create exactly 3 Anki flashcards.

Format each flashcard on its own line as:
Q: [question]
A: [answer]

Keep questions short (under 50 chars) and answers concise (under 100 chars).

Text:
{page.text}

Flashcards:"""

        response = client.generate(
            model=model,
            prompt=prompt,
            options={"num_ctx": num_ctx},
        )

        parsed = _parse_flashcards(response["response"])
        flashcards.extend(parsed)

    return flashcards


def _parse_flashcards(text: str) -> list[Flashcard]:
    flashcards = []
    lines = text.split("\n")
    question = None

    for line in lines:
        line = line.strip()
        if not line or line == "---":
            continue
        if line.startswith("Q:") or line.startswith("q:"):
            question = line[2:].strip()
        elif (line.startswith("A:") or line.startswith("a:")) and question:
            answer = line[2:].strip()
            flashcards.append(Flashcard(front=question, back=answer))
            question = None

    return flashcards


def export_to_anki_csv(flashcards: list[Flashcard], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["front", "back", "card_type", "tags"])
        for card in flashcards:
            tags_str = ",".join(card.tags) if card.tags else ""
            writer.writerow([card.front, card.back, card.card_type, tags_str])


def flashcards_to_dict(flashcards: list[Flashcard]) -> list[dict]:
    return [
        {
            "front": card.front,
            "back": card.back,
            "card_type": card.card_type,
            "tags": card.tags,
        }
        for card in flashcards
    ]


def dict_to_flashcards(data: list[dict]) -> list[Flashcard]:
    return [
        Flashcard(
            front=item["front"],
            back=item["back"],
            card_type=item.get("card_type", "basic"),
            tags=item.get("tags", []),
        )
        for item in data
    ]


if __name__ == "__main__":
    import sys
    from pathlib import Path

    from src.ocr import extract_text_from_pdf

    if len(sys.argv) < 2:
        print("Usage: python -m src.flashcards <pdf_path> [max_pages] [output_csv]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    output_csv = sys.argv[3] if len(sys.argv) > 3 else "flashcards.csv"

    print(f"Extracting text from {pdf_path}...")
    pages = extract_text_from_pdf(pdf_path, max_pages)
    print(f"Extracted {len(pages)} pages")

    print("Generating flashcards...")
    flashcards = generate_flashcards(pages)
    print(f"Generated {len(flashcards)} flashcards")

    export_to_anki_csv(flashcards, output_csv)
    print(f"Exported to {output_csv}")
