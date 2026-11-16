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
HOW_IT_WORKS = {'how_page', 'how_btn', 'how_btn_pressed'}   # desktop only
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
        expected = IMAGES | HOW_IT_WORKS if name == 'desktop' else IMAGES
        self.assertEqual(set(game.A), expected)
        if hasattr(game, 'SND'):
            self.assertEqual(set(game.SND), {'card', 'click', 'rocket', 'success', 'fail', 'alarm'})
            self.assertTrue(pygame.mixer.music.get_busy(), 'theme music did not start')
        for seed in range(GAMES):
            self.assertEqual(play(game, seed), 'end', f'{name} game {seed}')

    def test_desktop(self):
        self.check_edition('desktop')

    def test_mobile(self):
        self.check_edition('mobile')

    def test_how_it_works_screen(self):
        """Desktop title menu: HOW IT WORKS opens the guide; click, Space or Esc return."""
        game = load('desktop', EDITIONS['desktop'])
        game.init()
        click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)
        key = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
        how, play = game.menu_how_rect(), game.menu_play_rect()
        self.assertFalse(how.colliderect(play))
        for back in (click((5, 5)), key(pygame.K_SPACE), key(pygame.K_ESCAPE)):
            game.G['scene'] = 'title'
            game.update(0.016, [click(how.center)])
            self.assertEqual(game.G['scene'], 'how')
            game.draw(0.0)
            self.assertTrue(game.update(0.016, [back]), 'Esc on the guide must not quit')
            self.assertEqual(game.G['scene'], 'title')
        # The guide page ends with the AI watermark required by Space Apps; the
        # blinking hint must never cover it (bottom 30 px identical, hint on or off).
        game.G['scene'] = 'how'
        band = lambda: pygame.image.tobytes(game.screen.subsurface((0, game.H - 30, game.W, 30)), 'RGB')
        game.draw(0.0)
        hint_on = band()
        game.draw(0.6)
        self.assertEqual(hint_on, band(), 'the hint covers the AI watermark')
        game.G['scene'] = 'title'
        self.assertFalse(game.update(0.016, [key(pygame.K_ESCAPE)]), 'Esc on the title quits')
        game.G['scene'] = 'title'
        game.update(0.016, [click(play.center)])
        self.assertNotEqual(game.G['scene'], 'title')


if __name__ == '__main__':
    unittest.main()
