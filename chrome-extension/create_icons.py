"""Generate placeholder icons for Chrome extension."""
from PIL import Image, ImageDraw, ImageFont
import os

# Create icons directory
icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(icons_dir, exist_ok=True)

# Icon sizes required by Chrome
sizes = [16, 32, 48, 128]

for size in sizes:
    # Create image with blue background
    img = Image.new('RGB', (size, size), color='#2563eb')
    draw = ImageDraw.Draw(img)

    # Add white circle (radar theme)
    margin = size // 8
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill='white', outline='#2563eb', width=max(1, size // 16))

    # Add "JR" text for larger icons
    if size >= 32:
        try:
            # Try to use a system font
            font_size = size // 3
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        text = "JR"
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]

        draw.text((x, y), text, fill='#2563eb', font=font)

    # Save icon
    icon_path = os.path.join(icons_dir, f'icon{size}.png')
    img.save(icon_path, 'PNG')
    print(f"Created {icon_path}")

print("\nPlaceholder icons created successfully!")
print("These are temporary icons. Replace with custom design later.")
