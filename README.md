# for_astronaut

An English-language, single-player space-mission design game built with Python
and Pygame. It uses a Reigns-style decision flow: every card offers two
choices, and each choice has visible trade-offs that affect the next phase.

## Mission flow

1. **Mission briefing** — choose a science objective and program difficulty.
2. **Spacecraft assembly** — select structure, power, attitude control,
   computer, communications and science instruments while managing budget,
   dry mass, power and schedule.
3. **Orbit and launcher** — compare low Earth, polar, geostationary and lunar
   orbits, then verify launcher compatibility.
4. **Mission simulation** — launch, transfer and operate the spacecraft through
   random events. Manage battery energy, propellant and onboard data.
5. **Results** — receive science, cost, safety and creativity scores with
   feedback explaining the consequences of the design.

## Physics model

The game turns mission-design concepts into playable decisions:

- Tsiolkovsky's rocket equation: `delta-v = Isp * g0 * ln(m0 / mf)`.
- Circular-orbit speed and period: `v = sqrt(mu / r)` and
  `T = 2 * pi * sqrt(r^3 / mu)`.
- Battery accounting: `energy (Wh) = power (W) * time (h)`.
- Communication capacity: `data = rate * contact time`.
- Dynamic pressure: `q = 1/2 * rho * v^2`.
- A numerical rotating-frame Lagrange model estimates the Earth-Moon L1
  point for the lunar-orbit briefing.

Empty stages and spent propellant are visibly dropped during the launch
animation, so the spacecraft becomes lighter as the mission progresses.

## Run locally

```bash
python -m pip install -r requirements.txt
python for_astronaut.py
```

Click the `PLAY` button on the supplied menu artwork (or press `Space`) to
start. Use the mouse or arrow keys to preview and select choices. The
astronaut sprites react to mission decisions, risks, flight stages and results.
Press `Space` to continue through briefings and completed flight animations,
`R` to restart on the results screen, and `Esc` to quit.

## Project structure

```text
for_astronaut.py         Desktop edition (entry point)
assets/images/           Artwork (astronaut, menus, mission modes, difficulty, scenery)
assets/audio/            Sound effects and theme music
for_astronaut_mobile/    Landscape mobile edition and Android packaging
tests/                   Headless automated tests
docs/                    Architecture, assets, development guide and AI usage
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Documentation

See [`docs/`](docs/README.md), including the record of how AI was and was not
used in this project: [`docs/ai_usage.md`](docs/ai_usage.md).

## NASA references

The mission structure, orbital concepts, visualization direction and
educational game style were informed by:

- [Design and Develop a Science Mission webinar](https://www.nasa.gov/wp-content/uploads/2025/04/250323-design-and-develop-science-mission.pdf)
- [NASA Software: GSC-19468-1](https://software.nasa.gov/software/GSC-19468-1)
- [NASA Goddard Mission Design Lab](https://etd.gsfc.nasa.gov/capabilities/integrated-design-center/mission-design-lab/)
- [NASA Mission Viz](https://nasa.github.io/mission-viz/)
- [Webb: Build It Yourself](https://science.nasa.gov/mission/webb/game-build-it-yourself/)

These are design references only; the game does not require network access
after installation.
