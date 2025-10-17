"""Whisper Settings Module for Audio Transcription"""

from dataclasses import dataclass, field
from typing import Dict, Literal

# Type definitions for better IDE support and validation
ModelSize = Literal["tiny", "base", "small", "medium", "large"]


@dataclass
class WhisperSettings:
    """Configuration settings for Whisper audio transcription.

    Attributes:
        model_size: Model size (tiny, base, small, medium, large)
        language: Language code (e.g., 'en', 'es', 'fr')
    """

    model_size: ModelSize = "base"
    language: str = "en"

    # Class-level constants (shared across instances)
    _VALID_SIZES: tuple = field(
        default=("tiny", "base", "small", "medium", "large"), init=False, repr=False
    )

    def __post_init__(self):
        """Validate initial values."""
        self._validate_model_size(self.model_size)

    def _validate_model_size(self, size: str) -> None:
        """Internal validation for model size."""
        if size not in self._VALID_SIZES:
            raise ValueError(
                f"Invalid model size '{size}'. Choose from {self._VALID_SIZES}."
            )

    def set_model_size(self, size: ModelSize) -> None:
        """Set model size with validation."""
        self._validate_model_size(size)
        self.model_size = size

    def set_language(self, lang: str) -> None:
        """Set language code."""
        self.language = lang

    def get_settings(self) -> Dict[str, any]:
        """Return only the user-facing settings."""
        return {"model_size": self.model_size, "language": self.language}

    def update(self, **kwargs) -> None:
        """Update multiple settings at once.

        Example:
            settings.update(model_size="large")
        """
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"Invalid setting: {key}")

            # Use setter methods for validation
            setter = getattr(self, f"set_{key}", None)
            if setter:
                setter(value)
            else:
                setattr(self, key, value)

    @classmethod
    def from_dict(cls, config: Dict[str, any]) -> "WhisperSettings":
        """Create settings from dictionary.

        Example:
            settings = WhisperSettings.from_dict({"model_size": "large"})
        """
        return cls(**config)

    def __repr__(self) -> str:
        """Enhanced string representation."""
        return (
            f"WhisperSettings(model_size='{self.model_size}', "
            f"language='{self.language}')"
        )
