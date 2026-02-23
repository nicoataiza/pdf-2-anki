# AGENTS.md - Agentic Coding Guidelines for pdf-2-anki

## Project Overview

Python project for extracting text from PDFs using OCR (via Ollama) and generating Anki flashcards. Uses `uv` for dependency management, Python 3.11+.

## Development Environment

- **Python**: 3.11+
- **Package Manager**: uv
- **Virtual Environment**: `.venv/`
- **Activate**: `source .venv/bin/activate` or use `uv run`

## Build, Lint, and Test Commands

### Running the Application

```bash
uv run python -m src.ocr <pdf_path> [max_pages]

# Example
uv run python -m src.ocr ./cses.pdf 5
```

### Adding Development Dependencies

```bash
uv add --dev ruff       # linting + formatting
uv add --dev pytest     # testing
```

### Running Tests (once configured)

```bash
uv run pytest                              # all tests
uv run pytest tests/test_ocr.py           # single file
uv run pytest tests/test_ocr.py::test_foo  # single function
uv run pytest -k "test_ocr"               # pattern match
```

### Linting and Formatting

```bash
uv run ruff check src/   # linter
uv run ruff format src/  # formatter
```

## Code Style Guidelines

### Imports

```python
# Standard library first
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Third-party (alphabetical)
import fitz
import ollama

# Local imports last
from src.ocr import extract_text_from_pdf
```

### Type Hints

Use modern Python 3.11+ syntax:
- `str | None` instead of `Optional[str]`
- `list[...]`, `dict[...]` instead of `List[...]`, `Dict[...]`
- Always type hint parameters and return values

### Naming Conventions

- **Classes**: PascalCase (`PageContent`, `OllamaClient`)
- **Functions/variables**: snake_case (`extract_text_from_pdf`)
- **Constants**: SCREAMING_SNAKE_CASE (`MAX_PAGE_SIZE`)
- **Private functions**: underscore prefix (`_internal_helper`)

### Data Classes

```python
@dataclass
class PageContent:
    page_number: int
    text: str
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Avoid bare except clauses

```python
if not Path(pdf_path).exists():
    raise FileNotFoundError(f"PDF not found: {pdf_path}")
```

### Functions

- Keep functions small and focused
- Use descriptive names
- Prefer early returns for error cases

```python
def extract_text_from_pdf(pdf_path: str, max_pages: int | None = None) -> list[PageContent]:
    """Extract text from PDF using OCR."""
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    # Main logic...
```

### Code Formatting

- Max line length: 88 characters
- 4 spaces for indentation (no tabs)
- Trailing commas in multi-line collections
- Use parentheses for line continuation

### File Structure

```
pdf-2-anki/
├── src/
│   ├── __init__.py      # Package exports
│   └── ocr.py           # Main OCR functionality
├── tests/
│   └── test_ocr.py      # Unit tests
├── pyproject.toml       # Project config
├── uv.lock              # Locked dependencies
└── README.md            # Project documentation
```

### Testing Guidelines (when added)

- Use `pytest`
- Place tests in `tests/` directory
- Name test files `test_<module>.py`
- Follow AAA pattern: Arrange, Act, Assert

```python
def test_extract_text_returns_list():
    result = extract_text_from_pdf("test.pdf")
    assert isinstance(result, list)
    assert len(result) > 0
```

### Git Practices

- Write meaningful commit messages
- Keep commits atomic and focused
- Run linting before committing
- Never commit secrets or credentials

### Dependencies

- Keep dependencies minimal
- Pin critical dependencies in pyproject.toml
- Use version constraints: `package>=1.0,<2.0`

## Common Tasks

```bash
uv sync                              # install dependencies
source .venv/bin/activate           # activate venv
python -m src.ocr ./document.pdf    # run application
uv add package_name                 # add dependency
uv add --dev package_name           # add dev dependency
```

## Notes for Agents

- Small project with minimal tooling
- OCR extraction using Ollama
- No complex framework - pure Python
- Start simple, avoid over-engineering
- Verify changes work before submitting
