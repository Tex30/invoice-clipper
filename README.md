# invoice-clipper

Paste invoice text, instantly get the values you need ready to copy into Dataforce ASAP. Built with Python's standard library — no installs required to run from source.

---

## What it does

- Finds the Total (inc GST) and VEEC rebate automatically by keyword
- Calculates `Total − VEEC` and shows both results with Copy buttons
- Formula shown below the result for visual verification
- STC rebate is ignored (handled separately in ASAP)
- Always-on-top window so it floats over other apps while you work

**Workflow:**
1. Copy the relevant section from the invoice
2. Click **Smart Paste**
3. Two rows appear — Total and the result
4. Click Copy on each when you're at the right field in ASAP

---

## Download

Grab the latest `InvoiceCalc.exe` from the [Releases](../../releases) page.
No Python required — just download and run.

---

## Running from source

Requires Python 3 (standard library only — no pip installs needed).

```
python invoice_calc.py
```

---

## Build the exe yourself

```
pip install pyinstaller
pyinstaller --onefile --windowed --name "InvoiceCalc" invoice_calc.py
```

Output will be in the `dist/` folder.

---

## How it works

See [how_it_works.md](how_it_works.md) for a line-by-line explanation of the code.

---

## Requirements

- Python 3.x (if running from source)
- Windows
- No third-party packages
