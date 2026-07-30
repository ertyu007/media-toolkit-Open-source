from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
    build_command,
    cleanup_temporary_output,
    convert,
    finalize_output,
    output_path,
    probe,
    temporary_output_path,
    tools_available,
    validate_operation,
)


BG = '#10131a'
CARD = '#191e29'
TEXT = '#f4f6fb'
MUTED = '#99a3b6'
ACCENT = '#7c5cff'


class CliporaApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('Clipora')
        self.geometry('720x540')
        self.minsize(680, 500)
        self.configure(bg=BG)

        self.source = tk.StringVar()
        self.destination = tk.StringVar(value=str(Path.home() / 'Downloads'))
        self.mode = tk.StringVar(value='audio')
        self.audio_format = tk.StringVar(value='mp3')
        self.quality = tk.StringVar(value='Balanced')
        self.status = tk.StringVar(value='พร้อมเริ่มงาน')
        self._cancellation: CancellationToken | None = None
        self._closing = False
        self._build()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _build(self) -> None:
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=CARD)
        style.configure('TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 10))
        style.configure('Card.TLabel', background=CARD, foreground=TEXT, font=('Segoe UI', 10))
        style.configure('Muted.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI Semibold', 10), padding=9)
        style.configure('Accent.TButton', background=ACCENT, foreground='white', padding=12)
        style.map('Accent.TButton', background=[('active', '#6c4df4'), ('disabled', '#47405e')])
        style.configure('TRadiobutton', background=CARD, foreground=TEXT, font=('Segoe UI', 10))
        style.map('TRadiobutton', background=[('active', CARD)])
        style.configure('TCombobox', padding=5)
        style.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor='#282e3c')

        main = ttk.Frame(self, padding=30)
        main.pack(fill='both', expand=True)

        ttk.Label(main, text='Clipora', font=('Segoe UI Semibold', 28)).pack(anchor='w')
        ttk.Label(
            main,
            text='แปลงวิดีโอและแยกเสียงบนเครื่องของคุณ',
            style='Muted.TLabel',
        ).pack(anchor='w', pady=(0, 22))

        card = ttk.Frame(main, style='Card.TFrame', padding=20)
        card.pack(fill='x')
        ttk.Label(card, text='ไฟล์ต้นฉบับ', style='Card.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Entry(card, textvariable=self.source).grid(
            row=1,
            column=0,
            sticky='ew',
            pady=(7, 15),
            padx=(0, 10),
        )
        ttk.Button(card, text='เลือกไฟล์', command=self._choose_source).grid(
            row=1,
            column=1,
            pady=(7, 15),
        )

        ttk.Label(card, text='บันทึกที่', style='Card.TLabel').grid(row=2, column=0, sticky='w')
        ttk.Entry(card, textvariable=self.destination).grid(
            row=3,
            column=0,
            sticky='ew',
            pady=(7, 15),
            padx=(0, 10),
        )
        ttk.Button(card, text='เลือกโฟลเดอร์', command=self._choose_destination).grid(
            row=3,
            column=1,
            pady=(7, 15),
        )

        options = ttk.Frame(card, style='Card.TFrame')
        options.grid(row=4, column=0, columnspan=2, sticky='ew')
        ttk.Radiobutton(
            options,
            text='แยกเสียง',
            variable=self.mode,
            value='audio',
            command=self._sync_options,
        ).pack(side='left')
        ttk.Radiobutton(
            options,
            text='แปลงเป็น MP4',
            variable=self.mode,
            value='video',
            command=self._sync_options,
        ).pack(side='left', padx=18)
        self.format_box = ttk.Combobox(
            options,
            textvariable=self.audio_format,
            values=('mp3', 'm4a'),
            state='readonly',
            width=10,
        )
        self.format_box.pack(side='right')
        self.quality_box = ttk.Combobox(
            options,
            textvariable=self.quality,
            values=('High', 'Balanced', 'Small'),
            state='readonly',
            width=12,
        )
        card.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(main, mode='determinate', maximum=100)
        self.progress.pack(fill='x', pady=(24, 8))
        ttk.Label(main, textvariable=self.status, style='Muted.TLabel').pack(anchor='w')
        self.start_button = ttk.Button(
            main,
            text='เริ่มแปลงไฟล์',
            style='Accent.TButton',
            command=self._start,
        )
        self.start_button.pack(fill='x', pady=(18, 0))
        self._sync_options()

    def _sync_options(self) -> None:
        if self.mode.get() == 'audio':
            self.quality_box.pack_forget()
            self.format_box.pack(side='right')
        else:
            self.format_box.pack_forget()
            self.quality_box.pack(side='right')

    def _choose_source(self) -> None:
        path = filedialog.askopenfilename(
            title='เลือกวิดีโอ',
            filetypes=[
                ('Video files', '*.mp4 *.mov *.mkv *.avi *.webm *.m4v'),
                ('All files', '*.*'),
            ],
        )
        if path:
            self.source.set(path)

    def _choose_destination(self) -> None:
        path = filedialog.askdirectory(title='เลือกโฟลเดอร์บันทึก')
        if path:
            self.destination.set(path)

    def _start(self) -> None:
        if self._cancellation is not None:
            return
        job = JobSpec(
            source=Path(self.source.get()),
            destination=Path(self.destination.get()),
            mode=self.mode.get(),
            quality=self.quality.get(),
            audio_format=self.audio_format.get(),
        )
        if not job.source.is_file():
            messagebox.showwarning('ยังไม่มีไฟล์', 'กรุณาเลือกไฟล์วิดีโอก่อน')
            return
        if not job.destination.is_dir():
            messagebox.showwarning('ไม่พบโฟลเดอร์', 'กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่')
            return
        if not tools_available():
            messagebox.showerror(
                'ไม่พบ FFmpeg',
                'ติดตั้ง FFmpeg และเพิ่ม ffmpeg/ffprobe ลงใน PATH ก่อนใช้งาน',
            )
            return

        target = output_path(job.source, job.destination, job.mode, job.audio_format)
        if target.exists() and not messagebox.askyesno(
            'ไฟล์มีอยู่แล้ว',
            f'{target.name} มีอยู่แล้ว ต้องการเขียนทับหรือไม่?',
        ):
            return
        cancellation = CancellationToken()
        self._cancellation = cancellation
        self.start_button.configure(text='ยกเลิกงาน', command=self._cancel)
        self.start_button.state(['!disabled'])
        self.progress['value'] = 0
        self.status.set('กำลังตรวจสอบไฟล์…')
        threading.Thread(
            target=self._run,
            args=(job, target, cancellation),
            daemon=True,
        ).start()

    def _run(self, job: JobSpec, target: Path, cancellation: CancellationToken) -> None:
        temporary = temporary_output_path(target)
        outcome = 'done'
        detail = ''
        try:
            if cancellation.cancelled:
                raise ConversionCancelled('ยกเลิกงานแล้ว')
            info = probe(job.source)
            validate_operation(info, job.mode)
            if cancellation.cancelled:
                raise ConversionCancelled('ยกเลิกงานแล้ว')
            command = build_command(
                job.source,
                temporary,
                job.mode,
                job.quality,
                job.audio_format,
            )
            self.after(0, self.status.set, 'กำลังประมวลผล…')
            convert(
                command,
                temporary,
                info.duration,
                lambda value: self.after(0, self._set_progress, value, cancellation),
                cancellation,
            )
            finalize_output(temporary, target)
        except ConversionCancelled:
            outcome = 'cancelled'
        except (FFmpegError, OSError, ValueError) as exc:
            outcome = 'failed'
            detail = str(exc)
        finally:
            try:
                cleanup_temporary_output(temporary, target)
            except (OSError, ValueError) as exc:
                outcome = 'failed'
                detail = f'ไม่สามารถลบไฟล์ชั่วคราวได้: {exc}\n{temporary}'

        if outcome == 'done':
            self.after(0, self._done, target, cancellation)
        elif outcome == 'cancelled':
            self.after(0, self._cancelled, cancellation)
        else:
            self.after(0, self._failed, detail, cancellation)

    def _set_progress(self, value: float, cancellation: CancellationToken) -> None:
        if cancellation is not self._cancellation or cancellation.cancelled:
            return
        self.progress['value'] = value * 100
        self.status.set(f'กำลังประมวลผล… {value * 100:.0f}%')

    def _finish_job(self, cancellation: CancellationToken) -> bool:
        if cancellation is not self._cancellation:
            return False
        self._cancellation = None
        self.start_button.configure(text='เริ่มแปลงไฟล์', command=self._start)
        self.start_button.state(['!disabled'])
        if self._closing:
            self.destroy()
            return False
        return True

    def _done(self, target: Path, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.status.set(f'เสร็จแล้ว: {target.name}')
        if messagebox.askyesno(
            'สำเร็จ',
            f'บันทึกไฟล์แล้ว\n{target}\n\nเปิดโฟลเดอร์หรือไม่?',
        ):
            os.startfile(target.parent)

    def _cancelled(self, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.progress['value'] = 0
        self.status.set('ยกเลิกงานแล้ว')

    def _failed(self, detail: str, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.status.set('เกิดข้อผิดพลาด')
        messagebox.showerror('แปลงไฟล์ไม่สำเร็จ', detail[-1200:])

    def _cancel(self) -> None:
        cancellation = self._cancellation
        if cancellation is None or cancellation.cancelled:
            return
        self.start_button.state(['disabled'])
        self.status.set('กำลังยกเลิก…')
        cancellation.cancel()

    def _on_close(self) -> None:
        cancellation = self._cancellation
        if cancellation is None:
            self.destroy()
            return
        if not messagebox.askyesno(
            'กำลังประมวลผล',
            'ต้องการยกเลิกงานและปิด Clipora หรือไม่?',
        ):
            return
        self._closing = True
        self._cancel()
