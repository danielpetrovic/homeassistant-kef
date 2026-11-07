"""Select platform for KEF configuration controls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BASS_EXTENSION_OPTIONS,
    CABLE_MODE_OPTIONS,
    DOMAIN,
    DTS_VIRTUAL_X_LAYOUT,
    EQ_BUTTON_OPTIONS,
    FAVOURITE_BUTTON_OPTIONS,
    IR_CODE_OPTIONS,
    MASTER_CHANNEL_OPTIONS,
    POLARITY_OPTIONS,
    PREFERRED_VIRTUALISER_OPTIONS,
    SOUND_PROFILE_OPTIONS,
    STANDBY_MODE_OPTIONS,
    STREAMING_QUALITY_OPTIONS,
    SUBWOOFER_PRESET_OPTIONS,
    WAKE_SOURCE_OPTIONS,
    WIRELESS_REAR_MODE_OPTIONS,
    model_supports_feature,
)
from .coordinator import KefConfigEntry, KefCoordinator
from .entity import KefEntity, apply_eq_profile_change, get_initialized_client
from .kef_client.const import model_has_subwoofer_preset_values
from .models import KefBackend, KefSnapshot

# Ask HA to serialize action calls within this platform for each entry.
PARALLEL_UPDATES = 1


async def _async_set_standby_mode(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the standby mode."""
    client = get_initialized_client(coordinator)
    await client.async_set_standby_mode(value)
    coordinator.async_apply_local_change(standby_mode=value)


async def _async_set_wake_source(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the wake source."""
    client = get_initialized_client(coordinator)
    await client.async_set_wake_source(value)
    coordinator.async_apply_local_change(wake_source=value)


async def _async_set_master_channel(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the master channel assignment."""
    client = get_initialized_client(coordinator)
    await client.async_set_master_channel(value)
    coordinator.async_apply_local_change(master_channel=value)


async def _async_set_cable_mode(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the cable mode."""
    client = get_initialized_client(coordinator)
    await client.async_set_cable_mode(value)
    coordinator.async_apply_local_change(cable_mode=value)


async def _async_set_bass_extension(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the EQ bass extension."""
    client = get_initialized_client(coordinator)
    await client.async_set_bass_extension(value)
    apply_eq_profile_change(coordinator, bass_extension=value)


async def _async_set_remote_ir_code(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the IR remote code set."""
    client = get_initialized_client(coordinator)
    await client.async_set_remote_ir_code(value)
    coordinator.async_apply_local_change(remote_ir_code=value)


async def _async_set_streaming_quality(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the Airable streaming quality."""
    client = get_initialized_client(coordinator)
    await client.async_set_streaming_quality(value)
    coordinator.async_apply_local_change(streaming_quality=value)


async def _async_set_favourite_button(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the favourite button action."""
    client = get_initialized_client(coordinator)
    await client.async_set_favourite_button_action(value)
    coordinator.async_apply_local_change(favourite_button=value)


async def _async_set_eq_button_1(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the first EQ button action."""
    client = get_initialized_client(coordinator)
    await client.async_set_eq_button_action(1, value)
    coordinator.async_apply_local_change(eq_button_1=value)


async def _async_set_eq_button_2(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the second EQ button action."""
    client = get_initialized_client(coordinator)
    await client.async_set_eq_button_action(2, value)
    coordinator.async_apply_local_change(eq_button_2=value)


async def _async_set_subwoofer_polarity(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the subwoofer polarity."""
    client = get_initialized_client(coordinator)
    await client.async_set_subwoofer_polarity(value)
    apply_eq_profile_change(coordinator, subwoofer_polarity=value)


async def _async_set_audio_polarity(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the main speaker audio polarity."""
    client = get_initialized_client(coordinator)
    await client.async_set_audio_polarity(value)
    apply_eq_profile_change(coordinator, audio_polarity=value)


async def _async_set_subwoofer_preset(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the subwoofer model preset."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_subwoofer_preset(
        value, coordinator.data.device.model
    )
    changes: dict[str, object] = {"subwoofer_preset": value}
    if applied is not None:
        changes["subwoofer_gain"] = applied["gain"]
        changes["sub_out_low_pass_frequency"] = applied["lowpass"]
        changes["high_pass_frequency"] = applied["highpass"]
    apply_eq_profile_change(coordinator, **changes)


async def _async_set_sound_profile(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the sound profile preset."""
    client = get_initialized_client(coordinator)
    await client.async_set_sound_profile(value)
    apply_eq_profile_change(coordinator, sound_profile=value)


async def _async_set_preferred_virtualiser(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Prefer DTS Virtual:X or Dolby Surround."""
    client = get_initialized_client(coordinator)
    prefer_virtual_x = value == "dts_virtual_x"
    await client.async_set_prefer_virtual_x(prefer_virtual_x)
    coordinator.async_apply_local_change(prefer_virtual_x=prefer_virtual_x)


def _preferred_virtualiser_value(data: KefSnapshot) -> str | None:
    """Return the preferred virtualiser as a select option key."""
    if data.prefer_virtual_x is None:
        return None
    return "dts_virtual_x" if data.prefer_virtual_x else "dolby"


async def _async_set_wireless_rear_mode(
    coordinator: KefCoordinator,
    value: str,
) -> None:
    """Set the surround channel layout."""
    client = get_initialized_client(coordinator)
    await client.async_set_wireless_rear_mode(value)
    coordinator.async_apply_local_change(wireless_rear_mode=value)


@dataclass(frozen=True, kw_only=True)
class KefSelectDescription(SelectEntityDescription):
    """Describe a KEF configuration select."""

    value_fn: Callable[[KefSnapshot], str | None]
    async_set_fn: Callable[[KefCoordinator, str], Awaitable[None]]
    options_map: dict[str, str]
    model_feature: str | None = None
    model_available_fn: Callable[[str], bool] = lambda _model: True


SELECTS: tuple[KefSelectDescription, ...] = (
    KefSelectDescription(
        key="standby_mode",
        translation_key="standby_mode",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.standby_mode,
        async_set_fn=_async_set_standby_mode,
        options_map=STANDBY_MODE_OPTIONS,
    ),
    KefSelectDescription(
        key="wake_source",
        translation_key="wake_source",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.wake_source,
        async_set_fn=_async_set_wake_source,
        options_map=WAKE_SOURCE_OPTIONS,
    ),
    KefSelectDescription(
        key="master_channel",
        translation_key="master_channel",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.master_channel,
        async_set_fn=_async_set_master_channel,
        options_map=MASTER_CHANNEL_OPTIONS,
        model_feature="stereo_pair",
    ),
    KefSelectDescription(
        key="cable_mode",
        translation_key="cable_mode",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.cable_mode,
        async_set_fn=_async_set_cable_mode,
        options_map=CABLE_MODE_OPTIONS,
        model_feature="cable_mode",
    ),
    KefSelectDescription(
        key="bass_extension",
        translation_key="bass_extension",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.bass_extension if data.eq_profile else None
        ),
        async_set_fn=_async_set_bass_extension,
        options_map=BASS_EXTENSION_OPTIONS,
    ),
    KefSelectDescription(
        key="remote_ir_code",
        translation_key="remote_ir_code",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.remote_ir_code,
        async_set_fn=_async_set_remote_ir_code,
        options_map=IR_CODE_OPTIONS,
    ),
    KefSelectDescription(
        key="streaming_quality",
        translation_key="streaming_quality",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.streaming_quality,
        async_set_fn=_async_set_streaming_quality,
        options_map=STREAMING_QUALITY_OPTIONS,
    ),
    KefSelectDescription(
        key="favourite_button",
        translation_key="favourite_button",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.favourite_button,
        async_set_fn=_async_set_favourite_button,
        options_map=FAVOURITE_BUTTON_OPTIONS,
    ),
    KefSelectDescription(
        key="eq_button_1",
        translation_key="eq_button_1",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.eq_button_1,
        async_set_fn=_async_set_eq_button_1,
        options_map=EQ_BUTTON_OPTIONS,
        model_feature="eq_button",
    ),
    KefSelectDescription(
        key="eq_button_2",
        translation_key="eq_button_2",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.eq_button_2,
        async_set_fn=_async_set_eq_button_2,
        options_map=EQ_BUTTON_OPTIONS,
        model_feature="eq_button",
    ),
    KefSelectDescription(
        key="subwoofer_polarity",
        translation_key="subwoofer_polarity",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.subwoofer_polarity if data.eq_profile else None
        ),
        async_set_fn=_async_set_subwoofer_polarity,
        options_map=POLARITY_OPTIONS,
    ),
    KefSelectDescription(
        key="audio_polarity",
        translation_key="audio_polarity",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.audio_polarity if data.eq_profile else None
        ),
        async_set_fn=_async_set_audio_polarity,
        options_map=POLARITY_OPTIONS,
    ),
    KefSelectDescription(
        key="subwoofer_preset",
        translation_key="subwoofer_preset",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.subwoofer_preset if data.eq_profile else None
        ),
        async_set_fn=_async_set_subwoofer_preset,
        options_map=SUBWOOFER_PRESET_OPTIONS,
        model_available_fn=model_has_subwoofer_preset_values,
    ),
    KefSelectDescription(
        key="sound_profile",
        translation_key="sound_profile",
        value_fn=lambda data: (
            data.eq_profile.sound_profile if data.eq_profile else None
        ),
        async_set_fn=_async_set_sound_profile,
        options_map=SOUND_PROFILE_OPTIONS,
        model_feature="xio",
    ),
    KefSelectDescription(
        key="preferred_virtualiser",
        translation_key="preferred_virtualiser",
        entity_category=EntityCategory.CONFIG,
        value_fn=_preferred_virtualiser_value,
        async_set_fn=_async_set_preferred_virtualiser,
        options_map=PREFERRED_VIRTUALISER_OPTIONS,
        model_feature="xio",
    ),
)

# Reported by an XIO once it runs firmware with wireless surround.
SURROUND_SELECTS: tuple[KefSelectDescription, ...] = (
    KefSelectDescription(
        key="wireless_rear_mode",
        translation_key="wireless_rear_mode",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.wireless_rear_mode,
        async_set_fn=_async_set_wireless_rear_mode,
        options_map=WIRELESS_REAR_MODE_OPTIONS,
        model_feature="xio",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KefConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KEF configuration selects."""
    coordinator = entry.runtime_data
    if coordinator.data.device.backend is not KefBackend.MODERN:
        return

    known_selects: set[str] = set()

    @callback
    def _async_add_selects() -> None:
        """Discover optional selects when the speaker starts reporting them."""
        data = coordinator.data
        entities = [
            KefSelect(coordinator, description)
            for description in (*SELECTS, *SURROUND_SELECTS)
            if description.key not in known_selects
            and description.value_fn(data) is not None
            and description.model_available_fn(data.device.model)
            and model_supports_feature(data.device.model, description.model_feature)
        ]
        known_selects.update(entity.entity_description.key for entity in entities)
        if entities:
            async_add_entities(entities)

    _async_add_selects()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_selects))


class KefSelect(KefEntity, CoordinatorEntity[KefCoordinator], SelectEntity):
    """Coordinator-backed KEF configuration select."""

    entity_description: KefSelectDescription

    def __init__(
        self,
        coordinator: KefCoordinator,
        description: KefSelectDescription,
    ) -> None:
        """Initialize the select."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.data.device.unique_id}_{description.key}"
        )

    @property
    def options(self) -> list[str]:
        """Offer wake inputs the speaker has, respecting ECO standby."""
        options = self.entity_description.options_map
        data = self.coordinator.data
        if self.entity_description.key == "wake_source":
            allowed = {"wakeup_default"}
            if data.standby_mode != "standby_20mins":
                allowed.update(data.source_list)
            return [label for raw, label in options.items() if raw in allowed]
        if self.entity_description.key == "standby_mode" and data.wake_source not in (
            None, "wakeup_default",
        ):
            return [label for raw, label in options.items() if raw != "standby_20mins"]
        if (
            self.entity_description.key == "wireless_rear_mode"
            and data.prefer_virtual_x
        ):
            # DTS Virtual:X renders 7.1.4 whatever layout the speaker has stored.
            return [DTS_VIRTUAL_X_LAYOUT]
        return list(options.values())

    @property
    def current_option(self) -> str | None:
        """Return the current friendly option."""
        value = self.entity_description.value_fn(self.coordinator.data)
        if value is None:
            return None
        if (
            self.entity_description.key == "wireless_rear_mode"
            and self.coordinator.data.prefer_virtual_x
        ):
            return DTS_VIRTUAL_X_LAYOUT
        return self.entity_description.options_map.get(value, value)

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        reverse_map = {
            friendly: raw
            for raw, friendly in self.entity_description.options_map.items()
        }
        raw_value = reverse_map.get(option, option)
        key = self.entity_description.key
        data = self.coordinator.data
        if key == "wireless_rear_mode" and data.prefer_virtual_x:
            # The displayed DTS layout is rendered, not a writable rear mode.
            return
        if (
            key == "standby_mode"
            and raw_value == "standby_20mins"
            and data.wake_source not in (None, "wakeup_default")
        ) or (
            key == "wake_source"
            and raw_value != "wakeup_default"
            and data.standby_mode == "standby_20mins"
        ):
            raise HomeAssistantError(
                "ECO standby does not support a second wake-up source",
                translation_domain=DOMAIN,
                translation_key="eco_wake_source",
            )
        if key == "wake_source" and raw_value not in {
            raw for raw, label in self.entity_description.options_map.items()
            if label in self.options
        }:
            raise HomeAssistantError(
                "This wake-up source is not supported by the speaker",
                translation_domain=DOMAIN,
                translation_key="unsupported_wake_source",
            )
        await self.async_call_kef(
            lambda: self.entity_description.async_set_fn(
                self.coordinator, raw_value
            )
        )
        await self.coordinator.async_request_refresh()
