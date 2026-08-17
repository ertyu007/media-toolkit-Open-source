from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def prepare_donate_qr(source: Path, destination: Path, padding: int = 24, radius: int = 28) -> Path:
    """Wrap a raw QR into a rounded white card with transparent corners.

    Raw PromptPay QRs usually fill the whole canvas with no quiet zone, so we
    add a white margin around the QR (needed for scanning) and round the outer
    corners with a transparent mask so the QR blends into the app's dark card.
    """
    qr = Image.open(source).convert('L')
    width, height = qr.size
    padded = Image.new('L', (width + 2 * padding, height + 2 * padding), 255)
    padded.paste(qr, (padding, padding))

    size = padded.size
    rgba = padded.convert('RGBA')
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)

    output = Image.new('RGBA', size, (255, 255, 255, 0))
    output.paste(rgba, (0, 0), mask)
    output.save(destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description='Prepare donate QR as a rounded card PNG')
    parser.add_argument('source', type=Path, help='raw QR image')
    parser.add_argument('destination', type=Path, help='output PNG')
    parser.add_argument('--padding', type=int, default=24, help='white margin around QR')
    parser.add_argument('--radius', type=int, default=28, help='corner radius in pixels')
    args = parser.parse_args()

    if not args.source.is_file():
        print(f'source not found: {args.source}', file=sys.stderr)
        return 1
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    output = prepare_donate_qr(args.source, args.destination, args.padding, args.radius)
    print(f'wrote {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
