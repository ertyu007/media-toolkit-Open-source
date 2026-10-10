import re
import unittest

from clipora.ui_components.widgets import (
    rainbow_color,
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


class RainbowColorTests(unittest.TestCase):
    def test_hex_format_and_hue_wrap(self):
        color = rainbow_color(0.0)
        self.assertTrue(re.fullmatch(r'#[0-9a-f]{6}', color), color)
        self.assertEqual(rainbow_color(0.0), rainbow_color(1.0))
        self.assertNotEqual(rainbow_color(0.0), rainbow_color(0.5))

    def test_switch_tick_repaints_text(self):
        try:
            import tkinter as tk

            from clipora.ui_components.widgets import Switch

            root = tk.Tk()
            root.withdraw()
        except Exception as exc:
            self.skipTest(f'no display: {exc}')
        try:
            variable = tk.BooleanVar(value=False)
            switch = Switch(root, variable=variable, text='demo', rainbow=True)
            switch.update()
            before = switch.itemcget(switch.find_all()[-1], 'fill')
            switch._rainbow_tick()
            switch.update()
            after = switch.itemcget(switch.find_all()[-1], 'fill')
            self.assertNotEqual(before, after)
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
