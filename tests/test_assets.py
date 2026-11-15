"""Static checks for the asset tree (no Pygame window needed)."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, 'for_astronaut_mobile')
SNAKE_CASE = re.compile(r'^[a-z0-9]+(_[a-z0-9]+)*$')


def asset_files(base):
    """Return the asset file paths under ``base/assets``, relative to ``base``."""
    found = []
    for folder, _, files in os.walk(os.path.join(base, 'assets')):
        for name in files:
            found.append(os.path.relpath(os.path.join(folder, name), base))
    return sorted(found)


class AssetTreeTest(unittest.TestCase):

    def test_names_are_snake_case(self):
        for base in (ROOT, MOBILE):
            for rel in asset_files(base):
                parts = rel.split(os.sep)
                for folder in parts[:-1]:
                    self.assertRegex(folder, SNAKE_CASE, rel)
                stem, _ = os.path.splitext(parts[-1])
                if parts[-1] != '.gitkeep':
                    self.assertRegex(stem, SNAKE_CASE, rel)

    def test_mobile_images_match_desktop(self):
        """The mobile edition ships its own copy of the images; keep them in sync."""
        mobile = asset_files(MOBILE)
        self.assertTrue(mobile)
        for rel in mobile:
            with open(os.path.join(ROOT, rel), 'rb') as a, open(os.path.join(MOBILE, rel), 'rb') as b:
                self.assertEqual(a.read(), b.read(), rel)


if __name__ == '__main__':
    unittest.main()
