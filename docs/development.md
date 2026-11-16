# Development guide

## Requirements

- Python 3.10 or newer
- [pygame](https://www.pygame.org/) 2.5 or newer

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Running the game

```bash
python for_astronaut.py                     # desktop edition
python for_astronaut_mobile/main.py         # mobile edition on a desktop screen
```

Both editions find their assets relative to their own file, so they can be
started from any directory.

## Running the tests

The tests run without a window or sound card (SDL dummy drivers), so they work
in a terminal or in CI:

```bash
python -m unittest discover -s tests -v
```

| Test | What it checks |
|---|---|
| `tests/test_assets.py::test_names_are_snake_case` | Every asset folder and file under `assets/` uses lowercase `snake_case` |
| `tests/test_assets.py::test_mobile_images_match_desktop` | The images copied into `for_astronaut_mobile/assets/` are byte-identical to the desktop ones |
| `tests/test_smoke.py::test_desktop` | The desktop edition starts, loads its 7 images, 6 sounds and the theme music, and plays 5 seeded games with random choices to the results screen |
| `tests/test_smoke.py::test_mobile` | The same for the mobile edition (images only; it has no audio yet) |

A failing smoke test usually means an asset path is wrong (an image raises
`FileNotFoundError`; a missing sound shows up as a missing key in `SND`).

## Packaging

### Web (itch.io)

The public build is published on itch.io. Whoever rebuilds it must include the
whole `assets/` folder next to `for_astronaut.py`.

### Windows executable (PyInstaller)

The desktop edition reads `sys._MEIPASS`, so it works from a PyInstaller
bundle. Bundle the `assets/` folder with the same relative path:

```bash
pyinstaller --onefile --windowed --add-data "assets:assets" for_astronaut.py
# On Windows the separator is ';':  --add-data "assets;assets"
```

### Android APK (Buildozer)

The GitHub Actions workflow `.github/workflows/android.yml` builds the APK
whenever something under `for_astronaut_mobile/` changes. Locally:

```bash
cd for_astronaut_mobile
buildozer android debug             # APK is written to for_astronaut_mobile/bin/
```

`buildozer.spec` packages `py`, `png` and `md` files from
`for_astronaut_mobile/` and its sub-folders, which includes
`assets/images/`.

## The user manual

The manual exists in three forms with the same content:

| File | Role |
|---|---|
| `docs/manual.md` | Source of truth; read it on GitHub |
| `docs/manual.pdf` | Laid-out version for reading and printing, **generated** from `manual.md` (never edited by hand) |
| `docs/manual.tex` | LaTeX version, so anyone can rebuild a PDF from the repository with a standard TeX distribution |

`manual.pdf` is produced by a small Markdown-to-PDF script (Python `markdown` +
WeasyPrint) that is kept outside this repository. To rebuild a PDF from the
repository alone, use the LaTeX version:

```bash
latexmk -pdf -outdir=build docs/manual.tex     # PDF in build/manual.pdf
```

When the manual changes, edit `manual.md`, mirror the change in `manual.tex`
and regenerate `manual.pdf`.

Both layouts follow the game's visual identity: navy `#1B1441` background,
violet `#614AD3` (the menu buttons), yellow `#FFFF00` (the `_` in the logo),
pixel stars and the pixel-art astronaut `assets/images/astronaut/waving.png`
on the cover. NASA branding is not used.

## Conventions

- Code, comments, documentation and file names in English.
- Asset names: lowercase `snake_case` (see [assets.md](assets.md)).
- Changes go through a branch and a pull request; `main` is never pushed to
  directly.
- Run the tests before opening a pull request.
