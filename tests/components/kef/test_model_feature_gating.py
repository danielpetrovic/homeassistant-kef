"""Model-specific configuration entity tests for KEF."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kef import _async_cleanup_optional_entities
from custom_components.kef.const import DOMAIN
from custom_components.kef.kef_client.models import KefBackend, KefEqProfile
from custom_components.kef.number import async_setup_entry as async_setup_numbers
from custom_components.kef.select import async_setup_entry as async_setup_selects
from custom_components.kef.sensor import async_setup_entry as async_setup_sensors
from custom_components.kef.switch import async_setup_entry as async_setup_switches
from tests.conftest import EQ_PROFILE_V2_VALUE, TEST_SNAPSHOT


async def _entity_keys_for_model(model: str) -> tuple[set[str], set[str], set[str]]:
    """Return number, switch, and select keys created for a modern model."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.device.model = model
    # v2-only fields (sound_profile, subwoofer_out, ...) are never populated by
    # the v1 kefEqProfile parse path TEST_SNAPSHOT uses; every real modern
    # speaker capable of these gated features reports v2, so use it here too.
    snapshot.eq_profile = KefEqProfile.from_modern_value(EQ_PROFILE_V2_VALUE)
    coordinator = Mock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    coordinator.config_entry = SimpleNamespace(domain="kef")
    coordinator.hass = Mock()
    entry = SimpleNamespace(
        runtime_data=coordinator,
        async_on_unload=lambda unload: None,
    )

    numbers = []
    switches = []
    selects = []
    await async_setup_numbers(Mock(), entry, numbers.extend)
    await async_setup_switches(Mock(), entry, switches.extend)
    await async_setup_selects(Mock(), entry, selects.extend)
    return (
        {
            entity.entity_description.key
            for entity in numbers
            if hasattr(entity, "entity_description")
        },
        {entity.entity_description.key for entity in switches},
        {entity.entity_description.key for entity in selects},
    )


async def _sensor_keys_for_model(
    model: str,
    *,
    diagnostics: bool,
    backend: KefBackend = KefBackend.MODERN,
) -> set[str]:
    """Return sensor keys created for a modern model and option set."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.device.model = model
    snapshot.device.backend = backend
    coordinator = Mock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    coordinator.config_entry = SimpleNamespace(domain="kef")
    coordinator.hass = Mock()
    entry = SimpleNamespace(
        runtime_data=coordinator,
        options={"enable_diagnostics": diagnostics},
        async_on_unload=lambda unload: None,
    )
    sensors = []

    await async_setup_sensors(Mock(), entry, sensors.extend)

    return {entity.entity_description.key for entity in sensors}


@pytest.mark.parametrize("model", ["LSX2LT", "LSXIILT"])
async def test_lsx_ii_lt_hides_only_known_unsupported_controls(model: str) -> None:
    """Both observed model identifiers should produce the same capability UI."""
    numbers, switches, selects = await _entity_keys_for_model(model)

    unsupported_switches = {
        "front_led",
        "top_panel",
        "top_panel_led",
        "top_panel_standby_led",
        "sub_enable_stereo",
        "auto_detect_placement",
        "wall_mounted",
    }
    assert unsupported_switches.isdisjoint(switches)
    assert {"desk_mode", "wall_mode", "standby_led"} <= switches
    assert {"balance", "desk_mode_db", "wall_mode_db"} <= numbers
    assert "cable_mode" not in selects
    assert {"eq_button_1", "eq_button_2", "preferred_virtualiser"}.isdisjoint(selects)
    assert "master_channel" in selects
    assert "subwoofer_preset" in selects


async def test_xio_keeps_top_panel_controls_and_hides_pair_controls() -> None:
    """The soundbar should expose its physical panel without stereo-pair settings."""
    numbers, switches, selects = await _entity_keys_for_model("XIO")

    assert {
        "top_panel",
        "top_panel_led",
        "top_panel_standby_led",
        "auto_detect_placement",
        "wall_mounted",
    } <= switches
    assert {
        "front_led",
        "desk_mode",
        "usb_charging",
        "wall_mode",
        "sub_enable_stereo",
        "standby_led",
    }.isdisjoint(switches)
    assert {"balance", "desk_mode_db", "wall_mode_db"}.isdisjoint(numbers)
    assert {"master_channel", "cable_mode"}.isdisjoint(selects)
    assert {
        "eq_button_1",
        "eq_button_2",
        "sound_profile",
        "subwoofer_preset",
        "preferred_virtualiser",
    } <= selects


@pytest.mark.parametrize("model", ["LS60", "LS60W"])
async def test_ls60_hides_desk_mode_but_keeps_unverified_controls_visible(
    model: str,
) -> None:
    """Hide only the confirmed-unsupported desk_mode; leave the rest visible."""
    numbers, switches, selects = await _entity_keys_for_model(model)

    assert "desk_mode" not in switches
    assert "desk_mode_db" not in numbers
    assert {"balance", "wall_mode_db"} <= numbers
    assert {"wall_mode", "front_led", "standby_led", "sub_enable_stereo"} <= switches
    assert {
        "top_panel",
        "top_panel_led",
        "top_panel_standby_led",
        "auto_detect_placement",
        "wall_mounted",
    }.isdisjoint(switches)
    assert {"master_channel", "cable_mode"} <= selects
    assert {
        "eq_button_1",
        "eq_button_2",
        "sound_profile",
        "preferred_virtualiser",
    }.isdisjoint(selects)
    assert "subwoofer_preset" not in selects


@pytest.mark.parametrize("model", ["LS50W2", "LS50WII"])
async def test_ls50_wireless_ii_keeps_top_panel_controls(model: str) -> None:
    """LS50 Wireless II supports top-panel locking in its speaker preferences."""
    _numbers, switches, selects = await _entity_keys_for_model(model)

    assert {"top_panel", "top_panel_led", "top_panel_standby_led"} <= switches
    assert "sub_enable_stereo" in switches
    assert "standby_led" in switches
    assert {"auto_detect_placement", "wall_mounted"}.isdisjoint(switches)
    assert {
        "eq_button_1",
        "eq_button_2",
        "sound_profile",
        "preferred_virtualiser",
    }.isdisjoint(selects)
    assert "subwoofer_preset" not in selects


async def test_unknown_models_keep_all_reported_controls() -> None:
    """A new model should default to the values actually reported by its API."""
    numbers, switches, selects = await _entity_keys_for_model("FUTURE")

    assert {
        "front_led",
        "top_panel",
        "desk_mode",
        "wall_mode",
        "sub_enable_stereo",
        "standby_led",
        "auto_detect_placement",
        "wall_mounted",
    } <= switches
    assert {"balance", "desk_mode_db", "wall_mode_db"} <= numbers
    assert {"master_channel", "cable_mode"} <= selects
    assert {
        "eq_button_1",
        "eq_button_2",
        "sound_profile",
        "preferred_virtualiser",
    } <= selects
    assert "subwoofer_preset" not in selects


async def test_xio_audio_sensors_follow_model_and_diagnostics_gates() -> None:
    """XIO audio sensors should be absent from verified unsupported models."""
    primary = {
        "audio_codec",
        "audio_virtualizer",
        "audio_sample_rate",
        "room_calibration",
        "calibration_adjustment",
    }
    diagnostics = {
        "audio_codec_raw",
        "audio_source_channels",
        "audio_playback_channels",
    }

    xio_default = await _sensor_keys_for_model("XIO", diagnostics=False)
    xio_diagnostics = await _sensor_keys_for_model("XIO", diagnostics=True)
    lsx_diagnostics = await _sensor_keys_for_model("LSXII", diagnostics=True)
    future_diagnostics = await _sensor_keys_for_model("FUTURE", diagnostics=True)
    legacy_diagnostics = await _sensor_keys_for_model(
        "KEF Legacy",
        diagnostics=True,
        backend=KefBackend.LEGACY,
    )

    assert primary <= xio_default
    assert diagnostics.isdisjoint(xio_default)
    assert primary | diagnostics <= xio_diagnostics
    assert (primary | diagnostics).isdisjoint(lsx_diagnostics)
    assert primary | diagnostics <= future_diagnostics
    assert (primary | diagnostics).isdisjoint(legacy_diagnostics)


async def test_subwoofer_switches_follow_reported_profile_values() -> None:
    """Writable subwoofer controls should exist when the EQ profile reports them."""
    profiles = [
        deepcopy(TEST_SNAPSHOT.eq_profile),
        KefEqProfile.from_modern_value(EQ_PROFILE_V2_VALUE),
    ]

    for profile in profiles:
        snapshot = deepcopy(TEST_SNAPSHOT)
        snapshot.eq_profile = profile
        coordinator = Mock()
        coordinator.data = snapshot
        coordinator.last_update_success = True
        coordinator.config_entry = SimpleNamespace(domain="kef")
        coordinator.hass = Mock()
        entry = SimpleNamespace(runtime_data=coordinator)
        switches = []

        await async_setup_switches(Mock(), entry, switches.extend)

        keys = {entity.entity_description.key for entity in switches}
        assert {"subwoofer", "kw1_adapter"} <= keys


async def test_cleanup_removes_only_model_unsupported_registry_entries(hass) -> None:
    """An upgrade should retire gated controls without touching supported ones."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.device.model = "XIO"
    coordinator = SimpleNamespace(data=snapshot)
    entry = MockConfigEntry(domain=DOMAIN, title="XIO")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    unique_id_prefix = f"{snapshot.device.unique_id}_"

    entries = {
        "obsolete_binary": registry.async_get_or_create(
            Platform.BINARY_SENSOR, DOMAIN, f"{unique_id_prefix}legacy_eq_state",
            config_entry=entry,
        ),
        "front_led": registry.async_get_or_create(
            Platform.SWITCH,
            DOMAIN,
            f"{unique_id_prefix}front_led",
            config_entry=entry,
        ),
        "top_panel": registry.async_get_or_create(
            Platform.SWITCH,
            DOMAIN,
            f"{unique_id_prefix}top_panel",
            config_entry=entry,
        ),
        "cable_mode": registry.async_get_or_create(
            Platform.SELECT,
            DOMAIN,
            f"{unique_id_prefix}cable_mode",
            config_entry=entry,
        ),
        "standby_mode": registry.async_get_or_create(
            Platform.SELECT,
            DOMAIN,
            f"{unique_id_prefix}standby_mode",
            config_entry=entry,
        ),
        "balance": registry.async_get_or_create(
            Platform.NUMBER,
            DOMAIN,
            f"{unique_id_prefix}balance",
            config_entry=entry,
        ),
        "desk_mode_db": registry.async_get_or_create(
            Platform.NUMBER,
            DOMAIN,
            f"{unique_id_prefix}desk_mode_db",
            config_entry=entry,
        ),
        "audio_codec": registry.async_get_or_create(
            Platform.SENSOR,
            DOMAIN,
            f"{unique_id_prefix}audio_codec",
            config_entry=entry,
        ),
        "audio_codec_raw": registry.async_get_or_create(
            Platform.SENSOR,
            DOMAIN,
            f"{unique_id_prefix}audio_codec_raw",
            config_entry=entry,
        ),
    }

    await _async_cleanup_optional_entities(hass, entry, coordinator)

    assert registry.async_get(entries["obsolete_binary"].entity_id) is None
    assert registry.async_get(entries["front_led"].entity_id) is None
    assert registry.async_get(entries["cable_mode"].entity_id) is None
    assert registry.async_get(entries["balance"].entity_id) is None
    assert registry.async_get(entries["desk_mode_db"].entity_id) is None
    assert registry.async_get(entries["top_panel"].entity_id) is not None
    assert registry.async_get(entries["standby_mode"].entity_id) is not None
    assert registry.async_get(entries["audio_codec"].entity_id) is not None
    assert registry.async_get(entries["audio_codec_raw"].entity_id) is None


async def test_cleanup_removes_xio_audio_sensors_from_legacy_devices(hass) -> None:
    """Legacy devices should not retain permanently unavailable XIO sensors."""
    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.device.backend = KefBackend.LEGACY
    snapshot.device.model = "KEF Legacy"
    coordinator = SimpleNamespace(data=snapshot)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="KEF Legacy",
        options={"enable_diagnostics": True},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    unique_id_prefix = f"{snapshot.device.unique_id}_"
    audio_codec = registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{unique_id_prefix}audio_codec",
        config_entry=entry,
    )
    audio_codec_raw = registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{unique_id_prefix}audio_codec_raw",
        config_entry=entry,
    )
    speaker_status = registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{unique_id_prefix}speaker_status",
        config_entry=entry,
    )
    start_calibration = registry.async_get_or_create(
        Platform.BUTTON,
        DOMAIN,
        f"{unique_id_prefix}start_calibration",
        config_entry=entry,
    )
    subwoofer_preset = registry.async_get_or_create(
        Platform.SELECT,
        DOMAIN,
        f"{unique_id_prefix}subwoofer_preset",
        config_entry=entry,
    )

    await _async_cleanup_optional_entities(hass, entry, coordinator)

    assert registry.async_get(audio_codec.entity_id) is None
    assert registry.async_get(audio_codec_raw.entity_id) is None
    assert registry.async_get(start_calibration.entity_id) is None
    assert registry.async_get(subwoofer_preset.entity_id) is None
    assert registry.async_get(speaker_status.entity_id) is not None


@pytest.mark.parametrize(
    ("model", "expect_button"),
    [
        ("XIO", True),
        ("LSXII", False),
        ("LS60W", False),
        ("FUTURE", True),
    ],
)
async def test_calibration_button_is_xio_only(
    model: str, expect_button: bool
) -> None:
    """The start-calibration button should only appear for XIO (and unknown models)."""
    from custom_components.kef.button import async_setup_entry as async_setup_buttons

    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.device.model = model
    coordinator = Mock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    coordinator.config_entry = SimpleNamespace(domain="kef")
    coordinator.hass = Mock()
    entry = SimpleNamespace(runtime_data=coordinator)

    buttons = []
    await async_setup_buttons(Mock(), entry, buttons.extend)

    assert bool(buttons) is expect_button
