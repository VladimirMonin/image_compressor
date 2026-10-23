"""Compatible Python facade. All rules and effects belong to image_compressor."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from image_compressor import BatchResult, ConversionRequest, ErrorCode, convert
from image_compressor.models import (
    INPUT_EXTENSIONS,
    OUTPUT_EXTENSIONS,
    ValidationError,
    validate_dimensions,
    validate_format,
    validate_quality,
)

_T = TypeVar("_T")


def _validated(call: Callable[[], _T]) -> _T:
    try:
        return call()
    except ValidationError as exc:
        exception = TypeError if exc.type_error else ValueError
        raise exception(exc.info.message) from None


class CompressionError(Exception):
    def __init__(self, result: BatchResult):
        self.result = result
        infos = [
            *result.errors,
            *(item.error for item in result.items if item.error),
            *(warning for item in result.items for warning in item.warnings),
            *result.warnings,
        ]
        self.code = infos[0].code if infos else ErrorCode.INTERNAL_ERROR
        super().__init__(f"Compression did not fully succeed: {self.code.value}.")


class ImageCompressor:
    supported_formats = INPUT_EXTENSIONS
    output_formats = {fmt.value: extension for fmt, extension in OUTPUT_EXTENSIONS.items()}

    def __init__(
        self,
        quality: int = 50,
        output_format: str = "HEIF",
        max_width: int | None = None,
        max_height: int | None = None,
    ):
        self.quality = quality
        self.output_format = output_format
        self.__max_width, self.__max_height = _validated(
            lambda: validate_dimensions(max_width, max_height)
        )
        self.last_result: BatchResult | None = None

    @property
    def quality(self) -> int:
        return self.__quality

    @quality.setter
    def quality(self, value: int) -> None:
        self.__quality = _validated(lambda: validate_quality(value))

    @property
    def output_format(self) -> str:
        return self.__output_format

    @output_format.setter
    def output_format(self, value: str) -> None:
        self.__output_format = _validated(lambda: validate_format(value)).value

    def _execute(
        self, source: str, *, destination: str | None = None, recursive: bool = True
    ) -> None:
        self.last_result = convert(
            ConversionRequest(
                (source,),
                output_format=self.output_format,
                quality=self.quality,
                max_width=self.__max_width,
                max_height=self.__max_height,
                recursive=recursive,
                output_path=destination,
            )
        )
        if self.last_result.status != "succeeded":
            raise CompressionError(self.last_result)

    def compress_image(self, input_path: str, output_path: str) -> None:
        self._execute(input_path, destination=output_path, recursive=False)

    def process_directory(self, directory: str) -> None:
        self._execute(directory, recursive=True)

    def process_input(self, input_path: str) -> None:
        self._execute(input_path.strip('"'), recursive=True)


def main() -> int:
    from image_compressor.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
