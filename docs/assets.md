# Assets

All assets live under `assets/`. The mobile edition keeps an identical copy of
the images it ships in `for_astronaut_mobile/assets/images/` (the "how it
works" images exist only in the desktop edition).

**Used by code** tells whether the current game loads the file. Artwork that
is not used yet was delivered for menus planned for later versions.

## Images

| Path (`assets/images/…`) | Previous name | Content | Used by code |
|---|---|---|---|
| `astronaut/simple.png` | `astronauta-simples.png` | Astronaut, neutral | Yes (`ASSET_FILES['simple']`) |
| `astronaut/waving.png` | `astronauta-acenando.png` | Astronaut waving | Yes |
| `astronaut/very_happy.png` | `astronauta-mt-feliz.png` | Astronaut very happy | Yes |
| `astronaut/angry.png` | `astronauta-bravo.png` | Astronaut angry | Yes |
| `astronaut/very_angry.png` | `astronauta-muitobravo.png` | Astronaut very angry | Yes |
| `astronaut/space.png` | `astronauta-espaco.png` | Astronaut floating in space | Yes |
| `menus/main_menu.png` | `menu-completo.png` | Title screen with the PLAY button | Yes (`A['menu']`) |
| `mission_modes/choose_your_mission.png` | `menu_modos/choose your mission.png` | "Choose your mission" title | Not yet |
| `mission_modes/mission_types_menu.png` | `menu_modos/tipos-de-missao-menu].png` | Mission-type menu background | Not yet |
| `mission_modes/observe_earth_button.png` | `menu_modos/botao-observe-earth.png` | "Observe Earth" button | Not yet |
| `mission_modes/earth_button_pressed.png` | `menu_modos/apertado-earth.png` | "Observe Earth" button, pressed | Not yet |
| `mission_modes/study_moon_button.png` | `menu_modos/botao-study-moon.png` | "Study the Moon" button | Not yet |
| `mission_modes/moon_button_pressed.png` | `menu_modos/apertado-moon.png` | "Study the Moon" button, pressed | Not yet |
| `how_it_works/button.png` | `menu_modos/botao-howitworks.png` | "How it works" button | Yes, desktop (`A['how_btn']`) |
| `how_it_works/button_pressed.png` | `menu_modos/apertado-howitworks.png` | "How it works" button, pressed | Yes, desktop (`A['how_btn_pressed']`) |
| `how_it_works/page_1.png` | `menu_modos/pag1-howitworks.png` | "How it works" page 1 (trade-offs: cost, mass, schedule). Carries the notice *Layout generated with AI (Claude) from original designs by Irene* | Yes, desktop (`A['how_page']`) |
| `difficulty/configure_mission_difficulty.png` | `dificuldades/configurate mission dificuty.png` | "Configure mission difficulty" title | Not yet |
| `difficulty/difficulty_menu.png` | `dificuldades/menu-dificuldade.png` | Difficulty menu background | Not yet |
| `difficulty/easy_button.png` | `dificuldades/easy-botao.png` | Easy button | Not yet |
| `difficulty/easy_description.png` | `dificuldades/easy-description.png` | Easy description | Not yet |
| `difficulty/medium_button.png` | `dificuldades/medium-botao.png` | Medium button | Not yet |
| `difficulty/medium_description.png` | `dificuldades/medium-description.png` | Medium description | Not yet |
| `difficulty/hard_button.png` | `dificuldades/gard-botao.png` | Hard button | Not yet |
| `difficulty/hard_description.png` | `dificuldades/hard-descripcion.png` | Hard description | Not yet |
| `scenery/earth_scene.png` | `Cenários/cenario-terra.png` | Earth scene | Not yet |
| `scenery/earth_background.png` | `Cenários/fundo-terra.png` | Earth background | Not yet |
| `scenery/moon_scene.png` | `Cenários/cenario-lua.png` | Moon scene | Not yet |
| `scenery/moon_background.png` | `Cenários/fundo-lua.png` | Moon background | Not yet |
| `scenery/rocket_scene.png` | `Cenários/cenario-foguete.png` | Rocket scene | Not yet |
| `scenery/rocket_background.png` | `Cenários/fundo-foguete.png` | Rocket background | Not yet |
| `scenery/game_frame.png` | `Cenários/retangulo-jogo.png` | Card/game frame rectangle | Not yet |
| `player_count/.gitkeep` | `numero-jogadores/a` | Placeholder for a future menu | — |

## Audio (desktop edition)

| Path (`assets/audio/…`) | Previous name | Played when | Used by code |
|---|---|---|---|
| `theme.ogg` | `Audios/Theme.ogg` | Background music, looped | Yes |
| `card.wav` | `Audios/Card.wav` | Previewing a card (first press / leaning to one side) | Yes (`SND['card']`) |
| `click.wav` | `Audios/Click.wav` | Confirming a choice, PLAY, continuing, restarting | Yes (`SND['click']`) |
| `rocket.ogg` | `Audios/Rocket.ogg` | Looped during the launch animation (trimmed in code to 0.65–1.55 s, faded out) | Yes (`SND['rocket']`) |
| `compatible.wav` | `Audios/Compatible.wav` | Launcher compatibility check passed; successful mission on the results screen | Yes (`SND['success']`) |
| `failure.wav` | `Audios/Failure.wav` | Launcher not compatible; failed mission on the results screen | Yes (`SND['fail']`) |
| `alarm.wav` | `Audios/Alarm.wav` | A critical (alert) event card appears | Yes (`SND['alarm']`) |

## Authorship and licences

Space Apps requires every third-party resource (code, image, audio, text) to be
listed, even free ones. The full credits, with links, are in
[CREDITS.md](../CREDITS.md).

| Asset group | Author / source | Licence | Confirmed |
|---|---|---|---|
| Astronaut pixel art, menus, mission modes, difficulty, scenery | Irene Mothio | | Pending |
| "How it works" page (`how_it_works/page_1.png`) | Layout generated with AI (Claude) from original designs by Irene (notice on the image) | | Pending |
| `theme.ogg` | Yoiyami (OpenGameArt) | CC0 1.0 | Yes |
| `card.wav`, `click.wav`, `rocket.ogg` | el_boss, SignatureSoundsOrg, derplayer (Freesound) | CC0 1.0 | Yes |
| `compatible.wav` | grunz (Freesound) | CC BY 3.0, credit required | Yes |
| `failure.wav`, `alarm.wav` | FunWithSound, newlocknew (Freesound) | CC BY 4.0, credit required | Yes |

## Adding a new asset

1. Put the file in the matching folder under `assets/` with a lowercase
   `snake_case` English name.
2. If it is an image used by the mobile edition, copy it to the same path under
   `for_astronaut_mobile/assets/`.
3. Load it with `os.path.join(asset_dir, 'assets', ...)` as described in
   [architecture.md](architecture.md).
4. Add a row to this file and, for third-party files, to `CREDITS.md`
   (author, link, licence). Prefer CC0 or CC BY; CC BY requires the credit.
5. Run the tests.
