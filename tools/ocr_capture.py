"""OCR Capture — select a screen region, extract text using Windows native OCR."""

import tkinter as tk
from tkinter import ttk
import sys, os, asyncio, subprocess, threading, tempfile
from .theme import *

try:
    import mss
    from PIL import Image as PilImage
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import StorageFile, FileAccessMode
    from winrt.windows.graphics.imaging import (
        BitmapDecoder, BitmapPixelFormat, SoftwareBitmap)
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

_PACKAGES = [
    "Pillow", "mss", "winrt-runtime",
    "winrt-Windows.Media.Ocr", "winrt-Windows.Storage",
    "winrt-Windows.Graphics.Imaging",
]


def build_tab(parent):
    root = parent.winfo_toplevel()

    top = tk.Frame(parent, bg=BG)
    top.pack(fill="x", padx=12, pady=10)

    ocr_status = tk.Label(top, bg=BG, font=FONT_SM,
                           text="" if OCR_AVAILABLE else "OCR packages not installed",
                           fg=RED if not OCR_AVAILABLE else FG_DIM)

    style = ttk.Style(root)
    style.configure("install.Horizontal.TProgressbar",
                    background=BLUE, troughcolor=BG2, borderwidth=0, thickness=6)
    install_bar = ttk.Progressbar(parent, style="install.Horizontal.TProgressbar",
                                   mode="indeterminate")

    ocr_box = tk.Text(parent, bg=BG2, fg=FG, font=FONT_SM,
                      relief="flat", wrap="word", width=44, height=3,
                      padx=8, pady=6, insertbackground=FG)

    # -- capture flow --

    def start_capture():
        if not OCR_AVAILABLE:
            ocr_status.config(text="OCR packages not installed — click Install", fg=RED)
            return
        ocr_status.config(text="")
        root.withdraw()
        root.after(300, _capture_screen)

    def _capture_screen():
        with mss.mss() as sct:
            virtual = sct.monitors[0]
            raw = sct.grab(virtual)
            full_shot = PilImage.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            phys_primary_w = sct.monitors[1]["width"]

        log_w = root.winfo_screenwidth()
        scale = phys_primary_w / log_w if log_w else 1.0

        vx = round(virtual["left"]   / scale)
        vy = round(virtual["top"]    / scale)
        sw = round(virtual["width"]  / scale)
        sh = round(virtual["height"] / scale)
        _show_selector(full_shot, scale, vx, vy, sw, sh)

    def _show_selector(full_shot, scale, vx, vy, sw, sh):
        sel = tk.Toplevel()
        sel.geometry(f"{sw}x{sh}+{vx}+{vy}")
        sel.overrideredirect(True)
        sel.attributes("-topmost", True)
        sel.attributes("-alpha", 0.25)
        sel.configure(bg="black", cursor="crosshair")

        canvas = tk.Canvas(sel, bg="black", highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)
        tk.Label(canvas,
                 text="  Click and drag to select region   \u2022   Esc to cancel  ",
                 bg="#1a1a1a", fg="#cccccc", font=("Segoe UI", 10),
                 padx=10, pady=5).place(relx=0.5, rely=0.02, anchor="n")

        state = {"start": None, "rect": None}

        def on_press(e):
            state["start"] = (e.x, e.y)
            if state["rect"]:
                canvas.delete(state["rect"])

        def on_drag(e):
            if not state["start"]:
                return
            x0, y0 = state["start"]
            if state["rect"]:
                canvas.delete(state["rect"])
            state["rect"] = canvas.create_rectangle(
                x0, y0, e.x, e.y, outline="#2ecc71", width=2)

        def on_release(e):
            if not state["start"]:
                return
            x0, y0 = state["start"]
            x1, y1 = e.x, e.y
            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)
            sel.destroy()
            root.deiconify()
            if x1 - x0 < 10 or y1 - y0 < 10:
                ocr_status.config(text="Selection too small — try again", fg=RED)
                return
            img = full_shot.crop((
                int(x0 * scale), int(y0 * scale),
                int(x1 * scale), int(y1 * scale)))
            ocr_status.config(text="Running OCR...", fg=FG_DIM)
            threading.Thread(target=lambda: _do_ocr(img), daemon=True).start()

        def on_escape(e):
            sel.destroy()
            root.deiconify()
            ocr_status.config(text="Cancelled", fg=FG_DIM)

        canvas.bind("<ButtonPress-1>",   on_press)
        canvas.bind("<B1-Motion>",       on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        sel.bind("<Escape>",             on_escape)
        sel.focus_force()

    # -- WinRT OCR --

    async def _ocr_async(path):
        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            recs = OcrEngine.available_recognizers
            if not recs:
                raise RuntimeError("No OCR language packs installed")
            engine = OcrEngine.try_create_from_language(recs[0])
        file   = await StorageFile.get_file_from_path_async(path)
        stream = await file.open_async(FileAccessMode.READ)
        dec    = await BitmapDecoder.create_async(stream)
        bitmap = await dec.get_software_bitmap_async()
        bitmap = SoftwareBitmap.convert(bitmap, BitmapPixelFormat.BGRA8)
        result = await engine.recognize_async(bitmap)
        return result.text

    def _do_ocr(img):
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            img.save(tmp)
            text = asyncio.run(_ocr_async(tmp))
            root.after(0, lambda: _finish_ocr(text))
        except Exception as ex:
            msg = str(ex)
            root.after(0, lambda: ocr_status.config(text=f"OCR error: {msg}", fg=RED))
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    def _finish_ocr(text):
        if text and text.strip():
            ocr_box.delete("1.0", tk.END)
            ocr_box.insert("1.0", text.strip())
            ocr_status.config(text="")
        else:
            ocr_status.config(text="No text found in selection", fg=FG_DIM)

    def _copy_ocr(btn):
        text = ocr_box.get("1.0", tk.END).strip()
        if not text:
            return
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        orig = btn.cget("text")
        btn.config(bg=GREEN2, text="Copied!")
        root.after(1200, lambda: btn.config(bg=BLUE, text=orig))

    def _clear_ocr():
        ocr_box.delete("1.0", tk.END)
        ocr_status.config(text="")

    # -- installer --

    def run_install():
        btn_install.config(state="disabled", text="Installing...")
        ocr_status.config(text="Installing — this may take a minute...", fg="white")
        install_bar.pack(fill="x", padx=12, pady=(0, 8))
        install_bar.start(12)
        threading.Thread(target=_do_install, daemon=True).start()

    def _do_install():
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + _PACKAGES,
                capture_output=True, text=True)
            if r.returncode != 0:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--user"] + _PACKAGES,
                    capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr[-400:])
            root.after(0, _install_ok)
        except Exception as e:
            root.after(0, lambda: _install_fail(str(e)))

    def _install_ok():
        install_bar.stop()
        install_bar.pack_forget()
        ocr_status.config(text="Installed — click Restart to activate", fg=GREEN2)
        btn_install.config(text="Restart App", state="normal", bg=GREEN2,
                           command=lambda: (root.destroy(),
                                            subprocess.Popen([sys.executable] + sys.argv)))

    def _install_fail(detail=""):
        install_bar.stop()
        install_bar.pack_forget()
        short = detail.strip().splitlines()[-1][:80] if detail.strip() else "unknown error"
        ocr_status.config(text=f"Install failed: {short}", fg=RED)
        btn_install.config(text="Install", state="normal")

    # -- layout --

    tk.Button(top, text="Capture Text", command=start_capture,
              bg=GREEN2, fg="white", font=FONT, relief="flat",
              padx=12, pady=5).pack(side="left")
    ocr_status.pack(side="left", padx=10)

    btn_install = tk.Button(top, text="Install", command=run_install,
                            bg=BLUE, fg="white", font=FONT_SM, relief="flat",
                            padx=8, pady=5)
    if not OCR_AVAILABLE:
        btn_install.pack(side="left")

    ocr_box.pack(fill="x", padx=10, pady=(0, 4))

    btns = tk.Frame(parent, bg=BG)
    btns.pack(fill="x", padx=10, pady=(0, 10))
    btn_copy = tk.Button(btns, text="Copy All",
                          command=lambda: _copy_ocr(btn_copy),
                          bg=BLUE, fg="white", font=FONT_SM, relief="flat",
                          padx=8, pady=3)
    btn_copy.pack(side="left")
    tk.Button(btns, text="Clear", command=_clear_ocr,
              bg=GREY, fg=FG_DIM, font=FONT_SM, relief="flat",
              padx=8, pady=3).pack(side="left", padx=(6, 0))
