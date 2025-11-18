@echo off
echo Building Dani's Level Editor...
echo.

REM Create dist and build directories if they don't exist
if not exist "dist" mkdir dist
if not exist "build" mkdir build

echo Building level editor (level_editor.py)...
pyinstaller --onefile --windowed --icon=editor.ico --name="Dani_Level_Editor" ^
    level_editor.py

echo.
echo.
echo Copying maps folder to distribution...
if exist "maps" (
    if not exist "dist\maps" mkdir dist\maps
    copy maps\*.json dist\maps\
    echo Maps folder copied to dist\maps\
) else (
    echo Warning: maps folder not found!
)

echo.
echo Editor build complete! 
echo Editor executable: dist\Dani_Level_Editor.exe
echo Maps folder: dist\maps\
echo.
echo The editor will read and write to the external maps folder.
echo Ready to distribute!
pause