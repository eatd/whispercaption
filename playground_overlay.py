"""
Playground: simple on-screen captions overlay using only the Python standard library.
- Drag the window to move it.
- Press Ctrl+Shift+C to toggle visibility.
- Press Esc to quit.
The text simulates streaming captions.
"""

import tkinter as tk

# Window setup
root = tk.Tk()
root.overrideredirect(True)  # frameless
root.attributes("-topmost", True)
root.attributes("-alpha", 0.88)
root.configure(bg="#000000")
root.geometry("800x120+100+50")

# Simple bordered container
container = tk.Frame(
    root, bg="#000000", highlightthickness=2, highlightbackground="white"
)
container.pack(fill="both", expand=True, padx=12, pady=8)

label = tk.Label(
    container,
    text="Listening…",
    fg="white",
    bg="#000000",
    font=("Segoe UI", 18, "bold"),
    wraplength=760,
    justify="center",
)
label.pack(fill="both", expand=True)

# Drag-to-move
_drag = {"x": 0, "y": 0}


def on_press(e):
    _drag["x"], _drag["y"] = e.x, e.y


def on_drag(e):
    x = e.x_root - _drag["x"]
    y = e.y_root - _drag["y"]
    root.geometry(f"+{x}+{y}")


root.bind("<ButtonPress-1>", on_press)
root.bind("<B1-Motion>", on_drag)

# Toggle visibility with Ctrl+Shift+C (when window is focused)
_hidden = {"v": False}


def toggle(_=None):
    # Hide/show content while keeping the window alive and focusable
    if _hidden["v"]:
        container.pack(fill="both", expand=True, padx=12, pady=8)
        root.attributes("-alpha", 0.88)
        _hidden["v"] = False
    else:
        container.pack_forget()
        root.attributes("-alpha", 0.25)
        _hidden["v"] = True


root.bind("<Control-Shift-c>", toggle)
root.bind("<Escape>", lambda e: root.destroy())

# Simulated streaming captions
sentences = [
    "This is a tiny demo showing a captions overlay.",
    "Everything here uses only the Python standard library.",
    "Drag the box to move it around the screen.",
    "Press Control Shift C to toggle visibility.",
    "Press Escape to close the demo.",
]

chunks = []
for s in sentences:
    words = s.split()
    step = 3
    for i in range(0, len(words), step):
        piece = " ".join(words[i : i + step])
        if i + step >= len(words) and not piece.endswith((".", "!", "?")):
            piece += "."
        chunks.append(piece)

_state = {"buf": "", "clear_next": False}


def tick(i=0):
    if i >= len(chunks):
        i = 0
    if _state["clear_next"]:
        label.config(text="")
        _state["buf"] = ""
        _state["clear_next"] = False
    ch = chunks[i]
    _state["buf"] = (f"{_state['buf']} {ch}").strip()
    label.config(text=_state["buf"])
    if ch.endswith((".", "!", "?")):
        _state["clear_next"] = True
    root.after(900, lambda: tick(i + 1))


# Kick off the simulation
root.after(600, tick)
root.mainloop()
