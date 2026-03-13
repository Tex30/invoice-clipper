# invoice_calc.py — line by line

---

## Imports and colours

```python
import tkinter as tk
import re
```
`tkinter` is Python's built-in GUI library — creates the window, buttons, labels.
`re` is the standard regex module — used to find dollar amounts inside text.

```python
BG    = "#1e1e1e"   # main window background (near black)
BG2   = "#252525"   # slightly lighter background used on each result row
FG    = "#cccccc"   # normal text colour (light grey)
FG_DIM = "#888888"  # dimmed text — used for the formula and status messages
GREEN  = "#2ecc71"  # bright green — result amount
GREEN2 = "#27ae60"  # darker green — "Total" label and Copied! flash
BLUE   = "#3a7bd5"  # blue — Copy buttons
GREY   = "#444444"  # grey — Clear button
RED    = "#e74c3c"  # red — error messages in the status bar
```

```python
FONT    = ("Segoe UI", 10)           # standard button text
FONT_LG = ("Segoe UI", 12, "bold")   # large bold — dollar amounts
FONT_SM = ("Segoe UI", 9)            # small — labels, formula, status
```

---

## extract_from_line(line)

```python
def extract_from_line(line):
    m = re.search(r'\$?([\d,]+\.\d{2})', line)
    return float(m.group(1).replace(',', '')) if m else None
```

Looks for a dollar amount in a single line of text.

- `re.search(...)` scans the line for the first match of the pattern
- `\$?` — dollar sign is optional (not every line has one)
- `[\d,]+` — one or more digits or commas, e.g. `3,870`
- `\.\d{2}` — a dot followed by exactly two digits, e.g. `.00`
- `m.group(1)` — gets just the number part (inside the brackets in the pattern)
- `.replace(',', '')` — strips the commas so `3,870.00` becomes `3870.00`
- `float(...)` — converts the string to a number Python can do maths with
- If no match is found, returns `None`

---

## find_next_amount(lines, idx)

```python
def find_next_amount(lines, idx):
    for i in range(idx + 1, min(idx + 5, len(lines))):
        val = extract_from_line(lines[i])
        if val:
            return val
    return None
```

Some invoice templates put the dollar amount on the line below the label
rather than on the same line. This handles that.

- `range(idx + 1, ...)` — starts checking from the line after the keyword line
- `min(idx + 5, len(lines))` — looks at most 4 lines ahead, and doesn't go past the end of the text
- Calls `extract_from_line` on each line and returns the first amount it finds
- Returns `None` if nothing found within those 4 lines

---

## copy_val(value, btn)

```python
def copy_val(value, btn):
    root.clipboard_clear()        # wipe whatever is currently on the clipboard
    root.clipboard_append(value)  # put the new value on the clipboard
    root.update()                 # commit the clipboard write before window loses focus
    orig = btn.cget("text")       # save the button's current label ("Copy")
    btn.config(bg=GREEN2, text="Copied!")   # flash it green
    root.after(1200, lambda: btn.config(bg=BLUE, text=orig))  # reset after 1.2s
```

`root.after(1200, ...)` schedules the reset without freezing the window.
The `lambda` is needed because `after` takes a function, not a direct call.

---

## smart_paste()

### Reading the clipboard

```python
try:
    text = root.clipboard_get()
except Exception:
    status.config(text="Clipboard empty", fg=RED)
    return
```

`clipboard_get()` throws an error if the clipboard is empty or contains
non-text content. The `try/except` catches that and shows a red message instead of crashing.

### Cleaning the text

```python
text  = text.replace('\u2212', '-').replace('\u2013', '-')
lines = [l.strip() for l in text.split('\n')]
```

- `\u2212` is the unicode minus sign `−` and `\u2013` is an en dash `–` —
  both appear in invoice PDFs instead of a regular hyphen. Replacing them
  ensures the regex can still find the numbers after them.
- `text.split('\n')` breaks the text into a list of individual lines
- `l.strip()` removes leading/trailing spaces and tabs from each line
- The whole thing is a list comprehension — a compact way of writing a loop

### Scanning for values

```python
total = None
veec  = None
```
Start both as `None` so we can check later whether they were found.

```python
for i, line in enumerate(lines):
    upper = line.upper()
```
`enumerate` gives both the index `i` and the line text on each loop.
`.upper()` converts the line to uppercase so the keyword check isn't case-sensitive.

```python
    if 'TOTAL' in upper and total is None:
        total = extract_from_line(line)
```
If the line contains the word TOTAL and we haven't found a total yet,
try to pull the amount from that line. Safe to match just `TOTAL` since
only the relevant invoice section is being copied.

```python
    elif 'VEEC' in upper and veec is None:
        val = extract_from_line(line)
        veec = val if val else find_next_amount(lines, i)
```
If the line contains `VEEC`, try the same line first.
If no amount is on that line (`val` is `None`), call `find_next_amount`
to check the lines below. The `and veec is None` guard stops it matching
a second VEEC line if one appears later in the text.

### Error checks

```python
if total is None:
    status.config(text="Could not find Total — check invoice format", fg=RED)
    return

if veec is None:
    status.config(text="VEEC not found in text", fg=RED)
    return
```
If either value wasn't found, show a red error and stop — nothing gets built.

### Building the result

```python
result     = total - veec                       # the actual subtraction
result_str = f"{result:.2f}"                    # e.g. "3100.00" — no commas, for clipboard
formula    = f"${total:,.2f} − ${veec:,.2f}"    # e.g. "$3,870.00 − $770.00" — for display only
```

`result_str` has no commas because ASAP doesn't accept them.
`formula` uses commas and the minus sign because it's just for visual checking.

### Total row

```python
row1 = tk.Frame(results_frame, bg=BG2)
row1.pack(fill="x", pady=2, padx=2)
```
Creates a horizontal container (frame) for the Total row and adds it to the results area.
`fill="x"` makes it stretch the full width. `pady=2` adds a small gap above and below.

```python
tk.Label(row1, text=f"$ {total:,.2f}", bg=BG2, fg=FG,
         font=FONT_LG, anchor="w").pack(side="left", padx=12, pady=6)
```
The dollar amount — large bold text, aligned left. `anchor="w"` means left-aligned within the label.

```python
tk.Label(row1, text="Total", bg=BG2, fg=GREEN2,
         font=FONT_SM).pack(side="left")
```
Small green "Total" label right next to the amount.

```python
btn1 = tk.Button(row1, text="Copy", bg=BLUE, fg="white",
                 font=FONT_SM, relief="flat", padx=8, pady=3)
btn1.config(command=lambda v=f"{total:.2f}", b=btn1: copy_val(v, b))
btn1.pack(side="right", padx=(2, 10))
```
The Copy button, pushed to the right side of the row.
`relief="flat"` removes the raised border so it looks modern.
The `lambda v=..., b=btn1` captures the current values of `total` and `btn1`
at the time the row is built — without this, the lambda would use whatever
those variables are at click time, which could be wrong.

### Result row

```python
row2 = tk.Frame(results_frame, bg=BG2)
row2.pack(fill="x", pady=2, padx=2)
```
Same structure as the Total row, just a second frame underneath.

```python
tk.Label(row2, text=f"$ {result:,.2f}", bg=BG2, fg=GREEN,
         font=FONT_LG, anchor="w").pack(side="left", padx=12, pady=6)
```
The result amount in bright green — visually distinct from the Total.

```python
tk.Label(row2, text=formula, bg=BG2, fg=FG_DIM,
         font=FONT_SM).pack(side="left", padx=(0, 8))
```
The formula in small dimmed text — e.g. `$3,870.00 − $770.00` — so you can
verify the calculation at a glance without it drawing attention.

```python
btn2 = tk.Button(row2, text="Copy", bg=BLUE, fg="white",
                 font=FONT_SM, relief="flat", padx=8, pady=3)
btn2.config(command=lambda v=result_str, b=btn2: copy_val(v, b))
btn2.pack(side="right", padx=(2, 10))
```
Copy button for the result. Same pattern as `btn1` — `result_str` (no commas)
is what actually goes to the clipboard.

```python
status.config(text="")
```
Clear any previous error message now that everything worked.

---

## clear_all(event=None)

```python
def clear_all(event=None):
    for w in results_frame.winfo_children():
        w.destroy()
    status.config(text="")
```

`winfo_children()` returns a list of everything inside `results_frame`.
Looping and calling `.destroy()` on each one removes the rows from the window.
`event=None` means this function works both as a button command and as a
keyboard binding (Escape passes an event object, a button call passes nothing).

---

## Window setup

```python
root = tk.Tk()                      # create the main window
root.title("Invoice Calculator")    # window title bar text
root.resizable(False, False)        # lock width and height — no resizing
root.attributes("-topmost", True)   # keep window above all other apps
root.configure(bg=BG)               # set the background colour
```

```python
top = tk.Frame(root, bg=BG)
top.pack(fill="x", padx=12, pady=10)
```
A frame for the top bar (Smart Paste, Clear, status message).
`fill="x"` stretches it across the full window width.

```python
tk.Button(top, text="Smart Paste", command=smart_paste, ...).pack(side="left")
tk.Button(top, text="Clear", command=clear_all, ...).pack(side="left", padx=(6, 0))
```
Both buttons packed to the left. `padx=(6, 0)` adds a 6px gap on the left of
Clear only, putting a small space between the two buttons.

```python
status = tk.Label(top, text="", bg=BG, fg=FG_DIM, font=FONT_SM)
status.pack(side="left", padx=10)
```
The status label starts empty. It's updated by `smart_paste` and `clear_all`
to show errors or be blanked out.

```python
results_frame = tk.Frame(root, bg=BG)
results_frame.pack(fill="x", padx=10, pady=(0, 10))
```
The container where the two result rows get built. Starts empty —
rows are added by `smart_paste` and removed by `clear_all`.

```python
root.bind("<Escape>", clear_all)
root.mainloop()
```
`bind` wires the Escape key to `clear_all` for the whole window.
`mainloop()` starts the event loop — the app sits here waiting for clicks
and keypresses until the window is closed.
