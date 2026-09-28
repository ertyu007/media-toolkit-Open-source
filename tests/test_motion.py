import unittest

from clipora.ui_components.motion import (
    Pulse,
    Tween,
    ease_in_out_quad,
    ease_out_cubic,
    fade_in_window,
    hex_to_rgb,
    mix_color,
    rgb_to_hex,
)


class FakeScheduler:
    """Deterministic stand-in for widget.after/after_cancel."""

    def __init__(self):
        self.queued: list[tuple[int, object, object]] = []
        self.cancelled: list[object] = []
        self._next_id = 0

    def after(self, delay_ms, callback):
        self._next_id += 1
        handle = ('after', self._next_id)
        self.queued.append((delay_ms, handle, callback))
        return handle

    def cancel(self, handle):
        self.cancelled.append(handle)
        self.queued = [item for item in self.queued if item[1] != handle]

    def fire_all(self, limit=1000):
        fired = 0
        while self.queued and fired < limit:
            _, _, callback = self.queued.pop(0)
            callback()
            fired += 1
        return fired


class ColorHelperTests(unittest.TestCase):
    def test_hex_round_trip(self):
        self.assertEqual(hex_to_rgb('#8b5cf6'), (139, 92, 246))
        self.assertEqual(rgb_to_hex(139, 92, 246), '#8b5cf6')

    def test_invalid_hex_is_rejected(self):
        for text in ('#fff', 'not a color', '#gggggg', ''):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    hex_to_rgb(text)

    def test_mix_color_endpoints_and_midpoint(self):
        self.assertEqual(mix_color('#000000', '#ffffff', 0.0), '#000000')
        self.assertEqual(mix_color('#000000', '#ffffff', 1.0), '#ffffff')
        self.assertEqual(mix_color('#000000', '#ffffff', 0.5), '#808080')

    def test_mix_color_clamps_amount(self):
        self.assertEqual(mix_color('#000000', '#ffffff', -2.0), '#000000')
        self.assertEqual(mix_color('#000000', '#ffffff', 2.0), '#ffffff')

    def test_easing_boundaries(self):
        for ease in (ease_out_cubic, ease_in_out_quad):
            self.assertAlmostEqual(ease(0.0), 0.0)
            self.assertAlmostEqual(ease(1.0), 1.0)
            middle = ease(0.5)
            self.assertGreater(middle, 0.0)
            self.assertLess(middle, 1.0)


class TweenTests(unittest.TestCase):
    def test_tween_reaches_one_and_calls_done(self):
        scheduler = FakeScheduler()
        tween = Tween(scheduler.after, scheduler.cancel, duration_ms=48, frame_ms=16)
        frames: list[float] = []
        finished: list[bool] = []
        tween.start(frames.append, lambda: finished.append(True))
        self.assertTrue(tween.running)
        scheduler.fire_all()
        self.assertFalse(tween.running)
        self.assertTrue(frames)
        self.assertAlmostEqual(frames[-1], 1.0)
        self.assertEqual(finished, [True])
        self.assertTrue(all(earlier <= later for earlier, later in zip(frames, frames[1:])))

    def test_restart_cancels_previous_tween(self):
        scheduler = FakeScheduler()
        tween = Tween(scheduler.after, scheduler.cancel, duration_ms=160, frame_ms=16)
        first_frames: list[float] = []
        second_frames: list[float] = []
        tween.start(first_frames.append)
        first_pending = scheduler.queued[-1][1]
        tween.start(second_frames.append)
        self.assertIn(first_pending, scheduler.cancelled)
        scheduler.fire_all()
        self.assertEqual(first_frames, [])
        self.assertTrue(second_frames)

    def test_cancel_stops_frames(self):
        scheduler = FakeScheduler()
        tween = Tween(scheduler.after, scheduler.cancel, duration_ms=160, frame_ms=16)
        frames: list[float] = []
        tween.start(frames.append)
        tween.cancel()
        scheduler.fire_all()
        self.assertEqual(frames, [])
        self.assertFalse(tween.running)

    def test_frame_exception_still_finishes(self):
        scheduler = FakeScheduler()
        tween = Tween(scheduler.after, scheduler.cancel, duration_ms=32, frame_ms=16)
        finished: list[bool] = []

        def bad_frame(_progress):
            raise RuntimeError('widget gone')

        tween.start(bad_frame, lambda: finished.append(True))
        scheduler.fire_all()
        self.assertEqual(finished, [True])
        self.assertFalse(tween.running)


class PulseTests(unittest.TestCase):
    def test_pulse_loops_until_stopped(self):
        scheduler = FakeScheduler()
        pulse = Pulse(scheduler.after, scheduler.cancel, period_ms=200, frame_ms=50)
        frames: list[float] = []
        pulse.start(frames.append)
        self.assertTrue(pulse.running)
        scheduler.fire_all(limit=6)
        self.assertTrue(frames)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in frames))
        pulse.stop()
        count = len(frames)
        scheduler.fire_all()
        self.assertEqual(len(frames), count)
        self.assertFalse(pulse.running)

    def test_restart_replaces_previous_loop(self):
        scheduler = FakeScheduler()
        pulse = Pulse(scheduler.after, scheduler.cancel, period_ms=200, frame_ms=50)
        pulse.start(lambda _phase: None)
        first_pending = scheduler.queued[-1][1]
        pulse.start(lambda _phase: None)
        self.assertIn(first_pending, scheduler.cancelled)


class FakeWindow:
    def __init__(self):
        self.alpha: float | None = None
        self.destroyed = False

    def attributes(self, _name, value):
        if self.destroyed:
            raise RuntimeError('window gone')
        self.alpha = value


class FadeInTests(unittest.TestCase):
    def test_fade_goes_transparent_to_opaque(self):
        scheduler = FakeScheduler()
        window = FakeWindow()
        fade_in_window(window, scheduler.after, duration_ms=48)
        self.assertEqual(window.alpha, 0.0)
        scheduler.fire_all()
        self.assertAlmostEqual(window.alpha, 1.0)

    def test_destroyed_window_does_not_raise(self):
        scheduler = FakeScheduler()
        window = FakeWindow()
        window.destroyed = True
        fade_in_window(window, scheduler.after, duration_ms=48)
        scheduler.fire_all()


if __name__ == '__main__':
    unittest.main()
