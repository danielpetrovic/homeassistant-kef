"""Models for the KEF integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite as _isfinite
from typing import Any

from .exceptions import KefResponseError as _KefResponseError


def _eq_number(value: Any) -> float:
    """Normalize EQ numbers without exposing Python conversion errors."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as err:
        raise _KefResponseError("Unexpected KEF EQ numeric value") from err
    if isinstance(value, bool) or not _isfinite(number):
        raise _KefResponseError("Unexpected KEF EQ numeric value")
    return number


def _legacy_eq_profile_to_native(dsp_info: dict[str, Any]) -> dict[str, Any]:
    """Convert v1 EQ wire values to the physical units exposed by HA."""
    profile = dict(dsp_info)

    if (value := profile.get("balance")) is not None:
        profile["balance"] = round(_eq_number(value)) - 30
    if (value := profile.get("trebleAmount")) is not None:
        profile["trebleAmount"] = round((_eq_number(value) / 16.0 * 6.0) - 3.0, 3)
    if (value := profile.get("subwooferGain")) is not None:
        profile["subwooferGain"] = round(_eq_number(value)) - 10
    if (value := profile.get("highPassModeFreq")) is not None:
        profile["highPassModeFreq"] = 50 + round(_eq_number(value)) * 5
    for key in ("deskModeSetting", "wallModeSetting"):
        if (value := profile.get(key)) is not None:
            profile[key] = round((_eq_number(value) / 2.0) - 10.0, 1)
    if (value := profile.get("subOutLPFreq")) is not None:
        scaled = _eq_number(value) * 10.0
        profile["subOutLPFreq"] = round(_eq_number(scaled))

    return profile


def _native_eq_profile_to_legacy(profile: dict[str, Any]) -> dict[str, Any]:
    """Convert physical EQ units back to the v1 wire representation."""
    dsp_info = dict(profile)

    if (value := dsp_info.get("balance")) is not None:
        dsp_info["balance"] = max(0, min(60, round(_eq_number(value) + 30)))
    if (value := dsp_info.get("trebleAmount")) is not None:
        legacy = round((_eq_number(value) + 3.0) / 6.0 * 16.0)
        dsp_info["trebleAmount"] = max(0, min(16, legacy))
    if (value := dsp_info.get("subwooferGain")) is not None:
        dsp_info["subwooferGain"] = max(0, min(20, round(_eq_number(value) + 10)))
    if (value := dsp_info.get("highPassModeFreq")) is not None:
        legacy = round((_eq_number(value) - 50.0) / 5.0)
        dsp_info["highPassModeFreq"] = max(0, min(10, legacy))
    for key in ("deskModeSetting", "wallModeSetting"):
        if (value := dsp_info.get(key)) is not None:
            legacy = round((_eq_number(value) + 10.0) * 2.0)
            dsp_info[key] = max(0, min(20, legacy))
    if (value := dsp_info.get("subOutLPFreq")) is not None:
        legacy = round(_eq_number(value) / 10.0)
        dsp_info["subOutLPFreq"] = max(4, min(25, legacy))

    return dsp_info


class KefBackend(StrEnum):
    """Supported KEF backends."""

    MODERN = "modern"
    LEGACY = "legacy"


@dataclass(slots=True)
class KefPlaybackInfo:
    """Playback information."""

    state: str | None = None
    title: str | None = None
    artist: str | None = None
    album_artist: str | None = None
    album: str | None = None
    image_url: str | None = None
    service_id: str | None = None
    codec: str | None = None
    sample_frequency: int | None = None
    stream_sample_rate: int | None = None
    stream_channels: int | str | None = None
    audio_channels: int | None = None
    duration_ms: int | None = None
    position_ms: int | None = None
    controls: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class KefFirmwareUpdateInfo:
    """Firmware-update information exposed by the modern API."""

    state: str | None = None
    download_progress: int | None = None
    available_version: str | None = None
    forced_update: bool | None = None
    image_size: int | None = None
    last_forced_version: str | None = None
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_modern_value(cls, value: dict[str, Any]) -> KefFirmwareUpdateInfo | None:
        """Build firmware-update info from the modern API payload."""
        update_info = value.get("firmwareUpdateStatus", {})
        if not isinstance(update_info, dict) or not update_info:
            return None

        image = update_info.get("imageDescription", {})
        if not isinstance(image, dict):
            image = {}

        return cls(
            state=update_info.get("state"),
            download_progress=update_info.get("downloadProgress"),
            available_version=image.get("version"),
            forced_update=image.get("forcedUpdate"),
            image_size=image.get("imageSize"),
            last_forced_version=image.get("lastForcedVersion"),
            url=image.get("url"),
            raw=update_info,
        )

    @property
    def is_available(self) -> bool:
        """Return whether a newer firmware image is available."""
        return self.state in {"newUpdateAvailable", "updateAvailable"}


@dataclass(slots=True)
class KefCalibrationStatus:
    """Room calibration status exposed by the modern API (XIO only)."""

    is_calibrated: bool | None = None
    year: int | None = None
    month: int | None = None
    day: int | None = None
    stability: int | None = None

    @classmethod
    def from_modern_value(cls, value: dict[str, Any]) -> KefCalibrationStatus | None:
        """Build calibration status from the raw kefDspCalibrationStatus payload."""
        if not value:
            return None
        return cls(
            is_calibrated=value.get("isCalibrated"),
            year=value.get("year"),
            month=value.get("month"),
            day=value.get("day"),
            stability=value.get("stability"),
        )


@dataclass(frozen=True, slots=True)
class KefSurroundDevice:
    """A wireless surround speaker or subwoofer paired to an XIO."""

    key: str
    position: str | None = None
    model_name: str | None = None
    connection_type: str | None = None
    connected: bool | None = None

    @classmethod
    def from_modern_value(cls, value: Any) -> KefSurroundDevice | None:
        """Build a paired surround device from one device-list entry."""
        if not isinstance(value, dict):
            return None
        receiver = value.get("rxDevice")
        if not isinstance(receiver, dict):
            receiver = {}
        key = receiver.get("macAddress") or value.get("modelMacAddress")
        if not isinstance(key, str) or not key:
            return None
        position = value.get("devicePosition") or receiver.get("devicePosition")
        connected = receiver.get("isConnected")
        return cls(
            key=key.lower(),
            position=position if isinstance(position, str) else None,
            model_name=(
                value["modelName"] if isinstance(value.get("modelName"), str) else None
            ),
            connection_type=(
                value["connectionType"]
                if isinstance(value.get("connectionType"), str)
                else None
            ),
            connected=connected if isinstance(connected, bool) else None,
        )

    @classmethod
    def from_modern_list(cls, value: Any) -> tuple[KefSurroundDevice, ...]:
        """Build the paired surround devices from a device-list payload."""
        if not isinstance(value, list):
            return ()
        devices = (cls.from_modern_value(item) for item in value)
        return tuple(device for device in devices if device is not None)


@dataclass(slots=True)
class KefWifiInfo:
    """Flattened KEF Wi-Fi information."""

    signal_level: int | None = None
    ssid: str | None = None
    frequency: int | None = None
    bssid: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_modern_value(cls, value: dict[str, Any]) -> KefWifiInfo | None:
        """Build a Wi-Fi info object from the modern API payload."""
        network_info = value.get("networkInfo", {})
        wireless = network_info.get("wireless", {})
        if not isinstance(wireless, dict) or not wireless:
            return None
        return cls(
            signal_level=wireless.get("signalLevel"),
            ssid=wireless.get("ssid"),
            frequency=wireless.get("frequency"),
            bssid=wireless.get("bssid"),
            raw=wireless,
        )


@dataclass(slots=True)
class KefEqProfile:
    """Flattened modern KEF EQ information."""

    api_version: str = "v1"
    is_expert_mode: bool | None = None
    profile_name: str | None = None
    profile_id: str | None = None
    balance: int | None = None
    bass_extension: str | None = None
    treble_amount: float | None = None
    subwoofer_gain: int | None = None
    high_pass_mode: bool | None = None
    high_pass_frequency: float | None = None
    desk_mode: bool | None = None
    desk_mode_setting: float | None = None
    wall_mode: bool | None = None
    wall_mode_setting: float | None = None
    phase_correction: bool | None = None
    audio_polarity: str | None = None
    subwoofer_polarity: str | None = None
    is_kw1: bool | None = None
    subwoofer_count: int | None = None
    sub_enable_stereo: bool | None = None
    subwoofer_preset: str | None = None
    sub_out_low_pass_frequency: float | None = None
    subwoofer_out: bool | None = None
    sound_profile: str | None = None
    dialogue_mode: bool | None = None
    wall_mounted: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_modern_value(cls, value: dict[str, Any]) -> KefEqProfile:
        """Build an EQ profile from the modern API payload."""
        if value.get("type") == "kefEqProfileV2" or "kefEqProfileV2" in value:
            return cls.from_modern_v2_value(value)

        profile = value.get("kefEqProfile", {})
        if not isinstance(profile, dict):
            profile = {}
        dsp_info = profile.get("dspInfo", {})
        if not isinstance(dsp_info, dict):
            dsp_info = {}
        native_dsp_info = _legacy_eq_profile_to_native(dsp_info)
        return cls(
            api_version="v1",
            is_expert_mode=profile.get("isExpertMode"),
            profile_name=profile.get("profileName") or None,
            profile_id=profile.get("profileId") or None,
            balance=native_dsp_info.get("balance"),
            bass_extension=native_dsp_info.get("bassExtension"),
            treble_amount=native_dsp_info.get("trebleAmount"),
            subwoofer_gain=native_dsp_info.get("subwooferGain"),
            high_pass_mode=native_dsp_info.get("highPassMode"),
            high_pass_frequency=native_dsp_info.get("highPassModeFreq"),
            desk_mode=native_dsp_info.get("deskMode"),
            desk_mode_setting=native_dsp_info.get("deskModeSetting"),
            wall_mode=native_dsp_info.get("wallMode"),
            wall_mode_setting=native_dsp_info.get("wallModeSetting"),
            phase_correction=native_dsp_info.get("phaseCorrection"),
            audio_polarity=native_dsp_info.get("audioPolarity"),
            subwoofer_polarity=native_dsp_info.get("subwooferPolarity"),
            is_kw1=native_dsp_info.get("isKW1"),
            subwoofer_count=native_dsp_info.get("subwooferCount"),
            sub_enable_stereo=native_dsp_info.get("subEnableStereo"),
            subwoofer_preset=native_dsp_info.get("subwooferPreset"),
            sub_out_low_pass_frequency=native_dsp_info.get("subOutLPFreq"),
            subwoofer_out=(
                native_dsp_info["subwooferCount"] > 0
                if isinstance(native_dsp_info.get("subwooferCount"), (int, float))
                else None
            ),
            raw=profile,
        )

    @classmethod
    def from_modern_v2_value(cls, value: dict[str, Any]) -> KefEqProfile:
        """Build an EQ profile from the modern v2 payload."""
        profile = value.get("kefEqProfileV2", {})
        if not isinstance(profile, dict):
            profile = {}
        return cls(
            api_version="v2",
            is_expert_mode=profile.get("isExpertMode"),
            profile_name=profile.get("profileName") or None,
            profile_id=profile.get("profileId") or None,
            balance=profile.get("balance"),
            bass_extension=profile.get("bassExtension"),
            treble_amount=profile.get("trebleAmount"),
            subwoofer_gain=profile.get("subwooferGain"),
            high_pass_mode=profile.get("highPassMode"),
            high_pass_frequency=profile.get("highPassModeFreq"),
            desk_mode=profile.get("deskMode"),
            desk_mode_setting=profile.get("deskModeSetting"),
            wall_mode=profile.get("wallMode"),
            wall_mode_setting=profile.get("wallModeSetting"),
            phase_correction=profile.get("phaseCorrection"),
            audio_polarity=profile.get("audioPolarity"),
            subwoofer_polarity=profile.get("subwooferPolarity"),
            is_kw1=profile.get("isKW1"),
            subwoofer_count=profile.get("subwooferCount"),
            sub_enable_stereo=profile.get("subEnableStereo"),
            subwoofer_preset=profile.get("subwooferPreset"),
            sub_out_low_pass_frequency=profile.get("subOutLPFreq"),
            subwoofer_out=profile.get("subwooferOut"),
            sound_profile=profile.get("soundProfile"),
            dialogue_mode=profile.get("dialogueMode"),
            wall_mounted=profile.get("wallMounted"),
            raw=profile,
        )


@dataclass(slots=True)
class KefDeviceInfo:
    """Basic KEF device information."""

    backend: KefBackend
    unique_id: str
    device_name: str
    model: str
    mac_address: str | None = None
    firmware_version: str | None = None
    release_text: str | None = None
    model_code: str | None = None
    serial_number: str | None = None
    kef_id: str | None = None
    hardware_version: str | None = None
    host: str | None = None
    port: int | None = None


@dataclass(slots=True)
class KefSnapshot:
    """Current KEF state."""

    device: KefDeviceInfo
    speaker_status: str | None
    source: str | None
    cable_mode: str | None
    master_channel: str | None
    volume_raw: int | None
    volume_level: float | None
    is_muted: bool | None
    play_mode: str | None
    playback: KefPlaybackInfo | None
    eq_profile: KefEqProfile | None
    firmware_update: KefFirmwareUpdateInfo | None
    wifi_info: KefWifiInfo | None
    standby_mode: str | None
    startup_tone_enabled: bool | None
    auto_switch_hdmi: bool | None
    front_led_enabled: bool | None
    standby_led_enabled: bool | None
    top_panel_enabled: bool | None
    top_panel_led_enabled: bool | None
    top_panel_standby_led_enabled: bool | None
    wake_source: str | None
    subwoofer_wake_enabled: bool | None
    kw1_wake_enabled: bool | None
    usb_charging_enabled: bool | None
    startup_volume_enabled: bool | None
    per_input_startup_volume_enabled: bool | None
    default_volume_global: int | None
    maximum_volume: int | None
    volume_step: int | None
    volume_limit_enabled: bool | None
    fixed_volume_level: int | None
    remote_ir_enabled: bool | None
    remote_ir_code: str | None
    favourite_button: str | None
    eq_button_1: str | None
    eq_button_2: str | None
    analytics_enabled: bool | None
    app_analytics_enabled: bool | None
    streaming_quality: str | None
    ui_language: str | None
    speaker_location: str | None
    network_ping_ms: float | None
    network_stability: str | None
    speed_test_status: str | None
    speed_test_average_download: float | None
    speed_test_current_download: float | None
    speed_test_packet_loss: float | None
    alert_alarm_count: int | None
    alert_timer_count: int | None
    alert_snooze_minutes: int | None
    player_notification_active: bool | None
    calibration_status: KefCalibrationStatus | None
    calibration_result: float | None
    auto_detect_placement: bool | None
    prefer_virtual_x: bool | None
    virtual_x_active: bool | None
    source_list: tuple[str, ...]
    default_volume_by_source: dict[str, int] = field(default_factory=dict)
    surround_mode: bool | None = None
    surround_devices: tuple[KefSurroundDevice, ...] = ()
    wireless_rear_mode: str | None = None
    wireless_rear_gain: float | None = None
    surround_master_channel: str | None = None

    @property
    def is_power_on(self) -> bool:
        """Return whether the speaker is on."""
        return self.speaker_status not in (None, "standby")
