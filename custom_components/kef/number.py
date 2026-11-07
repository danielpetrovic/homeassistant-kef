"""Number platform for KEF configuration controls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import WAKE_SOURCE_OPTIONS, model_supports_feature
from .coordinator import KefConfigEntry, KefCoordinator
from .entity import KefEntity, apply_eq_profile_change, get_initialized_client
from .models import KefBackend, KefSnapshot

# Ask HA to serialize action calls within this platform for each entry.
PARALLEL_UPDATES = 1


async def _async_set_default_volume_global(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the global startup volume."""
    client = get_initialized_client(coordinator)
    await client.async_set_default_volume_global(round(value))
    coordinator.async_apply_local_change(default_volume_global=round(value))


async def _async_set_maximum_volume(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the maximum volume."""
    client = get_initialized_client(coordinator)
    await client.async_set_maximum_volume(round(value))
    coordinator.async_apply_local_change(maximum_volume=round(value))


async def _async_set_volume_step(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the volume step."""
    client = get_initialized_client(coordinator)
    await client.async_set_volume_step(round(value))
    coordinator.async_apply_local_change(volume_step=round(value))


async def _async_set_wireless_rear_gain(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the wireless rear speaker gain."""
    client = get_initialized_client(coordinator)
    await client.async_set_wireless_rear_gain(value)
    coordinator.async_apply_local_change(wireless_rear_gain=value)


async def _async_set_fixed_volume_level(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the fixed volume level."""
    client = get_initialized_client(coordinator)
    await client.async_set_fixed_volume_level(round(value))
    coordinator.async_apply_local_change(fixed_volume_level=round(value))


async def _async_set_balance(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set EQ balance."""
    client = get_initialized_client(coordinator)
    await client.async_set_balance(round(value))
    apply_eq_profile_change(coordinator, balance=round(value))


async def _async_set_treble_amount(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set EQ treble amount."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_treble_amount(value)
    apply_eq_profile_change(
        coordinator,
        treble_amount=float(applied["trebleAmount"]),
    )


async def _async_set_subwoofer_gain(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set EQ subwoofer gain."""
    client = get_initialized_client(coordinator)
    await client.async_set_subwoofer_gain(round(value))
    apply_eq_profile_change(
        coordinator, subwoofer_gain=round(value), subwoofer_preset="custom"
    )


async def _async_set_high_pass_frequency(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set EQ high-pass frequency."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_high_pass_frequency(value)
    apply_eq_profile_change(
        coordinator,
        high_pass_frequency=float(applied["highPassModeFreq"]),
        subwoofer_preset=str(applied.get("subwooferPreset") or "custom"),
    )


async def _async_set_sub_out_low_pass_frequency(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the subwoofer output low-pass crossover frequency."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_sub_out_low_pass_frequency(value)
    apply_eq_profile_change(
        coordinator,
        sub_out_low_pass_frequency=float(applied["subOutLPFreq"]),
        subwoofer_preset=str(applied.get("subwooferPreset") or "custom"),
    )


async def _async_set_desk_mode_db(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the desk mode attenuation."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_desk_mode_db(value)
    apply_eq_profile_change(
        coordinator,
        desk_mode_setting=float(applied["deskModeSetting"]),
    )


async def _async_set_wall_mode_db(
    coordinator: KefCoordinator,
    value: float,
) -> None:
    """Set the wall mode attenuation."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_wall_mode_db(value)
    apply_eq_profile_change(
        coordinator,
        wall_mode_setting=float(applied["wallModeSetting"]),
    )


async def _async_set_source_volume(
    coordinator: KefCoordinator,
    source: str,
    value: float,
) -> None:
    """Set the startup volume for a single source."""
    client = get_initialized_client(coordinator)
    await client.async_set_default_volume_for_source(source, round(value))
    updated_by_source = {
        **coordinator.data.default_volume_by_source,
        source: round(value),
    }
    coordinator.async_apply_local_change(default_volume_by_source=updated_by_source)


def _friendly_source_name(source: str) -> str:
    """Return a UI-friendly source label."""
    return WAKE_SOURCE_OPTIONS.get(source, source.replace("_", " ").title())


@dataclass(frozen=True, kw_only=True)
class KefNumberDescription(NumberEntityDescription):
    """Describe a KEF configuration number."""

    value_fn: Callable[[KefSnapshot], int | float | None]
    async_set_fn: Callable[[KefCoordinator, float], Awaitable[None]]
    model_feature: str | None = None


NUMBERS: tuple[KefNumberDescription, ...] = (
    KefNumberDescription(
        key="default_volume_global",
        translation_key="default_volume_global",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        value_fn=lambda data: data.default_volume_global,
        async_set_fn=_async_set_default_volume_global,
    ),
    KefNumberDescription(
        key="maximum_volume",
        translation_key="maximum_volume",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        value_fn=lambda data: data.maximum_volume,
        async_set_fn=_async_set_maximum_volume,
    ),
    KefNumberDescription(
        key="volume_step",
        translation_key="volume_step",
        entity_category=EntityCategory.CONFIG,
        native_min_value=1,
        native_max_value=10,
        native_step=1,
        value_fn=lambda data: data.volume_step,
        async_set_fn=_async_set_volume_step,
    ),
    KefNumberDescription(
        key="fixed_volume_level",
        translation_key="fixed_volume_level",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        value_fn=lambda data: data.fixed_volume_level,
        async_set_fn=_async_set_fixed_volume_level,
    ),
    KefNumberDescription(
        key="balance",
        translation_key="balance",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-30,
        native_max_value=30,
        native_step=1,
        value_fn=lambda data: data.eq_profile.balance if data.eq_profile else None,
        async_set_fn=_async_set_balance,
        model_feature="stereo_pair",
    ),
    KefNumberDescription(
        key="treble_amount",
        translation_key="treble_amount",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="dB",
        native_min_value=-3.0,
        native_max_value=3.0,
        native_step=0.25,
        value_fn=lambda data: (
            data.eq_profile.treble_amount if data.eq_profile else None
        ),
        async_set_fn=_async_set_treble_amount,
    ),
    KefNumberDescription(
        key="subwoofer_gain",
        translation_key="subwoofer_gain",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="dB",
        native_min_value=-10,
        native_max_value=10,
        native_step=1,
        value_fn=lambda data: (
            data.eq_profile.subwoofer_gain if data.eq_profile else None
        ),
        async_set_fn=_async_set_subwoofer_gain,
    ),
    KefNumberDescription(
        key="high_pass_frequency",
        translation_key="high_pass_frequency",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="Hz",
        native_min_value=50.0,
        native_max_value=120.0,
        native_step=5.0,
        value_fn=lambda data: (
            data.eq_profile.high_pass_frequency if data.eq_profile else None
        ),
        async_set_fn=_async_set_high_pass_frequency,
    ),
    KefNumberDescription(
        key="sub_out_low_pass_frequency",
        translation_key="sub_out_low_pass_frequency",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="Hz",
        native_min_value=40.0,
        native_max_value=250.0,
        native_step=5.0,
        value_fn=lambda data: (
            data.eq_profile.sub_out_low_pass_frequency if data.eq_profile else None
        ),
        async_set_fn=_async_set_sub_out_low_pass_frequency,
    ),
    KefNumberDescription(
        key="wireless_rear_gain",
        translation_key="wireless_rear_gain",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-10.0,
        native_max_value=10.0,
        native_step=0.5,
        value_fn=lambda data: (
            data.wireless_rear_gain if data.wireless_rear_mode is not None else None
        ),
        async_set_fn=_async_set_wireless_rear_gain,
        model_feature="xio",
    ),
    KefNumberDescription(
        key="desk_mode_db",
        translation_key="desk_mode_db",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="dB",
        native_min_value=-10.0,
        native_max_value=0.0,
        native_step=0.5,
        value_fn=lambda data: (
            data.eq_profile.desk_mode_setting if data.eq_profile else None
        ),
        async_set_fn=_async_set_desk_mode_db,
        model_feature="desk_mode",
    ),
    KefNumberDescription(
        key="wall_mode_db",
        translation_key="wall_mode_db",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="dB",
        native_min_value=-10.0,
        native_max_value=0.0,
        native_step=0.5,
        value_fn=lambda data: (
            data.eq_profile.wall_mode_setting if data.eq_profile else None
        ),
        async_set_fn=_async_set_wall_mode_db,
        model_feature="wall_mode",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KefConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KEF configuration numbers."""
    coordinator = entry.runtime_data
    if coordinator.data.device.backend is not KefBackend.MODERN:
        return

    known_numbers: set[str] = set()

    @callback
    def _async_add_numbers() -> None:
        """Discover optional controls when firmware starts reporting their values."""
        entities = [
            KefNumber(coordinator, description)
            for description in NUMBERS
            if description.key not in known_numbers
            and description.value_fn(coordinator.data) is not None
            and model_supports_feature(
                coordinator.data.device.model, description.model_feature
            )
        ]
        known_numbers.update(entity.entity_description.key for entity in entities)
        if entities:
            async_add_entities(entities)

    _async_add_numbers()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_numbers))
    entities: list[NumberEntity] = []
    for source, value in coordinator.data.default_volume_by_source.items():
        entities.append(
            KefSourceVolumeNumber(
                coordinator,
                source,
                value,
            )
        )
    async_add_entities(entities)


class KefNumber(KefEntity, CoordinatorEntity[KefCoordinator], NumberEntity):
    """Coordinator-backed KEF configuration number."""

    entity_description: KefNumberDescription

    def __init__(
        self,
        coordinator: KefCoordinator,
        description: KefNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        eq_profile = coordinator.data.eq_profile
        if eq_profile is not None and eq_profile.api_version == "v1":
            if description.key == "treble_amount":
                description = replace(description, native_step=0.375)
            elif description.key == "high_pass_frequency":
                description = replace(description, native_max_value=100.0)
            elif description.key == "sub_out_low_pass_frequency":
                description = replace(description, native_step=10.0)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.data.device.unique_id}_{description.key}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the current numeric value."""
        value = self.entity_description.value_fn(self.coordinator.data)
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        await self.async_call_kef(
            lambda: self.entity_description.async_set_fn(self.coordinator, value)
        )
        await self.coordinator.async_request_refresh()


class KefSourceVolumeNumber(KefEntity, CoordinatorEntity[KefCoordinator], NumberEntity):
    """Coordinator-backed source-specific KEF startup volume number."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(
        self,
        coordinator: KefCoordinator,
        source: str,
        initial_value: int,
    ) -> None:
        """Initialize the source startup volume number."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        self._source = source
        self._initial_value = initial_value
        self._attr_unique_id = (
            f"{coordinator.data.device.unique_id}_default_volume_{source}"
        )
        self._attr_translation_key = "source_startup_volume"
        self._attr_translation_placeholders = {"source": _friendly_source_name(source)}

    @property
    def available(self) -> bool:
        """Return whether the number is available."""
        return (
            self.coordinator.last_update_success
            and self._source in self.coordinator.data.default_volume_by_source
        )

    @property
    def native_value(self) -> float | None:
        """Return the current source-specific startup volume."""
        value = self.coordinator.data.default_volume_by_source.get(
            self._source,
            self._initial_value,
        )
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the source-specific startup volume."""
        await self.async_call_kef(
            lambda: _async_set_source_volume(self.coordinator, self._source, value)
        )
        await self.coordinator.async_request_refresh()
