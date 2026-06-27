import subprocess
import threading
import time
import os
import sys
import tkinter as tk
from tkinter import ttk
import webbrowser

# ── start Flask in background ──────────────────────────
def start_flask():
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    subprocess.Popen(
        [sys.executable, script],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

# ── splash / loader window ─────────────────────────────
root = tk.Tk()
root.title("ExpenseIQ")
root.geometry("380x260")
root.resizable(False, False)
root.configure(bg="#0d0d0d")

# Center the window
root.update_idletasks()
w = root.winfo_screenwidth()
h = root.winfo_screenheight()
root.geometry(f"380x260+{(w-380)//2}+{(h-260)//2}")

# Icon-like label
tk.Label(root, text="💰", font=("Segoe UI Emoji", 48), bg="#0d0d0d").pack(pady=(30, 5))
tk.Label(root, text="ExpenseIQ", font=("Segoe UI", 20, "bold"),
         fg="#00e676", bg="#0d0d0d").pack()
tk.Label(root, text="Starting your app...", font=("Segoe UI", 10),
         fg="#555555", bg="#0d0d0d").pack(pady=(8, 16))

# Progress bar
style = ttk.Style()
style.theme_use("clam")
style.configure("green.Horizontal.TProgressbar",
                troughcolor="#1a1a1a", background="#00e676",
                bordercolor="#0d0d0d", lightcolor="#00e676", darkcolor="#00c853")
bar = ttk.Progressbar(root, style="green.Horizontal.TProgressbar",
                      length=280, mode="determinate")
bar.pack()

status = tk.Label(root, text="", font=("Segoe UI", 9), fg="#444444", bg="#0d0d0d")
status.pack(pady=6)

# ── launch sequence ────────────────────────────────────
def launch():
    start_flask()

    steps = [
        (20, "Loading database…"),
        (50, "Starting server…"),
        (80, "Almost ready…"),
        (100, "Opening ExpenseIQ!"),
    ]

    for value, msg in steps:
        time.sleep(0.8)
        bar["value"] = value
        status.config(text=msg)
        root.update()

    time.sleep(0.4)
    webbrowser.open("http://localhost:8080")
    root.destroy()

threading.Thread(target=launch, daemon=True).start()
root.mainloop()
