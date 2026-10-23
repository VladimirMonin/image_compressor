import logging
from pathlib import Path

from PIL import Image

from image_compressor import ConversionRequest, convert, diagnostics, get_capabilities

from .test_cli import response, run_cli


def test_real_file_handler_useful_output_and_no_private_data(image_factory, tmp_path, monkeypatch):
    source = image_factory("PRIVATE_PATH_SENTINEL/source_PRIVATE_FILENAME_SENTINEL.png")
    get_capabilities()
    path = tmp_path / "diagnostics.log"
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger = diagnostics.LOGGER
    old_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        success = convert(ConversionRequest([source], postfix="PRIVATE_POSTFIX_SENTINEL"))
        assert success.status == "succeeded"

        def broken_save(self, fp, *args, **kwargs):
            Path(fp).write_bytes(b"STAGING_BYTES")
            raise OSError("PRIVATE_EXCEPTION_SENTINEL")

        monkeypatch.setattr(Image.Image, "save", broken_save)
        failure = convert(ConversionRequest([source], output_format="JPEG"))
        assert failure.items[0].error.code == "ENCODE_FAILED"
        handler.flush()
        data = path.read_bytes()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        handler.close()
    assert b"event=conversion_started" in data and b"event=conversion_finished" in data
    assert b"reason=ENCODE_FAILED" in data and b"succeeded=1" in data and b"published=0" in data
    assert b"duration_ms=" in data and b"index=0" in data
    assert b"PRIVATE_" not in data and b"Traceback" not in data
    assert "PRIVATE_" not in failure.items[0].error.message


def test_cli_stderr_separate_from_local_result_paths(image_factory):
    source = image_factory("PRIVATE_PATH_SENTINEL/PRIVATE_FILENAME_SENTINEL.png")
    process = run_cli("convert", source, "--postfix", "PRIVATE_POSTFIX_SENTINEL", "--progress")
    payload = response(process, 0)
    assert "PRIVATE_PATH_SENTINEL" in payload["result"]["items"][0]["source"]
    assert b"PRIVATE_" not in process.stderr
    assert b"event=conversion_started" in process.stderr
    assert b"event=conversion_finished" in process.stderr and b"published=1" in process.stderr


def test_handler_formatter_and_observer_failures_do_not_retry_or_leak(
    image_factory, tmp_path, capsys
):
    source = image_factory()
    path = tmp_path / "broken-formatter.log"

    class BrokenFormatter(logging.Formatter):
        def format(self, record):
            raise RuntimeError("PRIVATE_FORMATTER_SENTINEL")

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(BrokenFormatter())
    logger = diagnostics.LOGGER
    old_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    calls = 0

    def observer(event):
        nonlocal calls
        calls += 1
        raise ValueError("PRIVATE_OBSERVER_SENTINEL")

    try:
        result = convert(ConversionRequest([source]), on_progress=observer)
        handler.flush()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        handler.close()
    assert result.status == "succeeded" and result.counts.published == 1 and calls == 1
    assert result.warnings[0].code == "OBSERVER_FAILED"
    assert len(list(source.parent.glob("*.webp"))) == 1
    assert "PRIVATE_" not in capsys.readouterr().err
    assert path.read_bytes() == b""  # Failure test only; useful output is proven above.


def test_raw_codec_warning_not_forwarded(image_factory, monkeypatch, capsys):
    import warnings

    source = image_factory()
    get_capabilities()
    original = Image.Image.save

    def noisy_save(*args, **kwargs):
        warnings.warn("PRIVATE_WARNING_SENTINEL", UserWarning, stacklevel=1)
        return original(*args, **kwargs)

    monkeypatch.setattr(Image.Image, "save", noisy_save)
    with warnings.catch_warnings(record=True) as leaked:
        warnings.simplefilter("always")
        result = convert(ConversionRequest([source]))
    assert result.status == "succeeded" and leaked == []
    assert "PRIVATE_WARNING_SENTINEL" not in capsys.readouterr().err
