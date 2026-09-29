import unittest

from clipora.ui import load_job_defaults, validate_job_settings
from clipora.ui_components.theme import (
    _DARK,
    _LIGHT,
    normalize_theme,
    resolve_palette,
)


class ThemeTests(unittest.TestCase):
    def test_palettes_cover_same_keys(self):
        self.assertEqual(set(_DARK), set(_LIGHT))
        self.assertGreater(
            sum(1 for key in _DARK if _DARK[key] != _LIGHT[key]), 20)

    def test_resolve_branches(self):
        self.assertEqual(resolve_palette('dark', False)['BG'], _DARK['BG'])
        self.assertEqual(resolve_palette('light', True)['BG'], _LIGHT['BG'])
        self.assertEqual(resolve_palette('system', False)['BG'], _LIGHT['BG'])
        self.assertEqual(resolve_palette('system', True)['BG'], _DARK['BG'])
        self.assertEqual(resolve_palette('neon', True)['BG'], _DARK['BG'])

    def test_normalize_theme(self):
        self.assertEqual(normalize_theme('light'), 'light')
        self.assertEqual(normalize_theme(' Dark '), 'dark')
        self.assertEqual(normalize_theme('neon'), 'system')
        self.assertEqual(normalize_theme(None), 'system')


class JobSettingsTests(unittest.TestCase):
    def test_empty_settings_yield_sane_defaults(self):
        defaults = validate_job_settings({})
        self.assertEqual(defaults['mode'], 'video')
        self.assertEqual(defaults['audio_format'], 'MP3')
        self.assertEqual(defaults['theme'], 'system')
        self.assertTrue(defaults['chime_enabled'])
        self.assertTrue(defaults['auto_update_check'])
        self.assertTrue(defaults['destination'])
        self.assertNotIn('auto_debug', defaults)

    def test_invalid_values_fall_back(self):
        validated = validate_job_settings({
            'mode': 'neon',
            'audio_format': 'WMA',
            'video_format': 'AVI',
            'fps': '999fps',
            'theme': 'neon',
        })
        self.assertEqual(validated['mode'], 'video')
        self.assertEqual(validated['audio_format'], 'MP3')
        self.assertEqual(validated['fps'], 'สูงสุด')
        self.assertEqual(validated['theme'], 'system')

    def test_valid_values_survive(self):
        validated = validate_job_settings({
            'mode': 'stems',
            'audio_format': 'FLAC',
            'theme': 'light',
            'chime_enabled': False,
            'destination': 'D:\\Music',
        })
        self.assertEqual(validated['mode'], 'stems')
        self.assertEqual(validated['audio_format'], 'FLAC')
        self.assertEqual(validated['theme'], 'light')
        self.assertFalse(validated['chime_enabled'])
        self.assertEqual(validated['destination'], 'D:\\Music')

    def test_load_job_defaults_never_raises(self):
        defaults = load_job_defaults()
        self.assertIn(defaults['mode'], ('audio', 'video', 'stems'))


if __name__ == '__main__':
    unittest.main()
