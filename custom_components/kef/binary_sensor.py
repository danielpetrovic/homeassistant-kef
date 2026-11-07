"""Binary sensor platform for KEF."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KefConfigEntry, KefCoordinator
from .entity import KefEntity
from .models import KefSurroundDevice

# The coordinator owns all reads; these entities send no actions.
PARALLEL_UPDATES = 0

_POSITION_LABELS = {
    "stereoRear": "Rear speaker",
    "leftRear": "Left rear speaker",
    "rightRear": "Right rear speaker",
    "subwoofer": "Subwoofer",
    "leftSubwoofer": "Left subwoofer",
    "rightSubwoofer": "Right subwoofer",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KefConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KEF binary sensors."""
    coordinator = entry.runtime_data
    surround_mode_added = False
    surround_mode_registered = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{coordinator.data.device.unique_id}_surround_mode"
    ) is not None
    known_devices: set[str] = set()

    @callback
    def _async_add_surround_entities() -> None:
        """Add the wireless surround entities once the speaker reports them."""
        nonlocal surround_mode_added
        data = coordinator.data
        entities: list[BinarySensorEntity] = []
        # Only a speaker that has been used as a rear speaker gets the flag. Every
        # speaker on current firmware reports it, mostly as off, and the XIO
        # transmits to its rear speakers without being one.
        if (
            not surround_mode_added
            and (data.surround_mode or surround_mode_registered)
            and data.device.model.upper() != "XIO"
        ):
            surround_mode_added = True
            entities.append(KefSurroundModeBinarySensor(coordinator))
        for device in data.surround_devices:
            if device.key not in known_devices:
                known_devices.add(device.key)
                entities.append(
                    KefSurroundDeviceConnectedBinarySensor(coordinator, device)
                )
        if entities:
            async_add_entities(entities)

    _async_add_surround_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_surround_entities))


class KefSurroundModeBinarySensor(
    KefEntity, CoordinatorEntity[KefCoordinator], BinarySensorEntity
):
    """Whether this speaker is used as a wireless surround receiver."""

    _attr_translation_key = "surround_mode"

    def __init__(self, coordinator: KefCoordinator) -> None:
        """Initialize the binary sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        self._attr_unique_id = f"{coordinator.data.device.unique_id}_surround_mode"

    @property
    def is_on(self) -> bool | None:
        """Return whether surround mode is on."""
        return self.coordinator.data.surround_mode


class KefSurroundDeviceConnectedBinarySensor(
    KefEntity, CoordinatorEntity[KefCoordinator], BinarySensorEntity
):
    """Whether a paired wireless surround speaker is connected to the XIO."""

    _attr_translation_key = "surround_device_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: KefCoordinator, device: KefSurroundDevice
    ) -> None:
        """Initialize the binary sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        self._device_key = device.key
        self._attr_unique_id = (
            f"{coordinator.data.device.unique_id}_surround_{device.key}_connected"
        )
        self._attr_translation_placeholders = {
            "speaker": _POSITION_LABELS.get(device.position or "", "Speaker")
        }

    def _device(self) -> KefSurroundDevice | None:
        """Return the paired device from the latest snapshot."""
        for device in self.coordinator.data.surround_devices:
            if device.key == self._device_key:
                return device
        return None

    @property
    def available(self) -> bool:
        """Return whether the speaker still lists this paired device."""
        return super().available and self._device() is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether the paired speaker is connected."""
        device = self._device()
        return None if device is None else device.connected
