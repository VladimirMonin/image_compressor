"""
Рабочий поток для сжатия изображений.
"""

import os
from typing import List
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from pillow_heif import register_heif_opener

from classes import ImageCompressor
from .utils import get_savings_info


class CompressionWorker(QThread):
    """Рабочий поток для сжатия изображений без блокировки UI."""

    progress_updated = pyqtSignal(int)  # Прогресс в процентах
    file_processed = pyqtSignal(str)  # Имя обработанного файла
    log_message = pyqtSignal(str)  # Сообщение для лога
    finished_processing = pyqtSignal(int, int)  # успешных, ошибок

    def __init__(
        self,
        files: List[str],
        quality: int,
        format_type: str,
        delete_original: bool = False,
        postfix: str = "_compressed",
    ):
        super().__init__()
        # Удаляем дубликаты из списка файлов
        self.files = list(set(files))
        self.quality = quality
        self.format_type = format_type
        self.delete_original = delete_original
        self.postfix = postfix
        self.is_cancelled = False

    def run(self):
        """Основной метод обработки в отдельном потоке."""
        successful = 0
        errors = 0

        # Проверяем дубликаты еще раз и сообщаем об этом
        original_count = len(self.files)
        unique_files = list(dict.fromkeys(self.files))  # Сохраняем порядок
        total_files = len(unique_files)

        if original_count != total_files:
            duplicates_count = original_count - total_files
            self.log_message.emit(f"⚠️ Найдено и удалено дубликатов: {duplicates_count}")

        try:
            # Инициализируем HEIF для чтения входных файлов
            register_heif_opener()

            # Создаем компрессор
            compressor = ImageCompressor(
                quality=self.quality, output_format=self.format_type
            )

            for i, file_path in enumerate(unique_files):
                if self.is_cancelled:
                    break

                try:
                    # Определяем выходной путь
                    input_path = Path(file_path)
                    extension = compressor.output_formats[self.format_type]

                    # Проверяем, совпадает ли расширение входного и выходного файла
                    input_extension = input_path.suffix.lower()
                    output_extension = extension.lower()

                    if input_extension == output_extension and not self.delete_original:
                        # Добавляем постфикс при совпадении расширений
                        base_name = input_path.stem
                        output_path = (
                            input_path.parent / f"{base_name}{self.postfix}{extension}"
                        )
                    else:
                        output_path = input_path.with_suffix(extension)

                    # Отладочная информация
                    self.log_message.emit(f"🔄 Обрабатываем: {input_path}")
                    self.log_message.emit(f"📁 Выходной путь: {output_path}")

                    # Проверяем права на запись в папку
                    output_dir = output_path.parent
                    if not os.access(output_dir, os.W_OK):
                        raise PermissionError(
                            f"Нет прав на запись в папку: {output_dir}"
                        )

                    # Сжимаем изображение
                    compressor.compress_image(str(input_path), str(output_path))

                    # Проверяем, что файл действительно создался
                    if output_path.exists():
                        original_size = input_path.stat().st_size
                        compressed_size = output_path.stat().st_size
                        saved_bytes, saved_percent = get_savings_info(
                            original_size, compressed_size
                        )

                        if saved_percent > 0:
                            self.log_message.emit(
                                f"✅ {input_path.name} -> {output_path.name}"
                            )
                            self.log_message.emit(
                                f"   💾 Экономия: {saved_bytes:,} байт ({saved_percent:.1f}%)"
                            )
                        else:
                            self.log_message.emit(
                                f"✅ {input_path.name} -> {output_path.name} (размер увеличился)"
                            )

                        # Удаляем оригинальный файл, если это требуется
                        if self.delete_original and input_path != output_path:
                            try:
                                input_path.unlink()
                                self.log_message.emit(
                                    f"🗑️ Удален оригинальный файл: {input_path.name}"
                                )
                            except Exception as e:
                                self.log_message.emit(
                                    f"⚠️ Не удалось удалить оригинал {input_path.name}: {str(e)}"
                                )

                        successful += 1
                    else:
                        raise FileNotFoundError(
                            f"Выходной файл не создался: {output_path}"
                        )

                    self.file_processed.emit(input_path.name)

                except Exception as e:
                    errors += 1
                    self.log_message.emit(f"❌ Ошибка {Path(file_path).name}: {str(e)}")

                # Обновляем прогресс
                progress = int(((i + 1) / total_files) * 100)
                self.progress_updated.emit(progress)

        except Exception as e:
            self.log_message.emit(f"❌ Критическая ошибка: {str(e)}")

        self.finished_processing.emit(successful, errors)

    def cancel(self):
        """Отменяет обработку."""
        self.is_cancelled = True
