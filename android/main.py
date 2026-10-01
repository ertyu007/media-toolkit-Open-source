"""Clipora on Android — Kivy front end for ``core``.

Threading contract (same rule as the PC build): worker threads never touch a
Kivy widget. Each worker reports through a queue, and ``Clock`` drains that
queue on the main thread. Every job is snapshotted into a frozen dataclass
before its thread starts, so later UI edits cannot change a running job.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault('KIVY_NO_ARGS', '1')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

import theme
from core import ffmpeg
from core import history
from core import ytdlp
from core.tools import (
    acquire_wake_lock,
    external_files_dir,
    missing_tools,
    prepare_environment,
    release_wake_lock,
)

AUDIO_FORMATS = list(ffmpeg.AUDIO_FORMATS)
QUALITIES = list(ffmpeg.VIDEO_QUALITY_PRESETS)
FPS_CHOICES = list(ffmpeg.FPS_OPTIONS)
LINK_QUALITIES = list(ytdlp.VIDEO_QUALITIES)
MEDIA_FILTER = ('*.mp4', '*.mkv', '*.mov', '*.webm', '*.avi', '*.m4v', '*.mp3', '*.m4a', '*.wav', '*.flac', '*.opus', '*.aac')


@dataclass(frozen=True)
class ConvertJob:
    source: Path
    destination: Path
    mode: str
    quality: str
    audio_format: str
    video_format: str
    fps: str
    start: float | None
    duration: float | None


@dataclass(frozen=True)
class DownloadJob:
    spec: ytdlp.ImportSpec


class JobRunner:
    """Runs one job on a worker thread and marshals events onto the Kivy thread.

    Events are ``(kind, payload)`` tuples pushed to a queue that the screen
    drains via :meth:`pump`, scheduled on ``Clock``. A crashed job emits
    ``('error', message)`` so the UI can never hang on a dead thread, and a
    wake lock is held for the whole run so Doze cannot kill a long job.
    """

    def __init__(self) -> None:
        self.events: queue.Queue = queue.Queue()
        self.token: ffmpeg.CancellationToken | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, target, *args) -> None:
        if self.running:
            return
        self.token = ffmpeg.CancellationToken()
        self._thread = threading.Thread(
            target=self._guarded,
            args=(target, *args, self.token, self.events.put),
            daemon=True,
        )
        self._thread.start()

    @staticmethod
    def _guarded(target, *args) -> None:
        emit = args[-1]
        acquire_wake_lock()
        try:
            target(*args)
        except ffmpeg.ConversionCancelled:
            emit('error', 'ยกเลิกงานแล้ว')
        except Exception as exc:  # surface crashes instead of hanging the UI
            emit('error', str(exc) or type(exc).__name__)
        finally:
            release_wake_lock()

    def cancel(self) -> None:
        if self.token is not None:
            self.token.cancel()

    def pump(self, handler) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                return
            handler(kind, payload)


def _select_files(multiple: bool) -> list[str]:
    from plyer import filechooser

    chooser = filechooser.FileChooser(
        filters=MEDIA_FILTER,
        multiple=multiple,
        title='เลือกไฟล์',
    )
    chooser.run()
    selection = chooser.selection or []
    return selection if multiple else selection[:1]


def _run_convert(job: ConvertJob, token, emit) -> None:
    emit('status', 'กำลังอ่านข้อมูลไฟล์…')
    info = ffmpeg.probe(job.source)
    ffmpeg.validate_operation(info, job.mode)
    job.destination.mkdir(parents=True, exist_ok=True)
    start_arg, duration_arg, effective = ffmpeg.normalize_trim(
        job.start, job.duration, info.duration,
    )
    ffmpeg.check_disk_space(job.destination)
    target = ffmpeg.output_path(
        job.source, job.destination, job.mode, job.audio_format, job.video_format,
    )
    temporary = ffmpeg.temporary_output_path(target)
    command = ffmpeg.build_command(
        job.source,
        temporary,
        job.mode,
        job.quality,
        job.audio_format,
        video_format=job.video_format,
        fps=job.fps,
        start_time=start_arg,
        duration_time=duration_arg,
    )
    emit('status', f'กำลังแปลง {target.name}')
    try:
        ffmpeg.convert(command, temporary, effective, lambda p: emit('progress', p), token)
        ffmpeg.finalize_output(temporary, target)
    except BaseException:
        ffmpeg.cleanup_temporary_output(temporary, target)
        raise
    emit('done', target)


def _run_download(job: DownloadJob, token, emit) -> None:
    emit('status', 'กำลังดาวน์โหลด…')
    target = ytdlp.download(
        job.spec,
        lambda fraction, speed, eta: emit('progress', (fraction, speed, eta)),
        token,
    )
    emit('done', target)


def _section(title: str) -> Label:
    label = Label(
        text=title,
        size_hint_y=None,
        height=dp(30),
        halign='left',
        valign='middle',
        color=theme.color('ACCENT_GLOW'),
        font_size=dp(13),
    )
    label.bind(size=lambda widget, value: setattr(widget, 'text_size', value))
    return label


def _field(text: str = '') -> TextInput:
    return TextInput(
        text=text,
        multiline=False,
        size_hint_y=None,
        height=dp(40),
        background_color=theme.color('FIELD'),
        foreground_color=theme.color('TEXT'),
        cursor_color=theme.color('ACCENT'),
        padding=[dp(10), dp(10)],
    )


def _spinner(values: list[str], default: str) -> Spinner:
    return Spinner(
        text=default,
        values=values,
        size_hint_y=None,
        height=dp(40),
        background_color=theme.color('BUTTON_BG'),
        background_normal='',
        color=theme.color('TEXT'),
    )


def _button(text: str, accent: bool = False) -> Button:
    return Button(
        text=text,
        size_hint_y=None,
        height=dp(46),
        background_normal='',
        background_color=theme.color('ACCENT' if accent else 'BUTTON_BG'),
        color=theme.color('TEXT'),
    )


def _body() -> ScrollView:
    scroll = ScrollView(do_scroll_x=False)
    inner = BoxLayout(
        orientation='vertical',
        size_hint_y=None,
        padding=dp(14),
        spacing=dp(8),
    )
    inner.bind(minimum_height=inner.setter('height'))
    scroll.add_widget(inner)
    return scroll, inner


def _tabbar(current: str) -> BoxLayout:
    bar = BoxLayout(size_hint_y=None, height=dp(52), padding=dp(8), spacing=dp(8))
    for name, label in (
        ('convert', 'แปลงไฟล์'),
        ('download', 'ดาวน์โหลด'),
        ('history', 'ประวัติ'),
    ):
        button = _button(label, accent=name == current)
        button.bind(on_release=lambda *_, target=name: _switch(target))
        bar.add_widget(button)
    return bar


def _switch(target: str) -> None:
    App.get_running_app().root.current = target


class ConvertScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.files: list[Path] = []
        self.runner = JobRunner()
        root = BoxLayout(orientation='vertical')
        scroll, body = _body()
        root.add_widget(scroll)
        root.add_widget(self._tabbar())
        self.add_widget(root)
        self._build(body)
        Clock.schedule_interval(lambda dt: self.runner.pump(self._on_event), 1 / 30)

    def _build(self, body: BoxLayout) -> None:
        self.pick = _button('เลือกไฟล์ (เลือกได้หลายไฟล์)')
        self.pick.bind(on_release=lambda *_: self._choose())
        self.file_list = Label(
            text='ยังไม่ได้เลือกไฟล์',
            size_hint_y=None,
            height=dp(48),
            halign='left',
            valign='top',
            color=theme.color('MUTED'),
            font_size=dp(12),
        )
        self.file_list.bind(size=lambda w, v: setattr(w, 'text_size', v))

        self.mode = _spinner(['เสียง', 'วิดีโอ'], 'เสียง')
        self.audio_format = _spinner(AUDIO_FORMATS, 'mp3')
        self.quality = _spinner(QUALITIES, 'Balanced')
        self.fps = _spinner(FPS_CHOICES, 'สูงสุด')
        self.start = _field('0')
        self.length = _field('')
        self.start.hint_text = 'จุดเริ่ม (วินาที หรือ MM:SS)'
        self.length.hint_text = 'ความยาว (วินาที หรือ MM:SS) — เว้นว่างไว้เพื่อจบไฟล์'

        self.output_label = Label(
            text='',
            size_hint_y=None,
            height=dp(34),
            halign='left',
            valign='middle',
            color=theme.color('MUTED'),
            font_size=dp(11),
        )
        self.output_label.bind(size=lambda w, v: setattr(w, 'text_size', v))

        self.status = self.output_label
        self.bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(6))
        self.start_button = _button('เริ่มแปลง', accent=True)
        self.start_button.bind(on_release=lambda *_: self._start())
        self.cancel_button = _button('ยกเลิก')
        self.cancel_button.bind(on_release=lambda *_: self.runner.cancel())

        body.add_widget(self.pick)
        body.add_widget(self.file_list)
        body.add_widget(_section('ตั้งค่า'))
        body.add_widget(_lbl('โหมด'))
        body.add_widget(self.mode)
        body.add_widget(_lbl('รูปแบบเสียง'))
        body.add_widget(self.audio_format)
        body.add_widget(_lbl('คุณภาพวิดีโอ'))
        body.add_widget(self.quality)
        body.add_widget(_lbl('เฟรมเรต'))
        body.add_widget(self.fps)
        body.add_widget(_section('ตัดช่วง (เว้นว่าง = ไม่ตัด)'))
        body.add_widget(self.start)
        body.add_widget(self.length)
        body.add_widget(self.bar)
        body.add_widget(self.status)
        body.add_widget(self.start_button)
        body.add_widget(self.cancel_button)

    def _tabbar(self) -> BoxLayout:
        return _tabbar('convert')

    def _choose(self) -> None:
        selected = _select_files(multiple=True)
        self.files = [Path(item) for item in selected]
        if not self.files:
            return
        names = '\n'.join(f'• {item.name}' for item in self.files[:6])
        if len(self.files) > 6:
            names += f'\n… และอีก {len(self.files) - 6} ไฟล์'
        self.file_list.text = names
        self.file_list.color = theme.color('TEXT')

    def _start(self) -> None:
        if self.runner.running:
            return
        try:
            start = ffmpeg.parse_trim_seconds(self.start.text)
            length = ffmpeg.parse_trim_seconds(self.length.text)
        except ValueError as exc:
            self.status.text = str(exc)
            self.status.color = theme.color('ERROR')
            return
        is_video = self.mode.text == 'วิดีโอ'
        mode = 'video' if is_video else 'audio'
        destination = external_files_dir() / 'output'
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.status.text = f'เปิดโฟลเดอร์ผลลัพธ์ไม่ได้: {exc}'
            self.status.color = theme.color('ERROR')
            return
        sources = self.files or []
        if not sources:
            self.status.text = 'กรุณาเลือกไฟล์ก่อน'
            self.status.color = theme.color('ERROR')
            return
        self.start_button.disabled = True
        self.bar.value = 0
        self.status.color = theme.color('MUTED')
        self._queue = [(source, destination) for source in sources]
        self._index = 0
        self._trim = (start, length)
        self._settings = (mode, self.quality.text, self.audio_format.text, self.fps.text)
        self._next()

    def _next(self) -> None:
        if self._index >= len(self._queue):
            self.start_button.disabled = False
            self.bar.value = 1
            self.status.text = f'เสร็จแล้ว {self._index} ไฟล์ → {external_files_dir() / "output"}'
            self.status.color = theme.color('SUCCESS')
            return
        source, destination = self._queue[self._index]
        mode, quality, audio_format, fps = self._settings
        start, length = self._trim
        job = ConvertJob(
            source=source,
            destination=destination,
            mode=mode,
            quality=quality,
            audio_format=audio_format,
            video_format='mp4',
            fps=fps,
            start=start,
            duration=length,
        )
        self.status.text = f'[{self._index + 1}/{len(self._queue)}] {source.name}'
        self._index += 1
        self._last_source = source
        self._last_mode = mode
        self.runner.start(_run_convert, job)

    def _on_event(self, kind: str, payload) -> None:
        if kind == 'progress':
            fraction = payload[0] if isinstance(payload, tuple) else payload
            self.bar.value = fraction
        elif kind == 'status':
            self.status.text = str(payload)
            self.status.color = theme.color('MUTED')
        elif kind == 'done':
            self._on_success(payload)
        else:
            self.start_button.disabled = False
            self.bar.value = 0
            self.status.text = str(payload)
            self.status.color = theme.color('ERROR')

    def _on_success(self, target: Path) -> None:
        self.bar.value = 1
        self.status.text = f'บันทึกแล้ว: {target.name}'
        self.status.color = theme.color('SUCCESS')
        history.add_entry(
            kind=self._last_mode,
            source_kind='file',
            name=target.name,
            target=target,
            source=str(self._last_source),
        )
        if self._index < len(self._queue):
            self._next()
        else:
            self.start_button.disabled = False


class DownloadScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.runner = JobRunner()
        root = BoxLayout(orientation='vertical')
        scroll, body = _body()
        root.add_widget(scroll)
        root.add_widget(self._tabbar())
        self.add_widget(root)
        self._build(body)
        Clock.schedule_interval(lambda dt: self.runner.pump(self._on_event), 1 / 30)

    def _build(self, body: BoxLayout) -> None:
        self.url = _field('')
        self.url.hint_text = 'วางลิงก์สาธารณะ (http/https)'
        self.mode = _spinner(['เสียง', 'วิดีโอ'], 'เสียง')
        self.audio_format = _spinner(AUDIO_FORMATS, 'mp3')
        self.quality = _spinner(LINK_QUALITIES, 'สูงสุด')
        self.fps = _spinner(FPS_CHOICES, 'สูงสุด')
        self.status = Label(
            text='',
            size_hint_y=None,
            height=dp(60),
            halign='left',
            valign='top',
            color=theme.color('MUTED'),
            font_size=dp(12),
        )
        self.status.bind(size=lambda w, v: setattr(w, 'text_size', v))
        self.bar = ProgressBar(max=1, value=0, size_hint_y=None, height=dp(6))
        self.start_button = _button('ดาวน์โหลด', accent=True)
        self.start_button.bind(on_release=lambda *_: self._start())
        self.cancel_button = _button('ยกเลิก')
        self.cancel_button.bind(on_release=lambda *_: self.runner.cancel())

        body.add_widget(_section('ลิงก์'))
        body.add_widget(self.url)
        body.add_widget(_section('ตั้งค่า'))
        body.add_widget(_lbl('โหมด'))
        body.add_widget(self.mode)
        body.add_widget(_lbl('รูปแบบเสียง'))
        body.add_widget(self.audio_format)
        body.add_widget(_lbl('คุณภาพวิดีโอ'))
        body.add_widget(self.quality)
        body.add_widget(_lbl('เฟรมเรต'))
        body.add_widget(self.fps)
        body.add_widget(self.bar)
        body.add_widget(self.status)
        body.add_widget(self.start_button)
        body.add_widget(self.cancel_button)

    def _tabbar(self) -> BoxLayout:
        return _tabbar('download')

    def _start(self) -> None:
        if self.runner.running:
            return
        try:
            url = ytdlp.validate_url(self.url.text)
        except ValueError as exc:
            self.status.text = str(exc)
            self.status.color = theme.color('ERROR')
            return
        destination = external_files_dir() / 'downloads'
        mode = 'video' if self.mode.text == 'วิดีโอ' else 'audio'
        job = DownloadJob(
            spec=ytdlp.ImportSpec(
                url=url,
                destination=destination,
                mode=mode,
                quality=self.quality.text,
                audio_format=self.audio_format.text,
                fps=self.fps.text,
            ),
        )
        self._last_url = url
        self._last_mode = mode
        self.start_button.disabled = True
        self.bar.value = 0
        self.status.color = theme.color('MUTED')
        self.runner.start(_run_download, job)

    def _on_event(self, kind: str, payload) -> None:
        if kind == 'progress':
            fraction, speed, eta = payload
            self.bar.value = fraction
            self.status.text = f'{fraction * 100:.0f}%  {speed}  เหลือ {eta}'
            self.status.color = theme.color('MUTED')
        elif kind == 'status':
            self.status.text = str(payload)
            self.status.color = theme.color('MUTED')
        elif kind == 'done':
            self.start_button.disabled = False
            self.bar.value = 1
            self.status.text = f'บันทึกแล้ว: {payload}'
            self.status.color = theme.color('SUCCESS')
            history.add_entry(
                kind=self._last_mode,
                source_kind='url',
                name=Path(payload).name,
                target=payload,
                source=self._last_url,
            )
        else:
            self.start_button.disabled = False
            self.bar.value = 0
            self.status.text = str(payload)
            self.status.color = theme.color('ERROR')


class HistoryScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical')
        scroll, self.body = _body()
        root.add_widget(scroll)
        root.add_widget(self._tabbar())
        self.add_widget(root)

    def _tabbar(self) -> BoxLayout:
        return _tabbar('history')

    def on_pre_enter(self, *args) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.body.clear_widgets()
        entries = history.load_history()
        if not entries:
            self.body.add_widget(_lbl('ยังไม่มีงานที่เสร็จ — ผลงานจะมาอยู่ตรงนี้'))
            return
        for entry in entries[:100]:
            self.body.add_widget(self._row(entry))
        clear = _button('ล้างประวัติ')
        clear.bind(on_release=lambda *_: (history.clear_history(), self._refresh()))
        self.body.add_widget(clear)

    @staticmethod
    def _row(entry: history.HistoryEntry) -> Label:
        kind = history.KIND_LABELS.get(entry.kind, entry.kind)
        when = time.strftime('%d/%m %H:%M', time.localtime(entry.finished_at))
        label = Label(
            text=f'{kind} • {entry.name}\n{when} → {entry.target}',
            size_hint_y=None,
            height=dp(52),
            halign='left',
            valign='middle',
            color=theme.color('TEXT'),
            font_size=dp(12),
        )
        label.bind(size=lambda widget, value: setattr(widget, 'text_size', value))
        return label


def _lbl(text: str) -> Label:
    label = Label(
        text=text,
        size_hint_y=None,
        height=dp(24),
        halign='left',
        valign='middle',
        color=theme.color('MUTED'),
        font_size=dp(12),
    )
    label.bind(size=lambda widget, value: setattr(widget, 'text_size', value))
    return label


class CliporaApp(App):
    def build(self):
        Window.clearcolor = theme.color('BG')
        manager = ScreenManager(transition=NoTransition())
        manager.add_widget(ConvertScreen(name='convert'))
        manager.add_widget(DownloadScreen(name='download'))
        manager.add_widget(HistoryScreen(name='history'))
        return manager

    def on_start(self):
        prepare_environment()
        # ponytail: no settings screen yet; log missing tools and let the first
        # job fail loudly instead of building a startup dialog.
        missing = missing_tools()
        if missing:
            print('Clipora: ไม่พบเครื่องมือ', ', '.join(missing))


if __name__ == '__main__':
    CliporaApp().run()
