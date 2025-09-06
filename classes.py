"""
Модуль classes.py содержит класс ImageCompressor для сжатия изображений в различные форматы.

Классы:
    ImageCompressor: Класс для сжатия изображений в формат HEIF, WebP, AVIF или JPEG.

Зависимости:
    - os: Для работы с файловой системой.
    - typing: Для аннотаций типов.
    - PIL: Для обработки изображений.
    - pillow_heif: Для поддержки формата HEIF.
    - pillow_avif: Для поддержки формата AVIF (опционально).

Использование:
    from classes import ImageCompressor

    compressor = ImageCompressor(quality=80, output_format="WEBP")
    compressor.process_input("path/to/image/or/directory")

Примечание:
    Перед использованием убедитесь, что установлены все необходимые зависимости.

"""

import os
from PIL import Image
from pillow_heif import register_heif_opener

# Импорт для поддержки AVIF - самый современный формат
try:
    import pillow_avif

    AVIF_AVAILABLE = True
except ImportError:
    AVIF_AVAILABLE = False


class ImageCompressor:
    """
    Класс для сжатия изображений и сохранения их в различных форматах.

    Атрибуты:
        supported_formats (tuple): Поддерживаемые форматы входных изображений.
        output_formats (dict): Поддерживаемые форматы вывода с расширениями файлов.

    Методы:
        compress_image(input_path: str, output_path: str) -> None:
            Сжимает изображение и сохраняет его в выбранном формате.

        process_directory(directory: str) -> None:
            Обрабатывает все изображения в указанной директории и её поддиректориях.

        process_input(input_path: str) -> None:
            Обрабатывает входной путь и запускает сжатие изображений.

    Свойства:
        quality (int): Получает или устанавливает качество сжатия изображений.
        output_format (str): Получает или устанавливает формат выходных изображений.
    """

    supported_formats = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".avif")
    output_formats = {"HEIF": ".heic", "WEBP": ".webp", "AVIF": ".avif", "JPEG": ".jpg"}

    def __init__(self, quality: int = 50, output_format: str = "HEIF"):
        self.__quality = quality
        self.__output_format = output_format.upper()

        # Инициализируем HEIF для чтения и записи
        register_heif_opener()

        # Проверяем поддержку AVIF для записи
        if self.__output_format == "AVIF":
            if not AVIF_AVAILABLE:
                raise ImportError(
                    "Для поддержки AVIF установите плагин: pip install pillow-avif-plugin"
                )

    def compress_image(self, input_path: str, output_path: str) -> None:
        """
        Сжимает изображение и сохраняет его в выбранном формате.
        Args:
            input_path (str): Путь к исходному изображению.
            output_path (str): Путь для сохранения сжатого изображения.
        Returns:
            None
        """
        with Image.open(input_path) as img:
            img.save(output_path, self.__output_format, quality=self.__quality)
        print(f"Сжато: {input_path} -> {output_path} (формат: {self.__output_format})")

    def process_directory(self, directory: str) -> None:
        """
        Обрабатывает все изображения в указанной директории и её поддиректориях.
        Args:
            directory (str): Путь к директории для обработки.
        Returns:
            None
        """
        extension = self.output_formats[self.__output_format]
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(self.supported_formats):
                    input_path = os.path.join(root, file)
                    output_path = os.path.splitext(input_path)[0] + extension
                    self.compress_image(input_path, output_path)

    def process_input(self, input_path: str) -> None:
        """
        Обрабатывает входной путь и запускает сжатие изображений.
        Args:
            input_path (str): Путь к файлу или директории для обработки.
        Returns:
            None
        """
        input_path = input_path.strip('"')  # Удаляем кавычки, если они есть
        extension = self.output_formats[self.__output_format]

        if os.path.exists(input_path):
            if os.path.isfile(input_path):
                print(f"Обрабатываем файл: {input_path}")
                output_path = os.path.splitext(input_path)[0] + extension
                self.compress_image(input_path, output_path)
            elif os.path.isdir(input_path):
                print(f"Обрабатываем директорию: {input_path}")
                self.process_directory(input_path)
        else:
            print("Указанный путь не существует")

    @property
    def quality(self) -> int:
        """
        Возвращает текущее значение качества сжатия.
        Returns:
            int: Значение качества сжатия.
        """
        return self.__quality

    @quality.setter
    def quality(self, value: int) -> None:
        """
        Устанавливает новое значение качества сжатия.
        Args:
            value (int): Новое значение качества сжатия.
        Returns:
            None
        """

        if not isinstance(value, int):
            raise TypeError("Качество сжатия должно быть целым числом")

        elif value < 0 or value > 100:
            raise ValueError("Качество сжатия должно быть в диапазоне от 0 до 100")

        else:
            self.__quality = value

    @property
    def output_format(self) -> str:
        """
        Возвращает текущий формат вывода.
        Returns:
            str: Формат вывода изображений.
        """
        return self.__output_format

    @output_format.setter
    def output_format(self, value: str) -> None:
        """
        Устанавливает новый формат вывода.
        Args:
            value (str): Новый формат вывода ('HEIF', 'WEBP' или 'AVIF').
        Returns:
            None
        """
        value = value.upper()

        if value not in self.output_formats:
            raise ValueError(
                f"Неподдерживаемый формат. Поддерживаемые форматы: {', '.join(self.output_formats.keys())}"
            )

        self.__output_format = value

        # Инициализируем необходимые кодеки
        # HEIF всегда инициализируем для чтения входных файлов
        register_heif_opener()

        # Дополнительная проверка AVIF для записи
        if value == "AVIF":
            if not AVIF_AVAILABLE:
                raise ImportError(
                    "Для поддержки AVIF установите плагин: pip install pillow-avif-plugin"
                )


def main() -> None:
    """
    Основная функция программы.
    """
    print("=== Компрессор изображений ===")

    # Выбор формата вывода
    print("\nВыберите формат сжатия:")
    print("1. HEIF (.heic) - высокая эффективность сжатия")
    print("2. WebP (.webp) - хорошая совместимость и качество")
    print("3. AVIF (.avif) - новейший формат с максимальным сжатием")
    print("4. JPEG (.jpg) - универсальный стандартный формат")

    format_choice = input(
        "Введите номер формата (1-4) или нажмите Enter для HEIF по умолчанию: "
    ).strip()

    if format_choice == "2":
        output_format = "WEBP"
    elif format_choice == "3":
        output_format = "AVIF"
    elif format_choice == "4":
        output_format = "JPEG"
    else:
        output_format = "HEIF"

    print(f"Выбран формат: {output_format}")

    # Создаем компрессор с выбранным форматом
    compressor = ImageCompressor(output_format=output_format)

    # Выбор качества сжатия
    quality = input(
        f"\nВведите качество сжатия (0-100) или нажмите Enter для значения по умолчанию (50): "
    ).strip()
    if quality:
        try:
            compressor.quality = int(quality)
            print(f"Установлено качество: {compressor.quality}")
        except Exception as e:
            print(f"Некорректное значение качества сжатия: {e}")
            print("Используется значение по умолчанию (50).")

    # Ввод пути для обработки
    user_input: str = input("\nВведите путь к файлу или директории: ")

    print(f"\nНачинаем обработку с параметрами:")
    print(f"- Формат: {compressor.output_format}")
    print(f"- Качество: {compressor.quality}")
    print("=" * 50)

    compressor.process_input(user_input)

    print("=" * 50)
    input("Обработка завершена. Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
