#!/usr/bin/env python3
"""
Generate app icon for TruyenFull Downloader
Creates a modern icon with book and download theme
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a modern app icon"""
    # Create a 1024x1024 image (high resolution for various sizes)
    size = 1024
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Define colors
    primary_color = (222, 184, 135)     # Beige #DEB887
    secondary_color = (210, 180, 140)   # Tan #D2B48C
    accent_color = (139, 69, 19)        # Brown #8B4513
    white = (255, 255, 255)
    shadow = (0, 0, 0, 60)

    # Draw shadow circle (for depth)
    shadow_offset = 20
    shadow_radius = int(size * 0.42)
    draw.ellipse(
        [size//2 - shadow_radius + shadow_offset,
         size//2 - shadow_radius + shadow_offset,
         size//2 + shadow_radius + shadow_offset,
         size//2 + shadow_radius + shadow_offset],
        fill=shadow
    )

    # Draw main circle background (gradient effect with two circles)
    radius = int(size * 0.42)
    draw.ellipse(
        [size//2 - radius, size//2 - radius,
         size//2 + radius, size//2 + radius],
        fill=primary_color
    )

    # Draw book shape (centered)
    book_width = int(size * 0.35)
    book_height = int(size * 0.45)
    book_left = size//2 - book_width//2
    book_top = size//2 - book_height//2 + int(size * 0.05)

    # Book shadow
    shadow_offset_book = 8
    draw.rounded_rectangle(
        [book_left + shadow_offset_book, book_top + shadow_offset_book,
         book_left + book_width + shadow_offset_book, book_top + book_height + shadow_offset_book],
        radius=15,
        fill=(0, 0, 0, 40)
    )

    # Book background (white)
    draw.rounded_rectangle(
        [book_left, book_top, book_left + book_width, book_top + book_height],
        radius=15,
        fill=white
    )

    # Book spine (left side darker)
    spine_width = int(book_width * 0.15)
    draw.rounded_rectangle(
        [book_left, book_top, book_left + spine_width, book_top + book_height],
        radius=15,
        fill=(220, 220, 220)
    )

    # Book pages (lines)
    page_color = (200, 200, 200)
    page_start = book_left + spine_width + int(book_width * 0.1)
    page_end = book_left + book_width - int(book_width * 0.1)
    page_spacing = int(book_height * 0.12)

    for i in range(5):
        y = book_top + int(book_height * 0.25) + i * page_spacing
        if y < book_top + book_height - int(book_height * 0.15):
            draw.line(
                [(page_start, y), (page_end, y)],
                fill=page_color,
                width=3
            )

    # Download arrow (green accent)
    arrow_size = int(size * 0.15)
    arrow_x = size//2
    arrow_y = size//2 + int(size * 0.25)

    # Arrow circle background
    arrow_circle_radius = int(arrow_size * 0.7)
    draw.ellipse(
        [arrow_x - arrow_circle_radius, arrow_y - arrow_circle_radius,
         arrow_x + arrow_circle_radius, arrow_y + arrow_circle_radius],
        fill=accent_color
    )

    # Arrow shape (pointing down)
    arrow_width = int(arrow_size * 0.25)
    arrow_height = int(arrow_size * 0.5)

    # Arrow shaft
    draw.rectangle(
        [arrow_x - arrow_width//4, arrow_y - arrow_height//2,
         arrow_x + arrow_width//4, arrow_y + arrow_height//4],
        fill=white
    )

    # Arrow head (triangle)
    arrow_head = [
        (arrow_x, arrow_y + arrow_height//2),  # Bottom point
        (arrow_x - arrow_width//2, arrow_y),    # Left point
        (arrow_x + arrow_width//2, arrow_y)     # Right point
    ]
    draw.polygon(arrow_head, fill=white)

    return img

def create_macos_icns(img, output_path):
    """Create macOS .icns file"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    # Create iconset directory
    iconset_dir = output_path.replace('.icns', '.iconset')
    os.makedirs(iconset_dir, exist_ok=True)

    for size in sizes:
        # Standard resolution
        icon = img.resize((size, size), Image.LANCZOS)
        icon.save(os.path.join(iconset_dir, f'icon_{size}x{size}.png'))

        # Retina resolution (2x)
        if size <= 512:
            icon_2x = img.resize((size * 2, size * 2), Image.LANCZOS)
            icon_2x.save(os.path.join(iconset_dir, f'icon_{size}x{size}@2x.png'))

    # Convert to .icns using iconutil (macOS only)
    try:
        import subprocess
        subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', output_path], check=True)
        print(f"✅ Created macOS icon: {output_path}")

        # Clean up iconset directory
        import shutil
        shutil.rmtree(iconset_dir)
    except Exception as e:
        print(f"⚠️  Could not create .icns file: {e}")
        print(f"   PNG files are available in: {iconset_dir}")

def create_windows_ico(img, output_path):
    """Create Windows .ico file"""
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []

    for size in sizes:
        icon = img.resize(size, Image.LANCZOS)
        icons.append(icon)

    icons[0].save(output_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=icons[1:])
    print(f"✅ Created Windows icon: {output_path}")

def main():
    print("Generating TruyenFull Downloader Icon...")
    print("=" * 60)

    # Create the icon
    img = create_icon()

    # Save as PNG (universal)
    png_path = "icon.png"
    img.save(png_path, 'PNG')
    print(f"✅ Created PNG icon: {png_path}")

    # Create smaller PNG for preview
    preview = img.resize((512, 512), Image.LANCZOS)
    preview.save("icon_512.png", 'PNG')
    print(f"✅ Created preview icon: icon_512.png")

    # Create macOS .icns
    if os.uname().sysname == 'Darwin':
        create_macos_icns(img, "icon.icns")

    # Create Windows .ico
    try:
        create_windows_ico(img, "icon.ico")
    except Exception as e:
        print(f"⚠️  Could not create .ico file: {e}")

    print("\n" + "=" * 60)
    print("✅ Icon generation complete!")
    print("\nFiles created:")
    print("  • icon.png (1024x1024) - Universal")
    print("  • icon_512.png (512x512) - Preview")
    if os.path.exists("icon.icns"):
        print("  • icon.icns - macOS app icon")
    if os.path.exists("icon.ico"):
        print("  • icon.ico - Windows app icon")

if __name__ == "__main__":
    main()
