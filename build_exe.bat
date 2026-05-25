@echo off
echo ===================================================
echo   Building Standalone Executable for PyAEDT Tool
echo ===================================================

echo Activating virtual environment (.venv)...
call .venv\Scripts\activate.bat

echo Installing PyInstaller if not present...
pip install pyinstaller

echo Running PyInstaller...
pyinstaller --clean --onefile --noconsole --name="PyAEDT_Config_Tool" main_gui.py

echo Build completed. Check the dist folder.
pause
