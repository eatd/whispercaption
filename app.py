#!/usr/bin/env python3
"""
Realtime captions overlay from VB-Audio Cable → Whisper → on-screen text.
"""

import argparse
import logging
import queue
import signal
import sys
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
import torch
from faster_whisper import WhisperModel
from pynput import keyboard
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


@dataclass(frozen=True)
class Config:
    sample_rate: int = 16000
    block_seconds: float = 1.0
    model_size: str = "small"
    language: str = "en"
    task: str = "transcribe"
    audio_queue_size: int = 8
    text_queue_size: int = 4
    control_queue_size: int = 2
    gui_poll_interval_ms: int = 50
    max_buffer_seconds: int = 10
    beam_size: int = 1
    temperature: float = 0.0
    vad_filter: bool = False

    @property
    def block_samples(self) -> int:
        return int(self.sample_rate * self.block_seconds)

    @property
    def max_buffer_samples(self) -> int:
        return self.block_samples * self.max_buffer_seconds


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def find_vb_audio_device() -> Optional[int]:
    """Find VB-Audio Cable input device index or None for default."""
    try:
        for idx, dev in enumerate(sd.query_devices()):
            name = dev.get("name", "").upper()
            if ("VB-AUDIO" in name or "CABLE" in name) and dev.get(
                "max_input_channels", 0
            ) > 0:
                logging.info(f"Found VB-Audio device: {dev['name']} (index {idx})")
                return idx
    except Exception as e:
        logging.error(f"Error querying devices: {e}")
    logging.warning("VB-Audio device not found, using default input")
    return None


def open_stream(config: Config, callback) -> sd.InputStream:
    """Open audio stream with optional WASAPI loopback on Windows."""
    device_idx = find_vb_audio_device()
    extra = None
    if sys.platform.startswith("win") and hasattr(sd, "WasapiSettings"):
        try:
            extra = sd.WasapiSettings(loopback=True)
            logging.info("Using WASAPI loopback mode")
        except Exception:
            logging.debug("WASAPI loopback not available")
    try:
        return sd.InputStream(
            device=device_idx,
            samplerate=config.sample_rate,
            channels=2,
            dtype="float32",
            callback=callback,
            blocksize=config.block_samples,
            extra_settings=extra,
        )
    except Exception as e:
        logging.critical(f"Failed to open audio stream: {e}")
        raise


class TranscriberThread(threading.Thread):
    """Worker thread for whisper transcription."""

    def __init__(
        self,
        config: Config,
        audio_queue: queue.Queue,
        text_queue: queue.Queue,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.config = config
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self.stop_event = stop_event
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Prefer lower-memory compute types when on CUDA; will fallback further if needed
        self.compute_type = "int8_float16" if self.device == "cuda" else "int8"
        self.model: Optional[WhisperModel] = None

    def run(self):
        # Try to load the model with a fallback sequence to avoid CUDA OOM
        load_attempts = []
        if self.device == "cuda":
            load_attempts.extend(
                [
                    ("cuda", "int8_float16"),
                    ("cuda", "int8"),
                    ("cuda", "float16"),
                ]
            )
        load_attempts.append(("cpu", "int8"))

        loaded = False
        for dev, ctype in load_attempts:
            try:
                logging.info(
                    f"Loading Whisper model '{self.config.model_size}' on {dev} ({ctype})"
                )
                self.model = WhisperModel(
                    self.config.model_size,
                    device=dev,
                    compute_type=ctype,
                )
                self.device = dev
                self.compute_type = ctype
                # Warm up with 1D mono silence to prime kernels and reduce first-run latency
                self.model.transcribe(
                    np.zeros(self.config.block_samples, dtype=np.float32),
                    beam_size=1,
                    language=self.config.language,
                    task=self.config.task,
                    temperature=self.config.temperature,
                    vad_filter=False,
                )
                logging.info("Whisper model loaded and warmed up")
                loaded = True
                break
            except Exception as e:
                logging.warning(f"Model load failed on {dev}/{ctype}: {e}")

        if not loaded:
            logging.error("All model load attempts failed; exiting")
            self.stop_event.set()
            return

        # 1D mono audio buffer
        buffer = np.empty((0,), dtype=np.float32)
        while not self.stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # Append to 1D buffer
            buffer = np.concatenate((buffer, chunk))
            if buffer.shape[0] > self.config.max_buffer_samples:
                buffer = buffer[-self.config.max_buffer_samples :]
            while buffer.shape[0] >= self.config.block_samples:
                segment = buffer[: self.config.block_samples]
                buffer = buffer[self.config.block_samples :]
                self._transcribe_segment(segment)
                self.audio_queue.task_done()

    def _transcribe_segment(self, segment: np.ndarray):
        try:
            # Ensure mono 1D float32
            if segment.ndim > 1:
                segment = segment.mean(axis=1)
            segment = segment.astype(np.float32, copy=False)
            segments, _ = self.model.transcribe(
                segment,
                beam_size=self.config.beam_size,
                language=self.config.language,
                task=self.config.task,
                temperature=self.config.temperature,
                vad_filter=self.config.vad_filter,
            )
            text = " ".join(s.text for s in segments).strip()
            if text:
                try:
                    self.text_queue.put_nowait(text)
                except queue.Full:
                    logging.debug("Text queue full; dropping snippet")
        except Exception as e:
            logging.warning(f"Transcription error: {e}")


class Overlay(QWidget):
    """Translucent on-screen subtitle overlay."""

    def __init__(
        self, text_queue: queue.Queue, control_queue: queue.Queue, cfg: Config
    ):
        super().__init__()
        self.text_queue = text_queue
        self.control_queue = control_queue
        self.cfg = cfg
        self._buffer = ""
        self._drag_offset = None
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.label = QLabel("Listening…", self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.label.font()
        font.setPointSize(22)
        font.setWeight(600)
        self.label.setFont(font)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(16, 12, 16, 12)

        self.setObjectName("overlay")
        self.setStyleSheet(
            "#overlay { background: rgba(0,0,0,120); border:2px solid white; border-radius:12px; }"
            "QLabel { color:white; background:transparent; }"
        )
        self.resize(800, 120)
        self.move(100, 50)

    def _setup_timer(self):
        timer = QTimer(self)
        timer.timeout.connect(self._on_tick)
        timer.start(self.cfg.gui_poll_interval_ms)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e):
        if self._drag_offset and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        self._drag_offset = None

    def _on_tick(self):
        try:
            while not self.control_queue.empty():
                cmd = self.control_queue.get_nowait()
                if cmd == "toggle":
                    self.setVisible(not self.isVisible())
        except queue.Empty:
            pass

        # Append incoming snippets to buffer; flush on sentence end punctuation.
        try:
            while not self.text_queue.empty():
                snippet = self.text_queue.get_nowait().strip()
                self._buffer = f"{self._buffer} {snippet}".strip()
                if snippet.endswith((".", "?", "!")):
                    self.label.setText(self._buffer)
                    self._buffer = ""
                else:
                    self.label.setText(self._buffer)
        except queue.Empty:
            pass


def start_hotkey_listener(control_queue: queue.Queue):
    """Global hotkey Ctrl+Shift+C to toggle overlay."""
    combo = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.KeyCode.from_char("c")}
    pressed = set()
    fired = False

    def on_press(k):
        nonlocal fired
        pressed.add(k)
        if not fired and combo.issubset(pressed):
            fired = True
            try:
                control_queue.put_nowait("toggle")
            except queue.Full:
                pass

    def on_release(k):
        nonlocal fired
        pressed.discard(k)
        if fired and not combo.issubset(pressed):
            fired = False

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
    listener.start()
    logging.info("Hotkey Ctrl+Shift+C registered")


def audio_callback(indata, status, audio_queue: queue.Queue):
    """Queue incoming audio frames for transcription."""
    if status:
        logging.warning(f"Audio status: {status}")
    try:
        # Convert to mono 1D float32 early to reduce downstream memory
        if indata.ndim > 1:
            mono = indata.mean(axis=1)
        else:
            mono = indata
        audio_queue.put_nowait(mono.astype(np.float32, copy=False).copy())
    except queue.Full:
        logging.debug("Audio queue full; dropping frame")


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Realtime Whisper captions overlay")
    parser.add_argument(
        "--list-devices", action="store_true", help="List audio devices and exit"
    )
    args = parser.parse_args()

    cfg = Config()
    if args.list_devices:
        print(sd.query_devices())
        sys.exit(0)

    audio_q = queue.Queue(maxsize=cfg.audio_queue_size)
    text_q = queue.Queue(maxsize=cfg.text_queue_size)
    control_q = queue.Queue(maxsize=cfg.control_queue_size)
    stop_evt = threading.Event()

    signal.signal(signal.SIGINT, lambda *_: stop_evt.set())
    signal.signal(signal.SIGTERM, lambda *_: stop_evt.set())

    transcriber = TranscriberThread(cfg, audio_q, text_q, stop_evt)
    transcriber.start()

    stream = open_stream(
        cfg,
        lambda indata, frames, time, status: audio_callback(indata, status, audio_q),
    )
    stream.start()

    app = QApplication(sys.argv)
    overlay = Overlay(text_q, control_q, cfg)
    overlay.show()

    start_hotkey_listener(control_q)
    logging.info("Overlay started. Drag to move. Ctrl+Shift+C toggles display.")

    try:
        sys.exit(app.exec())
    finally:
        stop_evt.set()
        stream.stop()
        stream.close()
        logging.info("Audio stream closed")


if __name__ == "__main__":
    main()
