# 🎮 Dani's Platformer Adventure

Egy átfogó 2D platformer játék teljes szerkesztő eszközökkel, fejlett trigger rendszerekkel és építési automatizálással.

## 📖 Áttekintés

Ez a projekt egy teljes értékű platformer játékot tartalmaz professzionális szintű level szerkesztővel. A játék pygame alapú, fejlett fizikai motorral, trigger rendszerekkel és PyInstaller kompatibilis build rendszerrel rendelkezik.

### ✨ Főbb Funkciók

- **🎯 Platformer Játék**: Komplex fizikai motor gravitációval, ugrásmechanikával és ütközésérzékeléssel
- **🛠️ Level Szerkesztő**: Professzionális szintű szerkesztő eszköz komplex akció rendszerekkel
- **⚙️ Trigger Rendszer**: Fejlett trigger-akció kapcsolatok többszörös műveletekkel és késleltetéssel
- **🚀 Build Automatizálás**: Különálló build scriptek játékhoz és szerkesztőhöz
- **💾 JSON Map Formátum**: Strukturált level fájlok kompatibilitási réteggel

## 🔧 Rendszerkövetelmények

### Szoftver Követelmények
- **Python 3.7+**
- **Pygame 2.6.1+**
- **PyInstaller** (építéshez)
- **PIL/Pillow** (képkezeléshez)
- **tkinter** (dialógusokhoz - általában Python-nal települ)

### Hardver Követelmények
- **CPU**: Modern 64-bit processzor
- **RAM**: Minimum 512 MB szabad memória
- **Tárhely**: ~50 MB (fejlesztési környezet), ~20 MB (telepített játék)
- **Grafika**: DirectX 9.0c kompatibilis videókártya

## 📦 Telepítés és Építés

### 1. Függőségek Telepítése

```powershell
# Python csomagok telepítése
pip install pygame pillow pyinstaller

# Vagy requirements file használatával (ha létrehozod)
pip install -r requirements.txt
```

### 2. Közvetlen Futtatás (Fejlesztői Mód)

```powershell
# Játék indítása
python dani_jatek.py

# Level szerkesztő indítása
python level_editor.py

# Humor módok (easter eggs)
python humor.py    # Fullscreen humor
python humor2.py   # Ablak spam
```

### 3. Építés Végrehajtható Fájlokhoz

#### 🎮 Játék Építése
```powershell
# Futtatás
.\build_game.bat

# Vagy manuálisan
pyinstaller --onefile --windowed --icon=favicon.ico --name="Dani_Platformer_Game" ^
    --add-data="char.png;." ^
    --add-data="humor.png;." ^
    --add-data="humor.mp3;." ^
    --add-data="bg_music.mp3;." ^
    --hidden-import=PIL --hidden-import=PIL.Image --hidden-import=PIL.ImageTk ^
    dani_jatek.py
```

#### 🛠️ Level Szerkesztő Építése
```powershell
# Futtatás
.\build_editor.bat

# Vagy manuálisan
pyinstaller --onefile --windowed --icon=editor.ico --name="Dani_Level_Editor" level_editor.py
```

### 4. Végleges Telepítés

Építés után:
```
dist/
├── Dani_Platformer_Game.exe    # Fő játék
├── Dani_Level_Editor.exe       # Level szerkesztő
└── maps/                       # Level fájlok mappa
    ├── test_level.json
    └── orosházáról.json
```

## 🎮 Játék Funkciók

### Alapvető Játékmenet
- **WASD / Nyíl billentyűk**: Mozgás és ugrás
- **Gravitáció és Fizika**: Valósághű esés és platformra ugrás
- **Ütközésérzékelés**: Minden irányú ütközés (fej, oldalak, lábak)
- **Pinch Detection**: Összecsípés érzékelés mozgó platformok között
- **Életrendszer**: 3 élet újraindítási lehetőséggel

### Fejlett Funkciók
- **Kamera Követés**: Smooth kamera mozgás a játékossal
- **Tile-based Rendering**: Optimalizált grafikai megjelenítés
- **Háttérzene**: Automatikus betöltés és lejátszás hangerő kontrolllal
- **Visual Feedback**: Immediate válasz trigger aktiválásokra

### Objektum Típusok
- **Yellow Blocks**: Szilárd platformok
- **Spikes**: Veszélyes akadályok (életvesztés)
- **Trigger Boxes**: Láthatatlan trigger területek
- **Pits**: Szakadékok (automatikus újraindítás)
- **Flag**: Szint befejezési pont

## 🛠️ Level Szerkesztő

### Használat
```powershell
# Szerkesztő indítása
python level_editor.py
# vagy
dist/Dani_Level_Editor.exe
```

### 🎨 Szerkesztő Irányítás

#### Alap Eszközök
- **1**: Yellow Block eszköz
- **2**: Pit (szakadék) eszköz  
- **3**: Flag (zászló) elhelyezés
- **4**: Start pozíció beállítás
- **5**: Spike (tüske) eszköz
- **6**: Trigger Box eszköz
- **7**: Delete/Erase eszköz
- **8**: Action Mode (trigger-akció szerkesztés)

#### Kamera és Nézet
- **WASD / Arrow Keys**: Kamera mozgatás
- **G**: Grid be/kikapcsolás
- **Mouse Wheel**: Zoom (ha implementált)

#### Fájl Műveletek
- **Enter**: Level mentése (névvel)
- **L**: Level betöltése (névvel)
- **N**: Új level létrehozása
- **T**: Level tesztelése a főjátékban
- **Ctrl+Z**: Undo (visszavonás)
- **Ctrl+Y**: Redo (újra)

### 🔧 Action Mode (Trigger Rendszer)

#### Trigger-Akció Kapcsolatok
1. **8 billentyű**: Action Mode aktiválása
2. **Klik trigger boxra**: Trigger kiválasztása
3. **Klik objektumra**: Célpont objektum kiválasztása
4. **Dialógus ablak**: Akció típusok beállítása

#### Támogatott Akciók
- **Appear**: Objektum megjelenítése
- **Disappear**: Objektum elrejtése
- **Move**: Objektum mozgatása új pozícióra

#### Fejlett Funkciók
- **Multiple Actions**: Egy trigger több akciót is végrehajthat
- **Delay System**: Akciók késleltetett végrehajtása
- **Duration Control**: Akció időtartam beállítása
- **Visual Indicators**: Kapcsolatok és ghost objektumok megjelenítése

### 📋 Level Validáció
A szerkesztő automatikusan ellenőrzi:
- **Flag jelenlét**: Minden levelnél szükséges befejező pont
- **Start pozíció**: Játékos kezdő pozíció megadva
- **Objektum konfliktusok**: Átfedő objektumok ellenőrzése

## 🗃️ Fájl Struktúra

```
csacska/
├── 📁 Core Game Files
│   ├── dani_jatek.py           # Fő játék motor
│   ├── level_editor.py         # Level szerkesztő
│   ├── humor.py               # Easter egg #1
│   └── humor2.py              # Easter egg #2
│
├── 📁 Build Scripts
│   ├── build_game.bat         # Játék építő script
│   └── build_editor.bat       # Szerkesztő építő script
│
├── 📁 Assets
│   ├── char.png              # Játékos karakter
│   ├── humor.png             # Humor kép
│   ├── horher.png            # Humor2 kép
│   ├── humor.mp3             # Humor hang
│   ├── bg_music.mp3          # Háttérzene
│   ├── favicon.ico           # Játék ikon
│   └── editor.ico            # Szerkesztő ikon
│
├── 📁 Maps
│   ├── test_level.json       # Teszt level
│   └── orosházáról.json      # Egyéni level
│
└── 📁 Documentation
    ├── README.md             # Ez a fájl
    └── ACTION_SYSTEM_FIXED.md # Akció rendszer dokumentáció
```

## 📝 Map Formátum (JSON)

### Alapvető Struktúra
```json
{
  "name": "Level Név",
  "start_position": {"x": 100, "y": 460},
  "yellow_blocks": [...],
  "pits": [...],
  "spikes": [...],
  "trigger_boxes": [...],
  "flag": {"x": 1200}
}
```

### Trigger Akció Formátum
```json
{
  "trigger_boxes": [{
    "id": 26,
    "x": 220, "y": 460,
    "width": 140, "height": 20,
    "actions": {
      "object_id": [{
        "action": "move",
        "duration": 2.0,
        "delay": 1.5,
        "target_x": 500,
        "target_y": 300
      }]
    },
    "enabled": true
  }]
}
```

### Backward Compatibility
A rendszer automatikusan kezeli:
- **Régi single-action formátum**: `"actions": {"id": {"action": "move"}}`
- **Új multi-action formátum**: `"actions": {"id": [{"action": "move"}]}`

## 🔧 Fejlesztői Információk

### Architektúra
- **GameObject**: Alap objektum osztály pozíció és láthatósági állapottal
- **Platform**: Platformok speciális ütközésérzékeléssel
- **TriggerBox**: Trigger logika akció végrehajtással
- **Camera**: Smooth követési rendszer
- **Game**: Fő játék állapot menedzsment

### Konfigurálható Paraméterek
```python
# dani_jatek.py - Játék konstansok
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRAVITY = 0.8
JUMP_STRENGTH = -15
PLAYER_SPEED = 5
BG_MUSIC_VOLUME = 0.2

# level_editor.py - Szerkesztő konstansok
GRID_SIZE = 20
CAMERA_SPEED = 10
GROUND_Y = 560
```

### Debugging
- **Debug Mode**: `self.debug_mode = True` a Game osztályban
- **Console Output**: Részletes trigger és akció logolás
- **Visual Indicators**: Szerkesztőben kapcsolatok és ghost objektumok

## 🚨 Troubleshooting

### Gyakori Problémák

#### "Module not found" hibák
```powershell
# Függőségek újratelepítése
pip install --upgrade pygame pillow pyinstaller
```

#### PyInstaller build hibák
```powershell
# Temp fájlok törlése
rmdir /s build dist
rmdir /s __pycache__

# Újra build
.\build_game.bat
```

#### Audio/grafikai hibák
- Ellenőrizd hogy minden asset fájl létezik
- Győződj meg róla, hogy a resource_path() funkció helyesen működik
- Teszteld előbb fejlesztői módban

#### Level betöltési hibák
```json
# Ellenőrizd JSON szintaxis érvényességét
# Használj JSON validátort online
```

### Performance Optimalizálás
- **Tile-based Rendering**: Csak látható objektumok rajzolása
- **Camera Culling**: Off-screen objektumok kihagyása
- **Efficient Collision**: Priority-based ütközésérzékelés

## 🎯 Jövőbeni Fejlesztések

### Tervezett Funkciók
- [ ] **Sound Effects**: Ugrás, ütközés, trigger hangok
- [ ] **Particle System**: Vizuális effektek megjelenéshez/eltűnéshez
- [ ] **Moving Platforms**: Automatikusan mozgó platformok
- [ ] **Power-ups**: Gyűjthető objektumok
- [ ] **Multiple Lives Display**: Grafikus életmutató
- [ ] **Level Selection Menu**: Telepített levelek listája

### Technikai Fejlesztések
- [ ] **Multiplayer Support**: Hálózati többjátékos mód
- [ ] **Custom Scripting**: Lua/Python script integráció
- [ ] **Animation System**: Sprite animációk
- [ ] **Physics Enhancement**: Fejlettebb fizikai motor
- [ ] **Mobile Support**: Touch control és mobil optimalizálás

## 👥 Közreműködés

### Fejlesztési Környezet
1. Repository klónozása
2. Virtuális környezet létrehozása
3. Függőségek telepítése
4. Kódolási stílus követése (PEP 8)

### Code Contribution
- **Bug Report**: Issue létrehozása leírással
- **Feature Request**: Új funkció javaslatok
- **Pull Request**: Kód változtatások merge-elése
- **Documentation**: README és komment fejlesztések

## 📄 Licenc

Ez a projekt oktatási és szórakozási célokat szolgál. 
- **Szabad felhasználás**: Személyes és oktatási projektekhez
- **Módosítás jogosultság**: Kód testreszabása és fejlesztése
- **Megosztási kötelezettség**: Eredeti forrás megjelölése javasolt

## 🙏 Köszönetnyilvánítás

- **Pygame Community**: Fantasztikus game development framework
- **PyInstaller Team**: Egyszerű executable generálás
- **Open Source Contributors**: Dependency könyvtárak
- **Beta Testers**: Játék tesztelés és feedback

---

**Készítette**: Dani & AI Team  
**Verziók**: Python 3.7+, Pygame 2.6.1+  
**Platform**: Windows, Linux, macOS  
**Utolsó frissítés**: November 2024

*Boldog játékélményt és sikeres level készítést! 🎮✨*