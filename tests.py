# test_jpeg_parser.py
import pytest
import os
import tempfile
from PIL import Image
import struct
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import parse_jpeg_headers, image_to_ascii, image_to_ascii_detail, \
    print_headers


class TestJPEGParser:
    """Тесты для парсера JPEG заголовков"""

    @pytest.fixture
    def sample_jpeg(self):
        """Создает временный JPEG файл для тестирования"""
        fd, path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(path, 'JPEG',
                     quality=95)  # Увеличиваем качество
            yield path
        finally:
            try:
                os.unlink(path)
            except:
                pass

    @pytest.fixture
    def invalid_jpeg(self):
        """Создает невалидный JPEG файл"""
        fd, path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            with open(path, 'wb') as f:
                f.write(b'INVALID_JPEG_DATA')
            yield path
        finally:
            try:
                os.unlink(path)
            except:
                pass

    @pytest.fixture
    def sample_image(self):
        """Создает временное изображение для тестов ASCII"""
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        try:
            img = Image.new('RGB', (10, 10), color='blue')
            img.save(path, 'PNG')
            yield path
        finally:
            try:
                os.unlink(path)
            except:
                pass

    def test_parse_jpeg_headers_valid_file(self, sample_jpeg):
        """Тест парсинга валидного JPEG файла"""
        headers = parse_jpeg_headers(sample_jpeg)

        assert 'SOI' in headers
        assert headers['SOI']['value'] == '0xFFD8'
        assert headers['SOI']['description'] == 'Start of Image'

        for marker, info in headers.items():
            assert 'value' in info
            assert 'description' in info

    def test_parse_jpeg_headers_invalid_file(self, invalid_jpeg):
        """Тест парсинга невалидного JPEG файла"""
        with pytest.raises(ValueError, match="Not a valid JPEG file"):
            parse_jpeg_headers(invalid_jpeg)

    def test_parse_jpeg_headers_nonexistent_file(self):
        """Тест парсинга несуществующего файла"""
        with pytest.raises(FileNotFoundError):
            parse_jpeg_headers('nonexistent_file.jpg')

    def test_print_headers(self, sample_jpeg, capsys):
        """Тест вывода заголовков"""
        headers = parse_jpeg_headers(sample_jpeg)
        print_headers(headers)

        captured = capsys.readouterr()
        output = captured.out

        # ключевая инфа
        assert 'SOI' in output
        assert '0xFFD8' in output
        assert 'Start of Image' in output

    def test_image_to_ascii_basic(self, sample_image):
        """Тупой тест базового преобразования в ASCII"""
        ascii_result = image_to_ascii(sample_image, max_width=20,
                                      max_height=10)

        assert ascii_result is not None
        assert isinstance(ascii_result, str)
        assert len(ascii_result) > 0

        lines = ascii_result.split('\n')
        assert len(lines) <= 10

    def test_image_to_ascii_detail_different_charsets(self, sample_image):
        """Тупой тест детального преобразования с разными наборами символов"""
        for charset in [0, 1, 2, 3]:
            ascii_result = image_to_ascii_detail(
                sample_image,
                max_width=20,
                max_height=10,
                charset=charset
            )

            assert ascii_result is not None
            assert isinstance(ascii_result, str)
            assert len(ascii_result) > 0

    def test_image_to_ascii_detail_invalid_charset(self, sample_image):
        """Тест с невалидным набором символов"""
        ascii_result = image_to_ascii_detail(
            sample_image,
            max_width=20,
            max_height=10,
            charset=999
        )

        assert ascii_result is not None
        assert isinstance(ascii_result, str)

    def test_image_to_ascii_small_dimensions(self, sample_image):
        """Тест с очень маленькими размерами"""
        ascii_result = image_to_ascii_detail(
            sample_image,
            max_width=5,
            max_height=3
        )

        assert ascii_result is not None
        lines = ascii_result.split('\n')
        assert len(lines) <= 3

    def test_image_to_ascii_large_dimensions(self, sample_image):
        """Тест с большими размерами"""
        ascii_result = image_to_ascii_detail(
            sample_image,
            max_width=100,
            max_height=50
        )

        assert ascii_result is not None
        lines = ascii_result.split('\n')
        assert len(lines) <= 50

    def test_image_to_ascii_nonexistent_file(self):
        """Тест преобразования несуществующего файла"""
        with pytest.raises(FileNotFoundError):
            image_to_ascii('nonexistent_image.jpg')

    def test_soi_marker_structure(self, sample_jpeg):
        """Тест структуры SOI маркера"""
        headers = parse_jpeg_headers(sample_jpeg)
        soi_info = headers['SOI']

        assert soi_info['value'] == '0xFFD8'
        assert soi_info['description'] == 'Start of Image'

    def test_jpeg_with_sof0_marker(self, sample_jpeg):
        """Тест SOF0 маркер присутствует и содержит правильные данные"""
        headers = parse_jpeg_headers(sample_jpeg)

        if 'SOF0' in headers:
            sof0_info = headers['SOF0']
            assert 'width' in sof0_info
            assert 'height' in sof0_info
            assert 'precision' in sof0_info
            assert sof0_info['width'] == 100
            assert sof0_info['height'] == 100


class TestJPEGParserEdgeCases:
    """Тесты граничных случаев"""

    def test_empty_file(self):
        """Тест с пустым файлом"""
        fd, path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            with open(path, 'wb') as f:
                f.write(b'')  # Пустой файл

            with pytest.raises((ValueError, struct.error)):
                parse_jpeg_headers(path)
        finally:
            try:
                os.unlink(path)
            except:
                pass

    def test_very_small_image(self):
        """Тест с очень маленьким изображением"""
        fd, path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            img = Image.new('RGB', (1, 1), color='white')
            img.save(path, 'JPEG')

            headers = parse_jpeg_headers(path)
            assert 'SOI' in headers

            ascii_result = image_to_ascii(path, max_width=10, max_height=10)
            assert ascii_result is not None
            assert len(ascii_result) > 0
        finally:
            try:
                os.unlink(path)
            except:
                pass

    def test_grayscale_image(self):
        """Тест с черно-белым изображением"""
        fd, path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            img = Image.new('L', (50, 50), color=128)
            img.save(path, 'JPEG')

            headers = parse_jpeg_headers(path)
            assert 'SOI' in headers

            ascii_result = image_to_ascii_detail(path)
            assert ascii_result is not None
        finally:
            try:
                os.unlink(path)
            except:
                pass


def test_image_processing_errors():
    """Тест ошибки при другом изображении"""

    # Не то изображение
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    try:
        with open(path, 'w') as f:
            f.write('This is not an image file')

        with pytest.raises(Exception):
            image_to_ascii(path)
    finally:
        try:
            os.unlink(path)
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
