"""Main launcher — tabbed window that loads each tool."""

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk
from .theme import BG, BG2, FG, FG_DIM, GREY, FONT_SM
from . import invoice_calc, ocr_capture, quick_list


def main():
    root = tk.Tk()
    root.title("Tools")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("default")
    style.configure("TNotebook",
                    background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab",
                    background=GREY, foreground=FG_DIM,
                    font=FONT_SM, padding=[14, 5])
    style.map("TNotebook.Tab",
              background=[("selected", BG2), ("active", "#333333")],
              foreground=[("selected", FG),  ("active", FG)])

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    for label, mod in [("  Invoice Calculator  ", invoice_calc),
                       ("  OCR Capture  ",        ocr_capture),
                       ("  Quick List  ",         quick_list)]:
        tab = tk.Frame(nb, bg=BG)
        nb.add(tab, text=label)
        mod.build_tab(tab)

    root.mainloop()


if __name__ == "__main__":
    main()
