"""Shared formatting helpers used by the UI and dialogs."""


def format_file_size(size: int) -> str:
    value = float(max(0, size))
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == 'B':
                return f'{int(value)} {unit}'
            return f'{value:.1f} {unit}'
        value /= 1024
    return '0 B'