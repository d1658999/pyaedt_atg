@echo off
echo ===================================================
echo   Building Standalone Executable for PyAEDT Tool
echo ===================================================

echo Activating virtual environment (.venv)...
call .venv\Scripts\activate.bat

echo Installing PyInstaller if not present...
pip install pyinstaller

echo Running PyInstaller...
pyinstaller --clean --onefile --noconsole --collect-all ansys.api.edb --copy-metadata ansys-tools-common --copy-metadata ansys-api-edb --copy-metadata ansys-edb-core --copy-metadata pyedb --copy-metadata pyaedt --name="PyAEDT_Config_Tool" main_gui.py

echo Build completed. Check the dist folder.
pause
