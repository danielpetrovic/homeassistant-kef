"""Wireless surround reads and entities for the XIO."""

from __future__ import annotations

import contextlib
from copy import deepcopy
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession, web
from homeassistant.const import CONF_HOST, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kef import _async_cleanup_optional_entities
from custom_components.kef.api import ModernKefClient
from custom_components.kef.const import CONF_BACKEND, DOMAIN, PROBE_PATHS
from custom_components.kef.coordinator import KefCoordinator
from custom_components.kef.exceptions import KefResponseError
from custom_components.kef.models import KefSurroundDevice
from tests.conftest import (
    DEVICE_NAME_VALUE,
    MAC_VALUE,
    MODEL_CODE_VALUE,
    MUTE_VALUE,
    PLAY_MODE_VALUE,
    SOURCE_VALUE,
    SPEAKER_STATUS_VALUE,
    TEST_HOST,
    TEST_SNAPSHOT,
    VERSION_VALUE,
    VOLUME_VALUE,
)
from tests.http_server import local_server

pytestmark = pytest.mark.usefixtures("socket_enabled")

# Shape observed on an XIO with firmware 1.5.160 and one paired LSX II.
DEVICE_LIST = [
    {
        "modelMacAddress": "8417150352C4",
        "rxDevice": {
            "isConnected": True,
            "firmwareVersion": "1",
            "channelMode": "surround",
            "devicePosition": "stereoRear",
            "macAddress": "8417152d11d2",
        },
        "devicePosition": "stereoRear",
        "modelName": "LSX II",
        "modelIpAddress": "lsxii-8417150352c4.local",
        "connectionType": "kw2",
    }
]

SURROUND_RESPONSES = {
    PROBE_PATHS["surround_mode"]: {"type": "bool_", "bool_": True},
    PROBE_PATHS["surround_device_list"]: {
        "type": "surroundModeDeviceList", "surroundModeDeviceList": DEVICE_LIST,
    },
    PROBE_PATHS["wireless_rear_mode"]: {
        "type": "kefDspWirelessRearMode", "kefDspWirelessRearMode": "rearSurround",
    },
    PROBE_PATHS["wireless_rear_gain"]: {"type": "double_", "double_": 5.0},
    PROBE_PATHS["surround_master_channel"]: {
        "type": "kefMasterChannelMode", "kefMasterChannelMode": "left",
    },
}


def test_surround_device_parses_a_paired_speaker() -> None:
    """The KW2 receiver address identifies the paired speaker."""
    devices = KefSurroundDevice.from_modern_list(DEVICE_LIST)

    assert devices == (
        KefSurroundDevice(
            key="8417152d11d2",
            position="stereoRear",
            model_name="LSX II",
            connection_type="kw2",
            connected=True,
        ),
    )


def test_surround_device_falls_back_to_the_speaker_address() -> None:
    """Entries without a receiver block still keep a stable identity."""
    devices = KefSurroundDevice.from_modern_list(
        [{"modelMacAddress": "8417150352C4", "devicePosition": "subwoofer"}]
    )

    assert devices == (
        KefSurroundDevice(key="8417150352c4", position="subwoofer"),
    )
    assert devices[0].connected is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        "text",
        [None, "x", {}, {"rxDevice": {}}, {"rxDevice": {"macAddress": ""}}],
    ],
    ids=["missing", "object", "text", "unusable-entries"],
)
def test_surround_device_list_ignores_unusable_payloads(value) -> None:
    """Unknown firmware shapes must not break a refresh."""
    assert KefSurroundDevice.from_modern_list(value) == ()


def _responses(release_text: str) -> dict:
    return {
        PROBE_PATHS["device_name"]: DEVICE_NAME_VALUE,
        PROBE_PATHS["version"]: VERSION_VALUE,
        PROBE_PATHS["release_text"]: {"type": "string_", "string_": release_text},
        PROBE_PATHS["mac"]: MAC_VALUE,
        PROBE_PATHS["model_code"]: MODEL_CODE_VALUE,
        PROBE_PATHS["speaker_status"]: SPEAKER_STATUS_VALUE,
        PROBE_PATHS["source"]: SOURCE_VALUE,
        PROBE_PATHS["volume"]: VOLUME_VALUE,
        PROBE_PATHS["mute"]: MUTE_VALUE,
        PROBE_PATHS["play_mode"]: PLAY_MODE_VALUE,
        **SURROUND_RESPONSES,
    }


async def _refresh(
    monkeypatch, hass, release_text: str, extra: dict | None = None, *, asked=None
):
    responses = _responses(release_text) | (extra or {})

    async def fake_get_item(self, path, *, roles="value"):
        if asked is not None:
            asked.append(path)
        if responses.get(path) is None:
            raise KefResponseError("Unsupported path")
        return responses[path]

    monkeypatch.setattr(ModernKefClient, "_get_path_item", fake_get_item)
    client = ModernKefClient(TEST_HOST, async_get_clientsession(hass))
    return await client.async_refresh()


async def test_xio_refresh_reads_the_surround_state(monkeypatch, hass) -> None:
    """The XIO snapshot carries mode, paired devices, rear mode and gain."""
    snapshot = await _refresh(monkeypatch, hass, "XIO_V15160")

    assert snapshot.device.model == "XIO"
    assert snapshot.surround_mode is True
    assert [device.key for device in snapshot.surround_devices] == ["8417152d11d2"]
    assert snapshot.wireless_rear_mode == "rearSurround"
    assert snapshot.wireless_rear_gain == 5.0
    # The orientation lives on the rear speaker, not on the soundbar.
    assert snapshot.surround_master_channel is None


async def test_xio_without_surround_firmware_reports_nothing(
    monkeypatch, hass
) -> None:
    """Older XIO firmware has no surround paths, so every value stays unknown."""
    snapshot = await _refresh(
        monkeypatch,
        hass,
        "XIO_V14135",
        {path: None for path in SURROUND_RESPONSES},
    )

    assert snapshot.surround_mode is None
    assert snapshot.surround_devices == ()
    assert snapshot.wireless_rear_mode is None
    assert snapshot.wireless_rear_gain is None


async def test_other_models_only_read_the_receiver_flag(monkeypatch, hass) -> None:
    """Speakers other than the XIO are not asked for the transmitter values."""
    asked: list[str] = []

    snapshot = await _refresh(monkeypatch, hass, "LSXII_V30137", asked=asked)

    assert snapshot.surround_mode is True
    assert snapshot.surround_master_channel == "left"
    assert snapshot.surround_devices == ()
    assert snapshot.wireless_rear_mode is None
    assert snapshot.wireless_rear_gain is None
    assert set(SURROUND_RESPONSES) & set(asked) == {
        PROBE_PATHS["surround_mode"],
        PROBE_PATHS["surround_master_channel"],
    }


def _xio_snapshot(**changes):
    snapshot = deepcopy(TEST_SNAPSHOT)
    snapshot.device = replace(snapshot.device, model="XIO")
    for name, value in changes.items():
        setattr(snapshot, name, value)
    return snapshot


async def _setup(hass, snapshot):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=snapshot.device.device_name,
        unique_id=snapshot.device.unique_id,
        data={CONF_HOST: TEST_HOST, CONF_BACKEND: snapshot.device.backend},
    )
    entry.add_to_hass(hass)

    async def refresh(coordinator):
        coordinator.async_set_updated_data(snapshot)

    with patch.object(KefCoordinator, "async_config_entry_first_refresh", refresh):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity_id(hass, platform: str, suffix: str) -> str | None:
    unique_id = f"{TEST_SNAPSHOT.device.unique_id}_{suffix}"
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)


async def test_surround_entities_report_the_xio_state(hass) -> None:
    """A surround-capable XIO exposes the speaker and the rear values."""
    snapshot = _xio_snapshot(
        surround_mode=False,
        surround_devices=KefSurroundDevice.from_modern_list(DEVICE_LIST),
        wireless_rear_mode="rearSurround",
        wireless_rear_gain=5.0,
    )
    await _setup(hass, snapshot)

    connected = _entity_id(hass, "binary_sensor", "surround_8417152d11d2_connected")
    rear_mode = _entity_id(hass, "select", "wireless_rear_mode")
    rear_gain = _entity_id(hass, "number", "wireless_rear_gain")
    assert None not in (connected, rear_mode, rear_gain)
    assert hass.states.get(connected).state == STATE_ON
    assert hass.states.get(rear_mode).state == "7.1.2"
    assert hass.states.get(rear_mode).attributes["options"] == ["5.1.2", "7.1.2"]
    gain = hass.states.get(rear_gain)
    assert gain.state == "5.0"
    limits = (gain.attributes["min"], gain.attributes["max"], gain.attributes["step"])
    assert limits == (-10.0, 10.0, 0.5)
    assert _entity_id(hass, "sensor", "wireless_rear_gain") is None
    assert er.async_get(hass).async_get(connected).original_name == (
        "SUR: Rear speaker connected"
    )
    # The soundbar transmits; it is never a surround receiver itself.
    assert _entity_id(hass, "binary_sensor", "surround_mode") is None


async def test_older_xio_firmware_creates_no_surround_entities(hass) -> None:
    """No surround paths, no entities."""
    await _setup(hass, _xio_snapshot(wireless_rear_gain=0.0))

    for platform, suffix in (
        ("binary_sensor", "surround_mode"),
        ("select", "wireless_rear_mode"),
        ("number", "wireless_rear_gain"),
    ):
        assert _entity_id(hass, platform, suffix) is None


async def test_speakers_that_are_not_rear_speakers_get_no_surround_mode(hass) -> None:
    """A speaker that reports no or an off flag gets nothing, until it turns on."""
    off = deepcopy(TEST_SNAPSHOT)
    off.surround_mode = False
    entry = await _setup(hass, off)
    assert _entity_id(hass, "binary_sensor", "surround_mode") is None

    entry.runtime_data.async_set_updated_data(
        replace(entry.runtime_data.data, surround_mode=True)
    )
    await hass.async_block_till_done()
    mode = _entity_id(hass, "binary_sensor", "surround_mode")
    assert hass.states.get(mode).state == STATE_ON

    off = replace(entry.runtime_data.data, surround_mode=False)

    async def refresh(coordinator):
        coordinator.async_set_updated_data(off)

    with patch.object(KefCoordinator, "async_config_entry_first_refresh", refresh):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert hass.states.get(mode).state == STATE_OFF


async def test_speakers_without_the_flag_create_no_surround_entities(hass) -> None:
    """A speaker that does not report the receiver flag gets nothing."""
    await _setup(hass, deepcopy(TEST_SNAPSHOT))

    assert _entity_id(hass, "binary_sensor", "surround_mode") is None


async def test_a_rear_speaker_reports_that_it_is_a_surround_receiver(hass) -> None:
    """A speaker used as a rear speaker reports it, without the XIO values."""
    rear = deepcopy(TEST_SNAPSHOT)
    rear.surround_mode = True
    rear.surround_master_channel = "right"
    await _setup(hass, rear)

    mode = _entity_id(hass, "binary_sensor", "surround_mode")
    assert hass.states.get(mode).state == STATE_ON
    channel = _entity_id(hass, "sensor", "surround_master_channel")
    assert hass.states.get(channel).state == "right"
    assert _entity_id(hass, "select", "wireless_rear_mode") is None
    assert _entity_id(hass, "number", "wireless_rear_gain") is None


async def test_surround_entities_appear_after_a_firmware_update(hass) -> None:
    """An XIO updated while Home Assistant runs gains the entities without a reload."""
    entry = await _setup(hass, _xio_snapshot(prefer_virtual_x=None))
    assert _entity_id(hass, "select", "wireless_rear_mode") is None
    assert _entity_id(hass, "select", "preferred_virtualiser") is None

    coordinator = entry.runtime_data
    coordinator.async_set_updated_data(
        replace(
            coordinator.data,
            surround_devices=KefSurroundDevice.from_modern_list(DEVICE_LIST),
            wireless_rear_mode="surround",
            wireless_rear_gain=3.0,
            prefer_virtual_x=False,
        )
    )
    await hass.async_block_till_done()

    assert _entity_id(hass, "binary_sensor", "surround_8417152d11d2_connected")
    assert _entity_id(hass, "select", "wireless_rear_mode")
    virtualiser = _entity_id(hass, "select", "preferred_virtualiser")
    assert virtualiser is not None
    assert hass.states.get(virtualiser).state == "Dolby Surround"
    gain = _entity_id(hass, "number", "wireless_rear_gain")
    assert gain is not None
    assert hass.states.get(gain).state == "3.0"

    coordinator.async_set_updated_data(
        replace(coordinator.data, wireless_rear_gain=4.0)
    )
    await hass.async_block_till_done()
    assert hass.states.get(gain).state == "4.0"


@pytest.mark.parametrize(
    ("model", "platform", "suffix"),
    [
        ("XIO", "binary_sensor", "surround_8417152d11d2_connected"),
        ("LSX II", "binary_sensor", "surround_mode"),
        ("LSX II", "sensor", "surround_master_channel"),
    ],
)
async def test_cleanup_preserves_surround_registry_settings(
    hass, model, platform, suffix
) -> None:
    """A missing optional read must not erase a remembered sensor's settings."""
    snapshot = _xio_snapshot()
    snapshot.device = replace(snapshot.device, model=model)
    entry = await _setup(hass, snapshot)
    registry = er.async_get(hass)
    registered = registry.async_get_or_create(
        platform, DOMAIN, f"{snapshot.device.unique_id}_{suffix}", config_entry=entry
    )
    custom = registry.async_update_entity(
        registered.entity_id,
        new_entity_id=f"{platform}.my_surround_sensor",
        name="My surround sensor",
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    await _async_cleanup_optional_entities(hass, entry, entry.runtime_data)

    assert registry.async_get(custom.entity_id) == custom


async def test_connected_sensor_follows_the_device_list(hass) -> None:
    """A speaker that is no longer paired shows as unavailable, not disconnected."""
    snapshot = _xio_snapshot(
        surround_devices=KefSurroundDevice.from_modern_list(DEVICE_LIST),
    )
    entry = await _setup(hass, snapshot)
    connected = _entity_id(hass, "binary_sensor", "surround_8417152d11d2_connected")

    entry.runtime_data.async_set_updated_data(
        replace(entry.runtime_data.data, surround_devices=())
    )
    await hass.async_block_till_done()
    assert hass.states.get(connected).state == STATE_UNAVAILABLE

    entry.runtime_data.async_set_updated_data(
        replace(
            entry.runtime_data.data,
            surround_devices=(
                KefSurroundDevice(
                    key="8417152d11d2", position="stereoRear", connected=False
                ),
            ),
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get(connected).state == STATE_OFF


@contextlib.asynccontextmanager
async def _entry_with_local_speaker(hass, monkeypatch, snapshot, status):
    """Set up an entry whose client talks to a local server answering `status`."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=snapshot.device.device_name,
        unique_id=snapshot.device.unique_id,
        data={CONF_HOST: TEST_HOST, CONF_BACKEND: snapshot.device.backend},
    )
    entry.add_to_hass(hass)

    async def refresh(coordinator):
        coordinator.async_set_updated_data(snapshot)

    monkeypatch.setattr(
        KefCoordinator, "_async_update_data", AsyncMock(return_value=snapshot)
    )
    with patch.object(KefCoordinator, "async_config_entry_first_refresh", refresh):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    captured = []

    async def handler(request):
        if request.method == "GET":
            return web.json_response([{"type": "string_", "string_": "none"}])
        captured.append(await request.json())
        return web.json_response({}, status=status)

    try:
        async with local_server(handler) as port, ClientSession() as session:
            entry.runtime_data.client = ModernKefClient("127.0.0.1", session, port=port)
            entry.runtime_data.async_request_refresh = AsyncMock()
            yield captured
    finally:
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("status", [200, 503], ids=["accepted", "unavailable"])
async def test_rear_gain_is_written_as_a_double(hass, monkeypatch, status) -> None:
    """The slider posts the typed value and only an accepted write is kept."""
    snapshot = _xio_snapshot(wireless_rear_gain=5.0, wireless_rear_mode="surround")
    async with _entry_with_local_speaker(hass, monkeypatch, snapshot, status) as sent:
        entity_id = _entity_id(hass, "number", "wireless_rear_gain")
        action = hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": 6.5},
            blocking=True,
        )
        if status == 200:
            await action
            assert float(hass.states.get(entity_id).state) == 6.5
        else:
            with pytest.raises(HomeAssistantError):
                await action
            assert float(hass.states.get(entity_id).state) == 5.0
        assert sent == [
            {
                "path": PROBE_PATHS["wireless_rear_gain"],
                "role": "value",
                "value": {"type": "double_", "double_": 6.5},
            }
        ]


@pytest.mark.parametrize("status", [200, 503], ids=["accepted", "unavailable"])
async def test_channel_layout_is_written_as_the_rear_mode(
    hass, monkeypatch, status
) -> None:
    """The select posts the raw rear mode and only an accepted write is kept."""
    snapshot = _xio_snapshot(wireless_rear_gain=5.0, wireless_rear_mode="surround")
    async with _entry_with_local_speaker(hass, monkeypatch, snapshot, status) as sent:
        entity_id = _entity_id(hass, "select", "wireless_rear_mode")
        assert hass.states.get(entity_id).state == "5.1.2"
        action = hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "7.1.2"},
            blocking=True,
        )
        if status == 200:
            await action
            assert hass.states.get(entity_id).state == "7.1.2"
        else:
            with pytest.raises(HomeAssistantError):
                await action
            assert hass.states.get(entity_id).state == "5.1.2"
        assert sent == [
            {
                "path": PROBE_PATHS["wireless_rear_mode"],
                "role": "value",
                "value": {
                    "type": "kefDspWirelessRearMode",
                    "kefDspWirelessRearMode": "rearSurround",
                },
            }
        ]


@pytest.mark.parametrize(
    ("prefer_virtual_x", "current", "choice", "expected"),
    [(False, "Dolby Surround", "DTS Virtual:X", True),
     (True, "DTS Virtual:X", "Dolby Surround", False)],
    ids=["to_dts", "to_dolby"],
)
async def test_preferred_virtualiser_select_writes_the_flag(
    hass, monkeypatch, prefer_virtual_x, current, choice, expected
) -> None:
    """The select replaces the former switch and posts the same boolean flag."""
    snapshot = _xio_snapshot(prefer_virtual_x=prefer_virtual_x)
    async with _entry_with_local_speaker(hass, monkeypatch, snapshot, 200) as sent:
        entity_id = _entity_id(hass, "select", "preferred_virtualiser")
        state = hass.states.get(entity_id)
        assert state.state == current
        assert state.attributes["options"] == ["Dolby Surround", "DTS Virtual:X"]
        assert _entity_id(hass, "switch", "prefer_virtual_x") is None
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": choice},
            blocking=True,
        )
        assert hass.states.get(entity_id).state == choice
        assert len(sent) == 1
        assert sent[0]["value"]["bool_"] is expected


async def test_the_former_virtualiser_switch_is_removed(hass) -> None:
    """An entity registered by the earlier prefer-DTS switch does not linger."""
    snapshot = _xio_snapshot(prefer_virtual_x=False)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=snapshot.device.device_name,
        unique_id=snapshot.device.unique_id,
        data={CONF_HOST: TEST_HOST, CONF_BACKEND: snapshot.device.backend},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{snapshot.device.unique_id}_prefer_virtual_x",
        config_entry=entry,
    )

    async def refresh(coordinator):
        coordinator.async_set_updated_data(snapshot)

    with patch.object(KefCoordinator, "async_config_entry_first_refresh", refresh):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert registry.async_get(old.entity_id) is None


async def test_selecting_dts_rendered_layout_does_not_write(hass, monkeypatch) -> None:
    """The displayed DTS layout is not a writable rear-mode protocol value."""
    snapshot = _xio_snapshot(wireless_rear_mode="rearSurround", prefer_virtual_x=True)
    async with _entry_with_local_speaker(hass, monkeypatch, snapshot, 200) as sent:
        entity_id = _entity_id(hass, "select", "wireless_rear_mode")
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": entity_id, "option": "7.1.4"}, blocking=True,
        )
        assert sent == []
        assert hass.states.get(entity_id).state == "7.1.4"
        assert snapshot.wireless_rear_mode == "rearSurround"


async def test_channel_layout_shows_7_1_4_while_dts_virtual_x_is_preferred(
    hass,
) -> None:
    """DTS Virtual:X renders 7.1.4, so the select shows it and refuses other layouts."""
    snapshot = _xio_snapshot(wireless_rear_mode="rearSurround", prefer_virtual_x=False)
    entry = await _setup(hass, snapshot)
    entity_id = _entity_id(hass, "select", "wireless_rear_mode")
    assert hass.states.get(entity_id).state == "7.1.2"

    coordinator = entry.runtime_data
    coordinator.async_set_updated_data(
        replace(coordinator.data, prefer_virtual_x=True)
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "7.1.4"
    assert state.attributes["options"] == ["7.1.4"]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "5.1.2"},
            blocking=True,
        )

    # The stored layout comes back by itself with the Dolby processing.
    coordinator.async_set_updated_data(
        replace(coordinator.data, prefer_virtual_x=False)
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "7.1.2"
    assert state.attributes["options"] == ["5.1.2", "7.1.2"]
