# PDF to Anki

Generate Anki flashcards from PDFs using OCR (Ollama) and export to Anki.

## Features

- Upload PDF files
- OCR text extraction using Ollama
- AI-powered flashcard generation
- Export to CSV or add directly to Anki via AnkiConnect

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) running with a vision model (e.g., `ministral-3b-instruct-64k`)
- [Anki](https://apps.ankiweb.net/) desktop app (optional, for AnkiConnect)

## Installation

```bash
# Clone the repository
cd pdf-2-anki

# Install dependencies
uv sync
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model to use | `ministral-3b-instruct-64k:latest` |
| `OLLAMA_NUM_CTX` | Context window size | `32768` |
| `MAX_PAGES` | Max pages to process (empty = all) | (empty) |
| `FLASK_SECRET_KEY` | Secret key for sessions | (auto-generated) |
| `FLASK_HOST` | Host to bind to | `0.0.0.0` |
| `FLASK_PORT` | Port to run on | `5000` |
| `ANKICONNECT_HOST` | AnkiConnect URL | `http://localhost:8765` |

## Running the App

### Web UI

```bash
uv run python -m src.app
```

Access at `http://localhost:5000` or `http://<your-pi-ip>:5000` from network devices.

### Command Line

```bash
# Extract text from PDF
uv run python -m src.ocr <pdf_path> [max_pages]

# Generate flashcards
uv run python -m src.flashcards <pdf_path> [max_pages] [output_csv]
```

## AnkiConnect Setup (Optional)

To add cards directly to Anki:

1. Open Anki desktop app
2. Go to **Tools > Add-ons > Get Add-ons...**
3. Enter code: `2055492159`
4. Restart Anki
5. Keep Anki running while using the web app

## Usage

1. Open the web UI
2. Upload a PDF file
3. Wait for OCR processing (may take a while)
4. Review generated flashcards, select/deselect
5. Export:
   - Download CSV for manual import
   - Or use AnkiConnect to add directly to Anki

## File Structure

```
pdf-2-anki/
├── src/
│   ├── __init__.py
│   ├── ocr.py           # PDF text extraction
│   ├── flashcards.py     # Flashcard generation
│   ├── app.py           # Flask web app
│   └── templates/
│       └── index.html   # Web UI
├── tests/
├── .env                 # Local config (gitignored)
├── .env.example         # Config template
├── pyproject.toml
└── uv.lock
```

## Development

```bash
# Install dev dependencies
uv add --dev ruff pytest

# Run linter
uv run ruff check src/

# Run formatter
uv run ruff format src/
```
