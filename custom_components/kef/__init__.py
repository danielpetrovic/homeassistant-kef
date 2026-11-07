"""The KEF integration."""

from __future__ import annotations

from collections.abc import Mapping

# HA aliases voluptuous to Probatio at runtime from 2026.9. Static typing cannot
# follow the alias; only the service-schema argument needs a suppression.
import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import (
    AUTH_FAILURE_MESSAGE,
    CONF_ENABLE_DIAGNOSTICS,
    DEFAULT_ENABLE_DIAGNOSTICS,
    DOMAIN,
    model_supports_feature,
)
from .coordinator import KefConfigEntry, KefCoordinator
from .diagnostic_events import remove_entry_history
from .exceptions import KefAuthenticationRequiredError, KefError

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.UPDATE,
    Platform.TEXT,
    Platform.BUTTON,
]

ATTR_FIRMWARE_FILE_PATH = "file_path"
SERVICE_INSTALL_FIRMWARE_FILE = "install_firmware_file"

_ACTIVE_BINARY_SENSOR_ENTITY_KEYS: set[str] = {"surround_mode"}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register KEF actions independently of speaker availability."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: KefConfigEntry) -> bool:
    """Set up KEF from a config entry."""
    # Subscribe before network awaits so a new connection cannot be lost.
    reload_settings = (entry.data, entry.options, entry.title, entry.unique_id)

    async def async_reload_changed_settings(
        hass: HomeAssistant, updated_entry: KefConfigEntry,
    ) -> None:
        nonlocal reload_settings
        settings = (
            updated_entry.data, updated_entry.options,
            updated_entry.title, updated_entry.unique_id,
        )
        if settings == reload_settings:
            return
        reload_settings = settings
        await async_reload_entry(hass, updated_entry)

    entry.async_on_unload(entry.add_update_listener(async_reload_changed_settings))
    coordinator = KefCoordinator(hass, entry)
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    await _async_cleanup_optional_entities(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start_event_listener()
    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration-level services."""
    if hass.services.has_service(DOMAIN, SERVICE_INSTALL_FIRMWARE_FILE):
        return

    async def async_handle_install_firmware_file(call: ServiceCall) -> None:
        await _async_handle_install_firmware_file(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_INSTALL_FIRMWARE_FILE,
        async_handle_install_firmware_file,
        schema=vol.Schema(  # type: ignore[arg-type, unused-ignore]
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
                vol.Required(ATTR_FIRMWARE_FILE_PATH): cv.string,
            }
        ),
    )


async def _async_handle_install_firmware_file(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Upload a local firmware image through the selected KEF update entity."""
    entity_id = call.data[ATTR_ENTITY_ID]
    registry = er.async_get(hass)
    entity_entry = registry.async_get(entity_id)
    if (
        entity_entry is None
        or entity_entry.domain != Platform.UPDATE
        or entity_entry.platform != DOMAIN
        or entity_entry.config_entry_id is None
    ):
        raise ServiceValidationError(
            "Target must be a KEF firmware update entity", translation_domain=DOMAIN,
            translation_key="invalid_firmware_target",
        )

    config_entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
    coordinator = getattr(config_entry, "runtime_data", None)
    if config_entry is None or coordinator is None or coordinator.client is None:
        raise ServiceValidationError(
            "KEF config entry is not ready", translation_domain=DOMAIN,
            translation_key="entry_not_ready",
        )

    try:
        await coordinator.client.async_upload_firmware_update(
            call.data[ATTR_FIRMWARE_FILE_PATH]
        )
        await coordinator.async_request_refresh()
    except KefAuthenticationRequiredError as err:
        config_entry.async_start_reauth(hass)
        raise HomeAssistantError(
            AUTH_FAILURE_MESSAGE,
            translation_domain=DOMAIN,
            translation_key="authentication_required",
        ) from err
    except KefError as err:
        raise HomeAssistantError(
            str(err), translation_domain=DOMAIN,
            translation_key="command_failed",
            translation_placeholders={"error": str(err)},
        ) from err


async def async_unload_entry(hass: HomeAssistant, entry: KefConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_stop_event_listener()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: KefConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: KefConfigEntry) -> None:
    """Discard session diagnostics when the entry is deleted."""
    remove_entry_history(hass, entry.entry_id)


async def _async_cleanup_optional_entities(
    hass: HomeAssistant,
    entry: KefConfigEntry,
    coordinator: KefCoordinator,
) -> None:
    """Remove stale registry entries for optional or retired entities."""
    from .button import BUTTON_MODEL_FEATURES
    from .number import NUMBERS
    from .select import SELECTS
    from .switch import SWITCHES

    registry = er.async_get(hass)
    device_unique_id = coordinator.data.device.unique_id
    device_model = coordinator.data.device.model
    diagnostics_enabled = entry.options.get(
        CONF_ENABLE_DIAGNOSTICS,
        DEFAULT_ENABLE_DIAGNOSTICS,
    )
    xio_supported = model_supports_feature(
        device_model, "xio"
    )
    expected_sensor_keys = {
        "backend", "speaker_status", "play_mode", "surround_master_channel"
    }
    if diagnostics_enabled:
        expected_sensor_keys.update(
            {
                "service_id",
                "wifi_signal_level",
                "wifi_ssid",
                "wifi_frequency",
                "wifi_bssid",
                "network_ping",
                "network_stability",
                "speed_test_status",
                "speed_test_average_download",
                "speed_test_current_download",
                "speed_test_packet_loss",
                "alert_alarm_count",
                "alert_timer_count",
                "alert_snooze_time",
            }
        )
        if xio_supported:
            expected_sensor_keys.update(
                {
                    "audio_codec_raw",
                    "audio_source_channels",
                    "audio_playback_channels",
                }
            )
    if xio_supported:
        expected_sensor_keys.update(
            {
                "audio_codec",
                "audio_virtualizer",
                "audio_sample_rate",
                "room_calibration",
                "calibration_adjustment",
            }
        )
    expected_binary_sensor_keys = set(_ACTIVE_BINARY_SENSOR_ENTITY_KEYS)
    model_features_by_platform: dict[str, Mapping[str, str | None]] = {
        "button": BUTTON_MODEL_FEATURES,
        "select": {
            description.key: description.model_feature for description in SELECTS
        },
        "switch": {
            description.key: description.model_feature for description in SWITCHES
        },
        "number": {
            description.key: description.model_feature for description in NUMBERS
        },
    }
    selects_by_key = {description.key: description for description in SELECTS}

    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        platform = entity_entry.entity_id.split(".", 1)[0]
        unique_id = entity_entry.unique_id
        if platform in model_features_by_platform:
            if not unique_id.startswith(f"{device_unique_id}_"):
                continue
            key = unique_id.removeprefix(f"{device_unique_id}_")
            if platform == "switch" and key == "prefer_virtual_x":
                # Replaced by the preferred virtualiser select.
                registry.async_remove(entity_entry.entity_id)
                continue
            feature = model_features_by_platform[platform].get(key)
            select_unavailable = (
                platform == "select"
                and key in selects_by_key
                and not selects_by_key[key].model_available_fn(device_model)
            )
            if select_unavailable or (
                feature is not None
                and not model_supports_feature(device_model, feature)
            ):
                registry.async_remove(entity_entry.entity_id)
            continue

        if platform not in {"sensor", "binary_sensor"}:
            continue

        if not unique_id.startswith(f"{device_unique_id}_"):
            registry.async_remove(entity_entry.entity_id)
            continue

        key = unique_id.removeprefix(f"{device_unique_id}_")
        if platform == "sensor" and key not in expected_sensor_keys:
            registry.async_remove(entity_entry.entity_id)
        paired_surround_sensor = (
            xio_supported and key.startswith("surround_") and key.endswith("_connected")
        )
        if (
            platform == "binary_sensor"
            and key not in expected_binary_sensor_keys
            and not paired_surround_sensor
        ):
            registry.async_remove(entity_entry.entity_id)
