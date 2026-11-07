"""Sensor platform for KEF."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .audio import audio_codec_value, audio_virtualizer_value
from .const import (
    CONF_ENABLE_DIAGNOSTICS,
    DEFAULT_ENABLE_DIAGNOSTICS,
    model_supports_feature,
)
from .coordinator import KefConfigEntry, KefCoordinator
from .entity import KefEntity
from .models import KefSnapshot

# The coordinator owns all reads; these entities send no actions.
PARALLEL_UPDATES = 0


def _room_calibration_value(data: KefSnapshot) -> str | None:
    """Return the room calibration status as a date, or a plain status string."""
    status = data.calibration_status
    if status is None:
        return None
    if status.is_calibrated is None:
        return None
    if status.is_calibrated is False:
        return "Not calibrated"
    if status.year and status.month and status.day:
        return f"{status.year}-{status.month:02d}-{status.day:02d}"
    return "Calibrated"


@dataclass(frozen=True, kw_only=True)
class KefSensorDescription(SensorEntityDescription):
    """Describe a KEF sensor."""

    value_fn: Callable[[KefSnapshot], Any]
    diagnostics_only: bool = False
    model_feature: str | None = None


SENSORS: tuple[KefSensorDescription, ...] = (
    KefSensorDescription(
        key="backend",
        translation_key="backend",
        device_class=SensorDeviceClass.ENUM,
        options=["modern", "legacy"],
        value_fn=lambda data: data.device.backend.value,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KefSensorDescription(
        key="speaker_status",
        translation_key="speaker_status",
        device_class=SensorDeviceClass.ENUM,
        options=["standby", "powerOn"],
        value_fn=lambda data: data.speaker_status,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KefSensorDescription(
        key="play_mode",
        translation_key="play_mode",
        value_fn=lambda data: data.play_mode,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KefSensorDescription(
        key="service_id",
        translation_key="service_id",
        value_fn=lambda data: data.playback.service_id if data.playback else None,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    KefSensorDescription(
        key="wifi_signal_level",
        translation_key="wifi_signal_level",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dBm",
        value_fn=lambda data: data.wifi_info.signal_level if data.wifi_info else None,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        value_fn=lambda data: data.wifi_info.ssid if data.wifi_info else None,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="wifi_frequency",
        translation_key="wifi_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="MHz",
        value_fn=lambda data: data.wifi_info.frequency if data.wifi_info else None,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="wifi_bssid",
        translation_key="wifi_bssid",
        value_fn=lambda data: data.wifi_info.bssid if data.wifi_info else None,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="network_ping",
        translation_key="network_ping",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="ms",
        value_fn=lambda data: data.network_ping_ms,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="network_stability",
        translation_key="network_stability",
        value_fn=lambda data: data.network_stability,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="speed_test_status",
        translation_key="speed_test_status",
        value_fn=lambda data: data.speed_test_status,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="speed_test_average_download",
        translation_key="speed_test_average_download",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Mbit/s",
        value_fn=lambda data: data.speed_test_average_download,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="speed_test_current_download",
        translation_key="speed_test_current_download",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Mbit/s",
        value_fn=lambda data: data.speed_test_current_download,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="speed_test_packet_loss",
        translation_key="speed_test_packet_loss",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        value_fn=lambda data: data.speed_test_packet_loss,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="alert_alarm_count",
        translation_key="alert_alarm_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.alert_alarm_count,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="alert_timer_count",
        translation_key="alert_timer_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.alert_timer_count,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="alert_snooze_time",
        translation_key="alert_snooze_time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="min",
        value_fn=lambda data: data.alert_snooze_minutes,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    KefSensorDescription(
        key="audio_codec",
        translation_key="audio_codec",
        value_fn=audio_codec_value,
        model_feature="xio",
    ),
    KefSensorDescription(
        key="audio_virtualizer",
        translation_key="audio_virtualizer",
        value_fn=audio_virtualizer_value,
        model_feature="xio",
    ),
    KefSensorDescription(
        key="audio_sample_rate",
        translation_key="audio_sample_rate",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Hz",
        value_fn=lambda data: (
            data.playback.sample_frequency if data.playback else None
        ),
        model_feature="xio",
    ),
    KefSensorDescription(
        key="audio_codec_raw",
        translation_key="audio_codec_raw",
        value_fn=lambda data: data.playback.codec if data.playback else None,
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        model_feature="xio",
    ),
    KefSensorDescription(
        key="audio_source_channels",
        translation_key="audio_source_channels",
        value_fn=lambda data: (
            data.playback.stream_channels if data.playback else None
        ),
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        model_feature="xio",
    ),
    KefSensorDescription(
        key="audio_playback_channels",
        translation_key="audio_playback_channels",
        value_fn=lambda data: (
            data.playback.audio_channels if data.playback else None
        ),
        diagnostics_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        model_feature="xio",
    ),
    KefSensorDescription(
        key="room_calibration",
        translation_key="room_calibration",
        value_fn=_room_calibration_value,
        model_feature="xio",
    ),
    KefSensorDescription(
        key="calibration_adjustment",
        translation_key="calibration_adjustment",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.calibration_result,
        model_feature="xio",
    ),
)

# The orientation a rear speaker was given in the pairing test of the KEF app.
SURROUND_RECEIVER_SENSORS: tuple[KefSensorDescription, ...] = (
    KefSensorDescription(
        key="surround_master_channel",
        translation_key="surround_master_channel",
        device_class=SensorDeviceClass.ENUM,
        options=["left", "right"],
        value_fn=lambda data: data.surround_master_channel,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KefConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KEF sensors."""
    coordinator = entry.runtime_data
    enable_diagnostics = entry.options.get(
        CONF_ENABLE_DIAGNOSTICS,
        DEFAULT_ENABLE_DIAGNOSTICS,
    )

    entities = []
    for description in SENSORS:
        if description.diagnostics_only and not enable_diagnostics:
            continue
        if not model_supports_feature(
            coordinator.data.device.model, description.model_feature
        ):
            continue
        entities.append(KefSensor(coordinator, description))
    async_add_entities(entities)

    receiver_added = False

    @callback
    def _async_add_surround_sensors() -> None:
        """Add the rear speaker sensors once the speaker reports them."""
        nonlocal receiver_added
        if receiver_added or coordinator.data.surround_master_channel is None:
            return
        receiver_added = True
        async_add_entities(
            KefSensor(coordinator, description)
            for description in SURROUND_RECEIVER_SENSORS
        )

    _async_add_surround_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_surround_sensors))


class KefSensor(KefEntity, CoordinatorEntity[KefCoordinator], SensorEntity):
    """Coordinator-backed KEF sensor."""

    entity_description: KefSensorDescription

    def __init__(
        self,
        coordinator: KefCoordinator,
        description: KefSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.data.device.unique_id}_{description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)
