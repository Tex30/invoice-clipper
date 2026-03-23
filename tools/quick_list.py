"""Quick List — paste a column of codes, get a Copy button next to each row."""

import tkinter as tk
from .theme import *


def build_tab(parent):
    root = parent.winfo_toplevel()

    top = tk.Frame(parent, bg=BG)
    top.pack(fill="x", padx=12, pady=10)

    status = tk.Label(top, text="", bg=BG, fg=FG_DIM, font=FONT_SM)

    rows_frame = tk.Frame(parent, bg=BG)
    rows_frame.pack(fill="x", padx=10, pady=(0, 10))

    auto_remove = tk.BooleanVar(value=False)

    def _copy(value, btn, row):
        root.clipboard_clear()
        root.clipboard_append(value)
        root.update()
        if auto_remove.get():
            row.destroy()
            remaining = len(rows_frame.winfo_children())
            status.config(text=f"{remaining} items" if remaining else "")
        else:
            orig = btn.cget("text")
            btn.config(bg=GREEN2, text="Copied!")
            root.after(1200, lambda: btn.config(bg=BLUE, text=orig))

    def paste_list():
        try:
            text = root.clipboard_get()
        except Exception:
            status.config(text="Clipboard empty", fg=RED)
            return

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not lines:
            status.config(text="Nothing to paste", fg=RED)
            return

        clear()
        for line in lines:
            row = tk.Frame(rows_frame, bg=BG2)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=line, bg=BG2, fg=FG, font=FONT_SM,
                     anchor="w", padx=8, pady=4).pack(side="left", fill="x", expand=True)
            btn = tk.Button(row, text="Copy", bg=BLUE, fg="white",
                            font=FONT_SM, relief="flat", padx=8, pady=2)
            btn.config(command=lambda v=line, b=btn, r=row: _copy(v, b, r))
            btn.pack(side="right", padx=(2, 6))

        status.config(text=f"{len(lines)} items", fg=FG_DIM)

    def clear():
        for w in rows_frame.winfo_children():
            w.destroy()
        status.config(text="")

    # layout
    tk.Button(top, text="Paste List", command=paste_list,
              bg=GREEN2, fg="white", font=FONT, relief="flat",
              padx=12, pady=5).pack(side="left")
    tk.Button(top, text="Clear", command=clear,
              bg=GREY, fg=FG_DIM, font=FONT_SM, relief="flat",
              padx=8, pady=5).pack(side="left", padx=(6, 0))
    tk.Checkbutton(top, text="Remove on copy", variable=auto_remove,
                   bg=BG, fg=FG_DIM, selectcolor=BG2, activebackground=BG,
                   activeforeground=FG, font=FONT_SM).pack(side="left", padx=(10, 0))
    status.pack(side="left", padx=10)
