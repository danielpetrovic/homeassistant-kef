"""Shared audio presentation helpers for KEF entities."""

from __future__ import annotations

from .models import KefSnapshot

# Formats the soundbar renders itself. Their codec string carries no
# " - <processing>" part, yet the output is not a plain passthrough.
_NATIVE_RENDERERS = {"Dolby Atmos"}


# Output channels of the soundbar's own rendering: Dolby at 5.1.2 or 7.1.2
# (the surround channel layout) and DTS Virtual:X at 7.1.4, as observed on an XIO.
_RENDERED_LAYOUTS = {8: "5.1.2", 10: "7.1.2", 12: "7.1.4"}


def _rendered_layout(audio_channels: int | None) -> str:
    """Return the layout the soundbar renders, 5.1.2 when the count is unknown."""
    return _RENDERED_LAYOUTS.get(audio_channels or 0, "5.1.2")


def format_channels(channel_count: int | str | None) -> str | None:
    """Convert a channel count to audio format notation (for example, 5.1.2)."""
    if channel_count is None:
        return None

    if isinstance(channel_count, str):
        channel_text = channel_count.strip()
        if not channel_text:
            return None
        try:
            channel_count = int(channel_text)
        except ValueError:
            return None if channel_text == "0.0" else channel_text

    if channel_count <= 0:
        return None
    channel_map = {2: "2.0", 6: "5.1", 8: "5.1.2"}
    return channel_map.get(channel_count, str(channel_count))


def audio_codec_value(data: KefSnapshot) -> str | None:
    """Return the decoded audio codec with channel format."""
    if data.playback is None or not data.playback.codec:
        return None
    codec_name = (
        data.playback.codec.split(" - ")[0]
        if " - " in data.playback.codec
        else data.playback.codec
    )
    if codec_name == "Dolby PCM":
        codec_name = "PCM"
    channel_format = format_channels(data.playback.stream_channels)
    if channel_format:
        return f"{codec_name} {channel_format}"
    return codec_name


def audio_virtualizer_value(data: KefSnapshot) -> str | None:
    """Return the decoded audio virtualizer mode with channel format."""
    if data.playback is None or not data.playback.codec:
        return None
    codec = data.playback.codec
    if " - " in codec:
        virtualizer_name = codec.split(" - ")[1]
    elif codec in _NATIVE_RENDERERS:
        virtualizer_name = codec
    else:
        virtualizer_name = "Direct"
    if virtualizer_name == "Direct" and data.virtual_x_active:
        # Without a Dolby processing part (e.g. DTS, which the Dolby upmixer
        # cannot process), Virtual:X is the renderer itself, not passthrough.
        return f"DTS Virtual:X {_rendered_layout(data.playback.audio_channels)}"
    if virtualizer_name == "Direct":
        channel_format = format_channels(data.playback.stream_channels)
        if channel_format is None:
            channel_format = format_channels(data.playback.audio_channels)
        return f"{virtualizer_name} {channel_format}" if channel_format else "Direct"
    layout = _rendered_layout(data.playback.audio_channels)
    # The codec string only names the Dolby upmixer; DTS Virtual:X is reported
    # by a separate decoder flag and runs on top of it, so the layout that
    # follows is what Virtual:X renders.
    if data.virtual_x_active:
        return f"{virtualizer_name} + Virtual:X {layout}"
    return f"{virtualizer_name} {layout}"
