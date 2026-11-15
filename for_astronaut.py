"""
for_astronaut: a space mission design game (Pygame)

A Reigns-style card game. Every card has two options (left / right) and every
option has good AND bad consequences, shown as numbers so you can learn the
trade-offs. The whole mission uses simple real physics:
  - Tsiolkovsky rocket equation  dv = Isp * g0 * ln(m0 / mf)  (mass loss while
    burning propellant, empty tanks are dropped)
  - Circular orbits  v = sqrt(mu / r),  T = 2 * pi * sqrt(r^3 / mu)
  - Eclipse and battery energy (Wh = W x h), data = rate x time

Five phases: 1 Briefing, 2 Spacecraft assembly, 3 Orbit and launcher,
4 Mission simulation (launch, transit, science operations), 5 Results.

Run:   pip install pygame      then      python for_astronaut.py
Controls: move the mouse left/right (or press the arrow keys / A, D) to preview
an option, click (or press the key again) to choose. SPACE continues. ESC quits.

Background data comes from the NASA material the team collected (mission design
webinar, GMAT/mission-viz style orbit concepts, Webb "Build It Yourself" game).
"""
import math
import os
import random
import sys

import pygame

W, H = 1000, 760
G0 = 9.80665          # standard gravity (m/s^2)
DATA_CAP = 120        # onboard memory (Gb)
FONT_UI = "dejavusans,arial,helvetica,liberationsans"
FONT_MONO = "dejavusansmono,consolas,couriernew,liberationmono"
ASSET_FILES = {
    'simple': 'astronauta-simples.png',
    'very_angry': 'astronauta-muitobravo.png',
    'very_happy': 'astronauta-mt-feliz.png',
    'space': 'astronauta-espaco.png',
    'angry': 'astronauta-bravo.png',
    'waving': 'astronauta-acenando.png',
}

# NASA references used to shape the mission-design flow, orbit model and game
# interaction. The game remains self-contained and does not download them.
NASA_SOURCES = (
    "https://www.nasa.gov/wp-content/uploads/2025/04/250323-design-and-develop-science-mission.pdf",
    "https://software.nasa.gov/software/GSC-19468-1",
    "https://etd.gsfc.nasa.gov/capabilities/integrated-design-center/mission-design-lab/",
    "https://nasa.github.io/mission-viz/",
    "https://science.nasa.gov/mission/webb/game-build-it-yourself/",
)

C_BG = (7, 9, 20)
C_PANEL = (20, 26, 52)
C_LINE = (60, 74, 120)
C_TEXT = (230, 235, 250)
C_DIM = (140, 150, 185)
C_GOOD = (110, 220, 140)
C_BAD = (255, 110, 100)
C_WARN = (255, 190, 80)
C_ACC = (120, 190, 255)
C_CARD = (226, 205, 150)
C_INK = (50, 34, 22)

# fx key -> (label, unit, +1 if increasing is good, -1 if bad, 0 neutral)
FXINFO = {
    'cost': ('Cost', 'M$', -1), 'mass': ('Dry mass', 'kg', -1), 'puse': ('Power draw', 'W', -1),
    'pgen': ('Power output', 'W', 1), 'sci': ('Science', 'pts', 1), 'rel': ('Reliability', '%', 1),
    'time': ('Schedule', 'months', -1), 'batt': ('Battery size', 'Wh', 1), 'comm': ('Downlink rate', 'Mbps', 1),
    'dpc': ('Data per campaign', 'Gb', 0), 'prop': ('Station-keeping fuel', 'kg', 1),
    'energy': ('Battery charge', 'Wh', 1), 'fuel': ('Propellant', 'kg', 1), 'data': ('Onboard data', 'Gb', -1),
    'down': ('Data sent to Earth', 'Gb', 1),
}

# ---------------------------------------------------------------- orbits
ORB = {}
for _k, _name, _body, _alt, _dv, _dvup, _ecl, _eclh, _link in [
        ('leo', 'Low Earth Orbit', 'earth', 400, 0, 9400, 0.35, 0.6, 1.0),
        ('polar', 'Polar orbit', 'earth', 700, 0, 9800, 0.05, 0.2, 1.0),
        ('geo', 'Geostationary orbit', 'earth', 35786, 3900, 9400, 0.03, 1.2, 0.6),
        ('lunar', 'Lunar orbit', 'moon', 100, 4100, 9400, 0.38, 0.8, 0.35)]:
    _mu, _rad = (398600.0, 6371.0) if _body == 'earth' else (4902.8, 1737.4)   # km^3/s^2, km
    _r = _rad + _alt
    ORB[_k] = dict(name=_name, body=_body, alt=_alt, dv=_dv, dv_up=_dvup, ecl=_ecl, ecl_h=_eclh, link=_link,
                   v=math.sqrt(_mu / _r), T=2 * math.pi * math.sqrt(_r ** 3 / _mu))


def lagrange_l1_distance(primary_mass, secondary_mass, separation_km):
    """Estimate the collinear L1 point with the circular restricted three-body model.

    The dimensionless rotating-frame equation is dOmega/dx = 0, where
    Omega = (x^2 + y^2) / 2 + (1-mu) / r1 + mu / r2.
    Newton's method solves the x-axis equation between the two bodies.
    """
    mu = secondary_mass / (primary_mass + secondary_mass)
    x = 1 - mu - (mu / 3) ** (1 / 3)

    def derivative(value):
        primary_term = (1 - mu) * (value + mu) / abs(value + mu) ** 3
        secondary_term = mu * (value - (1 - mu)) / abs(value - (1 - mu)) ** 3
        return value - primary_term - secondary_term

    for _ in range(20):
        h = 1e-6
        slope = (derivative(x + h) - derivative(x - h)) / (2 * h)
        x -= derivative(x) / slope
    return ((1 - mu) - x) * separation_km


# Approximate Earth/Moon masses and mean separation, used for an educational
# L1 readout in the lunar-orbit briefing.
EARTH_MOON_L1_KM = lagrange_l1_distance(5.972e24, 7.342e22, 384400.0)

# how useful each orbit is for each objective (science multiplier)
FIT = {'earth': {'leo': 0.85, 'polar': 1.0, 'geo': 0.7, 'lunar': 0.15},
       'moon': {'leo': 0.2, 'polar': 0.2, 'geo': 0.2, 'lunar': 1.0},
       'scope': {'leo': 0.8, 'polar': 0.65, 'geo': 0.95, 'lunar': 0.75}}
OBJ_NAME = {'earth': 'Observe the Earth', 'moon': 'Study the Moon', 'scope': 'Space telescope'}

# ---------------------------------------------------------------- launchers
LAUNCH = {
    'light': dict(name='Light launcher', cost=55, stages=[dict(dry=1200, prop=23000, isp=300), dict(dry=270, prop=5500, isp=345)]),
    'medium': dict(name='Medium launcher', cost=110, stages=[dict(dry=4000, prop=76000, isp=310), dict(dry=1000, prop=19000, isp=350)]),
    'heavy': dict(name='Heavy launcher', cost=200, stages=[dict(dry=9500, prop=210000, isp=315), dict(dry=2400, prop=52000, isp=355)]),
}


def capacity(launcher, dv_req):
    """Payload mass (kg) a launcher can deliver, solved from the rocket equation by bisection."""
    lo, hi = 0.0, 80000.0
    for _ in range(70):
        p = (lo + hi) / 2
        m0 = p + sum(s['dry'] + s['prop'] for s in launcher['stages'])
        dv = 0.0
        for s in launcher['stages']:
            dv += s['isp'] * G0 * math.log(m0 / (m0 - s['prop']))   # Tsiolkovsky
            m0 -= s['prop'] + s['dry']                                # drop the empty stage
        if dv > dv_req:
            lo = p
        else:
            hi = p
    return lo


CAP = {k: (capacity(v, 9400), capacity(v, 9800)) for k, v in LAUNCH.items()}   # (to LEO, to polar)


def stage_calc(kind, ship, dv):
    """Upper stage that takes the spacecraft from LEO to GEO / the Moon (propellant from the rocket equation)."""
    isp, k, eng = (320, 0.10, 35) if kind == 'chem' else (1700, 0.15, 110)   # Isp (s), tank fraction, engine mass
    e = math.exp(dv / (isp * G0))
    mp = (e - 1) * (ship + eng) / (1 - k * (e - 1))     # tanks scale with propellant, so solve the loop algebraically
    dry = eng + k * mp
    thrust = 3500.0 if kind == 'chem' else 2 * 3000 * 0.6 / (isp * G0)    # ion: F = 2 * eta * P / (g0 * Isp)
    burn_s = mp * isp * G0 / thrust
    months = max(0.3, burn_s / (30 * 86400) * 1.15) if kind == 'ion' else 0.3
    return dict(kind=kind, isp=isp, mp=mp, dry=dry, thrust=thrust, burn_s=burn_s, months=months, wet=ship + dry + mp)


# ---------------------------------------------------------------- state
S = {}       # mission state (design values + simulation values)
G = {}       # UI state (scene, deck of cards, toast, flight ...)
F = {}       # fonts
A = {}       # astronaut emotion sprites and menu artwork
screen = None


def new_game():
    S.clear()
    S.update(obj=None, diff='Rookie', budget=700, cap=900, deadline=40, mult=1.0, dbonus=0,
             spent=0.0, mass=0.0, pgen=0.0, puse=0.0, sci=0.0, rel=60.0, time=0.0, batt=0.0, comm=0.0, dpc=0.0,
             prop=40.0, comp=None, att=None, pcomm=0.0, orbit=None, launcher=None, stage=None, st=None,
             wet=0.0, cap_l=1.0, lcost=0.0, ltime=0.0, creative=0, log=[], mode='build', launched=False,
             energy=0.0, fuel=0.0, fuel0=1.0, data=0.0, dgen=0.0, dret=0.0, used=set(), fail=None,
             deadline_on=True, overflow=False,
             hidden_score=0,  hidden_notes=[])
    G.update(deck=start_deck(), cur=None, lean=0, off=0.0, fly=None, toast=('', C_TEXT, 0.0),
             phase='', fl=None, res=None, emotion='simple')
    


def card(who, title, text, art, left, right, tip=''):
    return dict(kind='card', who=who, title=title, text=text, art=art, L=left, R=right, tip=tip)


def ch(label, fx=None, note='', **kw):
    return dict(label=label, fx=fx or {}, note=note, **kw)


def banner(phase, title, lines, hud=None):
    return dict(kind='banner', phase=phase, title=title, lines=lines, hud=hud)


def gen(fn):
    return dict(kind='gen', fn=fn)


# ---------------------------------------------------------------- deck: phase 1 and 2
def start_deck():
    def diff2():
        return [card('Mission Director', 'How tough is the program?', 'Harder programs give you less money, less mass and less time, but the final score gets a multiplier.', 'clock',
                     ch('Veteran', set=dict(diff='Veteran', budget=560, cap=700, deadline=32, mult=1.1, dbonus=10),
                        note='560 M$, 700 kg dry mass, 32 months. Score x1.1'),
                     ch('Expert', set=dict(diff='Expert', budget=450, cap=560, deadline=26, mult=1.2, dbonus=20),
                        note='450 M$, 560 kg dry mass, 26 months. Score x1.2'),
                     tip='Real missions fight a three-way battle: cost, mass and schedule. Saving on one usually costs another.')]

    def obj2():
        return [card('NASA Science Director', 'Beyond Earth: which target?', 'The Moon is close and rich in resources like water ice. A space telescope looks at stars and galaxies without our atmosphere in the way.', 'moon',
                     ch('Study the Moon', set=dict(obj='moon'), note='Real science needs a lunar orbit.', art='moon'),
                     ch('Space telescope', set=dict(obj='scope'), note='Flexible orbit. Pointing and power hungry.', art='scope'),
                     tip='The objective decides which instruments make sense and how good each orbit is.')]

    return [
        banner('PHASE 1/5: MISSION BRIEFING', 'Welcome, Mission Manager', [
            'You will design and fly a complete space mission.',
            'Every card gives you two options. Each option has good AND bad effects.',
            '',
            'Move the mouse left/right (or press the arrow keys) to preview an option.',
            'The top bars show how your choice would change the mission.',
            'Click (or press the arrow key again) to choose.',
            '',
            'Five phases: Briefing, Assembly, Orbit and launcher, Simulation, Results.',
            'Run out of money, mass, time or power and the mission is lost.'], hud='build'),
        card('NASA Science Director', 'What will your mission study?', 'Every mission starts with a science question. The objective decides which instruments and orbits are useful.', 'earth',
             ch('Observe the Earth', set=dict(obj='earth'), note='Climate, oceans, forests. Works from many orbits.', art='earth'),
             ch('Look farther out', then=obj2, note='The Moon or a space telescope.', art='moon'),
             tip='Missions are born from science goals, then engineering makes them possible.'),
        card('Mission Director', 'How tough is the program?', 'The program sets your budget, your dry-mass limit and your deadline. Choose your difficulty.', 'clock',
             ch('Rookie', set=dict(diff='Rookie', budget=700, cap=900, deadline=40, mult=1.0, dbonus=0),
                note='700 M$, 900 kg dry mass, 40 months. Score x1.0'),
             ch('Go harder', then=diff2, note='Veteran or Expert.'),
             tip='Real missions fight a three-way battle: cost, mass and schedule.'),
        gen(assembly_deck),
        gen(launch_prep_deck),
        gen(sim_deck),
        dict(kind='end'),
    ]


def assembly_deck():
    ob = S['obj']
    inst = {
        'earth': (ch('Multispectral imager', dict(cost=70, mass=60, puse=90, sci=18, dpc=25, time=4), 'Good science, moderate power.', art='lens'),
                  ch('Synthetic aperture radar', dict(cost=110, mass=120, puse=250, sci=24, dpc=45, time=6), 'Sees through clouds. Heavy and hungry.', art='radar'),
                  'Earth instrument'),
        'moon': (ch('Neutron spectrometer', dict(cost=60, mass=35, puse=40, sci=16, dpc=8, time=4), 'Hunts for water ice. Light and cheap.', art='lens'),
                 ch('Stereo camera + laser altimeter', dict(cost=95, mass=70, puse=120, sci=22, dpc=30, time=5), '3D maps of the surface. More data.', art='radar'),
                 'Lunar instrument'),
        'scope': (ch('UV / optical telescope', dict(cost=90, mass=100, puse=110, sci=20, dpc=20, time=5), 'Sharp images. No cryogenics.', art='scope'),
                  ch('Infrared telescope + cooler', dict(cost=130, mass=160, puse=280, sci=27, dpc=30, time=7), 'Sees cold, distant objects. Needs a cryocooler.', art='scope'),
                  'Telescope')}[ob]
    return [
        banner('PHASE 2/5: SPACECRAFT ASSEMBLY', 'Build your spacecraft', lambda: [
            f"Difficulty: {S['diff']}",
            f"Budget {S['budget']} M$   |   Dry-mass limit {S['cap']} kg   |   Deadline {S['deadline']} months",
            '',
            'You will pick 7 subsystems. Every part has cost, mass, power draw and science value.',
            'Watch the four bars on top: BUDGET, MASS, POWER (draw / output) and SCHEDULE.',
            'Heavy parts need a bigger rocket later. More power draw needs bigger solar arrays.',
            'Batteries matter: in eclipse the arrays make no power and the battery supplies Wh = W x h.']),
        card('Chief Engineer', 'Structure', 'The frame holds everything together through launch vibrations. Mass saved here is mass you can spend on science.', 'frame',
             ch('Aluminium truss', dict(cost=30, mass=220, rel=8, time=2), 'Heavy but proven and forgiving.', set=dict(struct='alu')),
             ch('Carbon-fibre frame', dict(cost=55, mass=140, rel=3, time=4), 'Light but costly and slow to build.', set=dict(struct='carbon'), creative=True),
             tip='Every kilogram costs money to launch. Strength per kilogram (specific strength) is what engineers chase.'),
        card('Power Lead', 'Power system', 'Solar arrays make power only in sunlight. In eclipse the battery must carry the load.', 'panel',
             ch('Large solar arrays', dict(cost=40, mass=90, pgen=1200, batt=350, time=3), 'More output, small battery.', art='panel'),
             ch('Arrays + battery bank', dict(cost=62, mass=150, pgen=900, batt=1100, rel=3, time=4), 'Big battery for eclipses. Less output.', art='battery'),
             tip='Energy (Wh) = power (W) x time (h). A 400 W load during a 36 min eclipse needs 240 Wh.'),
        card('ADCS Lead', 'Attitude control', 'The craft must point its instruments and antenna precisely, and hold that direction against small torques.', 'wheel',
             ch('Reaction wheels', dict(cost=35, mass=45, puse=70, sci=4, time=3), 'Precise pointing, no propellant. Can saturate.', set=dict(att='wheels')),
             ch('Cold-gas thrusters', dict(cost=20, mass=25, puse=10, prop=-12, time=2), 'Cheap and light, but burns propellant.', set=dict(att='thrusters'), art='thruster'),
             tip='Wheels trade momentum with the craft (angular momentum is conserved). Thrusters expel mass to turn.'),
        card('Software Lead', 'Flight computer', 'Space radiation flips bits in memory. Radiation-hardened chips resist it but are slower and pricey.', 'chip',
             ch('Rad-hard computer', dict(cost=45, mass=12, puse=35, rel=9, time=3), 'Very reliable in radiation belts.', set=dict(comp='radhard')),
             ch('Commercial (COTS) computer', dict(cost=12, mass=8, puse=20, rel=-7, sci=2, time=1), 'Cheap and fast. Risky in radiation.', set=dict(comp='cots'), creative=True),
             tip='Single-event upsets are caused by high-energy particles hitting a transistor.'),
        card('Comms Lead', 'Communication', 'Everything you measure must come home. Data returned = data rate x contact time. A bigger dish means a faster link.', 'dish',
             ch('Low-gain antenna', dict(cost=15, mass=10, puse=20, comm=1, time=1), 'Simple, 1 Mbps. Slow data.', set=dict(pcomm=20)),
             ch('High-gain dish', dict(cost=50, mass=45, puse=80, comm=10, time=3), 'Fast, 10 Mbps. Heavy and power hungry.', set=dict(pcomm=80)),
             tip='Signal strength falls with distance squared, so far orbits (GEO, Moon) get slower links.'),
        card('Principal Investigator', inst[2], 'This is the heart of the mission: the instrument that answers the science question. It also decides how much data you will have to send home.', inst[0]['art'],
             inst[0], inst[1], tip='Instrument power and data volume ripple through the whole spacecraft.'),
        card('Principal Investigator', 'Secondary experiment?', 'There is room on the deck for a small extra experiment (a plasma and radiation monitor). More science, more mass, more power.', 'lens',
             ch('Skip it', note='Keep the design lean.'),
             ch('Add the experiment', dict(cost=25, mass=25, puse=40, sci=6, dpc=5, time=2), 'Extra science for a small price.', creative=True),
             tip='Margins matter: every added kilogram reduces your safety margin.'),
        banner('PHASE 2/5: SPACECRAFT ASSEMBLY', 'Design review', design_review_lines),
    ]


def design_review_lines():
    pr = S['puse'] / S['pgen'] if S['pgen'] else 9.9
    lines = [f"Dry mass: {S['mass']:.0f} kg  (limit {S['cap']} kg)    Cost so far: {S['spent']:.0f} M$  (budget {S['budget']})",
             f"Power: {S['puse']:.0f} W draw vs {S['pgen']:.0f} W output ({pr * 100:.0f}% used)    Battery: {S['batt']:.0f} Wh",
             f"Downlink: {S['comm']:.0f} Mbps    Reliability: {S['rel']:.0f}%    Design science: {S['sci']:.0f} pts    Schedule: {S['time']:.1f} months",
             '']
    if pr > 0.8:
        lines.append(('Warning: power draw is above 80% of the array output. Little margin for eclipses.', C_WARN))
    if S['mass'] > 0.9 * S['cap']:
        lines.append(('Warning: you are close to the dry-mass limit.', C_WARN))
    if S['spent'] > 0.55 * S['budget']:
        lines.append(('Warning: the launch will still cost 60-250 M$. Keep money in reserve.', C_WARN))
    lines.append('Next: choose the orbit and the launcher.')
    return lines


# ---------------------------------------------------------------- deck: phase 3
def orbit_banner_lines():
    lines = ['Orbit facts (circular, from v = sqrt(mu/r) and T = 2 pi sqrt(r^3/mu)):']
    for o in ORB.values():
        lines.append('|' + f"{o['name']:<20} alt {o['alt']:>6,} km  T {o['T'] / 60:>6.0f} min  v {o['v']:.2f} km/s  extra dv {o['dv']:>4} m/s")
    lines += ['', 'Launchers (capacity from the rocket equation, to LEO / to polar orbit):']
    for k, v in LAUNCH.items():
        lines.append('|' + f"{v['name']:<16} {v['cost']:>3} M$   {CAP[k][0]:>7,.0f} kg / {CAP[k][1]:>7,.0f} kg")
    fit = FIT[S['obj']]
    lines += ['', f"Objective: {OBJ_NAME[S['obj']]}.  Orbit fit: LEO {fit['leo']:.2f}, Polar {fit['polar']:.2f}, GEO {fit['geo']:.2f}, Lunar {fit['lunar']:.2f}",
              f"Earth-Moon L1 estimate: {EARTH_MOON_L1_KM:,.0f} km from the Moon (rotating-frame Lagrange model).",
              'Going to GEO or the Moon needs an upper stage with extra delta-v. Heavier ships need bigger rockets.']
    return lines


def orbit_cards():
    def o3():
        return [card('Mission Analyst', 'High orbits: Earth or Moon?', 'Both need about 4 km/s of extra delta-v after reaching LEO, and both have slower communication links.', 'planet',
                     ch('Geostationary', set=dict(orbit='geo'), note='Hovers over one spot. 24 h period. Rare eclipses.', art='orbit_geo'),
                     ch('Lunar orbit', set=dict(orbit='lunar'), note='Around the Moon. 2 h period. Long eclipses.', art='orbit_lunar'),
                     tip=f'Geostationary: the orbital period equals one sidereal day (23 h 56 min), so the craft hovers. The Earth-Moon L1 point is about {EARTH_MOON_L1_KM:,.0f} km from the Moon.')]

    def o2():
        return [card('Mission Analyst', 'Polar or higher?', 'A polar orbit passes over both poles while the planet turns underneath, so it eventually sees everywhere.', 'planet',
                     ch('Polar orbit', set=dict(orbit='polar'), note='Global coverage. Launch needs extra energy.', art='orbit_polar'),
                     ch('Go higher', then=o3, note='Geostationary or lunar.', art='planet'),
                     tip='Launching east gives a free speed boost from Earth rotation (about 0.46 km/s). Polar orbits lose it.')]

    return [card('Mission Analyst', 'Which orbit?', 'Orbit altitude sets the speed, the period, the eclipse time and how much delta-v you need.', 'planet',
                 ch('Low Earth Orbit', set=dict(orbit='leo'), note='400 km. Cheap to reach. 92 min period.', art='orbit_leo'),
                 ch('Go higher', then=o2, note='Polar, geostationary or lunar.', art='planet'),
                 tip='Lower orbits are faster: v = sqrt(mu / r). The ISS circles Earth every 92 minutes.')]


def stage_items():
    orb = ORB[S['orbit']]
    if orb['dv'] == 0:
        S['stage'] = None
        return []
    ship = S['mass'] + S['prop']
    c = stage_calc('chem', ship, orb['dv'])
    i = stage_calc('ion', ship, orb['dv'])
    return [card('Propulsion Lead', 'Upper stage for ' + orb['name'], f"From LEO you need about {orb['dv']:,} m/s of extra delta-v. The rocket equation makes propellant grow exponentially with delta-v and shrink with higher Isp.", 'thruster',
                 ch('Chemical stage', dict(cost=30, time=c['months']), 'Fast and powerful, very heavy propellant load.', set=dict(stage='chem'), lc=True,
                    info=f"Isp 320 s. Propellant {c['mp']:,.0f} kg. Wet mass {c['wet']:,.0f} kg. Transfer: hours."),
                 ch('Electric (ion) stage', dict(cost=70, time=i['months']), 'Tiny propellant, but months of slow spiralling.', set=dict(stage='ion'), lc=True, creative=True,
                    info=f"Isp 1700 s. Propellant {i['mp']:,.0f} kg. Wet mass {i['wet']:,.0f} kg. Transfer: {i['months']:.1f} months."),
                 tip='Specific impulse Isp is exhaust velocity / g0. Higher Isp means less propellant for the same delta-v.')]


def launch_chain():
    def l2():
        return [card('Launch Provider', 'Medium or Heavy?', 'Bigger rockets lift more mass but cost much more. Launch capacity is not free: it comes from the rocket equation.', 'rocket_m',
                     ch('Medium launcher', lambda: dict(cost=110, time=6), 'Balanced choice.', set=dict(launcher='medium'), lc=True, art='rocket_m',
                        info=f"Lifts {CAP['medium'][0]:,.0f} kg to LEO, {CAP['medium'][1]:,.0f} kg to polar."),
                     ch('Heavy launcher', lambda: dict(cost=200, time=6), 'Huge capacity, huge price.', set=dict(launcher='heavy'), lc=True, art='rocket_l',
                        info=f"Lifts {CAP['heavy'][0]:,.0f} kg to LEO, {CAP['heavy'][1]:,.0f} kg to polar."),
                     tip='Two stages: dropping the empty first stage lets the second stage accelerate a much lighter rocket.')]

    return [card('Launch Provider', 'Choose your rocket', 'The launcher must lift your spacecraft (plus upper stage and propellant) to orbit. The campaign takes about 6 months to prepare.', 'rocket_s',
                 ch('Light launcher', lambda: dict(cost=55, time=6), 'Cheap. Only for lean spacecraft.', set=dict(launcher='light'), lc=True, art='rocket_s',
                    info=f"Lifts {CAP['light'][0]:,.0f} kg to LEO, {CAP['light'][1]:,.0f} kg to polar."),
                 ch('Go bigger', then=l2, note='Medium or Heavy.', art='rocket_m'),
                 tip='Launch cost is a large part of every mission budget.'),
            gen(stage_items), dict(kind='check')]


def launch_prep_deck():
    return [banner('PHASE 3/5: ORBIT AND LAUNCHER', 'Where to, and how?', orbit_banner_lines)] + orbit_cards() + launch_chain()


def check_launch():
    """Compatibility check: can the chosen launcher lift the ship to the chosen orbit?"""
    orb, lc = ORB[S['orbit']], LAUNCH[S['launcher']]
    cap = CAP[S['launcher']][1 if S['orbit'] == 'polar' else 0]
    ship = S['mass'] + S['prop']
    if orb['dv'] > 0:
        S['st'] = stage_calc(S['stage'], ship, orb['dv'])
        wet = S['st']['wet']
    else:
        S['st'], wet = None, ship
    S['wet'], S['cap_l'] = wet, cap
    if wet <= cap:
        fit = FIT[S['obj']][S['orbit']]
        lines = [('COMPATIBILITY CHECK: PASSED', C_GOOD),
                 f"{lc['name']} can lift {cap:,.0f} kg to this orbit. Your craft at liftoff: {wet:,.0f} kg.",
                 f"Margin: {(cap - wet) / cap * 100:.0f}%  (dry {S['mass']:.0f} + fuel {S['prop']:.0f}" +
                 (f" + upper stage {S['st']['dry'] + S['st']['mp']:,.0f}" if S['st'] else '') + ' kg)',
                 f"Target orbit: {orb['name']}. Orbit fit for your objective: {fit:.2f}"]
        if fit < 0.5:
            lines.append(('Warning: this orbit is a poor match for your objective. Science will be reduced.', C_WARN))
        lines.append(f"Spent so far: {S['spent']:.0f} of {S['budget']} M$.  Schedule: {S['time']:.1f} of {S['deadline']} months.")
        return [banner('PHASE 3/5: ORBIT AND LAUNCHER', 'Launch approved', lines)]
    return [card('Launch Integration', 'NOT COMPATIBLE', f"The {lc['name']} lifts {cap:,.0f} kg to this orbit, but your craft weighs {wet:,.0f} kg at liftoff. It cannot reach orbit.", 'alert',
                 ch('Pick another launcher', reset=True, then=launch_chain, note='Refunds the launcher and stage.'),
                 ch('Pick another orbit', reset=True, then=lambda: orbit_cards() + launch_chain(), note='A lower orbit needs less delta-v.'),
                 tip='If mass at liftoff exceeds capacity, the rocket equation says the delta-v is not enough.')]


# ---------------------------------------------------------------- deck: phase 4
def sim_deck():
    S['mode'] = 'sim'
    S['energy'] = S['batt']
    S['fuel'] = S['fuel0'] = max(S['prop'], 5.0)
    S['data'] = 0.0
    items = [banner('PHASE 4/5: MISSION SIMULATION', 'Flight time', [
        'The bars now show ENERGY (battery), FUEL (station-keeping propellant),',
        'DATA (onboard memory, do not let it fill up) and FUNDS (money left).',
        '',
        'Launch, transit and science operations bring surprises.',
        'Watch the rocket lose mass as it burns propellant and drops empty tanks.',
        'Power loss or empty funds end the mission early.'], 'sim')]
    items += [ev(n) for n in random.sample(['weather', 'maxq', 'hold'], 3)]
    items.append(dict(kind='flight', mode='ascent'))
    if S['st']:
        items += [gen(lambda: [transfer_card()]), dict(kind='flight', mode='transfer')]
    items += [pick(['deploy', 'vanallen', 'wheel', 'commwin', 'meteor']) for _ in range(2)]
    items.append(banner('PHASE 4/5: MISSION SIMULATION', 'Science operations begin', lambda: [
        f"Orbit reached: {ORB[S['orbit']]['name']}. Instruments are on.",
        'Collect data, then send it to Earth. Science only counts if the data comes home.',
        f"Onboard memory holds {DATA_CAP} Gb. Link: {S['comm']:.0f} Mbps (x{ORB[S['orbit']]['link']} for this distance)."]))
    items += [ev('campaign'), pick(['eclipse', 'flare', 'bufferfull', 'drag', 'critical_leak', 'critical_thermal', 'supernova', 'black_hole']), ev('downlink'), ev('campaign2'), ev('downlink2'), ev('extend')]
    return items


def transfer_card():
    if S['stage'] == 'chem':
        return card('Flight Dynamics', 'Burn plan for the transfer', 'One long burn at perigee gets the most from the Oberth effect: an engine adds the most energy where the craft is fastest. Three shorter burns are safer but lose a little efficiency.', 'thruster',
                    ch('One long burn at perigee', {}, 'Most efficient.', risk=dict(p=0.2, fx=dict(rel=-8, cost=8), msg='The engine ran hot and needs extra checks.', log=('bad', 'A long engine burn overheated the stage.')), msg='Perfect burn.'),
                    ch('Split into 3 burns', dict(time=0.3, cost=3, rel=3), 'Safer, a bit slower.', creative=True, msg='Three clean burns.', log=('good', 'Splitting the transfer burn reduced engine risk.')),
                    tip='Oberth effect: burning deep in a gravity well (at perigee) gives more energy per kilogram of propellant.')
    return card('Flight Dynamics', 'Ion thruster plan', 'The ion engine thrusts almost all the time and slowly spirals outward. Thrusting through eclipses is faster but heats the engine.', 'thruster',
                ch('Thrust non-stop', {}, 'Fastest spiral.', risk=dict(p=0.25, fx=dict(rel=-6, time=0.6), msg='The thruster grid wore out early.', log=('bad', 'Non-stop ion thrusting wore the thruster.')), msg='The spiral went smoothly.'),
                ch('Pause in eclipse', dict(time=0.8, rel=3), 'Gentler, slower.', msg='A relaxed trip.', log=('good', 'Pausing the ion engine in eclipse protected it.')),
                tip='Ion thrust is tiny (F = 2 x eff x P / (g0 x Isp)), but a huge Isp makes it very propellant efficient.')


def ev(name):
    return gen(lambda: [c for c in [EVENTS[name]()] if c])


def pick(names):
    def fn():
        opts = [(n, EVENTS[n]()) for n in names if n not in S['used']]
        opts = [(n, c) for n, c in opts if c]
        if not opts:
            return []
        n, c = random.choice(opts)
        S['used'].add(n)
        return [c]
    return gen(fn)


def orb_now():
    return ORB[S['orbit']]


def _risk(p, fx, msg, log):
    return dict(p=p, fx=fx, msg=msg, log=('bad', log))


def _gb():
    return S['comm'] * orb_now()['link'] * 3.6     # Gb per hour = Mbps x 3600 s / 1000


def _drag():
    return (S['mass'] + S['fuel']) * (1 - math.exp(-15 / (220 * G0)))   # propellant for 15 m/s, Isp 220 s


EVENTS = {
    'weather': lambda: card('Launch Director', 'Winds aloft out of limits', 'Upper-level wind shear is above the safe limit. A tall, slender rocket bends easily and the structure could be overloaded.', 'alert',
                            ch('Scrub, wait 2 days', dict(cost=4, time=0.1), 'Safe but costs money.', msg='Scrubbed. The next window is calm.', log=('good', 'You scrubbed the launch for high wind shear.')),
                            ch('Launch anyway', {}, 'Saves time. Risky.', risk=_risk(0.35, dict(rel=-12, cost=8, sci=-4), 'Wind shear stressed the structure.', 'Launching into high wind shear damaged hardware.'), msg='You were lucky with the winds.'),
                            tip='Aerodynamic loads grow with wind shear and with dynamic pressure q = 1/2 rho v^2.'),
    'maxq': lambda: card('Chief Engineer', 'Max-Q ahead', 'In about 80 seconds the rocket meets maximum dynamic pressure. Speed is rising but the air is still dense.', 'rocket_m',
                         ch('Throttle down through Max-Q', dict(cost=2, rel=2), 'Gentle. Costs a little delta-v.', msg='Max-Q passed gently.', log=('good', 'Throttling through Max-Q protected the structure.')),
                         ch('Full throttle', {}, 'Efficient, higher loads.', risk=_risk(0.2, dict(rel=-10, sci=-3), 'Vibration rattled the instruments.', 'Full throttle at Max-Q shook the instruments.'), msg='Max-Q passed without trouble.'),
                         tip='Max-Q is where q = 1/2 rho v^2 peaks: speed grows while air density falls with altitude.'),
    'hold': lambda: card('Range Safety', 'Hold at T-10 min', 'One temperature sensor reads off-nominal. It could be a bad sensor or a real leak.', 'alert',
                         ch('Hold and diagnose', dict(time=0.3, cost=3, rel=4), 'Slower, safer.', msg='The sensor was faulty. Swapped.', log=('good', 'A launch hold caught a faulty sensor.')),
                         ch('Continue the count', {}, 'Keeps the schedule.', risk=_risk(0.25, dict(rel=-8, cost=6), 'A real fault caused damage.', 'Ignoring an off-nominal sensor caused damage.'), msg='It was just a glitch.'),
                         tip='Engineers rely on redundancy: one odd reading is a clue, not a fact.'),
    'deploy': lambda: card('Power Lead', 'Unfold the solar arrays', 'The arrays must open before the battery runs low. Pyro bolts are fast but violent, motors are gentle but slow.', 'panel',
                           ch('Motor deployment', dict(energy=-60, time=0.1, rel=2), 'Gentle and controlled.', msg='Arrays unfolded smoothly.'),
                           ch('Pyro release', {}, 'Fast. A jam is possible.', risk=_risk(0.3, dict(pgen=-200, cost=10), 'A panel jammed half open.', 'Pyro deployment jammed a solar panel.'), msg='All panels popped open.'),
                           tip='Array power: P = area x efficiency x 1361 W/m^2 (sunlight at Earth).'),
    'vanallen': lambda: card('Software Lead', 'Van Allen belts ahead', 'Trapped protons and electrons can flip bits in memory (single-event upsets).', 'chip',
                             ch('Safe mode through the belts', dict(energy=-40, time=0.2), 'Slow, electronics mostly off.', msg='Belts crossed in safe mode.', log=('good', 'Safe mode kept the computer healthy in the radiation belts.')),
                             ch('Stay fully active', {}, 'Faster. Risky without rad-hard parts.', risk=_risk(0.5 if S['comp'] == 'cots' else 0.12, dict(rel=-10, sci=-4), 'Bit flips corrupted some data.', 'Radiation upsets hit the computer in the Van Allen belts.'), msg='No upsets this time.'),
                             tip='Radiation-hardened chips use bigger transistors and error-correcting memory.') if S['st'] else None,
    'wheel': lambda: card('ADCS Lead', 'Reaction wheels near saturation', 'Small torques from sunlight and gravity slowly add momentum to the wheels. At their speed limit they cannot steer anymore.', 'wheel',
                          ch('Dump with thrusters', dict(fuel=-4, energy=-20), 'Fast. Burns propellant.'),
                          ch('Use magnetic torquers', dict(time=0.2, energy=-50), 'No propellant. Slow, uses power.', msg='Earth magnetic field absorbed the momentum.'),
                          tip='Angular momentum is conserved: wheels spin up to absorb it, thrusters push it away.') if S['att'] == 'wheels' else
                card('ADCS Lead', 'Pointing drift', 'Small disturbances nudge the craft. Each correction pulse of the cold-gas thrusters uses propellant.', 'thruster',
                     ch('Re-point precisely', dict(fuel=-6), 'Sharp pointing. Costs fuel.'),
                     ch('Accept some drift', dict(sci=-3), 'Saves fuel. Slightly blurry data.'),
                     tip='Thrust = mass flow x exhaust velocity. Every pulse permanently removes mass.'),
    'commwin': lambda: card('Comms Lead', 'Short commissioning window', 'The ground station can talk to you for only 20 minutes. Link capacity is data rate x time.', 'dish',
                            ch('Upload full checkout', dict(energy=-30, rel=4), 'Thorough. Uses energy.', msg='All systems verified.', log=('good', 'A full checkout verified the spacecraft early.')),
                            ch('Trust autonomy', {}, 'Saves energy.', risk=_risk(0.25, dict(rel=-6, time=0.5), 'Unverified settings caused a delay.', 'Skipping checkout let a bad setting through.'), msg='The craft behaved.'),
                            tip='A radio link is a data pipe: capacity = bits per second x seconds of contact.'),
    'meteor': lambda: card('Flight Director', 'Micrometeoroid shower', 'A debris stream crosses your path. Impact energy is 1/2 m v^2: even a grain at 20 km/s hurts.', 'alert',
                           ch('Turn the shielded side', dict(energy=-40, fuel=-1), 'Safe. Costs a bit of energy and fuel.', msg='The shield absorbed the grains.'),
                           ch('Do nothing', {}, 'Free. Risky.', risk=_risk(0.2, dict(pgen=-100, rel=-5), 'Grains pitted the solar arrays.', 'A micrometeoroid shower damaged the arrays.'), msg='Nothing hit you.'),
                           tip='At orbital speeds even a speck of paint carries the energy of a bullet.'),
    'campaign': lambda: card('Principal Investigator', 'Rare observing chance', 'A 6-hour campaign could return your best data. The instruments draw power from the battery during eclipse and fill the memory.', 'lens',
                             ch('Run the campaign', dict(energy=-round(S['puse'] * orb_now()['ecl_h']), data=round(S['dpc'], 1), sci=10), 'Great science. Costs energy and memory.', msg='A superb dataset.'),
                             ch('Skip it', dict(energy=50), 'Safe and quiet.'),
                             tip='Battery energy needed in eclipse = load (W) x eclipse time (h).'),
    'campaign2': lambda: card('Principal Investigator', 'Extended survey', 'A longer survey covers much more area. It needs more power and a lot of memory.', 'lens',
                              ch('Run the survey', dict(energy=-round(S['puse'] * orb_now()['ecl_h'] * 1.3), data=round(S['dpc'] * 1.3, 1), sci=12), 'Best science. Big data volume.', msg='A huge, valuable dataset.'),
                              ch('A short survey', dict(energy=-round(S['puse'] * orb_now()['ecl_h'] * 0.5), data=round(S['dpc'] * 0.5, 1), sci=5), 'Modest and safe.'),
                              tip='Data you cannot store or send home is science you do not get.'),
    'eclipse': lambda: card('Power Lead', 'Eclipse season', f"The craft sits in shadow up to {orb_now()['ecl_h'] * 60:.0f} min per orbit. The arrays make nothing and the battery supplies the load.", 'sun',
                            ch('Keep instruments on', dict(energy=-round(S['puse'] * orb_now()['ecl_h'] * 1.5), sci=4, data=round(S['dpc'] * 0.3, 1)), 'More science, big battery drain.', msg='Instruments kept running.'),
                            ch('Hibernate instruments', dict(energy=-round(S['puse'] * orb_now()['ecl_h'] * 0.5)), 'Saves the battery.', msg='Hibernation saved energy.', log=('good', 'Hibernating in eclipse protected the battery.')),
                            tip='Energy (Wh) = power (W) x time (h).') if orb_now()['ecl_h'] >= 0.5 else None,
    'flare': lambda: card('Space Weather Officer', 'Solar flare incoming', 'A coronal mass ejection arrives in 20 hours. Charged particles degrade solar cells and corrupt electronics.', 'sun',
                          ch('Safe mode for 2 days', dict(energy=-30), 'Safe. No observing.', msg='The storm passed over a quiet craft.', log=('good', 'Safe mode protected the craft from a solar flare.')),
                          ch('Keep observing', dict(sci=5, data=round(S['dpc'] * 0.3, 1)), 'Extra data. Risky.', risk=_risk(0.45 if S['comp'] == 'cots' else 0.25, dict(pgen=-150, rel=-8), 'Particles degraded the solar cells.', 'Observing through a solar flare damaged the arrays.'), msg='The storm missed you.'),
                          tip='Solar cells lose output when hit by energetic particles (radiation damage).'),
    'bufferfull': lambda: card('Software Lead', 'Memory is almost full', 'The onboard recorder is at ' + f"{S['data'] / DATA_CAP * 100:.0f}" + '% and new data would overwrite old data.', 'chip',
                               ch('Compress the data', dict(data=-round(S['data'] * 0.4, 1), sci=-2), 'Lossy: a bit less science.'),
                               ch('Delete the oldest files', dict(data=-round(S['data'] * 0.5, 1), sci=-5), 'Frees more, loses more.'),
                               tip='Compression trades quality for volume. Better: downlink more often.') if S['data'] > 0.5 * DATA_CAP else None,
    'drag': lambda: card('Flight Dynamics', 'Atmospheric drag', f"At 400 km thin air slowly lowers the orbit. A reboost of 15 m/s uses about {_drag():.1f} kg of propellant (Isp 220 s).", 'orbit_leo',
                         ch('Reboost now', dict(fuel=-round(_drag(), 1)), 'Stays high. Burns propellant.', msg='Orbit restored.'),
                         ch('Let it decay', {}, 'Saves fuel. Risky.', risk=_risk(0.5, dict(sci=-4, rel=-5), 'The lower orbit raised drag and spoiled some data.', 'Letting the orbit decay degraded the mission.'), msg='Still stable for now.'),
                         tip='Drag removes orbital energy, so the orbit shrinks. That is why the ISS needs regular reboosts.') if S['orbit'] == 'leo' else None,
    'downlink': lambda: card('Comms Lead', 'Ground station pass', f"Your link returns about {_gb():.1f} Gb per hour of contact (rate x time, reduced by distance).", 'dish',
                             ch('Full 2-hour pass', dict(down=round(_gb() * 2, 1), energy=-round(S['pcomm'] * 2)), 'Sends the most. Uses energy.', msg='A long, productive pass.'),
                             ch('Short 30-min pass', dict(down=round(_gb() * 0.5, 1), energy=-round(S['pcomm'] * 0.5)), 'Quick. Sends little.'),
                             tip='Data returned = data rate x contact time.'),
    'downlink2': lambda: card('Comms Lead', 'Final data dump', f"This is your last big window. At {_gb():.1f} Gb per hour, how long do you transmit?", 'dish',
                              ch('3-hour pass', dict(down=round(_gb() * 3, 1), energy=-round(S['pcomm'] * 3)), 'Sends the most. Costs energy.', msg='Everything possible was sent.'),
                              ch('1-hour pass', dict(down=round(_gb(), 1), energy=-round(S['pcomm'])), 'Quick and cheap.'),
                              tip='Unsent data is lost science. A bigger dish raises the rate.'),
    'extend': lambda: card('NASA Headquarters', 'Extended mission offer', 'The craft is healthy. HQ offers extra months of science if you can afford the money and consumables.', 'clock',
                           ch('Extend the mission', dict(cost=20, fuel=-8, sci=10, data=round(S['dpc'] * 0.5, 1)), 'More science. Costs funds and fuel.', creative=True, msg='Bonus science collected.'),
                           ch('Close out on time', {}, 'Bank your results.'),
                           tip='Successful missions often outlive their plan (Voyager, Opportunity, Hubble).'),
    'critical_leak': lambda: card('Flight Director', 'ALARM: Valve pressure drop', 'A micro-leak was detected in the auxiliary tank. Closing the main valve now saves propellant, but isolates the secondary sensor.', 'alert',
                                  ch('Isolate main valve', dict(secret_sci=-25, secret_note='Isolating the valve blinded final telemetry, reducing data accuracy.'), 'Keeps current resources.'),
                                  ch('Maintain flow and compensate', dict(fuel=-8, secret_sci=15, secret_note='Compensating for the leak secured 100% telemetry until end of mission.'), 'Spends fuel now.'),
                                  tip='Isolation valves prevent total loss, but sacrifice system redundancy.'),
    'critical_thermal': lambda: card('Thermal Lead', 'CRITICAL: Optical bench drift', 'Uneven solar heating is warping the sensor mount by microns. Active heaters fix it, but drain battery charge right before eclipse.', 'alert',
                                     ch('Let it stabilize passively', dict(secret_sci=-30, secret_note='Thermal warping blurred the final high-resolution imagery.'), 'Saves battery now.'),
                                     ch('Engage precision heaters', dict(energy=-55, secret_sci=20, secret_note='Active thermal control preserved razor-sharp optical focus.'), 'Uses battery charge.'),
                                     tip='Thermal expansion changes focal length: delta_L = alpha * L * delta_T.'),
    'critical_parity': lambda: card('Software Lead', 'URGENT: Memory parity mismatch', 'Cosmic rays triggered checksum errors in the science buffer. Running a deep scrub takes time, while bypassing it risks silent data corruption.', 'alert',
                                    ch('Bypass scrub and transmit', dict(secret_sci=-25, secret_note='Corrupted memory packets invalidated a major portion of the dataset.'), 'Fast and free now.'),
                                    ch('Run full memory scrub', dict(time=0.4, energy=-30, secret_sci=15, secret_note='Error-correcting scrub recovered clean, peer-reviewable science data.'), 'Costs time and energy.'),
                                    tip='Error-correcting code (ECC) memory detects and fixes single-bit flips from radiation.'),
    'supernova': lambda: card('Principal Investigator', 'URGENT: Massive stellar core collapse', 'A distant star just went supernova, flooding our sensors with X-rays and gamma bursts. Closing the shutters protects the optics, while keeping them open captures rare high-energy data.', 'alert',
                              ch('Close shutters for protection', dict(secret_sci=-10, secret_note='Shutting down optics saved the sensors, but missed historic supernova data.'), 'Safe, protects hardware.'),
                              ch('Record full radiation burst', dict(energy=-45, secret_sci=40, secret_note='Capturing the supernova shockwave yielded breakthrough high-energy science!'), 'High power draw, risks saturation.'),
                              tip='Core-collapse supernovae release most of their energy in neutrinos and high-energy photons.'),
    'black_hole': lambda: card('Navigation Lead', 'ANOMALY: Unexplained gravitational lensing', 'Telescopes detected background starlight bending around an invisible, ultra-dense object. Holding the precise pointing lock drains thruster fuel, while letting the craft drift saves propellant.', 'alert',
                               ch('Conserve fuel and let it drift', dict(secret_sci=-10, secret_note='Conserving attitude fuel broke the pointing lock, missing a rare gravitational lens event.'), 'Saves fuel now.'),
                               ch('Hold fine pointing lock', dict(fuel=-9, energy=-45, secret_sci=45, secret_note='Sustained pointing lock confirmed a rogue stellar-mass black hole via microlensing!'), 'Drains fuel and battery.'),
                               tip='Gravitational lensing bends light by theta = 4GM / (c^2 * b) without emitting any light.'),
}


# ---------------------------------------------------------------- effects and checks
def apply_fx(fx, st):
    for k, v in fx.items():
        if k == 'down':
            got = min(st['data'], v)
            st['data'] -= got
            st['dret'] += got
        elif k == 'data':
            st['data'] = max(0.0, st['data'] + v)
            if v > 0:
                st['dgen'] += v
            if st['data'] > DATA_CAP:
                st['data'] = DATA_CAP
                if st is S and not S['overflow']:
                    S['overflow'] = True
                    S['log'].append(('bad', 'The memory overflowed and some data was lost.'))
        elif k == 'energy':
            st['energy'] = min(st['batt'], st['energy'] + v)
        elif k == 'fuel':
            st['fuel'] = max(0.0, st['fuel'] + v)
        elif k == 'rel':
            st['rel'] = max(0.0, min(100.0, st['rel'] + v))
        elif k in ('sci', 'pgen', 'puse'):
            st[k] = max(0.0, st[k] + v)
        elif k == 'secret_sci':
            if st is S:
                st['hidden_score'] += v
        elif k == 'secret_note':
            if st is S:
                tipo = 'good' if fx.get('secret_sci', 0) >= 0 else 'bad'
                st['hidden_notes'].append((tipo, v))
        else:
            st['spent' if k == 'cost' else k] += v      # 'cost' adds to the money spent


def tick():
    """Average power balance after every card in orbit: sunlit fraction feeds the loads and the battery."""
    if not S['launched']:
        return
    S['pgen'] *= 0.985                                           # solar cells age
    net = S['pgen'] * (1 - orb_now()['ecl']) - 0.8 * S['puse']   # W, assuming an 80% duty cycle
    S['energy'] = min(S['batt'], S['energy'] + net * 3.0)


def check_fail():
    if S['spent'] > S['budget']:
        return f"Funding exhausted: you spent {S['spent']:.0f} M$ of a {S['budget']} M$ budget."
    if S['mode'] == 'build' and S['mass'] > S['cap']:
        return f"Overweight spacecraft: dry mass {S['mass']:.0f} kg is above the {S['cap']} kg limit."
    if S['deadline_on'] and S['time'] > S['deadline']:
        return f"Launch window missed: the schedule reached {S['time']:.1f} months (deadline {S['deadline']})."
    if S['mode'] == 'sim' and S['launched'] and S['energy'] <= 0:
        return 'Total power loss: the battery ran flat in eclipse and the spacecraft went silent.'
    return None


def resolve(c):
    if c.get('reset'):
        S['spent'] -= S['lcost']
        S['time'] -= S['ltime']
        S['lcost'] = S['ltime'] = 0.0
        S['stage'] = None
    fx = c['fx']() if callable(c['fx']) else c['fx']
    apply_fx(fx, S)
    if c.get('lc'):
        S['lcost'] += fx.get('cost', 0)
        S['ltime'] += fx.get('time', 0)
    S.update(c.get('set', {}))
    if c.get('creative'):
        S['creative'] += 1
    msg, col, went_bad = c.get('msg', ''), C_GOOD, False
    r = c.get('risk')
    if r:
        p = min(0.9, max(0.03, r['p'] * (1.3 - S['rel'] / 100)))   # higher reliability lowers the failure chance
        if random.random() < p:
            apply_fx(r['fx'], S)
            msg, col, went_bad = r['msg'], C_BAD, True
            S['log'].append(r['log'])
    if c.get('log') and not went_bad:
        S['log'].append(c['log'])
    if went_bad:
        G['emotion'] = 'very_angry'
    elif c.get('creative'):
        G['emotion'] = 'very_happy'
    elif msg:
        G['emotion'] = 'waving'
    else:
        G['emotion'] = 'simple'
    G['toast'] = (msg, col, 4.0)
    if S['mode'] == 'sim':
        tick()
    reason = check_fail()
    if reason:
        S['fail'] = reason
        G['deck'] = [dict(kind='end')]
        return
    G['deck'][0:0] = c['then']() if c.get('then') else []


def advance():
    deck = G['deck']
    while True:
        if not deck:
            deck.append(dict(kind='end'))
        it = deck.pop(0)
        k = it['kind']
        if k == 'gen':
            deck[0:0] = it['fn']()
        elif k == 'check':
            deck[0:0] = check_launch()
        elif k == 'banner':
            if it.get('hud'):
                S['mode'] = it['hud']
            G['phase'] = it['phase']
            it['lines'] = it['lines']() if callable(it['lines']) else it['lines']
            G.update(scene='banner', cur=it)
            return
        elif k == 'card':
            G.update(scene='card', cur=it, lean=0, off=0.0)
            return
        elif k == 'flight':
            start_flight(it['mode'])
            G['scene'] = 'flight'
            return
        elif k == 'end':
            compute_results()
            G['scene'] = 'end'
            return


def choose(side):
    it = G['cur']
    G['fly'] = dict(item=it, side=side, t=0.0)
    resolve(it['L'] if side < 0 else it['R'])


# ---------------------------------------------------------------- flight (rocket equation animation)
def fl_mass(fl):
    m = fl['payload']
    for j in range(fl['idx'], len(fl['stages'])):
        s = fl['stages'][j]
        m += s['dry'] + s['left']
    return m


def start_flight(mode):
    orb = orb_now()
    if mode == 'ascent':
        lc = LAUNCH[S['launcher']]
        stages = [dict(s) for s in lc['stages']]
        payload = S['wet']
        m0 = payload + sum(s['dry'] + s['prop'] for s in stages)
        stages[0]['thrust'] = 1.35 * m0 * G0                                       # liftoff thrust-to-weight 1.35
        stages[1]['thrust'] = 0.9 * (payload + stages[1]['dry'] + stages[1]['prop']) * G0
        dv_req, title = orb['dv_up'], lc['name'] + ': ascent to orbit'
    else:
        st = S['st']
        stages = [dict(dry=st['dry'], prop=st['mp'], isp=st['isp'], thrust=st['thrust'])]
        payload = S['mass'] + S['prop']
        dv_req = orb['dv']
        title = ('Chemical' if st['kind'] == 'chem' else 'Ion') + f" stage: transfer to {orb['name']}"
    for s in stages:
        s['left'] = float(s['prop'])
    total = sum(s['prop'] * s['isp'] * G0 / s['thrust'] for s in stages)
    fl = dict(mode=mode, title=title, stages=stages, payload=payload, idx=0, t=0.0, dv=0.0, dv_req=dv_req, T=total,
              factor=total / 18.0, hist=[], debris=[], done=False, fairing=(mode == 'ascent'), fair_t=None, ion=(mode == 'transfer' and S['st']['kind'] == 'ion'),
              asc='polar' if S['orbit'] == 'polar' else 'leo')
    fl['m0'] = fl_mass(fl)
    fl['hist'].append((0.0, fl['m0']))
    G['fl'] = fl


def update_flight(dt):
    fl = G['fl']
    for d in fl['debris']:
        d['vy'] += 150 * dt
        d['x'] += d['vx'] * dt
        d['y'] += d['vy'] * dt
        d['rot'] += d['vr'] * dt
    fl['debris'] = [d for d in fl['debris'] if d['y'] < H + 150]
    if fl['done']:
        return
    s = fl['stages'][fl['idx']]
    mdot = s['thrust'] / (s['isp'] * G0)
    burn_t = min(dt * fl['factor'] * (3 if pygame.key.get_pressed()[pygame.K_f] else 1), s['left'] / mdot)
    m_before = fl_mass(fl)
    s['left'] -= mdot * burn_t
    m_after = fl_mass(fl)
    fl['dv'] += s['isp'] * G0 * math.log(m_before / m_after)      # Tsiolkovsky, step by step
    fl['t'] += burn_t
    fl['hist'].append((fl['t'], m_after))
    if fl['fairing'] and fl['idx'] >= 1 and fl['t'] > fl['fair_t']:
        fl['fairing'] = False
        for sgn in (-1, 1):
            fl['debris'].append(dict(x=330 + sgn * 14, y=300, vx=sgn * 70, vy=-30, rot=0.0, vr=sgn * 1.5, w=10, h=46, col=(235, 235, 245)))
    if s['left'] <= 1e-6:
        fl['debris'].append(dict(x=330, y=470, vx=random.choice((-25, 25)), vy=20, rot=0.0, vr=random.choice((-0.8, 0.8)), w=50 - 6 * fl['idx'], h=110, col=(150, 155, 170)))
        fl['idx'] += 1
        fl['hist'].append((fl['t'], fl_mass(fl)))                  # mass drops instantly with the empty tank
        if fl['idx'] == 1 and fl['mode'] == 'ascent':
            fl['fair_t'] = fl['t'] + fl['T'] * 0.04
        if fl['idx'] >= len(fl['stages']):
            fl['done'] = True
            if fl['mode'] == 'ascent':
                S['launched'] = True
                S['deadline_on'] = False
                S['log'].append(('good', f"Orbit reached with {fl['dv'] - fl['dv_req']:,.0f} m/s of spare delta-v."))
            else:
                S['log'].append(('good', 'The transfer burn put the craft on target.'))


# ---------------------------------------------------------------- results
def compute_results():
    orbit = S['orbit']
    fit = FIT[S['obj']][orbit] if (orbit and S['obj']) else 0.0
    ret = S['dret'] / S['dgen'] if S['dgen'] > 0 else 0.0
    good = [t for k, t in S['log'] if k == 'good']
    bad = [t for k, t in S['log'] if k == 'bad']

    for k,t in S.get('hidden_notes', []):
        if k == 'good':
            good.insert(0,t)
        else:
            bad.insert(0,t)

    res = dict(science=0.0, cost=0.0, safety=0.0, creativity=0.0, total=0.0, grade='F', fit=fit, ret=ret, parts=[])
    if S['launched']:
        sci_total = max(0.0, S['sci'] + S.get('hidden_score', 0))
        res['science'] = min(100.0, sci_total * fit * (0.4 + 0.6 * ret) / 60 * 100)
        res['cost'] = max(0.0, min(100.0, (1 - S['spent'] / S['budget']) * 160))
        pwr = S['pgen'] * (1 - ORB[orbit]['ecl']) / max(1.0, 0.8 * S['puse'])
        parts = [('Reliability', S['rel']),
                 ('Power margin', max(0.0, min(100.0, (pwr - 1) / 0.5 * 100))),
                 ('Mass margin', max(0.0, min(100.0, (S['cap'] - S['mass']) / S['cap'] * 400))),
                 ('Launcher margin', max(0.0, min(100.0, (S['cap_l'] - S['wet']) / S['cap_l'] * 400))),
                 ('Fuel reserve', max(0.0, min(100.0, S['fuel'] / S['fuel0'] * 100)))]
        res['parts'] = parts
        res['safety'] = sum(p[1] for p in parts) / len(parts)
        res['creativity'] = min(100.0, S['creative'] * 14 + S['dbonus'])
        total = 0.4 * res['science'] + 0.2 * res['cost'] + 0.25 * res['safety'] + 0.15 * res['creativity']
        if S['fail']:
            total *= 0.5
            res['science'] *= 0.5
        res['total'] = min(100.0, total * S['mult'])
        res['grade'] = 'S' if res['total'] >= 85 else 'A' if res['total'] >= 70 else 'B' if res['total'] >= 55 else 'C' if res['total'] >= 40 else 'D'
        if S['dgen'] > 0 and ret < 0.5:
            bad.append(f"Only {ret * 100:.0f}% of the generated data reached Earth. A bigger antenna or longer passes would help.")
        if ret >= 0.8:
            good.append(f"{ret * 100:.0f}% of your data came home. Great link planning.")
        if fit < 0.5:
            bad.append(f"The orbit suits this objective poorly (fit {fit:.2f}), so science was cut.")
        if fit >= 0.9:
            good.append('The orbit is an excellent match for the science goal.')
        if (S['cap_l'] - S['wet']) / S['cap_l'] < 0.05:
            bad.append('The launcher was at its limit: no margin for a heavier craft or a launch dispersion.')
        if S['spent'] < 0.7 * S['budget']:
            good.append(f"You finished with {100 - S['spent'] / S['budget'] * 100:.0f}% of the budget unspent.")
        if S['fuel'] / S['fuel0'] < 0.2:
            bad.append('Station-keeping fuel is nearly gone. The mission could not last long.')
        if pwr < 1.1:
            bad.append('Power margin was thin: the arrays barely covered the loads.')
    else:
        bad.append('The mission never launched, so no science was returned.')
    res['good'], res['bad'] = good[:5], bad[:5]
    G['res'] = res


# ---------------------------------------------------------------- drawing helpers
def text(surf, s, font, color, x, y, maxw=None, align='left', lh=None):
    """Draw (optionally wrapped) text. Returns the y below the last line."""
    lh = lh or font.get_linesize()
    lines = []
    for para in str(s).split('\n'):
        if maxw is None:
            lines.append(para)
            continue
        cur = ''
        for w in para.split(' '):
            test = (cur + ' ' + w).strip()
            if font.size(test)[0] <= maxw or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    for ln in lines:
        img = font.render(ln, True, color)
        px = x - img.get_width() // 2 if align == 'center' else x - img.get_width() if align == 'right' else x
        surf.blit(img, (px, y))
        y += lh
    return y


def draw_astronaut(surf, rect, emotion='simple', alpha=255):
    """Draw one of the supplied astronaut sprites at a UI location."""
    image = A.get(emotion) or A['simple']
    scaled = pygame.transform.smoothscale(image, (rect[2], rect[3]))
    if alpha != 255:
        scaled.set_alpha(alpha)
    surf.blit(scaled, (rect[0], rect[1]))


def draw_art(surf, rect, kind, t):
    x0, y0, w, h = rect
    cx, cy = x0 + w // 2, y0 + h // 2
    pygame.draw.rect(surf, (10, 12, 30), rect, border_radius=8)
    for i in range(22):     # fixed star field
        surf.set_at((x0 + (i * 97 + 31) % w, y0 + (i * 57 + 13) % h), (190, 195, 225))
    if kind.startswith('orbit_'):
        k = kind[6:]
        o = ORB[k]
        ang = t * 1200.0 / o['T'] * 2 * math.pi       # 1 s on screen = 20 min of flight
        pr, rx, ry = {'leo': (40, 62, 62), 'polar': (36, 22, 76), 'geo': (20, 76, 76), 'lunar': (30, 56, 56)}[k]
        earth = o['body'] == 'earth'
        pygame.draw.circle(surf, (60, 125, 215) if earth else (165, 165, 172), (cx, cy), pr)
        spin = t * 1200.0 / 86164.0 * 2 * math.pi if earth else 0
        if earth:
            for a, r2 in ((0.5, 0.55), (2.6, 0.45), (4.2, 0.6)):
                pygame.draw.circle(surf, (70, 160, 90), (int(cx + math.cos(a + spin) * pr * r2), int(cy + math.sin(a + spin) * pr * r2 * 0.8)), pr // 5)
        else:
            for a, r2 in ((1.0, 0.5), (3.0, 0.4), (5.0, 0.6)):
                pygame.draw.circle(surf, (130, 130, 138), (int(cx + math.cos(a) * pr * r2), int(cy + math.sin(a) * pr * r2)), pr // 6)
        pygame.draw.ellipse(surf, (90, 105, 160), (cx - rx, cy - ry, 2 * rx, 2 * ry), 1)
        sx, sy = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
        if k == 'geo':      # a ground marker that the satellite always stays above
            gx, gy = cx + pr * math.cos(spin), cy + pr * math.sin(spin)
            pygame.draw.line(surf, (110, 120, 170), (gx, gy), (sx, sy), 1)
            pygame.draw.circle(surf, (255, 90, 80), (int(gx), int(gy)), 3)
        pygame.draw.circle(surf, (255, 230, 120), (int(sx), int(sy)), 5)
        text(surf, f"alt {o['alt']:,} km | period {o['T'] / 60:,.0f} min | {o['v']:.2f} km/s", F['s'], C_DIM, cx, y0 + h - 18, align='center')
        text(surf, '(not to scale, time x1200)', F['s'], C_DIM, cx, y0 + 4, align='center')
    elif kind.startswith('rocket'):
        s = {'rocket_s': 0.7, 'rocket_m': 0.95, 'rocket_l': 1.2}.get(kind, 1.0)
        bw, bh = 30 * s, 100 * s
        top = cy - bh / 2
        pygame.draw.rect(surf, (225, 225, 235), (cx - bw / 2, top, bw, bh), border_radius=5)
        pygame.draw.polygon(surf, (230, 90, 70), [(cx - bw / 2, top), (cx + bw / 2, top), (cx, top - 28 * s)])
        pygame.draw.polygon(surf, (230, 90, 70), [(cx - bw / 2, top + bh), (cx - bw / 2 - 14 * s, top + bh + 10), (cx - bw / 2, top + bh - 26 * s)])
        pygame.draw.polygon(surf, (230, 90, 70), [(cx + bw / 2, top + bh), (cx + bw / 2 + 14 * s, top + bh + 10), (cx + bw / 2, top + bh - 26 * s)])
        fl = 22 * s + 8 * math.sin(t * 30)
        pygame.draw.polygon(surf, (255, 170, 60), [(cx - bw / 3, top + bh), (cx + bw / 3, top + bh), (cx, top + bh + fl)])
    elif kind in ('earth', 'planet'):
        pygame.draw.circle(surf, (60, 125, 215), (cx, cy), 56)
        for a, r2 in ((0.5, 0.5), (2.4, 0.4), (4.1, 0.55)):
            pygame.draw.circle(surf, (70, 160, 90), (int(cx + math.cos(a + t * 0.2) * 56 * r2), int(cy + math.sin(a + t * 0.2) * 56 * r2 * 0.8)), 12)
    elif kind == 'moon':
        pygame.draw.circle(surf, (170, 170, 176), (cx, cy), 52)
        for dx, dy, r in ((-18, -12, 10), (14, 8, 14), (-6, 24, 7), (24, -22, 6)):
            pygame.draw.circle(surf, (130, 130, 138), (cx + dx, cy + dy), r)
    elif kind == 'sun':
        pygame.draw.circle(surf, (255, 200, 70), (cx, cy), 38)
        for i in range(12):
            a = i * math.pi / 6 + t
            pygame.draw.line(surf, (255, 200, 70), (cx + math.cos(a) * 46, cy + math.sin(a) * 46), (cx + math.cos(a) * 62, cy + math.sin(a) * 62), 3)
    elif kind == 'panel':
        pygame.draw.rect(surf, (200, 200, 210), (cx - 18, cy - 18, 36, 36))
        for sgn in (-1, 1):
            px = cx + sgn * 24 if sgn > 0 else cx - 24 - 80
            pygame.draw.rect(surf, (40, 80, 170), (px, cy - 30, 80, 60))
            for gx in range(1, 4):
                pygame.draw.line(surf, (110, 150, 230), (px + gx * 20, cy - 30), (px + gx * 20, cy + 30))
            pygame.draw.line(surf, (110, 150, 230), (px, cy), (px + 80, cy))
    elif kind == 'battery':
        pygame.draw.rect(surf, (90, 200, 130), (cx - 50, cy - 26, 96, 52), border_radius=6)
        pygame.draw.rect(surf, (90, 200, 130), (cx + 46, cy - 10, 8, 20))
        for i in range(4):
            pygame.draw.rect(surf, (20, 60, 40), (cx - 42 + i * 22, cy - 18, 16, 36))
    elif kind == 'frame':
        pygame.draw.rect(surf, (190, 190, 200), (cx - 50, cy - 40, 100, 80), 4)
        pygame.draw.line(surf, (190, 190, 200), (cx - 50, cy - 40), (cx + 50, cy + 40), 3)
        pygame.draw.line(surf, (190, 190, 200), (cx + 50, cy - 40), (cx - 50, cy + 40), 3)
    elif kind == 'wheel':
        pygame.draw.circle(surf, (190, 190, 200), (cx, cy), 42, 4)
        for i in range(4):
            a = i * math.pi / 2 + t * 4
            pygame.draw.line(surf, (190, 190, 200), (cx, cy), (cx + math.cos(a) * 40, cy + math.sin(a) * 40), 3)
    elif kind == 'thruster':
        pygame.draw.polygon(surf, (190, 190, 200), [(cx - 18, cy - 30), (cx + 18, cy - 30), (cx + 34, cy + 10), (cx - 34, cy + 10)])
        for i in range(3):
            pygame.draw.circle(surf, (255, 170, 80), (cx + int(math.sin(t * 9 + i) * 8), int(cy + 22 + i * 14 + (t * 40 % 14))), 5 - i)
    elif kind == 'chip':
        pygame.draw.rect(surf, (70, 80, 110), (cx - 36, cy - 36, 72, 72), border_radius=6)
        pygame.draw.rect(surf, (110, 220, 170), (cx - 18, cy - 18, 36, 36), 2)
        for i in range(6):
            pygame.draw.line(surf, (190, 190, 200), (cx - 30 + i * 12, cy - 36), (cx - 30 + i * 12, cy - 46), 2)
            pygame.draw.line(surf, (190, 190, 200), (cx - 30 + i * 12, cy + 36), (cx - 30 + i * 12, cy + 46), 2)
    elif kind == 'dish':
        pygame.draw.arc(surf, (210, 210, 220), (cx - 50, cy - 40, 100, 80), math.pi, 2 * math.pi, 5)
        pygame.draw.line(surf, (210, 210, 220), (cx, cy), (cx, cy - 26), 3)
        for i in range(3):
            r = int(14 + ((t * 30 + i * 14) % 42))
            pygame.draw.arc(surf, (120, 190, 255), (cx - r, cy - 26 - r, 2 * r, 2 * r), 0.9, 2.2, 2)
    elif kind in ('lens', 'radar'):
        for i, r in enumerate((46, 32, 18)):
            pygame.draw.circle(surf, (110, 160, 230) if i != 2 else (255, 230, 120), (cx, cy), r, 3 if i != 2 else 0)
        if kind == 'radar':
            a = t * 3
            pygame.draw.line(surf, (110, 220, 170), (cx, cy), (cx + math.cos(a) * 46, cy + math.sin(a) * 46), 2)
    elif kind == 'scope':
        pygame.draw.polygon(surf, (190, 190, 200), [(cx - 56, cy + 18), (cx - 56, cy - 4), (cx + 50, cy - 24), (cx + 50, cy + 2)])
        pygame.draw.ellipse(surf, (110, 160, 230), (cx + 42, cy - 26, 14, 30))
        pygame.draw.rect(surf, (200, 200, 210), (cx - 24, cy + 14, 30, 30))
    elif kind == 'clock':
        pygame.draw.circle(surf, (220, 220, 230), (cx, cy), 44, 4)
        pygame.draw.line(surf, (255, 190, 80), (cx, cy), (cx + math.cos(t) * 32, cy + math.sin(t) * 32), 3)
        pygame.draw.line(surf, (220, 220, 230), (cx, cy), (cx, cy - 22), 3)
    else:       # alert
        pygame.draw.polygon(surf, (255, 190, 80), [(cx, cy - 46), (cx + 50, cy + 36), (cx - 50, cy + 36)], 5)
        text(surf, '!', F['h2'], (255, 190, 80), cx, cy - 18, align='center')


def render_card(it, lean, t):
    cw, chh = 420, 480
    s = pygame.Surface((cw, chh), pygame.SRCALPHA)
    pygame.draw.rect(s, C_CARD, (0, 0, cw, chh), border_radius=18)
    pygame.draw.rect(s, (160, 135, 90), (0, 0, cw, chh), 3, border_radius=18)
    text(s, it['title'], F['h2'], C_INK, cw // 2, 14, maxw=cw - 36, align='center', lh=28)
    c = it['L'] if lean < 0 else it['R'] if lean > 0 else None
    art = (c.get('art') if c else None) or it['art']
    draw_art(s, (18, 82, cw - 36, 168), art, t)
    text(s, it['text'], F['n'], C_INK, 20, 260, maxw=cw - 40, lh=19)
    if it['tip']:
        text(s, 'Physics: ' + it['tip'], F['s'], (110, 80, 50), 20, 382, maxw=cw - 40, lh=16)
    pygame.draw.rect(s, (60, 42, 30), (0, 446, cw, 34), border_bottom_left_radius=18, border_bottom_right_radius=18)
    text(s, it['who'], F['b'], C_CARD, cw // 2, 452, align='center')
    return s


def fmt(v):
    return f"{v:+,.0f}" if abs(v) >= 10 or v == int(v) else f"{v:+.1f}"


def draw_side(rect, c, active):
    x, y, w, h = rect
    pygame.draw.rect(screen, (34, 44, 86) if active else C_PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, C_ACC if active else C_LINE, rect, 3 if active else 1, border_radius=12)
    yy = text(screen, c['label'], F['b'], C_TEXT, x + 14, y + 12, maxw=w - 28, lh=22) + 4
    if c['note']:
        yy = text(screen, c['note'], F['s'], C_DIM, x + 14, yy, maxw=w - 28, lh=16) + 8
    fx = c['fx']() if callable(c['fx']) else c['fx']
    for k, v in fx.items():
        if k in ('secret_sci', 'secret_note'):
            continue
        lab, unit, gs = FXINFO[k]
        col = C_DIM if gs == 0 else (C_GOOD if v * gs > 0 else C_BAD)
        yy = text(screen, f"{lab}: {fmt(v)} {unit}", F['n'], col, x + 14, yy, maxw=w - 28, lh=19)
    r = c.get('risk')
    if r:
        p = min(0.9, max(0.03, r['p'] * (1.3 - S['rel'] / 100)))
        yy = text(screen, f"RISK ~{p * 100:.0f}%: " + ', '.join(f"{FXINFO[k][0]} {fmt(v)}" for k, v in r['fx'].items()), F['s'], C_WARN, x + 14, yy + 6, maxw=w - 28, lh=16)
    info = c.get('info')
    if info:
        text(screen, info() if callable(info) else info, F['s'], C_ACC, x + 14, yy + 8, maxw=w - 28, lh=16)


def hud_values(st):
    if st['mode'] == 'build':
        pr = st['puse'] / st['pgen'] if st['pgen'] > 0 else (0 if st['puse'] == 0 else 1.2)
        return [('BUDGET', st['spent'] / st['budget'], 'use', f"{st['spent']:.0f}/{st['budget']} M$"),
                ('MASS', st['mass'] / st['cap'], 'use', f"{st['mass']:.0f}/{st['cap']} kg"),
                ('POWER', pr, 'use', f"{st['puse']:.0f}/{st['pgen']:.0f} W"),
                ('SCHEDULE', st['time'] / st['deadline'], 'use', f"{st['time']:.1f}/{st['deadline']} mo")]
    return [('ENERGY', st['energy'] / max(st['batt'], 1), 'level', f"{st['energy']:.0f}/{st['batt']:.0f} Wh"),
            ('FUEL', st['fuel'] / st['fuel0'], 'level', f"{st['fuel']:.1f}/{st['fuel0']:.0f} kg"),
            ('DATA', st['data'] / DATA_CAP, 'use', f"{st['data']:.0f}/{DATA_CAP} Gb"),
            ('FUNDS', (st['budget'] - st['spent']) / st['budget'], 'level', f"{st['budget'] - st['spent']:.0f} M$")]


def draw_hud(pv):
    cur = hud_values(S)
    new = hud_values(pv) if pv else cur
    for i, ((lab, f0, kind, txt0), (_, f1, _, txt1)) in enumerate(zip(cur, new)):
        x, y, bw = 18 + i * 245, 26, 225
        text(screen, lab, F['s'], C_DIM, x, 6)
        pygame.draw.rect(screen, (28, 34, 64), (x, y, bw, 16), border_radius=8)
        d = f1 if kind == 'use' else 1 - f1
        col = C_GOOD if d < 0.7 else C_WARN if d < 0.9 else C_BAD
        a, b = max(0.0, min(1.0, f0)), max(0.0, min(1.0, f1))
        pygame.draw.rect(screen, col, (x, y, int(bw * min(a, b)), 16), border_radius=8)
        if a != b:
            pygame.draw.rect(screen, (255, 255, 255), (x + int(bw * min(a, b)), y, int(bw * abs(a - b)) + 1, 16))
        pygame.draw.rect(screen, C_BAD if f1 > 1.0 or (kind == 'level' and f1 <= 0) else C_LINE, (x, y, bw, 16), 1, border_radius=8)
        text(screen, txt1, F['s'], C_TEXT if pv else C_DIM, x, 46)


# ---------------------------------------------------------------- scenes: draw
def draw_stars(t):
    for i in range(70):
        sx, sy = (i * 137 + 40) % W, (i * 89 + int(t * (4 + i % 5))) % H
        screen.set_at((sx, sy), (110 + i % 100, 115 + i % 90, 160 + i % 90))


def menu_play_rect():
    return pygame.Rect(round(452 / 1299 * W), round(318 / 770 * H),
                       round(423 / 1299 * W), round(108 / 770 * H))


def draw_title(t):
    screen.fill((0, 0, 0))
    menu = pygame.transform.smoothscale(A['menu'], (W, H))
    screen.blit(menu, (0, 0))
    play = menu_play_rect()
    if play.collidepoint(pygame.mouse.get_pos()):
        overlay = pygame.Surface(play.size, pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 28))
        screen.blit(overlay, play.topleft)
        pygame.draw.rect(screen, C_WARN, play, 3)
    draw_astronaut(screen, (W - 142, H - 148, 112, 112), 'waving')
    if int(t * 2) % 2 == 0:
        text(screen, 'Click PLAY or press SPACE to start', F['b'], C_WARN, W // 2, H - 42, align='center')


def draw_banner(t):
    screen.fill(C_BG)
    draw_stars(t)
    it = G['cur']
    if it.get('hud') or S['mode'] in ('build', 'sim'):
        draw_hud(None)
    text(screen, G['phase'], F['s'], C_DIM, W // 2, 76, align='center')
    pygame.draw.rect(screen, C_PANEL, (80, 110, W - 160, 560), border_radius=16)
    pygame.draw.rect(screen, C_LINE, (80, 110, W - 160, 560), 2, border_radius=16)
    draw_astronaut(screen, (850, 132, 100, 100), G['emotion'])
    text(screen, it['title'], F['h1'], C_TEXT, W // 2, 130, align='center')
    y = 200
    for ln in it['lines']:
        col, font = C_TEXT, F['n']
        if isinstance(ln, tuple):
            ln, col = ln
        if ln.startswith('|'):
            ln, font = ln[1:], F['m']
        y = text(screen, ln, font, col, 110, y, maxw=W - 220, lh=font.get_linesize() + 4)
    if int(t * 2) % 2 == 0:
        text(screen, 'Press SPACE to continue', F['b'], C_WARN, W // 2, 690, align='center')


def draw_card_scene(t):
    screen.fill(C_BG)
    draw_stars(t)
    it, lean = G['cur'], G['lean']
    c = it['L'] if lean < 0 else it['R'] if lean > 0 else None
    pv = None
    if c:
        pv = dict(S)
        apply_fx(c['fx']() if callable(c['fx']) else c['fx'], pv)
    draw_hud(pv)
    text(screen, G['phase'] + f"     Science: {S['sci']:.0f} pts", F['s'], C_DIM, W // 2, 76, align='center')
    draw_astronaut(screen, (454, 86, 92, 92), G['emotion'])
    draw_side((12, 134, 270, 480), it['L'], lean < 0)
    draw_side((718, 134, 270, 480), it['R'], lean > 0)
    G['off'] += (lean * 24 - G['off']) * 0.2
    if G['fly']:
        f = G['fly']
        p = min(1.0, f['t'] / 0.25)
        cs = render_card(f['item'], f['side'], t)
        cs.set_alpha(int(255 * (1 - p)))
        screen.blit(pygame.transform.rotate(cs, -f['side'] * 18 * p), cs.get_rect(center=(W // 2 + f['side'] * 520 * p, 374)).move(0, 0))
    else:
        cs = render_card(it, lean, t)
        screen.blit(pygame.transform.rotate(cs, -G['off'] * 0.22), cs.get_rect(center=(W // 2 + G['off'], 374)))
    txt, col, left = G['toast']
    if left > 0 and txt:
        text(screen, txt, F['b'], col, W // 2, 640, maxw=W - 80, align='center')
    text(screen, 'Left / Right: preview.  Click or press again: choose.  ESC: quit.', F['s'], C_DIM, W // 2, 736, align='center')


def draw_flight(t):
    fl = G['fl']
    G['emotion'] = 'space' if fl['mode'] == 'transfer' else 'very_happy'
    frac = min(1.0, fl['dv'] / fl['dv_req']) if fl['dv_req'] else 1.0
    if fl['mode'] == 'ascent':
        k = max(0.0, 1 - frac * 1.4)
        screen.fill((int(7 + 90 * k), int(9 + 140 * k), int(20 + 210 * k)))
        if frac > 0.3:
            draw_stars(t)
        pygame.draw.rect(screen, (45, 95, 55), (0, int(600 + frac * 1200), 600, 400))
        pygame.draw.rect(screen, (170, 170, 175), (250, int(560 + frac * 1200), 160, 40))
    else:
        screen.fill(C_BG)
        draw_stars(t)
        pygame.draw.circle(screen, (50, 110, 200), (330, int(1050 + frac * 500)), 480)
    # rocket stack
    x, y = 330, 540
    biggest = max(s['dry'] + s['prop'] for s in fl['stages'])
    for j in range(fl['idx'], len(fl['stages'])):
        s = fl['stages'][j]
        hh = int(60 + 70 * (s['dry'] + s['prop']) / biggest)
        ww = 56 - 8 * j if fl['mode'] == 'ascent' else 46
        pygame.draw.rect(screen, (150, 155, 170), (x - ww // 2, y - hh, ww, hh), border_radius=4)
        pf = s['left'] / s['prop']
        pygame.draw.rect(screen, (90, 190, 240) if fl['ion'] else (240, 160, 70), (x - ww // 2 + 4, y - 4 - int((hh - 8) * pf), ww - 8, int((hh - 8) * pf)))
        if j == fl['idx'] and not fl['done']:
            ln = 16 if fl['ion'] else 36 + random.random() * 30
            pygame.draw.polygon(screen, (120, 190, 255) if fl['ion'] else (255, 200, 80), [(x - ww // 3, y), (x + ww // 3, y), (x, y + ln)])
        y -= hh
    if fl['mode'] == 'ascent':
        if fl['fairing']:
            pygame.draw.polygon(screen, (235, 235, 245), [(x - 22, y), (x + 22, y), (x + 20, y - 36), (x, y - 70), (x - 20, y - 36)])
        else:
            pygame.draw.rect(screen, (210, 210, 225), (x - 14, y - 34, 28, 34))
    else:
        pygame.draw.rect(screen, (210, 210, 225), (x - 16, y - 34, 32, 34))
        pygame.draw.rect(screen, (40, 80, 170), (x - 64, y - 26, 44, 18))
        pygame.draw.rect(screen, (40, 80, 170), (x + 20, y - 26, 44, 18))
    for d in fl['debris']:
        sf = pygame.Surface((d['w'], d['h']), pygame.SRCALPHA)
        sf.fill(d['col'])
        rs = pygame.transform.rotate(sf, math.degrees(d['rot']))
        screen.blit(rs, rs.get_rect(center=(d['x'], d['y'])))
    # readouts
    px = 620
    pygame.draw.rect(screen, C_PANEL, (px - 20, 20, 380, 720), border_radius=14)
    text(screen, fl['title'], F['b'], C_TEXT, px, 34, maxw=340)
    tt = f"T+ {fl['t'] / 86400:.0f} days" if fl['ion'] else f"T+ {int(fl['t']) // 60:02d}:{int(fl['t']) % 60:02d}"
    text(screen, tt, F['h2'], C_ACC, px, 90)
    m = fl_mass(fl)
    text(screen, 'MASS', F['s'], C_DIM, px, 138)
    text(screen, f"{m:,.0f} kg", F['h1'], C_WARN, px, 154)
    text(screen, f"liftoff mass {fl['m0']:,.0f} kg", F['s'], C_DIM, px, 202)
    pygame.draw.rect(screen, (28, 34, 64), (px, 232, 340, 14), border_radius=7)
    pygame.draw.rect(screen, C_GOOD, (px, 232, int(340 * frac), 14), border_radius=7)
    text(screen, f"Delta-v {fl['dv']:,.0f} / {fl['dv_req']:,.0f} m/s", F['n'], C_TEXT, px, 252)
    if fl['mode'] == 'ascent':
        o = ORB[fl['asc']]
        v = min(o['v'], max(0.0, (fl['dv'] - 1600 * frac) / 1000))
        text(screen, f"Speed {v:.2f} km/s   Altitude {o['alt'] * frac ** 2.2:,.0f} km", F['n'], C_TEXT, px, 278)
        text(screen, '(speed = delta-v minus about 1.6 km/s of gravity and drag losses)', F['s'], C_DIM, px, 300, maxw=340)
    elif fl['ion']:
        text(screen, 'Ion engine: tiny thrust, a huge Isp. Time runs fast here.', F['s'], C_DIM, px, 278, maxw=340)
    if not fl['done']:
        s = fl['stages'][fl['idx']]
        text(screen, f"Stage {fl['idx'] + 1} burning. Tank {s['left'] / s['prop'] * 100:.0f}% full.", F['n'], C_WARN, px, 330)
    # mass-vs-time plot
    gx, gy, gw, gh = px, 390, 340, 190
    pygame.draw.rect(screen, (12, 15, 34), (gx, gy, gw, gh))
    pygame.draw.rect(screen, C_LINE, (gx, gy, gw, gh), 1)
    pts = [(gx + gw * h[0] / fl['T'], gy + gh - 8 - (gh - 16) * math.log(h[1] / fl['payload']) / math.log(fl['m0'] / fl['payload'])) for h in fl['hist'][::3] + fl['hist'][-2:]]
    if len(pts) > 1:
        pygame.draw.lines(screen, C_WARN, False, pts, 2)
    text(screen, 'Mass vs time (log scale): sudden drops are empty tanks released', F['s'], C_DIM, gx, gy + gh + 4, maxw=gw)
    text(screen, 'Rocket equation: dv = Isp x g0 x ln(m0 / mf). Burning propellant and dropping dead weight makes the rest accelerate faster. Hold F to fast-forward.', F['s'], C_DIM, px, 640, maxw=340, lh=16)
    if fl['done']:
        if fl['mode'] == 'ascent':
            msg = f"ORBIT REACHED. Spare delta-v {fl['dv'] - fl['dv_req']:,.0f} m/s."
        else:
            msg = f"TRANSFER COMPLETE. Now in {orb_now()['name']}."
        text(screen, msg, F['b'], C_GOOD, 30, 640, maxw=560)
        if int(t * 2) % 2 == 0:
            text(screen, 'Press SPACE to continue', F['b'], C_WARN, 30, 680)


def draw_end(t):
    res = G['res']
    screen.fill(C_BG)
    draw_stars(t)
    if S['fail']:
        head, col = ('MISSION LOST' if S['launched'] else 'MISSION CANCELLED'), C_BAD
    else:
        head, col = 'MISSION COMPLETE', C_GOOD
    text(screen, 'PHASE 5/5: RESULTS', F['s'], C_DIM, W // 2, 14, align='center')
    text(screen, head, F['h1'], col, 40, 34)
    draw_astronaut(screen, (690, 42, 96, 96), 'very_happy' if not S['fail'] else 'angry')
    if S['fail']:
        text(screen, S['fail'], F['n'], C_WARN, 40, 80, maxw=700)
    info = f"{S['diff']}  |  " + (OBJ_NAME[S['obj']] if S['obj'] else '') + (f"  |  {ORB[S['orbit']]['name']}" if S['orbit'] else '') + (f"  |  {LAUNCH[S['launcher']]['name']}" if S['launcher'] else '')
    text(screen, info, F['s'], C_DIM, 40, 112)
    pygame.draw.rect(screen, C_PANEL, (790, 30, 190, 160), border_radius=14)
    text(screen, res['grade'], F['big'], C_WARN, 885, 40, align='center')
    text(screen, f"Score {res['total']:.0f}/100", F['b'], C_TEXT, 885, 130, align='center')
    text(screen, f"x{S['mult']} difficulty", F['s'], C_DIM, 885, 158, align='center')
    y = 150
    for lab, val, w8 in (('Science value', res['science'], '40%'), ('Cost efficiency', res['cost'], '20%'),
                         ('Safety margin', res['safety'], '25%'), ('Creativity', res['creativity'], '15%')):
        text(screen, f"{lab} ({w8})", F['n'], C_TEXT, 40, y)
        pygame.draw.rect(screen, (28, 34, 64), (260, y + 2, 400, 16), border_radius=8)
        pygame.draw.rect(screen, C_GOOD if val >= 60 else C_WARN if val >= 35 else C_BAD, (260, y + 2, int(4 * val), 16), border_radius=8)
        text(screen, f"{val:.0f}", F['n'], C_TEXT, 676, y)
        y += 30
    if res['parts']:
        text(screen, 'Safety: ' + '  '.join(f"{n} {v:.0f}" for n, v in res['parts']), F['s'], C_DIM, 40, y + 4, maxw=720)
    if S['launched']:
        text(screen, f"Orbit fit {res['fit']:.2f}   Data returned {res['ret'] * 100:.0f}%   Spent {S['spent']:.0f}/{S['budget']} M$   Schedule {S['time']:.1f} months", F['s'], C_DIM, 40, y + 24, maxw=740)
    for cx0, title, lst, c0 in ((40, 'What went right', res['good'], C_GOOD), (520, 'What went wrong', res['bad'], C_BAD)):
        pygame.draw.rect(screen, C_PANEL, (cx0 - 10, 320, 460, 360), border_radius=12)
        text(screen, title, F['b'], c0, cx0, 330)
        yy = 366
        for ln in lst or ['Nothing notable.']:
            yy = text(screen, '- ' + ln, F['n'], C_TEXT, cx0, yy, maxw=430, lh=19) + 8
    text(screen, 'R: new mission     ESC: quit', F['b'], C_WARN, W // 2, 712, align='center')


# ---------------------------------------------------------------- main loop
def init():
    global screen
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption('for_astronaut | Space Mission Design Game')
    F.update(big=pygame.font.SysFont(FONT_UI, 72, bold=True), h1=pygame.font.SysFont(FONT_UI, 40, bold=True),
             h2=pygame.font.SysFont(FONT_UI, 22, bold=True), b=pygame.font.SysFont(FONT_UI, 18, bold=True),
             n=pygame.font.SysFont(FONT_UI, 15), s=pygame.font.SysFont(FONT_UI, 13), m=pygame.font.SysFont(FONT_MONO, 14))
    asset_dir = os.path.dirname(os.path.abspath(__file__))
    A['menu'] = pygame.image.load(os.path.join(asset_dir, 'menu-completo.png')).convert_alpha()
    for emotion, filename in ASSET_FILES.items():
        A[emotion] = pygame.image.load(os.path.join(asset_dir, filename)).convert_alpha()
    new_game()
    G['scene'] = 'title'


def update(dt, events):
    """Advance the game. Returns False when the player quits."""
    sc = G['scene']
    G['toast'] = (G['toast'][0], G['toast'][1], max(0.0, G['toast'][2] - dt))
    if G['fly']:
        G['fly']['t'] += dt
        if G['fly']['t'] >= 0.25:
            G['fly'] = None
            advance()
    if sc == 'flight':
        update_flight(dt)
    for e in events:
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            return False
        go = e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN)
        if sc == 'title' and (go or (e.type == pygame.MOUSEBUTTONDOWN and menu_play_rect().collidepoint(e.pos))):
            new_game()
            advance()
        elif sc == 'banner' and (go or e.type == pygame.MOUSEBUTTONDOWN):
            advance()
        elif sc == 'flight' and (go or e.type == pygame.MOUSEBUTTONDOWN) and G['fl']['done']:
            advance()
        elif sc == 'end' and e.type == pygame.KEYDOWN and e.key == pygame.K_r:
            new_game()
            advance()
        elif sc == 'card' and not G['fly']:
            if e.type == pygame.MOUSEMOTION:
                G['lean'] = -1 if e.pos[0] < W // 2 - 60 else 1 if e.pos[0] > W // 2 + 60 else 0
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                side = -1 if e.pos[0] < W // 2 else 1
                G['lean'] = side
                choose(side)
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                side = -1 if e.key in (pygame.K_LEFT, pygame.K_a) else 1
                if G['lean'] == side:
                    choose(side)       # second press confirms
                else:
                    G['lean'] = side   # first press previews
    return True


def draw(t):
    {'title': draw_title, 'banner': draw_banner, 'card': draw_card_scene, 'flight': draw_flight, 'end': draw_end}[G['scene']](t)


def main():
    init()
    clock = pygame.time.Clock()
    t = 0.0
    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        t += dt
        if not update(dt, pygame.event.get()):
            break
        draw(t)
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
