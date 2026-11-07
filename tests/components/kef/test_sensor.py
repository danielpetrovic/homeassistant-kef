"""Sensor-platform tests for KEF."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_HOST
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.icon import async_get_icons
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kef.audio import (
    audio_codec_value,
    audio_virtualizer_value,
    format_channels,
)
from custom_components.kef.const import (
    CONF_BACKEND,
    CONF_ENABLE_DIAGNOSTICS,
    DOMAIN,
    model_supports_feature,
)
from custom_components.kef.coordinator import KefCoordinator
from custom_components.kef.models import KefCalibrationStatus
from custom_components.kef.sensor import SENSORS, _room_calibration_value
from tests.conftest import TEST_HOST, TEST_SNAPSHOT

EXPECTED_SENSORS = tuple(
    description
    for description in SENSORS
    if model_supports_feature(
        TEST_SNAPSHOT.device.model, description.model_feature
    )
)


@pytest.mark.parametrize(
    ("channel_count", "expected"),
    [
        (None, None),
        (0, None),
        ("0", None),
        ("0.0", None),
        (2, "2.0"),
        ("2", "2.0"),
        ("2.0", "2.0"),
        (6, "5.1"),
        ("6", "5.1"),
        (8, "5.1.2"),
        ("8", "5.1.2"),
        (7, "7"),
    ],
)
def test_format_channels_accepts_numeric_and_wire_string_values(
    channel_count: int | str | None,
    expected: str | None,
) -> None:
    """Channel formatting should tolerate both observed payload shapes."""
    assert format_channels(channel_count) == expected


@pytest.mark.parametrize(
    (
        "codec",
        "stream_channels",
        "audio_channels",
        "expected_codec",
        "expected_virtualizer",
    ),
    [
        ("Dolby PCM - Direct", 6, 2, "PCM 5.1", "Direct 5.1"),
        ("Dolby PCM - Direct", "0", 2, "PCM", "Direct 2.0"),
        (
            "Dolby Digital Plus - Dolby Surround",
            "2",
            2,
            "Dolby Digital Plus 2.0",
            "Dolby Surround 5.1.2",
        ),
        ("PCM", "2.0", 2, "PCM 2.0", "Direct 2.0"),
        ("Dolby Atmos", 0, 8, "Dolby Atmos", "Dolby Atmos 5.1.2"),
        # Observed on an XIO with the surround channel layout set to 7.1.2.
        ("Dolby Atmos", 0, 10, "Dolby Atmos", "Dolby Atmos 7.1.2"),
        (None, None, None, None, None),
    ],
)
def test_audio_sensor_values_decode_codec_and_channel_contract(
    codec: str | None,
    stream_channels: int | str | None,
    audio_channels: int | None,
    expected_codec: str | None,
    expected_virtualizer: str | None,
) -> None:
    """Codec sensors should decode live values without leaking zero channels."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    assert snapshot.playback is not None
    snapshot.playback.codec = codec
    snapshot.playback.stream_channels = stream_channels
    snapshot.playback.audio_channels = audio_channels

    assert audio_codec_value(snapshot) == expected_codec
    assert audio_virtualizer_value(snapshot) == expected_virtualizer


def test_audio_virtualizer_includes_virtual_x_when_active() -> None:
    """DTS Virtual:X is a separate decoder flag layered on the Dolby upmixer."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    assert snapshot.playback is not None
    snapshot.playback.codec = "Dolby Digital Plus - Dolby Surround"
    snapshot.virtual_x_active = True

    assert audio_virtualizer_value(snapshot) == "Dolby Surround + Virtual:X 5.1.2"


def test_audio_virtualizer_shows_what_virtual_x_renders_for_atmos() -> None:
    """With DTS Virtual:X preferred an Atmos stream is rendered at 7.1.4."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    assert snapshot.playback is not None
    snapshot.playback.codec = "Dolby Atmos"
    snapshot.playback.stream_channels = 0
    snapshot.playback.audio_channels = 12
    snapshot.virtual_x_active = True

    assert audio_virtualizer_value(snapshot) == "Dolby Atmos + Virtual:X 7.1.4"


def test_audio_virtualizer_names_virtual_x_as_renderer_for_dts() -> None:
    """DTS has no Dolby processing part, so Virtual:X renders it, not passthrough."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    assert snapshot.playback is not None
    snapshot.playback.codec = "DTS"
    snapshot.playback.stream_channels = 6
    snapshot.playback.audio_channels = 12
    snapshot.virtual_x_active = True

    assert audio_codec_value(snapshot) == "DTS 5.1"
    assert audio_virtualizer_value(snapshot) == "DTS Virtual:X 7.1.4"


def test_audio_virtualizer_keeps_direct_when_virtual_x_is_off() -> None:
    """Real passthrough without the Virtual:X flag stays Direct."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    assert snapshot.playback is not None
    snapshot.playback.codec = "DTS"
    snapshot.playback.stream_channels = 6
    snapshot.virtual_x_active = False

    assert audio_virtualizer_value(snapshot) == "Direct 5.1"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (None, None),
        (KefCalibrationStatus(is_calibrated=None), None),
        (KefCalibrationStatus(is_calibrated=False), "Not calibrated"),
        (KefCalibrationStatus(is_calibrated=True), "Calibrated"),
        (
            KefCalibrationStatus(
                is_calibrated=True,
                year=2026,
                month=9,
                day=16,
            ),
            "2026-09-16",
        ),
    ],
)
def test_room_calibration_value_distinguishes_unknown_and_uncalibrated(
    status: KefCalibrationStatus | None,
    expected: str | None,
) -> None:
    """Missing calibration state must not be reported as a negative result."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.calibration_status = status

    assert _room_calibration_value(snapshot) == expected


async def _async_publish_test_snapshot(coordinator: KefCoordinator) -> None:
    """Publish the test snapshot instead of contacting a speaker."""
    coordinator.async_set_updated_data(TEST_SNAPSHOT)


async def test_sensor_platform_registers_distinct_names_and_metadata(hass) -> None:
    """Sensors should keep their descriptions and expose useful presentation data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=TEST_SNAPSHOT.device.device_name,
        unique_id=TEST_SNAPSHOT.device.unique_id,
        data={
            CONF_HOST: TEST_HOST,
            CONF_BACKEND: TEST_SNAPSHOT.device.backend,
        },
        options={CONF_ENABLE_DIAGNOSTICS: True},
    )
    entry.add_to_hass(hass)

    with patch.object(
        KefCoordinator,
        "async_config_entry_first_refresh",
        _async_publish_test_snapshot,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    translations = await async_get_translations(hass, "en", "entity", {DOMAIN})
    sensor_entries = {
        entity_entry.unique_id: entity_entry
        for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity_entry.domain == "sensor"
    }

    assert len(sensor_entries) == len(EXPECTED_SENSORS)
    assert len(
        {item.entity_id for item in sensor_entries.values()}
    ) == len(EXPECTED_SENSORS)

    icons = (await async_get_icons(hass, "entity", {DOMAIN}))[DOMAIN]
    for description in EXPECTED_SENSORS:
        unique_id = f"{TEST_SNAPSHOT.device.unique_id}_{description.key}"
        entity_entry = sensor_entries[unique_id]

        assert entity_entry.original_name == translations[
            f"component.kef.entity.sensor.{description.translation_key}.name"
        ]
        assert entity_entry.entity_id.startswith("sensor.lsx_ii_test_")
        assert description.device_class is not None or icons["sensor"].get(
            description.translation_key, {}
        ).get("default")
        if description.device_class is SensorDeviceClass.ENUM:
            assert description.value_fn(TEST_SNAPSHOT) in description.options

    signal_state = hass.states.get("sensor.lsx_ii_test_wi_fi_signal_level")
    assert signal_state is not None
    assert signal_state.state == "-49"
    assert signal_state.attributes["device_class"] == "signal_strength"
    assert signal_state.attributes["state_class"] == "measurement"
    assert signal_state.attributes["unit_of_measurement"] == "dBm"

    packet_loss_state = hass.states.get(
        "sensor.lsx_ii_test_speed_test_packet_loss"
    )
    assert packet_loss_state is not None
    assert icons["sensor"]["speed_test_packet_loss"]["default"] == (
        "mdi:package-variant-closed-remove"
    )
    assert packet_loss_state.attributes["state_class"] == "measurement"
    assert packet_loss_state.attributes["unit_of_measurement"] == "%"
