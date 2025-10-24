import argparse
import struct
from PIL import Image
import sys
import os

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
                headers['EOI'] = {'value': '0xFFD9', 'description': 'End of Image'}
                break
            length = struct.unpack('>H', f.read(2))[0]
            data = f.read(length - 2)

            # Interpret common markers
            if marker_type == 0xE0:  # APP0
                headers['APP0'] = {'value': f'0xFFE0, length={length}', 'description': 'JFIF Application Segment', 'data': data}
            elif marker_type == 0xC0:  # SOF0
                precision, height, width = struct.unpack('>BHH', data[:5])
                headers['SOF0'] = {'value': f'0xFFC0, length={length}', 'description': 'Start of Frame (Baseline DCT)', 'precision': precision, 'height': height, 'width': width}
            elif marker_type == 0xC4:  # DHT
                headers['DHT'] = {'value': f'0xFFC4, length={length}', 'description': 'Define Huffman Table'}
            elif marker_type == 0xDA:  # SOS
                headers['SOS'] = {'value': f'0xFFDA, length={length}', 'description': 'Start of Scan'}
            else:
                headers[f'Marker 0xFF{marker_type:02X}'] = {'value': f'0xFF{marker_type:02X}, length={length}', 'description': 'Unknown or other marker'}

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
        row = ''.join(ascii_chars[pixel // 32] for pixel in pixels[i*new_width:(i+1)*new_width])
        ascii_image.append(row)

    return '\n'.join(ascii_image)

def main():
    parser = argparse.ArgumentParser(
        description="JPEG File Parser - Analyzes JPEG files, displays detailed header information, and renders images as ASCII art in the terminal.",
        epilog="Examples:\n  python main.py image.jpg\n  python main.py image.jpg --headers-only\n  python main.py -h"
    )
    parser.add_argument('file', help='Path to the JPEG file to parse')
    parser.add_argument('--headers-only', action='store_true', help='Display only the JPEG headers without rendering the image as ASCII art')
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)

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
            ascii_art = image_to_ascii(args.file)
            print("\nImage (ASCII representation):")
            print(ascii_art)
        except Exception as e:
            print(f"Error displaying image: {e}")

if __name__ == "__main__":
    main()