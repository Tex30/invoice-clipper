import tkinter as tk
from tkinter import ttk
import sys, os, json, asyncio, subprocess, threading, tempfile
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

try:
    from pynput import keyboard as kb
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False

_PACKAGES = [
    "Pillow", "mss", "pynput", "winrt-runtime",
    "winrt-Windows.Foundation",
    "winrt-Windows.Media.Ocr", "winrt-Windows.Storage",
    "winrt-Windows.Graphics.Imaging",
]

DEFAULT_HOTKEY = "<ctrl>+<shift>+q"
DEFAULT_DISPLAY = "Ctrl + Shift + Q"
_CFG_PATH = os.path.join(os.path.dirname(__file__), "hotkey.json")


def _load_cfg():
    try:
        with open(_CFG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cfg(combo, display, enabled):
    try:
        with open(_CFG_PATH, "w") as f:
            json.dump({"combo": combo, "display": display, "enabled": enabled}, f)
    except Exception:
        pass


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

    _busy = {"capturing": False}

    def start_capture():
        if _busy["capturing"]:
            return
        if not OCR_AVAILABLE:
            ocr_status.config(text="OCR packages not installed — click Install", fg=RED)
            return
        _busy["capturing"] = True
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
        sel.withdraw()
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

        sel.geometry(f"{sw}x{sh}+{vx}+{vy}")
        sel.deiconify()

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
            _busy["capturing"] = False
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
            _busy["capturing"] = False
            ocr_status.config(text="Cancelled", fg=FG_DIM)

        canvas.bind("<ButtonPress-1>",   on_press)
        canvas.bind("<B1-Motion>",       on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        sel.bind("<Escape>",             on_escape)
        sel.focus_force()

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

    def run_install():
        btn_install.config(state="disabled", text="Installing...")
        ocr_status.config(text="Installing — this may take a minute...", fg="white")
        install_bar.pack(fill="x", padx=12, pady=(0, 8))
        install_bar.start(12)
        threading.Thread(target=_do_install, daemon=True).start()

    def _do_install():
        _no_window = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + _PACKAGES,
                capture_output=True, text=True, **_no_window)
            if r.returncode != 0:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--user"] + _PACKAGES,
                    capture_output=True, text=True, **_no_window)
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
                                            subprocess.Popen(
                                                [sys.executable] + sys.argv,
                                                creationflags=0x08000000 if sys.platform == "win32" else 0)))

    def _install_fail(detail=""):
        install_bar.stop()
        install_bar.pack_forget()
        short = detail.strip().splitlines()[-1][:80] if detail.strip() else "unknown error"
        ocr_status.config(text=f"Install failed: {short}", fg=RED)
        btn_install.config(text="Install", state="normal")

    _MODIFIERS = {"ctrl_l", "ctrl_r", "shift", "shift_l", "shift_r",
                  "alt_l", "alt_r", "alt_gr", "cmd", "cmd_l", "cmd_r"}
    _MOD_DISPLAY = {"ctrl_l": "Ctrl", "ctrl_r": "Ctrl", "shift": "Shift",
                    "shift_l": "Shift", "shift_r": "Shift",
                    "alt_l": "Alt", "alt_r": "Alt", "alt_gr": "AltGr",
                    "cmd": "Win", "cmd_l": "Win", "cmd_r": "Win"}
    _MOD_PYNPUT = {"ctrl_l": "<ctrl>", "ctrl_r": "<ctrl>",
                   "shift": "<shift>", "shift_l": "<shift>", "shift_r": "<shift>",
                   "alt_l": "<alt>", "alt_r": "<alt>", "alt_gr": "<alt_gr>",
                   "cmd": "<cmd>", "cmd_l": "<cmd>", "cmd_r": "<cmd>"}

    cfg = _load_cfg()
    hk = {"listener": None,
          "combo": cfg.get("combo", DEFAULT_HOTKEY),
          "display": cfg.get("display", DEFAULT_DISPLAY),
          "enabled": cfg.get("enabled", False),
          "recording": False, "pressed": set(), "rec_listener": None}

    def _key_name(key):
        if hasattr(key, "name"):
            return key.name
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        return None

    def _display_combo(keys):
        mods = sorted(k for k in keys if k in _MODIFIERS)
        regular = sorted(k for k in keys if k not in _MODIFIERS)
        parts, seen = [], set()
        for m in mods:
            nice = _MOD_DISPLAY.get(m, m.title())
            if nice not in seen:
                parts.append(nice)
                seen.add(nice)
        for r in regular:
            parts.append(r.upper() if len(r) == 1 else r.replace("_", " ").title())
        return " + ".join(parts)

    def _to_pynput(keys):
        mods = sorted(k for k in keys if k in _MODIFIERS)
        regular = sorted(k for k in keys if k not in _MODIFIERS)
        parts, seen = [], set()
        for m in mods:
            token = _MOD_PYNPUT.get(m, f"<{m}>")
            if token not in seen:
                parts.append(token)
                seen.add(token)
        for r in regular:
            parts.append(r if len(r) == 1 else f"<{r}>")
        return "+".join(parts)

    def _hotkey_fired():
        root.after(0, start_capture)

    def _start_listener(combo):
        _stop_listener()
        if not HOTKEY_AVAILABLE:
            return
        try:
            hotkey = kb.HotKey(kb.HotKey.parse(combo), _hotkey_fired)
            listener = kb.Listener(
                on_press=lambda k: hotkey.press(listener.canonical(k)),
                on_release=lambda k: hotkey.release(listener.canonical(k)))
            listener.daemon = True
            listener.start()
            hk["listener"] = listener
            hk["combo"] = combo
        except Exception:
            pass

    def _stop_listener():
        if hk["listener"]:
            hk["listener"].stop()
            hk["listener"] = None

    def _stop_recording():
        hk["recording"] = False
        if hk["rec_listener"]:
            hk["rec_listener"].stop()
            hk["rec_listener"] = None

    def _start_recording():
        if hk["recording"]:
            _stop_recording()
            hk_record.config(text=hk["display"], bg=BG2, fg=FG)
            hk_toggle.config(state="normal")
            hk_status.config(text="", fg=FG_DIM)
            return
        _stop_listener()
        hk["recording"] = True
        hk["pressed"] = set()
        hk_record.config(text="Press keys...", bg="#e67e22", fg="white")
        hk_status.config(text="Esc to cancel", fg=FG_DIM)
        hk_toggle.config(state="disabled")

        def on_press(key):
            name = _key_name(key)
            if name is None:
                return
            if name == "esc":
                root.after(0, _cancel_recording)
                return False
            hk["pressed"].add(name)
            root.after(0, lambda: hk_record.config(
                text=_display_combo(hk["pressed"]) or "Press keys..."))

        def on_release(key):
            keys = hk["pressed"].copy()
            if not keys:
                return
            has_mod = any(k in _MODIFIERS for k in keys)
            has_key = any(k not in _MODIFIERS for k in keys)
            if has_mod and has_key:
                hk["recording"] = False
                combo = _to_pynput(keys)
                display = _display_combo(keys)
                hk["combo"] = combo
                hk["display"] = display
                root.after(0, lambda: _finish_recording(display))
                return False

        rec = kb.Listener(on_press=on_press, on_release=on_release)
        rec.daemon = True
        rec.start()
        hk["rec_listener"] = rec

    def _cancel_recording():
        _stop_recording()
        hk_record.config(text=hk["display"], bg=BG2, fg=FG)
        hk_toggle.config(text="Enable", bg=GREY, fg=FG_DIM, state="normal")
        hk_status.config(text="Cancelled", fg=FG_DIM)

    def _finish_recording(display):
        _stop_recording()
        hk_record.config(text=display, bg=BG2, fg=FG)
        hk_toggle.config(text="Enable", bg=GREY, fg=FG_DIM, state="normal")
        hk_status.config(text="Click Enable to activate", fg=FG_DIM)
        _save_cfg(hk["combo"], hk["display"], False)

    def _on_hotkey_toggle():
        if hk["listener"]:
            _stop_listener()
            hk_toggle.config(text="Enable", bg=GREY, fg=FG_DIM)
            hk_status.config(text="Hotkey off", fg=FG_DIM)
            _save_cfg(hk["combo"], hk["display"], False)
        else:
            _start_listener(hk["combo"])
            if hk["listener"]:
                hk_toggle.config(text="Disable", bg=RED, fg="white")
                hk_status.config(text="Active", fg=GREEN2)
                _save_cfg(hk["combo"], hk["display"], True)
            else:
                hk_status.config(text="Invalid combo", fg=RED)

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

    if HOTKEY_AVAILABLE:
        hk_frame = tk.Frame(parent, bg=BG)
        hk_frame.pack(fill="x", padx=10, pady=(2, 10))
        tk.Label(hk_frame, text="Hotkey", bg=BG, fg=FG_DIM,
                 font=FONT_SM).pack(side="left")
        hk_record = tk.Button(hk_frame, text=hk["display"],
                               command=_start_recording,
                               bg=BG2, fg=FG, font=FONT_SM, relief="flat",
                               padx=8, pady=2, cursor="hand2")
        hk_record.pack(side="left", padx=(6, 0))
        hk_toggle = tk.Button(hk_frame, text="Enable", command=_on_hotkey_toggle,
                               bg=GREY, fg=FG_DIM, font=FONT_SM, relief="flat",
                               padx=8, pady=2)
        hk_toggle.pack(side="left", padx=(6, 0))
        hk_status = tk.Label(hk_frame, text="", bg=BG, fg=FG_DIM, font=FONT_SM)
        hk_status.pack(side="left", padx=(8, 0))

        if hk["enabled"]:
            _start_listener(hk["combo"])
            if hk["listener"]:
                hk_toggle.config(text="Disable", bg=RED, fg="white")
                hk_status.config(text="Active", fg=GREEN2)
