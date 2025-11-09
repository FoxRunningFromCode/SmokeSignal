Packaging instructions — SmokeSignal

This folder contains helper scripts and templates to produce a Windows executable and installer.

Quick start (Windows PowerShell)
1. From the repository root run (PowerShell):
   .\tools\build_windows_installer.ps1

2. The script will create a virtual environment (.venv_build), install requirements and pyinstaller, and run pyinstaller to build the app into `dist\SmokeSignal`.

3. If you have Inno Setup installed (ISCC.exe on PATH), the script will then compile `installer\SmokeSignal.iss` to create a Windows installer in `installer_output`.

Notes & tips
- If you want a single-file executable, re-run the script with the -OneFile flag:
  .\tools\build_windows_installer.ps1 -OneFile

- The generated exe will be created by PyInstaller. Packaging PyQt6 apps may need additional hidden imports or data files. If you run into errors related to missing Qt plugins (platforms, svg, etc.), add `--add-binary` or include the `PyQt6` plugins directory in the installer step.

- Logo: place a 256x256 PNG at `resources\logo.png` to include it on the PDF front page and optionally as an installer icon.

- Inno Setup: to customize the installer appearance/change icons/edit license text, edit `installer\\SmokeSignal.iss`.

Troubleshooting
- If the executable crashes with missing libraries (DLLs), inspect the build output under `build\` and `dist\SmokeSignal` to see what was included. You may need to add specific files using `--add-binary` or hidden imports.

Advanced: generate an MSI or signed installer
- For code signing and MSI creation consider using signtool.exe and WiX Toolset; these are outside the scope of this script but can be added.

If you want, I can:
- Add a CI workflow (GitHub Actions) to create releases/windows installers automatically.
- Create a more robust PyInstaller spec file tuned for PyQt6 and ReportLab.
- Add an installer icon and license page to the Inno Setup script.
