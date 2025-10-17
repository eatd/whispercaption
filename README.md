# WhisperCaption

Realtime caption overlay that routes system audio through VB-Audio Cable, transcribes it with [faster-whisper](https://github.com/guillaumekln/faster-whisper), and renders subtitles in a translucent PyQt window.

## Highlights
- Uses VB-Audio Cable (or any loopback-capable input) to capture system audio.
- Streams audio into a background Whisper worker with smart GPU/CPU fallbacks.
- Displays live captions in a draggable, always-on-top overlay with hotkey toggle.
- Includes a `tkinter` playground overlay and a PowerShell helper for installing VB-Cable.

## Requirements
- Python 3.10 or newer (PyQt6 wheels require modern Python on Windows/macOS/Linux).
- Optional: NVIDIA GPU with CUDA for fastest transcription; falls back to CPU.
- VB-Audio Cable or another virtual audio device if you want to capture system audio.

Install the Python dependencies:

```pwsh
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install pynput
```

## Capturing System Audio

1. Install VB-Audio Cable (or your preferred virtual audio driver).
	- Run PowerShell as Administrator and execute `powershell -ExecutionPolicy Bypass -File install_vb_cable.ps1`.
	- Reboot when prompted so the virtual device appears.
2. Set the system default playback device to your speakers and the default recording device to `CABLE Output (VB-Audio Virtual Cable)`.
3. In the app you can list available devices with `python app.py --list-devices`.

If you already have another loopback device, skip the installer script and use `--list-devices` to locate its index.

## Running the Overlay

```pwsh
python app.py
```

- Drag the overlay to reposition it.
- Press `Ctrl+Shift+C` (left Ctrl) to toggle visibility.
- Press `Ctrl+C` in the terminal to exit, or close the window.

You can tweak defaults by editing the `Config` dataclass in `app.py` (model size, temperature, buffer durations, etc.).

## GPU & Performance Notes
- The transcriber tries CUDA first with low-memory compute types (`int8_float16`).
- If CUDA is unavailable or fails, it automatically falls back to CPU with int8 inference.
- Reduce `Config.model_size` or `Config.block_seconds` if you’re seeing high latency on CPU-only setups.

## Playground Overlay

`playground_overlay.py` is a standalone Tk demo that simulates streaming captions without any dependencies beyond the Python standard library. Useful for UI tweaks or verifying window behavior on machines where PyQt6 is not installed.

## Troubleshooting
- “VB-Audio device not found” → run `python app.py --list-devices` to ensure the driver is installed and the virtual cable is selected as the input device.
- “Audio queue full” logs → try increasing `audio_queue_size` or reducing `block_seconds`.
- “Model load failed” logs → install `torch` with CUDA support or let the script fall back to CPU; you can also pre-download Whisper weights to avoid first-run delays.

## Project Structure

```
whispercaption/
├── app.py                 # Main realtime overlay application
├── _whisper_settings.py   # Reusable dataclass for managing Whisper config
├── playground_overlay.py  # Tk-based UI sandbox
├── install_vb_cable.ps1   # Helper for installing VB-Audio Cable on Windows
├── requirements.txt       # Python dependencies for the PyQt app
└── README.md
```

## Contributing
Issues and pull requests are welcome. If you add new features, please document configuration changes and describe how they impact latency or resource usage.