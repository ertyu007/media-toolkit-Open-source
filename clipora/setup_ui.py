from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .dependencies import (
    DependencyInstallCancelled,
    DependencySpec,
    WINDOWS_X64_DEPENDENCIES,
    dependencies_to_install,
    install_windows_toolchain,
)


WIZARD_STEPS = ('ยินดีต้อนรับ', 'ข้อตกลง', 'ตรวจสอบ', 'ติดตั้ง', 'เสร็จสิ้น')


def dependency_rows(specs: tuple[DependencySpec, ...]) -> tuple[str, ...]:
    return tuple(
        f'{spec.display_name} {spec.version}  •  {spec.expected_bytes / (1024 * 1024):.0f} MB'
        for spec in specs
    )


def total_download_mb(specs: tuple[DependencySpec, ...]) -> int:
    return round(sum(spec.expected_bytes for spec in specs) / (1024 * 1024))


class ToolSetupDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        repair_mode: bool = False,
        first_run: bool = False,
        on_ready: Callable[[], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title('ติดตั้งเครื่องมือสำหรับ Clipora')
        self.geometry('680x550')
        self.minsize(620, 520)
        self.resizable(True, True)
        self.configure(bg='#090d15')
        self.transient(parent)
        self.protocol('WM_DELETE_WINDOW', self._request_close)

        self._repair_mode = repair_mode
        self._first_run = first_run
        self._on_ready = on_ready
        self._on_cancelled = on_cancelled
        self._selected = (
            WINDOWS_X64_DEPENDENCIES
            if repair_mode
            else dependencies_to_install(force=False)
        )
        self._step = 0
        self._running = False
        self._closing = False
        self._cancel_event = threading.Event()

        self.accepted = tk.BooleanVar(value=False)
        self.status = tk.StringVar()
        self.detail = tk.StringVar()
        self.progress_value = tk.DoubleVar(value=0)
        self.step_text = tk.StringVar()

        self._build_shell()
        self._show_step(0)
        self.grab_set()
        self.after_idle(self.next_button.focus_set)

    def _build_shell(self) -> None:
        shell = ttk.Frame(self, padding=(30, 24, 30, 22))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        title = 'ซ่อมเครื่องมือ Clipora' if self._repair_mode else 'ตั้งค่า Clipora ครั้งแรก'
        ttk.Label(shell, text=title, style='Heading.TLabel').grid(
            row=0,
            column=0,
            sticky='w',
        )
        ttk.Label(shell, textvariable=self.step_text, style='Muted.TLabel').grid(
            row=1,
            column=0,
            sticky='w',
            pady=(2, 18),
        )

        self.page = ttk.Frame(shell)
        self.page.grid(row=2, column=0, sticky='nsew')
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(0, weight=1)

        separator = ttk.Separator(shell)
        separator.grid(row=3, column=0, sticky='ew', pady=(18, 16))

        actions = ttk.Frame(shell)
        actions.grid(row=4, column=0, sticky='ew')
        actions.columnconfigure(1, weight=1)
        self.cancel_button = ttk.Button(
            actions,
            text='ยกเลิก',
            style='Secondary.TButton',
            command=self._request_close,
        )
        self.cancel_button.grid(row=0, column=0, sticky='w')
        self.back_button = ttk.Button(
            actions,
            text='ย้อนกลับ',
            style='Secondary.TButton',
            command=self._go_back,
        )
        self.back_button.grid(row=0, column=2, padx=(8, 8))
        self.next_button = ttk.Button(
            actions,
            text='ถัดไป',
            style='Accent.TButton',
            command=self._go_next,
        )
        self.next_button.grid(row=0, column=3, sticky='e')

    def _clear_page(self) -> None:
        for child in self.page.winfo_children():
            child.destroy()

    def _show_step(self, step: int) -> None:
        self._step = max(0, min(step, len(WIZARD_STEPS) - 1))
        self.step_text.set(
            f'ขั้นตอน {self._step + 1} จาก {len(WIZARD_STEPS)}  •  '
            f'{WIZARD_STEPS[self._step]}'
        )
        self._clear_page()
        self.back_button.state(['!disabled'] if self._step in (1, 2) else ['disabled'])
        self.cancel_button.state(['!disabled'])
        self.cancel_button.configure(text='ยกเลิก')
        self.next_button.state(['!disabled'])
        self.next_button.configure(text='ถัดไป', command=self._go_next)

        builders = (
            self._build_welcome,
            self._build_consent,
            self._build_review,
            self._build_install,
            self._build_complete,
        )
        builders[self._step]()

    def _page_card(self) -> ttk.Frame:
        card = ttk.Frame(self.page, style='Card.TFrame', padding=(24, 22))
        card.grid(row=0, column=0, sticky='nsew')
        card.columnconfigure(0, weight=1)
        return card

    def _build_welcome(self) -> None:
        card = self._page_card()
        heading = (
            'ตรวจสอบและติดตั้งเครื่องมือใหม่'
            if self._repair_mode
            else 'ยินดีต้อนรับสู่ Clipora'
        )
        ttk.Label(card, text=heading, style='Section.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(
            card,
            text=(
                'ตัวช่วยนี้จะเตรียม FFmpeg, yt-dlp และ Deno สำหรับดาวน์โหลด '
                'แยกเสียง และแปลงวิดีโอบนเครื่องของคุณ'
            ),
            style='Card.TLabel',
            wraplength=570,
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(14, 12))
        ttk.Label(
            card,
            text=(
                '• ติดตั้งเฉพาะบัญชีผู้ใช้ปัจจุบัน\n'
                '• ไม่ต้องใช้สิทธิ์ Administrator และไม่แก้ PATH\n'
                '• ไม่มีโฆษณา บัญชี หรือการอัปโหลดไฟล์ในเครื่อง\n'
                '• ดาวน์โหลดเฉพาะเมื่อคุณกดยืนยัน'
            ),
            style='CardMuted.TLabel',
            justify='left',
        ).grid(row=2, column=0, sticky='w')

    def _build_consent(self) -> None:
        card = self._page_card()
        ttk.Label(card, text='ข้อตกลงก่อนติดตั้ง', style='Section.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(
            card,
            text=(
                'Clipora จะเชื่อมต่ออินเทอร์เน็ตเพื่อดาวน์โหลดเครื่องมือจาก '
                'release ทางการผ่าน HTTPS จากนั้นตรวจ SHA-256 ก่อนติดตั้ง '
                'เครื่องมือเหล่านี้มี license ของผู้พัฒนาแต่ละราย\n\n'
                'ใช้ Clipora กับสื่อที่คุณเป็นเจ้าของ ได้รับอนุญาต '
                'หรือมีสิทธิ์ใช้งานเท่านั้น โปรแกรมไม่รองรับ DRM, '
                'สื่อ private/paid, cookies หรือการข้ามระบบควบคุมการเข้าถึง'
            ),
            style='Card.TLabel',
            wraplength=570,
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(14, 18))
        consent = tk.Checkbutton(
            card,
            text='ฉันเข้าใจและยินยอมให้ดาวน์โหลดและติดตั้งเครื่องมือที่ระบุ',
            variable=self.accepted,
            command=self._sync_consent,
            bg='#141a26',
            fg='#f7f8fc',
            activebackground='#141a26',
            activeforeground='#f7f8fc',
            selectcolor='#0d1320',
            font=('Segoe UI', 10),
            anchor='w',
        )
        consent.grid(row=2, column=0, sticky='w')
        self._sync_consent()

    def _sync_consent(self) -> None:
        if self.accepted.get():
            self.next_button.state(['!disabled'])
        else:
            self.next_button.state(['disabled'])

    def _build_review(self) -> None:
        card = self._page_card()
        ttk.Label(card, text='พร้อมติดตั้ง', style='Section.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        rows = dependency_rows(self._selected)
        ttk.Label(
            card,
            text='\n'.join(f'✓  {row}' for row in rows),
            style='Card.TLabel',
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(14, 14))
        ttk.Label(
            card,
            text=(
                f'ดาวน์โหลดประมาณ {total_download_mb(self._selected)} MB\n'
                'ตำแหน่งติดตั้ง: %LOCALAPPDATA%\\Clipora\\tools\n'
                'ไฟล์เดิมที่ใช้งานได้จะไม่ถูกลบหากดาวน์โหลดล้มเหลวหรือยกเลิก'
            ),
            style='CardMuted.TLabel',
            wraplength=570,
            justify='left',
        ).grid(row=2, column=0, sticky='w')
        self.next_button.configure(text='ติดตั้ง')

    def _build_install(self) -> None:
        card = self._page_card()
        ttk.Label(card, text='กำลังติดตั้งเครื่องมือ', style='Section.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(card, textvariable=self.status, style='Card.TLabel').grid(
            row=1, column=0, sticky='w', pady=(18, 4)
        )
        ttk.Label(card, textvariable=self.detail, style='CardMuted.TLabel').grid(
            row=2, column=0, sticky='w'
        )
        ttk.Progressbar(
            card,
            variable=self.progress_value,
            maximum=100,
            style='Clipora.Horizontal.TProgressbar',
        ).grid(row=3, column=0, sticky='ew', pady=(18, 10))
        ttk.Label(
            card,
            text='ปิด Clipora ได้หลังจากยกเลิกเสร็จ เพื่อป้องกันไฟล์ติดตั้งไม่สมบูรณ์',
            style='CardMuted.TLabel',
            wraplength=570,
        ).grid(row=4, column=0, sticky='w')
        self.back_button.state(['disabled'])
        self.next_button.state(['disabled'])
        if not self._running:
            self._start_install()

    def _build_complete(self) -> None:
        card = self._page_card()
        ttk.Label(card, text='Clipora พร้อมใช้งานแล้ว', style='Section.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(
            card,
            text=(
                'ติดตั้งและตรวจสอบเครื่องมือเรียบร้อยแล้ว\n\n'
                'กด “เสร็จสิ้น” เพื่อเปิด Clipora และเริ่มวางลิงก์ '
                'หรือเลือกไฟล์ในเครื่องได้ทันที'
            ),
            style='Card.TLabel',
            wraplength=570,
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(16, 0))
        self.cancel_button.grid_remove()
        self.back_button.state(['disabled'])
        self.next_button.configure(text='เสร็จสิ้น', command=self._finish)
        self.next_button.state(['!disabled'])

    def _go_next(self) -> None:
        if self._step == 1 and not self.accepted.get():
            return
        if self._step == 2:
            self._show_step(3)
            return
        self._show_step(self._step + 1)

    def _go_back(self) -> None:
        if self._step in (1, 2):
            self._show_step(self._step - 1)

    def _start_install(self) -> None:
        if self._running:
            return
        self._running = True
        self._closing = False
        self._cancel_event.clear()
        self.progress_value.set(0)
        self.status.set('กำลังเตรียมดาวน์โหลด…')
        self.detail.set('0%  •  กรุณาเปิด Clipora ไว้จนกว่าจะเสร็จ')
        self.cancel_button.configure(text='ยกเลิกการติดตั้ง')
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self) -> None:
        try:
            install_windows_toolchain(
                on_progress=self._report_from_worker,
                cancel_event=self._cancel_event,
                force=self._repair_mode,
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
        value = max(0, min(fraction * 100, 100))
        self.progress_value.set(value)
        self.status.set(message)
        self.detail.set(f'{value:.0f}%  •  ดาวน์โหลด ตรวจสอบ และติดตั้งบนเครื่องนี้')

    def _completed(self) -> None:
        self._running = False
        self.progress_value.set(100)
        self._show_step(4)

    def _cancelled(self) -> None:
        self._running = False
        if self._closing:
            self._close_without_setup()
            return
        self.status.set('ยกเลิกการติดตั้งแล้ว')
        self.detail.set('ไฟล์เดิมยังอยู่ครบ กด “ลองอีกครั้ง” เมื่อพร้อม')
        self.cancel_button.configure(text='ปิด')
        self.next_button.configure(text='ลองอีกครั้ง', command=self._retry_install)
        self.next_button.state(['!disabled'])

    def _failed(self, detail: str) -> None:
        self._running = False
        self.status.set('ติดตั้งเครื่องมือไม่สำเร็จ')
        self.detail.set(detail)
        self.cancel_button.configure(text='ปิด')
        self.next_button.configure(text='ลองอีกครั้ง', command=self._retry_install)
        self.next_button.state(['!disabled'])

    def _retry_install(self) -> None:
        self._clear_page()
        self._build_install()

    def _finish(self) -> None:
        self.grab_release()
        self.destroy()
        if self._on_ready is not None:
            self._on_ready()

    def _close_without_setup(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        if self._on_cancelled is not None:
            self._on_cancelled()

    def _request_close(self) -> None:
        if not self._running:
            if self._first_run and not messagebox.askyesno(
                'ออกจากการตั้งค่า Clipora?',
                'ยังติดตั้งเครื่องมือไม่ครบ หากออกตอนนี้ Clipora จะปิดและถามใหม่เมื่อเปิดครั้งถัดไป',
                parent=self,
            ):
                return
            self._close_without_setup()
            return
        if not messagebox.askyesno(
            'ยกเลิกการติดตั้ง?',
            'ต้องการหยุดดาวน์โหลดและออกจากตัวช่วยติดตั้งหรือไม่?',
            parent=self,
        ):
            return
        self._closing = True
        self._cancel_event.set()
        self.status.set('กำลังยกเลิกอย่างปลอดภัย…')
        self.detail.set('รอให้ Clipora ปิดไฟล์ชั่วคราว')
        self.cancel_button.state(['disabled'])
