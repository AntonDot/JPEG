import argparse
import math
import struct
from PIL import Image, ImageTk
import sys
import os
import tkinter as tk
from tkinter import ttk

# Try to import matplotlib
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def parse_jpeg_headers(file_path):
    """Parse JPEG file headers and return a dictionary of markers."""
    headers = {}
    with open(file_path, 'rb') as f:
        # Check SOI
        soi = f.read(2)
        if soi != b'\xff\xd8':
            raise ValueError("Not a valid JPEG file")
        headers['SOI'] = {'value': '0xFFD8', 'description': 'Start of Image'}

        while True:
            marker = f.read(2)
            if not marker or marker[0] != 0xFF:
                break
            marker_type = marker[1]
            if marker_type == 0xD9:  # EOI
                headers['EOI'] = {'value': '0xFFD9',
                                  'description': 'End of Image'}
                break
            length = struct.unpack('>H', f.read(2))[0]
            data = f.read(length - 2)

            # Interpret common markers
            if marker_type == 0xE0:  # APP0
                headers['APP0'] = {'value': f'0xFFE0, length={length}',
                                   'description': 'JFIF Application Segment',
                                   'data': data}
            elif marker_type == 0xC0:  # SOF0
                precision, height, width = struct.unpack('>BHH', data[:5])
                headers['SOF0'] = {'value': f'0xFFC0, length={length}',
                                   'description': 'Start of Frame (Baseline DCT)',
                                   'precision': precision, 'height': height,
                                   'width': width}
            elif marker_type == 0xC4:  # DHT
                headers['DHT'] = {'value': f'0xFFC4, length={length}',
                                  'description': 'Define Huffman Table'}
            elif marker_type == 0xDA:  # SOS
                headers['SOS'] = {'value': f'0xFFDA, length={length}',
                                  'description': 'Start of Scan'}
            else:
                headers[f'Marker 0xFF{marker_type:02X}'] = {
                    'value': f'0xFF{marker_type:02X}, length={length}',
                    'description': 'Unknown or other marker'}

    return headers


def print_headers(headers):
    """Print detailed header information."""
    for marker, info in headers.items():
        print(f"\n{marker}:")
        print(f"  Value: {info['value']}")
        print(f"  Description: {info['description']}")
        if 'precision' in info:
            print(f"  Precision: {info['precision']} bits")
        if 'height' in info:
            print(f"  Height: {info['height']} pixels")
        if 'width' in info:
            print(f"  Width: {info['width']} pixels")
        if 'data' in info:
            print(f"  Data: {info['data'][:50]}...")  # Show first 50 bytes


def image_to_ascii(image_path, max_width=80, max_height=24):
    """Convert image to ASCII art."""
    img = Image.open(image_path).convert('L')  # Grayscale
    width, height = img.size

    # Scale to fit terminal
    aspect_ratio = width / height
    if width > max_width or height > max_height:
        if aspect_ratio > max_width / max_height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
    else:
        new_width, new_height = width, height

    img = img.resize((new_width, new_height))

    pixels = list(img.getdata())
    ascii_chars = ' .:-=+*#%@'  # From dark to light

    ascii_image = []
    for i in range(new_height):
        row = ''.join(ascii_chars[pixel // 32] for pixel in
                      pixels[i * new_width:(i + 1) * new_width])
        ascii_image.append(row)

    return '\n'.join(ascii_image)


def image_to_ascii_detail(image_path, max_width=80, max_height=24,
                          charset=1):
    img = Image.open(image_path).convert('L')
    width, height = img.size

    # Scaling calculation
    aspect_ratio = width / height
    scale_width = min(max_width, width)
    scale_height = min(max_height, int(scale_width / aspect_ratio))

    if scale_height > max_height:
        scale_height = max_height
        scale_width = int(scale_height * aspect_ratio)

    # High-quality resampling
    img = img.resize((scale_width, scale_height), Image.LANCZOS)

    char_sets = [
        '@%#*+=-:. ',  # Standard
        '$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,"^`\'. ',
        # Detailed
        '█▓▒░ ',  # Block characters
        ' .:-=+*#%@',  # Reversed
    ]

    ascii_chars = char_sets[min(charset, len(char_sets) - 1)]
    pixels = list(img.getdata())

    ascii_art = []
    for y in range(scale_height):
        line = ''
        for x in range(scale_width):
            pixel = pixels[y * scale_width + x]
            # Какой-то корректор гаммы, сложнааа
            gamma_corrected = math.pow(pixel / 255.0, 1.5)
            char_index = int(gamma_corrected * (len(ascii_chars) - 1))
            line += ascii_chars[max(0, min(len(ascii_chars) - 1, char_index))]
        ascii_art.append(line)

    return '\n'.join(ascii_art)


def show_histogram_ui(file_path):
    """Displays a UI with the image and its histogram."""
    if not MATPLOTLIB_AVAILABLE:
        print(
            "Error: Matplotlib is required for the histogram UI. Please install it using 'pip install matplotlib'")
        sys.exit(1)

    root = tk.Tk()
    root.title(f"Image and Histogram - {os.path.basename(file_path)}")

    # Main frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Left frame for histogram
    left_frame = ttk.Frame(main_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Right frame for image
    right_frame = ttk.Frame(main_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

    # --- Image Display ---
    try:
        img = Image.open(file_path)
        # Resize for display
        img.thumbnail((600, 600), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        image_label = ttk.Label(right_frame, image=photo)
        image_label.pack(anchor=tk.CENTER, expand=True)
        image_label.image = photo
    except Exception as e:
        ttk.Label(right_frame, text=f"Error loading image:\n{e}").pack()
        root.mainloop()
        return

    # --- Histogram Display ---
    fig = Figure(figsize=(5, 7), dpi=100)
    canvas = FigureCanvasTkAgg(fig, master=left_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)

    # Overall Histogram
    ax_overall = fig.add_subplot(4, 1, 1)
    hist_overall = img.convert('L').histogram()
    ax_overall.plot(hist_overall)
    ax_overall.set_title("Overall (Luminosity)")
    ax_overall.grid(True)

    # Channel Histograms
    if img.mode == 'RGB':
        colors = ('red', 'green', 'blue')
        channels = img.split()
        for i, (channel, color) in enumerate(zip(channels, colors)):
            ax = fig.add_subplot(4, 1, i + 2)
            ax.plot(channel.histogram(), color=color)
            ax.set_title(f"{color.capitalize()} Channel")
            ax.grid(True)

    fig.tight_layout()
    canvas.draw()

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="JPEG File Parser - Analyzes JPEG files, displays detailed header information, and renders images as ASCII art in the terminal.",
        epilog="Examples:\n  python main.py image.jpg\n  python main.py image.jpg --headers-only\n  python main.py image.jpg --histogram"
    )
    parser.add_argument('file', help='Path to the JPEG file to parse')
    parser.add_argument('--headers-only', action='store_true',
                        help='Display only the JPEG headers without rendering the image as ASCII art')
    parser.add_argument('--histogram', action='store_true',
                        help='Display a UI with the image and its histogram')
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)

    if args.histogram:
        show_histogram_ui(args.file)
    else:
        # Parse headers
        try:
            headers = parse_jpeg_headers(args.file)
            print_headers(headers)
        except Exception as e:
            print(f"Error parsing headers: {e}")
            sys.exit(1)

        if not args.headers_only:
            # Display image as ASCII
            try:
                ascii_art = image_to_ascii_detail(args.file, charset=3)
                print("\nImage (ASCII representation):")
                print(ascii_art)
            except Exception as e:
                print(f"Error displaying image: {e}")


if __name__ == "__main__":
    main()
