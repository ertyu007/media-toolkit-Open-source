import unittest

from clipora.ui_components.widgets import (
    segment_index_at,
    segment_layout,
    segment_origin,
)


class SegmentLayoutTests(unittest.TestCase):
    def test_no_gap_matches_old_math(self):
        seg, stride = segment_layout(300.0, 3)
        self.assertEqual((seg, stride), (100.0, 100.0))
        self.assertEqual(segment_origin(2, 300.0, 3), 200.0)
        self.assertEqual(segment_index_at(150.0, 300.0, 3), 1)

    def test_gap_shrinks_segments(self):
        seg, stride = segment_layout(300.0, 3, 8.0)
        self.assertAlmostEqual(seg, (300.0 - 16.0) / 3)
        self.assertAlmostEqual(stride, seg + 8.0)
        # Last segment still ends exactly at the edge.
        self.assertAlmostEqual(segment_origin(2, 300.0, 3, 8.0) + seg, 300.0)

    def test_hit_testing_with_gap(self):
        # 3 segments of ~94.67px with 8px gaps: centers hit, edges clamp.
        self.assertEqual(segment_index_at(10.0, 300.0, 3, 8.0), 0)
        self.assertEqual(segment_index_at(150.0, 300.0, 3, 8.0), 1)
        self.assertEqual(segment_index_at(290.0, 300.0, 3, 8.0), 2)
        self.assertEqual(segment_index_at(9999.0, 300.0, 3, 8.0), 2)
        self.assertEqual(segment_index_at(-5.0, 300.0, 3, 8.0), 0)

    def test_degenerate_inputs(self):
        self.assertEqual(segment_layout(300.0, 0), (0.0, 0.0))
        self.assertEqual(segment_index_at(10.0, 300.0, 0), 0)
        self.assertEqual(segment_index_at(10.0, 0.0, 3), 0)


if __name__ == '__main__':
    unittest.main()
