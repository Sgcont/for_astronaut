"""Headless smoke test: load each edition, check its assets and play seeded games.

Run with:  python -m unittest discover -s tests -v
"""
import importlib.util
import os
import random
import sys
import unittest

# SDL must use its dummy drivers before Pygame is imported.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.dont_write_bytecode = True

import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITIONS = {
    'desktop': os.path.join(ROOT, 'for_astronaut.py'),
    'mobile': os.path.join(ROOT, 'for_astronaut_mobile', 'for_astronaut.py'),
}
IMAGES = {'menu', 'simple', 'very_angry', 'very_happy', 'space', 'angry', 'waving'}
GAMES = 5


def load(name, path):
    """Import a game file as a module without running its main loop."""
    spec = importlib.util.spec_from_file_location(f'for_astronaut_{name}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def play(game, seed):
    """Play one game with random choices; return the final scene."""
    random.seed(seed)
    game.new_game()
    game.advance()
    t = 0.0
    for _ in range(4000):
        if game.G['scene'] == 'end':
            break
        if game.G['scene'] == 'card' and not game.G['fly']:
            key = random.choice([pygame.K_LEFT, pygame.K_RIGHT])
            events = [pygame.event.Event(pygame.KEYDOWN, key=key)] * 2
        else:
            events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)]
        for step in range(3):
            t += 0.05
            game.update(0.05, events if step == 0 else [])
            game.draw(t)
    return game.G['scene']


class SmokeTest(unittest.TestCase):

    def tearDown(self):
        pygame.quit()

    def check_edition(self, name):
        game = load(name, EDITIONS[name])
        game.init()
        self.assertEqual(set(game.A), IMAGES)
        if hasattr(game, 'SND'):
            self.assertEqual(set(game.SND), {'card', 'click', 'rocket', 'success', 'fail', 'alarm'})
            self.assertTrue(pygame.mixer.music.get_busy(), 'theme music did not start')
        for seed in range(GAMES):
            self.assertEqual(play(game, seed), 'end', f'{name} game {seed}')

    def test_desktop(self):
        self.check_edition('desktop')

    def test_mobile(self):
        self.check_edition('mobile')


if __name__ == '__main__':
    unittest.main()
