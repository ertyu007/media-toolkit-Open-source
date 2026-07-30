from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output = project_root / 'assets' / 'clipora.ico'
    output.parent.mkdir(parents=True, exist_ok=True)

    size = 256
    image = Image.new('RGBA', (size, size), (9, 13, 21, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((26, 26, 230, 230), radius=52, fill=(124, 92, 255, 255))
    draw.polygon(((105, 78), (105, 178), (181, 128)), fill=(247, 248, 252, 255))
    image.save(
        output,
        format='ICO',
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(output)


if __name__ == '__main__':
    main()
