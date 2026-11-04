import unittest

from clipora.url_queue import (
    add_url,
    aggregate_percent,
    queue_summary,
    remove_at,
)

LINK_A = 'https://example.com/a'
LINK_B = 'https://example.com/b'
LINK_C = 'https://example.com/c'


class AddUrlTests(unittest.TestCase):
    def test_appends_valid_link_trimmed(self):
        self.assertEqual(
            add_url((), f'  {LINK_A}  '),
            (LINK_A,),
        )
        self.assertEqual(add_url((LINK_A,), LINK_B), (LINK_A, LINK_B))

    def test_returns_new_tuple_and_keeps_input(self):
        queue = [LINK_A]
        result = add_url(queue, LINK_B)
        self.assertEqual(result, (LINK_A, LINK_B))
        self.assertEqual(queue, [LINK_A])

    def test_invalid_link_uses_core_thai_message(self):
        with self.assertRaisesRegex(ValueError, 'http'):
            add_url((), 'ftp://example.com/file.mp4')
        with self.assertRaises(ValueError):
            add_url((), 'not a link')

    def test_rejects_duplicate_case_insensitively(self):
        with self.assertRaisesRegex(ValueError, 'อยู่ในคิว'):
            add_url((LINK_A,), LINK_A.upper())
        with self.assertRaisesRegex(ValueError, 'อยู่ในคิว'):
            add_url((LINK_A,), f'  {LINK_A}  ')

    def test_similar_links_are_not_duplicates(self):
        self.assertEqual(add_url((LINK_A,), LINK_B), (LINK_A, LINK_B))


class RemoveAtTests(unittest.TestCase):
    def test_removes_middle_item(self):
        queue = (LINK_A, LINK_B, LINK_C)
        self.assertEqual(remove_at(queue, 1), (LINK_A, LINK_C))
        self.assertEqual(queue, (LINK_A, LINK_B, LINK_C))

    def test_removes_ends(self):
        self.assertEqual(remove_at((LINK_A, LINK_B), 0), (LINK_B,))
        self.assertEqual(remove_at((LINK_A, LINK_B), 1), (LINK_A,))
        self.assertEqual(remove_at((LINK_A,), 0), ())

    def test_out_of_bounds_is_rejected(self):
        with self.assertRaises(IndexError):
            remove_at((LINK_A,), 1)
        with self.assertRaises(IndexError):
            remove_at((LINK_A,), -1)
        with self.assertRaises(IndexError):
            remove_at((), 0)


class AggregatePercentTests(unittest.TestCase):
    def test_second_of_four_at_half_is_37_5(self):
        self.assertAlmostEqual(aggregate_percent(2, 4, 50.0), 37.5)

    def test_boundaries(self):
        self.assertEqual(aggregate_percent(1, 4, 0.0), 0.0)
        self.assertEqual(aggregate_percent(4, 4, 100.0), 100.0)

    def test_partial_progress_is_incremental(self):
        self.assertAlmostEqual(aggregate_percent(1, 2, 50.0), 25.0)
        self.assertAlmostEqual(aggregate_percent(2, 3, 25.0), 125.0 / 3)

    def test_clamped_to_0_100(self):
        self.assertEqual(aggregate_percent(1, 4, -50.0), 0.0)
        self.assertEqual(aggregate_percent(5, 4, 100.0), 100.0)
        self.assertEqual(aggregate_percent(0, 4, 50.0), 0.0)
        self.assertEqual(aggregate_percent(2, 4, 1000.0), 100.0)

    def test_zero_or_negative_total_is_zero(self):
        self.assertEqual(aggregate_percent(1, 0, 50.0), 0.0)
        self.assertEqual(aggregate_percent(1, -3, 50.0), 0.0)


class QueueSummaryTests(unittest.TestCase):
    def test_empty_queue_message(self):
        self.assertEqual(queue_summary(()), 'ยังไม่มีลิงก์ในคิว')
        self.assertEqual(queue_summary([]), 'ยังไม่มีลิงก์ในคิว')

    def test_counts_links(self):
        self.assertEqual(queue_summary([LINK_A]), 'คิว 1 ลิงก์')
        self.assertEqual(queue_summary((LINK_A, LINK_B, LINK_C)), 'คิว 3 ลิงก์')


if __name__ == '__main__':
    unittest.main()
