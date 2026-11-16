# Architecture

## Repository layout

```text
for_astronaut/
├── for_astronaut.py            # Desktop edition (1000x760 window) — entry point
├── requirements.txt            # Runtime dependency: pygame
├── assets/
│   ├── images/
│   │   ├── astronaut/          # Pixel-art astronaut, one file per emotion
│   │   ├── menus/              # Title screen artwork
│   │   ├── mission_modes/      # "Choose your mission" menu pieces
│   │   ├── how_it_works/       # "How it works" button and pages
│   │   ├── difficulty/         # Difficulty menu pieces
│   │   ├── scenery/            # Earth, Moon and rocket backgrounds
│   │   └── player_count/       # Reserved for a future player-count menu
│   └── audio/                  # Sound effects and theme music
├── for_astronaut_mobile/       # Mobile edition (landscape 1280x720, Android via Buildozer)
│   ├── main.py                 # Buildozer entry point (imports for_astronaut.main)
│   ├── for_astronaut.py        # Mobile copy of the game
│   ├── buildozer.spec          # Android packaging settings
│   └── assets/images/          # Copy of the desktop images it ships
├── tests/                      # Headless automated tests
├── docs/                       # This documentation
└── .github/workflows/android.yml   # CI job that builds the APK
```

## Two editions

The game logic lives in a single module per edition:

| Edition | File | Screen | Extra |
|---|---|---|---|
| Desktop / web | `for_astronaut.py` | 1000x760 window | Sound effects and theme music |
| Mobile | `for_astronaut_mobile/for_astronaut.py` | 1280x720 logical canvas, scaled (`SCALED`) | Touch controls, no audio yet |

The mobile folder is self-contained because Buildozer packages only the
contents of `for_astronaut_mobile/` (`source.dir = .`). That is why it keeps
its own copy of `assets/images/`. The test `tests/test_assets.py` checks that
both copies stay identical.

## How assets are loaded

Both editions resolve asset paths relative to the game file itself, not to the
current working directory, so the game starts from any folder:

```python
asset_dir = os.path.dirname(os.path.abspath(__file__))       # mobile
asset_dir = getattr(sys, '_MEIPASS', os.path.dirname(...))   # desktop (also works inside a PyInstaller bundle)

os.path.join(asset_dir, 'assets', 'images', 'menus', 'main_menu.png')
os.path.join(asset_dir, 'assets', 'images', 'astronaut', filename)   # filename from ASSET_FILES
os.path.join(asset_dir, 'assets', 'audio', fname)                    # sound effects
os.path.join(asset_dir, 'assets', 'audio', 'theme.ogg')              # music
```

Images are required: a missing image stops the game at start-up. Sounds and
music are optional: the desktop edition checks `os.path.exists` and simply
plays without the missing sound.

## Naming conventions

- Python modules and every asset file and folder use lowercase `snake_case`
  (PEP 8 style), in English.
- Image folders group files by the screen that uses them; sound files are
  named after the event that plays them (`alarm`, `card`, `click`, ...).
