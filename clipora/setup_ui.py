from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .dependencies import (
    DependencyInstallCancelled,
    DependencyInstallError,
    WINDOWS_X64_DEPENDENCIES,
    dependencies_to_install,
    install_windows_toolchain,
)


class ToolSetupDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        repair_mode: bool = False,
        on_ready: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title('เครื่องมือของ Clipora')
        self.geometry('570x445')
        self.resizable(False, False)
        self.configure(bg='#090d15')
        self.transient(parent)
        self.protocol('WM_DELETE_WINDOW', self._request_close)
        self._repair_mode = repair_mode
        self._on_ready = on_ready
        self._cancel_event = threading.Event()
        self._running = False
        self._closing = False
        self.status = tk.StringVar()
        self.detail = tk.StringVar()
        self.progress_value = tk.DoubleVar(value=0)
        self._build()
        self.grab_set()
        self.after_idle(self.install_button.focus_set)

    def _build(self) -> None:
        content = ttk.Frame(self, padding=(26, 22, 26, 20))
        content.pack(fill='both', expand=True)
        content.columnconfigure(0, weight=1)

        ttk.Label(content, text='เตรียม Clipora ให้พร้อม', style='Heading.TLabel').grid(
            row=0,
            column=0,
            sticky='w',
        )
        ttk.Label(
            content,
            text='ติดตั้งเครื่องมือประมวลผลลงในบัญชีผู้ใช้ของคุณ ไม่แก้ PATH และไม่ต้องใช้สิทธิ์ Admin',
            style='Muted.TLabel',
            wraplength=510,
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(3, 14))

        card = ttk.Frame(content, style='Card.TFrame', padding=(18, 15))
        card.grid(row=2, column=0, sticky='ew')
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text='เครื่องมือที่ใช้', style='Step.TLabel').grid(row=0, column=0, sticky='w')

        selected = dependencies_to_install(force=self._repair_mode)
        shown = selected or WINDOWS_X64_DEPENDENCIES
        lines = []
        for spec in shown:
            size_mb = spec.expected_bytes / (1024 * 1024)
            marker = 'ต้องติดตั้ง' if spec in selected else 'พร้อมใช้งาน'
            lines.append(f'{spec.display_name} {spec.version}  •  {size_mb:.0f} MB  •  {marker}')
        ttk.Label(
            card,
            text='\n'.join(lines),
            style='Card.TLabel',
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(10, 8))
        ttk.Label(
            card,
            text='ดาวน์โหลดผ่าน HTTPS จาก release ทางการและตรวจ SHA-256 ก่อนติดตั้งทุกไฟล์',
            style='CardMuted.TLabel',
            wraplength=480,
            justify='left',
        ).grid(row=2, column=0, sticky='w')

        if selected:
            total_mb = sum(spec.expected_bytes for spec in selected) / (1024 * 1024)
            self.status.set(f'ต้องดาวน์โหลดประมาณ {total_mb:.0f} MB')
            install_text = 'ติดตั้งเครื่องมือที่จำเป็น'
            close_text = 'ไว้ทีหลัง'
        else:
            self.status.set('เครื่องมือพร้อมใช้งานแล้ว')
            install_text = 'ติดตั้งใหม่ / ซ่อมเครื่องมือ'
            close_text = 'ปิด'
        self.detail.set('การดาวน์โหลดเกิดขึ้นครั้งแรกหรือเมื่อคุณเลือกซ่อมเท่านั้น')

        ttk.Label(content, textvariable=self.status, style='Section.TLabel').grid(
            row=3,
            column=0,
            sticky='w',
            pady=(16, 3),
        )
        ttk.Label(content, textvariable=self.detail, style='Muted.TLabel').grid(
            row=4,
            column=0,
            sticky='w',
        )
        self.progress = ttk.Progressbar(
            content,
            variable=self.progress_value,
            maximum=100,
            style='Clipora.Horizontal.TProgressbar',
        )
        self.progress.grid(row=5, column=0, sticky='ew', pady=(10, 14))

        actions = ttk.Frame(content)
        actions.grid(row=6, column=0, sticky='ew')
        actions.columnconfigure(0, weight=1)
        self.close_button = ttk.Button(
            actions,
            text=close_text,
            style='Secondary.TButton',
            command=self._request_close,
        )
        self.close_button.grid(row=0, column=0, sticky='w')
        self.install_button = ttk.Button(
            actions,
            text=install_text,
            style='Accent.TButton',
            command=self._start_install,
        )
        self.install_button.grid(row=0, column=1, sticky='e')

    def _start_install(self) -> None:
        if self._running:
            return
        force = self._repair_mode or not dependencies_to_install()
        self._running = True
        self._cancel_event.clear()
        self.progress_value.set(0)
        self.status.set('กำลังเตรียมดาวน์โหลด…')
        self.detail.set('อย่าปิดเครื่องระหว่างติดตั้งเครื่องมือ')
        self.install_button.state(['disabled'])
        self.close_button.configure(text='ยกเลิก')
        threading.Thread(target=self._install_worker, args=(force,), daemon=True).start()

    def _install_worker(self, force: bool) -> None:
        try:
            install_windows_toolchain(
                on_progress=self._report_from_worker,
                cancel_event=self._cancel_event,
                force=force,
            )
        except DependencyInstallCancelled:
            self.after(0, self._cancelled)
        except Exception as exc:
            self.after(0, self._failed, str(exc))
        else:
            self.after(0, self._completed)

    def _report_from_worker(self, fraction: float, message: str) -> None:
        try:
            self.after(0, self._update_progress, fraction, message)
        except tk.TclError:
            pass

    def _update_progress(self, fraction: float, message: str) -> None:
        self.progress_value.set(max(0, min(fraction * 100, 100)))
        self.status.set(message)
        self.detail.set(f'{self.progress_value.get():.0f}%')

    def _completed(self) -> None:
        self._running = False
        self.progress_value.set(100)
        self.status.set('Clipora พร้อมใช้งานแล้ว')
        self.detail.set('ติดตั้งและตรวจสอบเครื่องมือเรียบร้อย')
        self.install_button.configure(text='เสร็จสิ้น', command=self.destroy)
        self.install_button.state(['!disabled'])
        self.close_button.grid_remove()
        if self._on_ready is not None:
            self._on_ready()

    def _cancelled(self) -> None:
        self._running = False
        self.status.set('ยกเลิกการติดตั้งแล้ว')
        self.detail.set('สามารถกลับมาติดตั้งได้จากเมนูเครื่องมือ')
        self.install_button.configure(text='ลองอีกครั้ง', command=self._start_install)
        self.install_button.state(['!disabled'])
        self.close_button.configure(text='ปิด')
        if self._closing:
            self.destroy()

    def _failed(self, detail: str) -> None:
        self._running = False
        self.status.set('ติดตั้งเครื่องมือไม่สำเร็จ')
        self.detail.set('ตรวจอินเทอร์เน็ตแล้วลองอีกครั้ง')
        self.install_button.configure(text='ลองอีกครั้ง', command=self._start_install)
        self.install_button.state(['!disabled'])
        self.close_button.configure(text='ปิด')
        messagebox.showerror('ติดตั้งไม่สำเร็จ', detail, parent=self)

    def _request_close(self) -> None:
        if not self._running:
            self.destroy()
            return
        if not messagebox.askyesno(
            'ยกเลิกการติดตั้ง?',
            'ต้องการหยุดดาวน์โหลดและติดตั้งเครื่องมือหรือไม่?',
            parent=self,
        ):
            return
        self._closing = True
        self._cancel_event.set()
        self.status.set('กำลังยกเลิก…')
        self.close_button.state(['disabled'])
