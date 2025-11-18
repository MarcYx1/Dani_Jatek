@echo off
echo Building Dani's Platformer Game and Level Editor...
echo.

REM Create dist and build directories if they don't exist
if not exist "dist" mkdir dist
if not exist "build" mkdir build

echo Building main game (dani_jatek.py)...
pyinstaller --onefile --windowed --icon=favicon.ico --name="Dani_Platformer_Game" ^
    --add-data="char.png;." ^
    --add-data="humor.png;." ^
    --add-data="horher.png;." ^
    --add-data="humor.mp3;." ^
    --add-data="bg_music.mp3;." ^
    --add-data="maps;maps" ^
    --hidden-import=PIL --hidden-import=PIL.Image --hidden-import=PIL.ImageTk ^
    dani_jatek.py

echo.
echo Building level editor (level_editor.py)...
pyinstaller --onefile --windowed --icon=editor.ico --name="Dani_Level_Editor" ^
    --add-data="maps;maps" ^
    level_editor.py

echo.
echo Build complete! 
echo Game executable: dist\Dani_Platformer_Game.exe
echo Editor executable: dist\Dani_Level_Editor.exe
echo.

echo.
echo Assets are now embedded in the executables.
echo No additional files needed for distribution!
echo Ready to distribute!
pause