# KEF Python Library

`kef_client` is the reusable async Python layer that powers the Home Assistant integration in this repository.

It supports two local transport families:

- modern KEF HTTP-based speakers such as LSX II / LS50 Wireless II / LS60 family
- older legacy KEF speakers through the binary transport path

## Installation

From this repository:

```bash
python -m pip install -e .
```

## Quick Start

```python
import asyncio

from aiohttp import ClientSession
from kef_client import ModernKefClient


async def main() -> None:
    async with ClientSession() as session:
        client = ModernKefClient("192.168.1.20", session)
        snapshot = await client.async_refresh()
        print(snapshot.device.device_name)
        print(snapshot.source)
        print(snapshot.volume)


asyncio.run(main())
```

If you want automatic backend selection, use `async_create_client(...)` instead of constructing a specific client directly.

## Main Workflow

Typical usage looks like this:

1. Create an `aiohttp.ClientSession` for modern devices
2. Create either a `ModernKefClient`, `LegacyBinaryClient`, or call `async_create_client(...)`
3. Call `async_identify()` for model details
4. Call `async_refresh()` for a full `KefSnapshot`
5. Apply controls or settings through the async setters

## Public Models

The most useful models are:

- `KefSnapshot`: current speaker state
- `KefDeviceInfo`: model, firmware, MAC, release text
- `KefPlaybackInfo`: current playback metadata
- `KefEqProfile`: equalizer and room/setup values
- `KefSurroundDevice`: a speaker paired for wireless surround, with its position and connection state
- `KefWifiInfo`: Wi-Fi details when the speaker exposes them
- `KefBackend`: `modern` or `legacy`

## Main Read Methods

- `async_identify()`
- `async_refresh()`

For modern devices, `async_refresh()` includes source, power state, volume, mute, playback metadata, EQ state, startup volume settings, and optional Wi-Fi information when available.

## Main Control Methods

- `async_turn_on()`
- `async_turn_off()`
- `async_set_volume_raw(volume)`
- `async_get_playback_state()`
- `async_toggle_play_pause()`
- `async_set_muted(muted)`
- `async_next_track()`
- `async_previous_track()`
- `async_select_source(source)`

## Main Settings Methods

- `async_set_standby_mode(mode)`
- `async_set_startup_tone_enabled(enabled)`
- `async_set_auto_switch_hdmi_enabled(enabled)`
- `async_set_front_led_enabled(enabled)`
- `async_set_standby_led_enabled(enabled)`
- `async_set_top_panel_enabled(enabled)`
- `async_set_wake_source(source)`
- `async_set_subwoofer_wake_enabled(enabled)`
- `async_set_kw1_wake_enabled(enabled)`
- `async_set_usb_charging_enabled(enabled)`
- `async_set_startup_volume_enabled(enabled)`
- `async_set_per_input_startup_volume_enabled(enabled)`
- `async_set_default_volume_global(volume)`
- `async_set_maximum_volume(volume)`
- `async_set_volume_step(step)`
- `async_set_volume_limit_enabled(enabled)`
- `async_set_default_volume_for_source(source, volume)`
- `async_set_wireless_rear_mode(mode)`: `surround` (5.1.2) or `rearSurround` (7.1.2), XIO with wireless surround firmware
- `async_set_wireless_rear_gain(gain)`: -10 to 10 in steps of 0.5, XIO with wireless surround firmware

## Choosing a Backend

- Use `ModernKefClient` when you know the device is from the newer HTTP-based family.
- Use `LegacyBinaryClient` for first-generation speakers that still expose the older binary port.
  It preserves the speaker's channel orientation and standby setting when
  changing source or power. Standalone callers can pass `standby_time=20`,
  `standby_time=60`, or `standby_time=None` to choose a standby setting explicitly;
  the default `standby_time="preserve"` keeps the current setting. Power-off
  changes 20-minute standby to 60 minutes before turning the speaker off to
  avoid a control-server failure described by the original legacy client.
- Use `async_create_client(...)` when you want the library to probe and choose for you.

## Error Handling

The library exposes:

- `KefError`: base exception
- `KefConnectionError`: connectivity or transport issue
- `KefResponseError`: invalid or unexpected device response
- `KefUnsupportedDeviceError`: the device does not match supported local APIs

## Notes

- Not every source supports every playback command.
- Capability differences matter across KEF families, so callers should inspect `KefSnapshot` instead of assuming all settings exist everywhere.
- The Home Assistant integration in `custom_components/kef` is built on top of this package.
