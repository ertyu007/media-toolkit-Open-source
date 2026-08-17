import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from clipora.donate import donate_image_path


class DonateAssetTests(unittest.TestCase):
    @patch('clipora.donate.sys.frozen', False, create=True)
    @patch('clipora.donate.sys._MEIPASS', None, create=True)
    def test_project_asset_directory_is_discovered(self):
        from clipora.donate import DONATE_IMAGE_NAME

        with TemporaryDirectory() as directory:
            asset = Path(directory) / DONATE_IMAGE_NAME
            asset.write_bytes(b'qr')
            with patch('clipora.donate._resource_directories', return_value=(Path(directory),)):
                self.assertEqual(donate_image_path(), asset)

    @patch('clipora.donate.sys.frozen', False, create=True)
    @patch('clipora.donate.sys._MEIPASS', None, create=True)
    def test_missing_asset_returns_none(self):
        with TemporaryDirectory() as directory:
            with patch('clipora.donate._resource_directories', return_value=(Path(directory),)):
                self.assertIsNone(donate_image_path())

    @patch('clipora.donate.sys.frozen', True, create=True)
    @patch('clipora.donate.sys._MEIPASS', 'C:\\bundle\\_internal', create=True)
    @patch('clipora.donate.sys.executable', 'C:\\bundle\\Clipora.exe')
    def test_bundled_asset_has_priority(self):
        from clipora.donate import DONATE_IMAGE_NAME

        with TemporaryDirectory() as directory:
            bundled = Path(directory) / DONATE_IMAGE_NAME
            bundled.write_bytes(b'bundled')
            with patch(
                'clipora.donate._resource_directories',
                return_value=(Path('C:\\bundle\\_internal'), Path('C:\\bundle'), Path(directory)),
            ):
                self.assertEqual(donate_image_path(), bundled)


if __name__ == '__main__':
    unittest.main()