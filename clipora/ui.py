from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .ffmpeg import (
    FFmpegError,
    JobSpec,
    build_command,
    convert,
    output_path,
    probe,
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
        self._build()

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
        self.start_button.state(['disabled'])
        self.progress['value'] = 0
        self.status.set('กำลังตรวจสอบไฟล์…')
        threading.Thread(target=self._run, args=(job, target), daemon=True).start()

    def _run(self, job: JobSpec, target: Path) -> None:
        try:
            info = probe(job.source)
            validate_operation(info, job.mode)
            command = build_command(
                job.source,
                target,
                job.mode,
                job.quality,
                job.audio_format,
            )
            self.after(0, self.status.set, 'กำลังประมวลผล…')
            convert(
                command,
                target,
                info.duration,
                lambda value: self.after(0, self._set_progress, value),
            )
            self.after(0, self._done, target)
        except (FFmpegError, OSError, ValueError) as exc:
            self.after(0, self._failed, str(exc))

    def _set_progress(self, value: float) -> None:
        self.progress['value'] = value * 100
        self.status.set(f'กำลังประมวลผล… {value * 100:.0f}%')

    def _done(self, target: Path) -> None:
        self.start_button.state(['!disabled'])
        self.status.set(f'เสร็จแล้ว: {target.name}')
        if messagebox.askyesno(
            'สำเร็จ',
            f'บันทึกไฟล์แล้ว\n{target}\n\nเปิดโฟลเดอร์หรือไม่?',
        ):
            os.startfile(target.parent)

    def _failed(self, detail: str) -> None:
        self.start_button.state(['!disabled'])
        self.status.set('เกิดข้อผิดพลาด')
        messagebox.showerror('แปลงไฟล์ไม่สำเร็จ', detail[-1200:])
