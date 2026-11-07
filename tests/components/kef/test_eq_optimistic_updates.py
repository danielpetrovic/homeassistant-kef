"""Optimistic entity update tests for KEF."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kef.const import CONF_BACKEND, CONF_TCP_PORT, DOMAIN
from custom_components.kef.coordinator import KefCoordinator
from custom_components.kef.exceptions import KefError
from custom_components.kef.number import (
    NUMBERS,
    KefNumber,
    KefSourceVolumeNumber,
    _async_set_balance,
    _async_set_default_volume_global,
    _async_set_desk_mode_db,
    _async_set_fixed_volume_level,
    _async_set_high_pass_frequency,
    _async_set_maximum_volume,
    _async_set_source_volume,
    _async_set_sub_out_low_pass_frequency,
    _async_set_subwoofer_gain,
    _async_set_treble_amount,
    _async_set_volume_step,
    _async_set_wall_mode_db,
)
from custom_components.kef.select import (
    _async_set_bass_extension,
    _async_set_cable_mode,
    _async_set_eq_button_1,
    _async_set_eq_button_2,
    _async_set_favourite_button,
    _async_set_master_channel,
    _async_set_remote_ir_code,
    _async_set_standby_mode,
    _async_set_streaming_quality,
    _async_set_subwoofer_preset,
    _async_set_wake_source,
    _async_set_wireless_rear_mode,
)
from custom_components.kef.switch import (
    SWITCHES,
    KefSwitch,
    _async_set_analytics,
    _async_set_app_analytics,
    _async_set_auto_detect_placement,
    _async_set_auto_switch_hdmi,
    _async_set_desk_mode,
    _async_set_front_led,
    _async_set_high_pass_mode,
    _async_set_kw1_adapter,
    _async_set_kw1_wake,
    _async_set_per_input_startup_volume,
    _async_set_phase_correction,
    _async_set_remote_ir,
    _async_set_standby_led,
    _async_set_startup_tone,
    _async_set_startup_volume,
    _async_set_subwoofer_enabled,
    _async_set_subwoofer_wake,
    _async_set_top_panel,
    _async_set_top_panel_led,
    _async_set_top_panel_standby_led,
    _async_set_usb_charging,
    _async_set_volume_limit,
    _async_set_wall_mode,
    _async_set_wall_mounted,
)
from tests.conftest import TEST_HOST, TEST_PORT, TEST_SNAPSHOT


def _coordinator_with_local_updates():
    """Create a lightweight coordinator that publishes local changes."""
    coordinator = Mock()
    coordinator.data = deepcopy(TEST_SNAPSHOT)

    def apply(**changes) -> None:
        coordinator.data = replace(coordinator.data, **changes)

    coordinator.async_apply_local_change = Mock(side_effect=apply)
    return coordinator


def _real_coordinator(hass) -> KefCoordinator:
    """Create a real coordinator for entity-to-refresh contract tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": TEST_HOST,
            "port": TEST_PORT,
            CONF_TCP_PORT: 50001,
            CONF_BACKEND: "modern",
        },
        title="KEF",
    )
    coordinator = KefCoordinator(hass, entry)
    coordinator.data = deepcopy(TEST_SNAPSHOT)
    return coordinator


def _refresh_immediately(coordinator: KefCoordinator) -> None:
    """Make an entity's requested refresh publish the fetched snapshot."""

    async def refresh() -> None:
        snapshot = await coordinator._async_update_data()
        coordinator.async_set_updated_data(snapshot)

    coordinator.async_request_refresh = AsyncMock(side_effect=refresh)


async def test_subwoofer_preset_publishes_all_written_values() -> None:
    """Preset selection should immediately publish its complete tuning tuple."""
    coordinator = _coordinator_with_local_updates()
    coordinator.client = SimpleNamespace(
        async_set_subwoofer_preset=AsyncMock(
            return_value={"gain": -1.0, "lowpass": 55.0, "highpass": 67.5}
        )
    )
    assert coordinator.data.eq_profile is not None
    original_balance = coordinator.data.eq_profile.balance

    await _async_set_subwoofer_preset(coordinator, "kc62")

    coordinator.client.async_set_subwoofer_preset.assert_awaited_once_with(
        "kc62", coordinator.data.device.model
    )
    profile = coordinator.data.eq_profile
    assert profile is not None
    assert profile.subwoofer_preset == "kc62"
    assert profile.subwoofer_gain == -1.0
    assert profile.sub_out_low_pass_frequency == 55.0
    assert profile.high_pass_frequency == 67.5
    assert profile.balance == original_balance


async def test_manual_tuning_publishes_custom_preset() -> None:
    """Manual subwoofer tuning should immediately retire the named preset."""
    coordinator = _coordinator_with_local_updates()
    coordinator.client = SimpleNamespace(async_set_subwoofer_gain=AsyncMock())
    assert coordinator.data.eq_profile is not None
    coordinator.data.eq_profile.subwoofer_preset = "kc62"

    await _async_set_subwoofer_gain(coordinator, -2)

    profile = coordinator.data.eq_profile
    assert profile is not None
    assert profile.subwoofer_gain == -2
    assert profile.subwoofer_preset == "custom"


async def test_failed_preset_write_does_not_publish_optimistic_state() -> None:
    """A rejected device write must leave the coordinator snapshot unchanged."""
    coordinator = _coordinator_with_local_updates()
    coordinator.client = SimpleNamespace(
        async_set_subwoofer_preset=AsyncMock(side_effect=KefError("write failed"))
    )
    before = deepcopy(coordinator.data)

    with pytest.raises(KefError, match="write failed"):
        await _async_set_subwoofer_preset(coordinator, "kc62")

    assert coordinator.data == before
    coordinator.async_apply_local_change.assert_not_called()


def _get_field(data, field_path: str):
    """Resolve a possibly-dotted field path against a snapshot."""
    obj = data
    for part in field_path.split("."):
        obj = getattr(obj, part)
    return obj


# (setter, client_method, field_path, value) - value doubles as the
# expected published result, since every one of these is a plain 1:1 write.
_SETTERS = [
    (
        _async_set_standby_mode,
        "async_set_standby_mode",
        "standby_mode",
        "standby_20mins",
    ),
    (_async_set_wake_source, "async_set_wake_source", "wake_source", "tv"),
    (_async_set_master_channel, "async_set_master_channel", "master_channel", "left"),
    (_async_set_cable_mode, "async_set_cable_mode", "cable_mode", "wireless"),
    (
        _async_set_bass_extension,
        "async_set_bass_extension",
        "eq_profile.bass_extension",
        "extra",
    ),
    (
        _async_set_remote_ir_code,
        "async_set_remote_ir_code",
        "remote_ir_code",
        "ir_code_set_b",
    ),
    (
        _async_set_streaming_quality,
        "async_set_streaming_quality",
        "streaming_quality",
        "320",
    ),
    (
        _async_set_favourite_button,
        "async_set_favourite_button_action",
        "favourite_button",
        "nextSource",
    ),
    (_async_set_eq_button_1, "async_set_eq_button_action", "eq_button_1", "music"),
    (_async_set_eq_button_2, "async_set_eq_button_action", "eq_button_2", "movie"),
    (
        _async_set_startup_tone,
        "async_set_startup_tone_enabled",
        "startup_tone_enabled",
        False,
    ),
    (
        _async_set_auto_switch_hdmi,
        "async_set_auto_switch_hdmi_enabled",
        "auto_switch_hdmi",
        True,
    ),
    (
        _async_set_standby_led,
        "async_set_standby_led_enabled",
        "standby_led_enabled",
        False,
    ),
    (_async_set_front_led, "async_set_front_led_enabled", "front_led_enabled", True),
    (_async_set_top_panel, "async_set_top_panel_enabled", "top_panel_enabled", False),
    (
        _async_set_top_panel_led,
        "async_set_top_panel_led_enabled",
        "top_panel_led_enabled",
        False,
    ),
    (
        _async_set_top_panel_standby_led,
        "async_set_top_panel_standby_led_enabled",
        "top_panel_standby_led_enabled",
        False,
    ),
    (
        _async_set_usb_charging,
        "async_set_usb_charging_enabled",
        "usb_charging_enabled",
        True,
    ),
    (
        _async_set_startup_volume,
        "async_set_startup_volume_enabled",
        "startup_volume_enabled",
        True,
    ),
    (
        _async_set_per_input_startup_volume,
        "async_set_per_input_startup_volume_enabled",
        "per_input_startup_volume_enabled",
        True,
    ),
    (
        _async_set_volume_limit,
        "async_set_volume_limit_enabled",
        "volume_limit_enabled",
        True,
    ),
    (
        _async_set_subwoofer_wake,
        "async_set_subwoofer_wake_enabled",
        "subwoofer_wake_enabled",
        True,
    ),
    (_async_set_kw1_wake, "async_set_kw1_wake_enabled", "kw1_wake_enabled", True),
    (_async_set_kw1_adapter, "async_set_kw1_enabled", "eq_profile.is_kw1", True),
    (_async_set_remote_ir, "async_set_remote_ir_enabled", "remote_ir_enabled", False),
    (_async_set_analytics, "async_set_analytics_enabled", "analytics_enabled", False),
    (
        _async_set_app_analytics,
        "async_set_app_analytics_enabled",
        "app_analytics_enabled",
        False,
    ),
    (_async_set_desk_mode, "async_set_desk_mode_enabled", "eq_profile.desk_mode", True),
    (_async_set_wall_mode, "async_set_wall_mode_enabled", "eq_profile.wall_mode", True),
    (
        _async_set_phase_correction,
        "async_set_phase_correction_enabled",
        "eq_profile.phase_correction",
        False,
    ),
    (
        _async_set_high_pass_mode,
        "async_set_high_pass_mode_enabled",
        "eq_profile.high_pass_mode",
        True,
    ),
    (
        _async_set_default_volume_global,
        "async_set_default_volume_global",
        "default_volume_global",
        50,
    ),
    (_async_set_maximum_volume, "async_set_maximum_volume", "maximum_volume", 80),
    (_async_set_volume_step, "async_set_volume_step", "volume_step", 5),
    (
        _async_set_fixed_volume_level,
        "async_set_fixed_volume_level",
        "fixed_volume_level",
        25,
    ),
    (_async_set_balance, "async_set_balance", "eq_profile.balance", 10),
    (
        _async_set_auto_detect_placement,
        "async_set_auto_detect_placement",
        "auto_detect_placement",
        False,
    ),
    (
        _async_set_wireless_rear_mode,
        "async_set_wireless_rear_mode",
        "wireless_rear_mode",
        "rearSurround",
    ),
]


@pytest.mark.parametrize(
    "setter, client_method, field_path, value",
    _SETTERS,
    ids=[params[2] for params in _SETTERS],
)
async def test_setter_publishes_optimistic_state(
    setter, client_method, field_path, value
) -> None:
    """Every writable select/switch/number entity should publish immediately.

    Covers the entities PR #30 did not touch (only subwoofer_preset/polarity,
    audio_polarity, sound_profile, and sub_enable_stereo got this fix there),
    closing the systemic gap where a write showed its new value, then
    flickered back to stale data until the next ~10s poll caught up.
    """
    coordinator = _coordinator_with_local_updates()
    coordinator.client = SimpleNamespace(**{client_method: AsyncMock()})

    await setter(coordinator, value)

    assert _get_field(coordinator.data, field_path) == value
    assert getattr(coordinator.client, client_method).await_count == 1
    assert coordinator.async_apply_local_change.call_count == 1


@pytest.mark.parametrize(
    (
        "setter",
        "client_method",
        "wire_key",
        "field_path",
        "requested",
        "applied",
    ),
    [
        (
            _async_set_treble_amount,
            "async_set_treble_amount",
            "trebleAmount",
            "eq_profile.treble_amount",
            1.4,
            1.5,
        ),
        (
            _async_set_desk_mode_db,
            "async_set_desk_mode_db",
            "deskModeSetting",
            "eq_profile.desk_mode_setting",
            -3.6,
            -3.5,
        ),
        (
            _async_set_wall_mode_db,
            "async_set_wall_mode_db",
            "wallModeSetting",
            "eq_profile.wall_mode_setting",
            -3.6,
            -3.5,
        ),
        (
            _async_set_high_pass_frequency,
            "async_set_high_pass_frequency",
            "highPassModeFreq",
            "eq_profile.high_pass_frequency",
            67.5,
            70.0,
        ),
        (
            _async_set_sub_out_low_pass_frequency,
            "async_set_sub_out_low_pass_frequency",
            "subOutLPFreq",
            "eq_profile.sub_out_low_pass_frequency",
            57.5,
            60.0,
        ),
    ],
)
async def test_eq_number_publishes_representable_value(
    setter,
    client_method: str,
    wire_key: str,
    field_path: str,
    requested: float,
    applied: float,
) -> None:
    """Optimistic EQ state should match the value encoded by the client."""
    coordinator = _coordinator_with_local_updates()
    coordinator.client = SimpleNamespace(
        **{
            client_method: AsyncMock(
                return_value={wire_key: applied, "subwooferPreset": "custom"}
            )
        }
    )

    await setter(coordinator, requested)

    assert _get_field(coordinator.data, field_path) == applied
    assert getattr(coordinator.client, client_method).await_count == 1
    assert coordinator.async_apply_local_change.call_count == 1


@pytest.mark.parametrize(
    ("enabled", "coordinator_count", "applied_profile", "expected_count"),
    [
        (True, 0, {"subwooferCount": 2}, 2),
        (True, 0, {"subwooferOut": True, "subwooferCount": 1}, 1),
        (False, 2, {"subwooferCount": 0}, 0),
    ],
)
async def test_subwoofer_enabled_publishes_client_profile(
    enabled: bool,
    coordinator_count: int,
    applied_profile: dict[str, object],
    expected_count: int,
) -> None:
    """Optimistic subwoofer state should come from the fresh client profile."""
    coordinator = _coordinator_with_local_updates()
    assert coordinator.data.eq_profile is not None
    coordinator.data = replace(
        coordinator.data,
        eq_profile=replace(
            coordinator.data.eq_profile,
            subwoofer_out=not enabled,
            subwoofer_count=coordinator_count,
        ),
    )
    coordinator.client = SimpleNamespace(
        async_set_subwoofer_enabled=AsyncMock(return_value=applied_profile)
    )

    await _async_set_subwoofer_enabled(coordinator, enabled)

    profile = coordinator.data.eq_profile
    assert profile is not None
    assert profile.subwoofer_out is enabled
    assert profile.subwoofer_count == expected_count
    coordinator.client.async_set_subwoofer_enabled.assert_awaited_once_with(enabled)
    assert coordinator.async_apply_local_change.call_count == 1


async def test_source_volume_publishes_only_the_touched_source() -> None:
    """Setting one source's startup volume must not disturb the others."""
    coordinator = _coordinator_with_local_updates()
    coordinator.client = SimpleNamespace(
        async_set_default_volume_for_source=AsyncMock()
    )
    original_by_source = dict(coordinator.data.default_volume_by_source)
    assert "wifi" in original_by_source

    await _async_set_source_volume(coordinator, "wifi", 45)

    updated = coordinator.data.default_volume_by_source
    assert updated["wifi"] == 45
    for source, value in original_by_source.items():
        if source != "wifi":
            assert updated[source] == value


@pytest.mark.parametrize("auto_detect_placement", [True, None])
async def test_wall_mounted_requires_confirmed_manual_placement(
    auto_detect_placement: bool | None,
) -> None:
    """Only a confirmed off state allows a manual placement write."""
    coordinator = _coordinator_with_local_updates()
    coordinator.data = replace(
        coordinator.data, auto_detect_placement=auto_detect_placement
    )
    coordinator.client = SimpleNamespace(async_set_wall_mounted=AsyncMock())

    with pytest.raises(ServiceValidationError, match="auto-detect placement"):
        await _async_set_wall_mounted(coordinator, True)

    coordinator.client.async_set_wall_mounted.assert_not_awaited()
    coordinator.async_apply_local_change.assert_not_called()


async def test_wall_mounted_publishes_client_profile() -> None:
    """With auto-detect off, the speaker-confirmed value is published."""
    coordinator = _coordinator_with_local_updates()
    coordinator.data = replace(coordinator.data, auto_detect_placement=False)
    coordinator.client = SimpleNamespace(
        async_set_wall_mounted=AsyncMock(return_value={"wallMounted": True})
    )

    await _async_set_wall_mounted(coordinator, True)

    coordinator.client.async_set_wall_mounted.assert_awaited_once_with(True)
    assert coordinator.data.eq_profile is not None
    assert coordinator.data.eq_profile.wall_mounted is True


async def test_switch_entity_keeps_optimistic_value_through_stale_refresh(
    hass,
) -> None:
    """A top-level switch write should survive its immediate stale refresh."""
    coordinator = _real_coordinator(hass)
    coordinator.client = SimpleNamespace(
        async_set_startup_tone_enabled=AsyncMock(),
        async_refresh=AsyncMock(return_value=deepcopy(TEST_SNAPSHOT)),
    )
    _refresh_immediately(coordinator)
    description = next(item for item in SWITCHES if item.key == "startup_tone")
    entity = KefSwitch(coordinator, description)

    await entity.async_turn_off()

    assert entity.is_on is False
    coordinator.client.async_set_startup_tone_enabled.assert_awaited_once_with(False)
    assert coordinator._local_changes == {"startup_tone_enabled": False}


async def test_eq_number_entity_keeps_normalized_value_through_stale_refresh(
    hass,
) -> None:
    """A nested EQ write should preserve its representable value on refresh."""
    coordinator = _real_coordinator(hass)
    coordinator.client = SimpleNamespace(
        async_set_treble_amount=AsyncMock(return_value={"trebleAmount": 1.5}),
        async_refresh=AsyncMock(return_value=deepcopy(TEST_SNAPSHOT)),
    )
    _refresh_immediately(coordinator)
    description = next(item for item in NUMBERS if item.key == "treble_amount")
    entity = KefNumber(coordinator, description)

    await entity.async_set_native_value(1.4)

    assert entity.native_value == 1.5
    assert coordinator.data.eq_profile is not None
    assert coordinator._local_changes == {"eq_profile": coordinator.data.eq_profile}


async def test_source_number_keeps_copied_map_through_stale_refresh(hass) -> None:
    """A source-volume write should keep its copied map on immediate refresh."""
    coordinator = _real_coordinator(hass)
    coordinator.client = SimpleNamespace(
        async_set_default_volume_for_source=AsyncMock(),
        async_refresh=AsyncMock(return_value=deepcopy(TEST_SNAPSHOT)),
    )
    _refresh_immediately(coordinator)
    original_by_source = dict(coordinator.data.default_volume_by_source)
    entity = KefSourceVolumeNumber(
        coordinator,
        "wifi",
        original_by_source["wifi"],
    )

    await entity.async_set_native_value(45)

    assert entity.native_value == 45
    assert coordinator.data.default_volume_by_source["wifi"] == 45
    for source, value in original_by_source.items():
        if source != "wifi":
            assert coordinator.data.default_volume_by_source[source] == value
