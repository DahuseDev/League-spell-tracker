@echo off
REM This batch file builds the Spell Tracker application for Windows using PyInstaller.

REM Run PyInstaller to create a single executable without a console window
pyinstaller --onefile --noconsole SpellTracker.py

REM Move the generated executable to the release directory
move dist\SpellTracker.exe ./

REM Clean up the build files
rmdir /s /q build
rmdir /s /q dist
del SpellTracker.spec

echo Build completed. The executable is located in the release directory.