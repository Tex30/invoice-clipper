@echo off
:: Launch the Tools app (tabbed multi-tool GUI)
:: Tries pythonw first (no console window), falls back to python
cd /d "%~dp0"

:: Try pythonw in PATH
where pythonw >nul 2>&1
if %errorlevel%==0 (
    pythonw -m tools.main
    exit /b
)

:: Try Miniconda/Anaconda base environment
for %%P in (
    "%USERPROFILE%\miniconda3\pythonw.exe"
    "%USERPROFILE%\anaconda3\pythonw.exe"
    "%LOCALAPPDATA%\miniconda3\pythonw.exe"
    "%LOCALAPPDATA%\anaconda3\pythonw.exe"
) do (
    if exist %%P (
        %%P -m tools.main
        exit /b
    )
)

:: Fallback: python with hidden window
start /min "" python -m tools.main
