import unittest

from clipora.legal import DISCLAIMER_TEXT


class LegalTextTests(unittest.TestCase):
    def test_disclaimer_contains_key_sections(self):
        for section in (
            'คำปฏิเสธความรับผิดชอบด้านลิขสิทธิ์',
            'ข้อกำหนดในการใช้งาน',
            'การปฏิเสธความรับผิดชอบ',
            'เจ้าของ',
        ):
            with self.subTest(section=section):
                self.assertIn(section, DISCLAIMER_TEXT)

    def test_disclaimer_holds_user_responsible(self):
        self.assertIn('ผู้ใช้มีหน้าที่ตรวจสอบสิทธิ์', DISCLAIMER_TEXT)


if __name__ == '__main__':
    unittest.main()
