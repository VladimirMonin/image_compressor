from image_compressor import CancellationToken, ConversionRequest, convert, imaging
from image_compressor import filesystem as fs

from .conftest import assert_image


def test_cancel_before_start_and_next_operation(image_factory):
    source = image_factory()
    token = CancellationToken()
    token.cancel()
    result = convert(ConversionRequest([source]), cancellation=token)
    assert result.status == "cancelled" and not result.discovery_complete
    assert result.counts.published == result.counts.total == 0
    next_result = convert(ConversionRequest([source]), cancellation=CancellationToken())
    assert next_result.status == "succeeded"


def test_cancel_during_discovery_does_not_convert_partial_manifest(image_factory):
    sources = [image_factory(f"root/{i}.png") for i in range(4)]
    token = CancellationToken()
    calls = 0

    def observer(event):
        nonlocal calls
        if event.phase == "discovering":
            calls += 1
            if calls == 4:
                token.cancel()

    result = convert(
        ConversionRequest([sources[0].parent]), cancellation=token, on_progress=observer
    )
    assert result.status == "cancelled" and not result.discovery_complete
    assert result.counts.total > 0 and result.counts.cancelled == result.counts.total
    assert result.counts.published == 0
    assert not list(sources[0].parent.glob("*.webp"))


def test_cancel_after_first_result_counts_and_progress(image_factory):
    sources = [image_factory(f"{i}.png") for i in range(3)]
    token = CancellationToken()
    events = []

    def observer(event):
        events.append(event)
        if event.phase == "item_finished" and event.index == 0:
            token.cancel()

    result = convert(ConversionRequest(sources), cancellation=token, on_progress=observer)
    assert result.status == "cancelled"
    assert [i.status for i in result.items] == ["succeeded", "cancelled", "cancelled"]
    assert result.counts.succeeded == result.counts.published == 1
    assert result.counts.cancelled == 2
    assert events[-1].phase == "finished" and events[-1].processed == 1
    with assert_image(result.items[0].destination):
        pass
    assert not sources[1].with_suffix(".webp").exists()
    assert convert(ConversionRequest(sources[1:])).status == "succeeded"


def test_cancel_after_encode_before_publish(image_factory, monkeypatch):
    source = image_factory()
    original = imaging.encode
    token = CancellationToken()

    def encode(*args, **kwargs):
        prepared = original(*args, **kwargs)
        token.cancel()
        return prepared

    monkeypatch.setattr(imaging, "encode", encode)
    result = convert(ConversionRequest([source]), cancellation=token)
    assert result.status == "cancelled" and result.counts.published == 0
    assert result.items[0].error.code == "CANCELLED"
    assert not list(source.parent.glob(".ic-*"))
    assert not source.with_suffix(".webp").exists()


def test_cancel_after_publication_keeps_current_and_stops_next(image_factory, monkeypatch):
    sources = [image_factory("first.png"), image_factory("second.png")]
    original = fs.publish_new
    token = CancellationToken()

    def publish(*args):
        original(*args)
        token.cancel()

    monkeypatch.setattr(fs, "publish_new", publish)
    result = convert(ConversionRequest(sources), cancellation=token)
    assert result.status == "cancelled" and result.items[0].status == "succeeded"
    assert result.counts.published == 1 and result.counts.cancelled == 1
    assert result.items[0].artifact.publication == "verified"


def test_late_cancellation_after_last_checkpoint_is_success(image_factory, monkeypatch):
    source = image_factory()
    original = fs.publish_new
    token = CancellationToken()

    def publish(*args):
        token.cancel()  # Real link still runs after the already-passed cooperative checkpoint.
        original(*args)

    monkeypatch.setattr(fs, "publish_new", publish)
    result = convert(ConversionRequest([source]), cancellation=token)
    assert token.is_cancelled() and result.status == "succeeded"
    with assert_image(result.items[0].destination):
        pass


def test_observer_failure_disabled_not_retried(image_factory):
    source = image_factory()
    calls = 0

    def observer(event):
        nonlocal calls
        calls += 1
        raise ValueError("PRIVATE_OBSERVER_SENTINEL")

    result = convert(ConversionRequest([source]), on_progress=observer)
    assert result.status == "succeeded" and result.counts.published == 1 and calls == 1
    assert result.warnings[0].code == "OBSERVER_FAILED"
    assert len(list(source.parent.glob("*.webp"))) == 1
