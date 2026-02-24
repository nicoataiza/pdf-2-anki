"""Anki integration using apy library.

This module provides direct database access to Anki without requiring
AnkiConnect or Anki to be running.
"""

import os
from pathlib import Path

from apyanki.anki import Anki as AnkiCore

from src.flashcards import Flashcard


def _get_anki_base_path() -> str:
    """Get Anki base path from environment or use default."""
    # Check environment variables first (APY_BASE or ANKI_BASE)
    base_path = os.getenv("APY_BASE") or os.getenv("ANKI_BASE")
    if base_path:
        return base_path

    # Try to get from config file
    config_path = Path.home() / ".config" / "apy" / "apy.json"
    if config_path.exists():
        import json

        with open(config_path) as f:
            config = json.load(f)
            if "base_path" in config:
                return config["base_path"]

    # Fall back to default Linux path
    import getpass

    return f"/home/{getpass.getuser()}/.local/share/Anki2/"


def _get_anki_profile() -> str:
    """Get Anki profile name from environment."""
    return os.getenv("ANKI_PROFILE", "default")


class AnkiService:
    """Service for interacting with Anki via apy."""

    def __init__(self) -> None:
        self.base_path = _get_anki_base_path()
        self.profile = _get_anki_profile()

    def get_decks(self) -> list[str]:
        """Get list of all deck names."""
        with AnkiCore(base_path=self.base_path, profile_name=self.profile) as anki:
            return list(anki.deck_names)

    def add_notes(self, deck_name: str, flashcards: list[Flashcard]) -> int:
        """Add flashcards to a deck.

        Args:
            deck_name: Name of the target deck
            flashcards: List of Flashcard objects to add

        Returns:
            Number of notes successfully added
        """
        with AnkiCore(base_path=self.base_path, profile_name=self.profile) as anki:
            # Use "Basic" model (standard note type)
            model_name = "Basic"

            count = 0
            for card in flashcards:
                tags = " ".join(card.tags) if card.tags else ""
                anki.add_notes_single(
                    field_values=[card.front, card.back],
                    markdown=False,
                    tags=tags,
                    model_name_in=model_name,
                    deck=deck_name,
                )
                count += 1

            return count


# Singleton instance
_anki_service: AnkiService | None = None


def get_anki_service() -> AnkiService:
    """Get or create the Anki service singleton."""
    global _anki_service
    if _anki_service is None:
        _anki_service = AnkiService()
    return _anki_service
