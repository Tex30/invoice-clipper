# Invoice calc tool - paste invoice text, get clean numbers to copy into ASAP
# Finds Total (inc GST) and VEEC, shows result ready to copy. STC ignored.
import tkinter as tk
import re

BG       = "#1e1e1e"
BG2      = "#252525"
FG       = "#cccccc"
FG_DIM   = "#888888"
GREEN    = "#2ecc71"
GREEN2   = "#27ae60"
BLUE     = "#3a7bd5"
GREY     = "#444444"
RED      = "#e74c3c"
FONT     = ("Segoe UI", 10)
FONT_LG  = ("Segoe UI", 12, "bold")
FONT_SM  = ("Segoe UI", 9)


def extract_from_line(line):
    m = re.search(r'\$?([\d,]+\.\d{2})', line)
    return float(m.group(1).replace(',', '')) if m else None


def find_next_amount(lines, idx):
    for i in range(idx + 1, min(idx + 5, len(lines))):
        val = extract_from_line(lines[i])
        if val:
            return val
    return None


def copy_val(value, btn):
    root.clipboard_clear()
    root.clipboard_append(value)
    root.update()
    orig = btn.cget("text")
    btn.config(bg=GREEN2, text="Copied!")
    root.after(1200, lambda: btn.config(bg=BLUE, text=orig))


def smart_paste():
    try:
        text = root.clipboard_get()
    except Exception:
        status.config(text="Clipboard empty", fg=RED)
        return

    text  = text.replace('\u2212', '-').replace('\u2013', '-')
    lines = [l.strip() for l in text.split('\n')]

    total = None
    veec  = None

    for i, line in enumerate(lines):
        upper = line.upper()
        if 'TOTAL' in upper and total is None:
            total = extract_from_line(line)
        elif 'VICTORIAN' in upper and veec is None:
            val = extract_from_line(line)
            # amount is sometimes on the line below the label
            veec = val if val else find_next_amount(lines, i)

    for w in results_frame.winfo_children():
        w.destroy()

    if total is None:
        status.config(text="Could not find Total — check invoice format", fg=RED)
        return

    if veec is None:
        status.config(text="VEEC not found in text", fg=RED)
        return

    result     = total - veec
    result_str = f"{result:.2f}"
    formula    = f"${total:,.2f} − ${veec:,.2f}"

    # Total row
    row1 = tk.Frame(results_frame, bg=BG2)
    row1.pack(fill="x", pady=2, padx=2)
    tk.Label(row1, text=f"$ {total:,.2f}", bg=BG2, fg=FG,
             font=FONT_LG, anchor="w").pack(side="left", padx=12, pady=6)
    tk.Label(row1, text="Total", bg=BG2, fg=GREEN2,
             font=FONT_SM).pack(side="left")
    btn1 = tk.Button(row1, text="Copy", bg=BLUE, fg="white",
                     font=FONT_SM, relief="flat", padx=8, pady=3)
    btn1.config(command=lambda v=f"{total:.2f}", b=btn1: copy_val(v, b))
    btn1.pack(side="right", padx=(2, 10))

    # Result row
    row2 = tk.Frame(results_frame, bg=BG2)
    row2.pack(fill="x", pady=2, padx=2)
    tk.Label(row2, text=f"$ {result:,.2f}", bg=BG2, fg=GREEN,
             font=FONT_LG, anchor="w").pack(side="left", padx=12, pady=6)
    tk.Label(row2, text=formula, bg=BG2, fg=FG_DIM,
             font=FONT_SM).pack(side="left", padx=(0, 8))
    btn2 = tk.Button(row2, text="Copy", bg=BLUE, fg="white",
                     font=FONT_SM, relief="flat", padx=8, pady=3)
    btn2.config(command=lambda v=result_str, b=btn2: copy_val(v, b))
    btn2.pack(side="right", padx=(2, 10))

    status.config(text="")


def clear_all(event=None):
    for w in results_frame.winfo_children():
        w.destroy()
    status.config(text="")


root = tk.Tk()
root.title("Invoice Calculator")
root.resizable(False, False)
root.attributes("-topmost", True)
root.configure(bg=BG)

top = tk.Frame(root, bg=BG)
top.pack(fill="x", padx=12, pady=10)

tk.Button(top, text="Smart Paste", command=smart_paste,
          bg=GREEN2, fg="white", font=FONT, relief="flat",
          padx=12, pady=5).pack(side="left")

tk.Button(top, text="Clear", command=clear_all,
          bg=GREY, fg=FG_DIM, font=FONT_SM, relief="flat",
          padx=8, pady=5).pack(side="left", padx=(6, 0))

status = tk.Label(top, text="", bg=BG, fg=FG_DIM, font=FONT_SM)
status.pack(side="left", padx=10)

results_frame = tk.Frame(root, bg=BG)
results_frame.pack(fill="x", padx=10, pady=(0, 10))

root.bind("<Escape>", clear_all)
root.mainloop()
