@echo off
echo Building Dani's Platformer Game...
echo.

REM Create dist and build directories if they don't exist
if not exist "dist" mkdir dist
if not exist "build" mkdir build

echo Building main game (dani_jatek.py)...
pyinstaller --onefile --windowed --icon=favicon.ico --name="Dani_Platformer_Game" ^
    --add-data="char.png;." ^
    --add-data="humor.png;." ^
    --add-data="humor.mp3;." ^
    --add-data="bg_music.mp3;." ^
    --hidden-import=PIL --hidden-import=PIL.Image --hidden-import=PIL.ImageTk ^
    dani_jatek.py

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
echo Game build complete! 
echo Game executable: dist\Dani_Platformer_Game.exe
echo Maps folder: dist\maps\
echo.
echo Game assets are embedded, maps folder is external.
echo Ready to distribute!
pause