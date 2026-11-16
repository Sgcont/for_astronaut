# for_astronaut — user manual

How to install, start and play for_astronaut, the space-mission design card game: plan a science mission, build the spacecraft, pick an orbit and a launcher, fly it and read your score.

## 1. Play online

Open <https://buenosaas.itch.io/for-astronaut> in a browser and press **Play**. Nothing needs to
be installed.

## 2. Run on your computer

You need Python 3.10 or newer.

```bash
python -m pip install -r requirements.txt
python for_astronaut.py
```

A 1000x760 window opens with the title screen and the theme music.

To try the landscape mobile layout on a computer:

```bash
python for_astronaut_mobile/main.py
```

## 3. Controls

| Action | Mouse | Keyboard | Touch (mobile) |
|---|---|---|---|
| Start from the title screen | Click **PLAY** | `Space` or `Enter` | Tap **PLAY** |
| Preview an option | Move the mouse to the left or right half | `←` / `→` or `A` / `D` | Tap a side |
| Choose the previewed option | Click | Press the same key again | Tap the same side again |
| Continue a briefing or a finished flight | Click | `Space` or `Enter` | Tap |
| Restart on the results screen | — | `R` | — |
| Quit | Close the window | `Esc` | — |

## 4. How a mission works

Each card shows two options. Each option has a good **and** a bad side, and the
numbers on the card tell you how it changes your budget, mass, power, schedule
and science.

1. **Mission briefing**: choose the science objective and the program
   difficulty. The briefing sets your budget, dry-mass limit and deadline.
2. **Spacecraft assembly**: pick the structure, power, attitude control,
   computer, communications and instruments. Watch the status bar: dry mass
   against its limit, cost against budget, power used against power generated.
3. **Orbit and launcher**: choose the orbit (low Earth, polar, geostationary or
   lunar) and the launcher. The compatibility check compares what the launcher
   can lift to that orbit with your spacecraft's mass at liftoff.
   - **PASSED**: you see the margin and how well the orbit fits your
     objective.
   - **NOT COMPATIBLE**: the craft is too heavy for that launcher and orbit.
4. **Mission simulation**: watch the launch. Empty stages drop away and the
   rocket gets lighter. Then handle the events of the flight, including
   **critical events** (marked with an alarm) whose outcome is hidden until you
   choose. Keep an eye on battery, propellant and onboard data.
5. **Results**: read your scores and the feedback on what worked and what did
   not.

## 5. Reading the results

| Score | What raises it |
|---|---|
| Science (40%) | Instruments, an orbit that fits the objective, and data actually sent to Earth |
| Cost (20%) | Money left in the budget |
| Safety (25%) | Reliability and margins of power, mass, launcher capacity and fuel |
| Creativity (15%) | Bold or unusual choices |

The weighted total gives a grade: **S** (85 or more), **A** (70), **B** (55),
**C** (40) or **D** (below 40). A failed mission halves the total. A spacecraft
that never launches gets **F**.

## 6. Tips

- More mass needs more fuel, which needs a bigger rocket, which costs more and
  takes longer. Saving on one of cost, mass or schedule usually costs you on
  another.
- A powerful instrument is useless if the antenna cannot send its data home.
- Leave margin: a craft right at the mass or power limit has nothing left when
  an event goes wrong.

## 7. Common problems

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pygame'` | Run `python -m pip install -r requirements.txt` |
| `FileNotFoundError` for a `.png` file at start-up | The `assets/` folder is missing or incomplete; download the whole repository |
| The game runs but is silent | The files in `assets/audio/` are missing, or the computer has no audio output; the game still works without sound |
| The window does not fit the screen | Use the online version or the mobile layout, which scales to the screen |
