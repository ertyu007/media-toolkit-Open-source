import unittest
from urllib.parse import unquote, urlsplit

from clipora.legal import DISCLAIMER_TEXT, DMCA_EMAIL, DMCA_NOTE, build_dmca_mailto


class LegalTextTests(unittest.TestCase):
    def test_disclaimer_contains_key_sections(self):
        for section in (
            'คำปฏิเสธความรับผิดชอบด้านลิขสิทธิ์',
            'ข้อกำหนดในการใช้งาน',
            'การปฏิเสธความรับผิดชอบ',
            'การรายงาน DMCA',
            'เจ้าของ',
        ):
            with self.subTest(section=section):
                self.assertIn(section, DISCLAIMER_TEXT)

    def test_dmca_note_is_available(self):
        self.assertIn('counter-notice', DMCA_NOTE)

    def test_dmca_email_is_under_ertyu_dev(self):
        self.assertEqual(DMCA_EMAIL, 'dmca@ertyu.dev')


class DmcaMailtoTests(unittest.TestCase):
    def test_builds_mailto_to_dmca_address(self):
        mailto = build_dmca_mailto(
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'rights@example.com',
            'I own this video',
        )
        self.assertTrue(mailto.startswith('mailto:dmca@ertyu.dev?'))
        parts = urlsplit(mailto)
        query = dict(
            pair.split('=', 1)
            for pair in parts.query.split('&')
            if '=' in pair
        )
        self.assertIn('subject', query)
        self.assertIn('body', query)
        self.assertIn('https://www.youtube.com/watch?v=dQw4w9WgXcQ', unquote(query['body']))
        self.assertIn('rights@example.com', unquote(query['body']))
        self.assertIn('I own this video', unquote(query['body']))

    def test_encodes_special_characters(self):
        mailto = build_dmca_mailto(
            'https://example.com/video?a=1&b=2',
            'holder@example.com',
            'การละเมิด',
        )
        self.assertNotIn(' ', mailto)


if __name__ == '__main__':
    unittest.main()
