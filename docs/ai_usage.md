# AI ("SI") usage

The NASA Space Apps Challenge allows Artificial Intelligence (called *SI* in the
rules) to **accelerate** work, but not to **come up with the idea** for the
solution. AI-generated code, data, images and audio must be acknowledged. This
file records, as specifically as possible, what AI did in this project and
what it did not do.

## Rules we follow

| Rule (Space Apps Project Submission Guide) | How this project complies |
|---|---|
| AI must not be used to come up with the solution idea | The challenge, the game concept and the design were decided by the team (see [Origin of the idea](#origin-of-the-idea)) |
| AI-generated code and data must be acknowledged in the description and in metadata | Listed below and in the project description on the Space Apps site |
| AI-generated images and videos must carry a visible watermark | The slides that used AI carry a notice in their footer; so does `assets/images/how_it_works/page_1.png` |
| AI-generated audio must be acknowledged | See [Declared AI use by the team](#declared-ai-use-by-the-team) |
| AI content must not use or modify NASA branding | No NASA logo or insignia is used or generated |

## Origin of the idea

The idea is the team's own:

| Date (2026) | Decision taken by the team |
|---|---|
| 1–5 Nov | Team vote on two candidate challenges; *Space Mission Design Game* chosen as the backup |
| 13 Nov | New vote after the challenges were published; the *Space Mission Design Game* won |
| 14 Nov | Game name *for_astronaut* (Irene); five-phase mission plan (Lucas Contreiras); Reigns-style two-choice cards (Rafael) |
| 14 Nov | Pixel-art astronaut with six emotions, menu and scenery drawn by hand (Irene) |
| 14 Nov | Five critical events with hidden outcomes (Rafael, pull request #3) |

## Declared AI use by the team

| Member | Tool | What AI did | What the person did |
|---|---|---|---|
| Lucas Contreiras | Claude, GitHub Copilot | Generated the main game code from the team's design and helped with the Android build scripts | Defined the phases and mechanics, reviewed and integrated the code |
| Irene Mothio | Claude | Helped polish the main menu and turn her designs into the story slides | Drew all the pixel art by hand; designed the menus and slides |
| Rafael Bueno | *To be confirmed* | | |
| Ronivaldo Andrade | Claude Code | See the log below | Requested, reviewed and approved each change |

## AI contribution log

Each entry records one piece of work done with AI assistance.

### 2026-11-15 — Repository organisation (Claude Code)

**Requested by:** Ronivaldo Andrade. **Branch:** `chore/project-structure`.

What the AI did:

- Moved every image to `assets/images/` and every sound to `assets/audio/`,
  grouped by screen, with English lowercase `snake_case` names
  (old → new names in [assets.md](assets.md)).
- Updated **only the asset paths** in `for_astronaut.py` and
  `for_astronaut_mobile/for_astronaut.py` (the `ASSET_FILES` file names and the
  `os.path.join(...)` calls in `init()`).
- Added `.gitignore`, a root `requirements.txt` and the automated tests in
  `tests/`.
- Wrote the documentation in `docs/`.
- Merged the latest `main` into the branch and moved the three new
  "how it works" images to the new layout (files unchanged).
- Renamed the "how it works" buttons uploaded to `assets/images/how_it_works/`
  to `button.png` and `button_pressed.png` and removed the identical copies
  from `mission_modes/` (files unchanged; no code uses them yet).

What the AI did **not** do:

- It did not change game logic, rules, physics, scoring, events, texts,
  artwork or sounds.
- It did not take part in choosing the challenge, the idea or the game design.

How the result was checked: 15 seeded games per edition were played headless
before and after the change. Every rendered frame and every loaded image and
sound was byte-identical, and the real entry points ran normally.

## Template for new entries

```markdown
### YYYY-MM-DD — <work> (<AI tool>)

**Requested by:** <name>.

What the AI did:
- ...

What the AI did not do:
- ...

How the result was checked: ...
```

## Text for the Space Apps "AI/SI Usage" section

> We used Claude and GitHub Copilot to assist with writing the game code from
> the mechanics, phases and physics model our team designed. Claude also
> helped polish the menu artwork into the presentation slides and, through
> Claude Code, organised the repository and wrote tests and documentation.
> The challenge, the game idea, the card mechanics, the pixel art and the
> critical events were created by the team. The team reviewed and validated
> all AI-assisted material.

Update this text when the table above is completed.
