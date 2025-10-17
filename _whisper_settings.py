"""Whisper Settings Module for Audio Transcription"""

from dataclasses import asdict, dataclass, field
from typing import Dict, Literal

# Type definitions for better IDE support and validation
ModelSize = Literal["tiny", "base", "small", "medium", "large"]
TaskType = Literal["transcribe", "translate"]


@dataclass
class WhisperSettings:
    """Configuration settings for Whisper audio transcription.

    Attributes:
        model_size: Model size (tiny, base, small, medium, large)
        language: Language code (e.g., 'en', 'es', 'fr')
        task: Task type (transcribe or translate)
        temperature: Sampling temperature (0.0-1.0)
    """

    model_size: ModelSize = "base"
    language: str = "en"
    task: TaskType = "transcribe"
    temperature: float = 0.0

    # Class-level constants (shared across instances)
    _VALID_SIZES: tuple = field(
        default=("tiny", "base", "small", "medium", "large"), init=False, repr=False
    )
    _VALID_TASKS: tuple = field(
        default=("transcribe", "translate"), init=False, repr=False
    )
    _TEMP_MIN: float = field(default=0.0, init=False, repr=False)
    _TEMP_MAX: float = field(default=1.0, init=False, repr=False)

    def __post_init__(self):
        """Validate initial values."""
        self._validate_model_size(self.model_size)
        self._validate_task(self.task)
        self._validate_temperature(self.temperature)

    def _validate_model_size(self, size: str) -> None:
        """Internal validation for model size."""
        if size not in self._VALID_SIZES:
            raise ValueError(
                f"Invalid model size '{size}'. Choose from {self._VALID_SIZES}."
            )

    def _validate_task(self, task: str) -> None:
        """Internal validation for task type."""
        if task not in self._VALID_TASKS:
            raise ValueError(f"Invalid task '{task}'. Choose from {self._VALID_TASKS}.")

    def _validate_temperature(self, temp: float) -> None:
        """Internal validation for temperature."""
        if not (self._TEMP_MIN <= temp <= self._TEMP_MAX):
            raise ValueError(
                f"Temperature must be between {self._TEMP_MIN} and {self._TEMP_MAX}."
            )

    def set_model_size(self, size: ModelSize) -> None:
        """Set model size with validation."""
        self._validate_model_size(size)
        self.model_size = size

    def set_language(self, lang: str) -> None:
        """Set language code."""
        self.language = lang

    def set_task(self, task: TaskType) -> None:
        """Set task type with validation."""
        self._validate_task(task)
        self.task = task

    def set_temperature(self, temp: float) -> None:
        """Set temperature with validation."""
        self._validate_temperature(temp)
        self.temperature = temp

    def get_settings(self) -> Dict[str, any]:
        """Return settings as dictionary."""
        return asdict(self)

    def update(self, **kwargs) -> None:
        """Update multiple settings at once.

        Example:
            settings.update(model_size="large", temperature=0.2)
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
            f"language='{self.language}', task='{self.task}', "
            f"temperature={self.temperature})"
        )
