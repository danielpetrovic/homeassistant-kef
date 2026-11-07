"""Switch platform for KEF configuration controls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, model_supports_feature
from .coordinator import KefConfigEntry, KefCoordinator
from .entity import KefEntity, apply_eq_profile_change, get_initialized_client
from .models import KefBackend, KefSnapshot

# Ask HA to serialize action calls within this platform for each entry.
PARALLEL_UPDATES = 1


async def _async_set_startup_tone(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the startup tone state."""
    client = get_initialized_client(coordinator)
    await client.async_set_startup_tone_enabled(enabled)
    coordinator.async_apply_local_change(startup_tone_enabled=enabled)


async def _async_set_auto_switch_hdmi(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set HDMI auto switching."""
    client = get_initialized_client(coordinator)
    await client.async_set_auto_switch_hdmi_enabled(enabled)
    coordinator.async_apply_local_change(auto_switch_hdmi=enabled)


async def _async_set_standby_led(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the standby LED state."""
    client = get_initialized_client(coordinator)
    await client.async_set_standby_led_enabled(enabled)
    coordinator.async_apply_local_change(standby_led_enabled=enabled)


async def _async_set_front_led(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the front LED state."""
    client = get_initialized_client(coordinator)
    await client.async_set_front_led_enabled(enabled)
    coordinator.async_apply_local_change(front_led_enabled=enabled)


async def _async_set_top_panel(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the top-panel enabled state."""
    client = get_initialized_client(coordinator)
    await client.async_set_top_panel_enabled(enabled)
    coordinator.async_apply_local_change(top_panel_enabled=enabled)


async def _async_set_top_panel_led(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the active top-panel LED state."""
    client = get_initialized_client(coordinator)
    await client.async_set_top_panel_led_enabled(enabled)
    coordinator.async_apply_local_change(top_panel_led_enabled=enabled)


async def _async_set_top_panel_standby_led(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the standby top-panel LED state."""
    client = get_initialized_client(coordinator)
    await client.async_set_top_panel_standby_led_enabled(enabled)
    coordinator.async_apply_local_change(top_panel_standby_led_enabled=enabled)


async def _async_set_usb_charging(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the USB charging state."""
    client = get_initialized_client(coordinator)
    await client.async_set_usb_charging_enabled(enabled)
    coordinator.async_apply_local_change(usb_charging_enabled=enabled)


async def _async_set_startup_volume(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set whether startup volume is enabled."""
    client = get_initialized_client(coordinator)
    await client.async_set_startup_volume_enabled(enabled)
    coordinator.async_apply_local_change(startup_volume_enabled=enabled)


async def _async_set_per_input_startup_volume(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set whether per-input startup volume is enabled."""
    client = get_initialized_client(coordinator)
    await client.async_set_per_input_startup_volume_enabled(enabled)
    coordinator.async_apply_local_change(per_input_startup_volume_enabled=enabled)


async def _async_set_volume_limit(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set whether the volume limiter is enabled."""
    client = get_initialized_client(coordinator)
    await client.async_set_volume_limit_enabled(enabled)
    coordinator.async_apply_local_change(volume_limit_enabled=enabled)


async def _async_set_subwoofer_wake(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set wired subwoofer wake-on-startup."""
    client = get_initialized_client(coordinator)
    await client.async_set_subwoofer_wake_enabled(enabled)
    coordinator.async_apply_local_change(subwoofer_wake_enabled=enabled)


async def _async_set_kw1_wake(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set KW1 subwoofer wake-on-startup."""
    client = get_initialized_client(coordinator)
    await client.async_set_kw1_wake_enabled(enabled)
    coordinator.async_apply_local_change(kw1_wake_enabled=enabled)


async def _async_set_subwoofer_enabled(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Enable or disable subwoofer output."""
    client = get_initialized_client(coordinator)
    applied = await client.async_set_subwoofer_enabled(enabled)
    raw_count = applied.get("subwooferCount")
    subwoofer_count = (
        raw_count
        if isinstance(raw_count, int) and not isinstance(raw_count, bool)
        else None
    )
    raw_enabled = applied.get("subwooferOut")
    applied_enabled = (
        raw_enabled
        if isinstance(raw_enabled, bool)
        else subwoofer_count is not None and subwoofer_count > 0
    )
    apply_eq_profile_change(
        coordinator,
        subwoofer_out=applied_enabled,
        subwoofer_count=subwoofer_count,
    )


async def _async_set_kw1_adapter(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Enable or disable the KW1 wireless subwoofer adapter."""
    client = get_initialized_client(coordinator)
    await client.async_set_kw1_enabled(enabled)
    apply_eq_profile_change(coordinator, is_kw1=enabled)


async def _async_set_sub_enable_stereo(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Enable or disable dual-subwoofer stereo channel separation."""
    client = get_initialized_client(coordinator)
    await client.async_set_sub_enable_stereo(enabled)
    apply_eq_profile_change(coordinator, sub_enable_stereo=enabled)


async def _async_set_remote_ir(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set IR remote control state."""
    client = get_initialized_client(coordinator)
    await client.async_set_remote_ir_enabled(enabled)
    coordinator.async_apply_local_change(remote_ir_enabled=enabled)


async def _async_set_analytics(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set KEF analytics state."""
    client = get_initialized_client(coordinator)
    await client.async_set_analytics_enabled(enabled)
    coordinator.async_apply_local_change(analytics_enabled=enabled)


async def _async_set_app_analytics(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set app analytics state."""
    client = get_initialized_client(coordinator)
    await client.async_set_app_analytics_enabled(enabled)
    coordinator.async_apply_local_change(app_analytics_enabled=enabled)


async def _async_set_desk_mode(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the desk mode state."""
    client = get_initialized_client(coordinator)
    await client.async_set_desk_mode_enabled(enabled)
    apply_eq_profile_change(coordinator, desk_mode=enabled)


async def _async_set_wall_mode(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the wall mode state."""
    client = get_initialized_client(coordinator)
    await client.async_set_wall_mode_enabled(enabled)
    apply_eq_profile_change(coordinator, wall_mode=enabled)


async def _async_set_phase_correction(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the phase correction state."""
    client = get_initialized_client(coordinator)
    await client.async_set_phase_correction_enabled(enabled)
    apply_eq_profile_change(coordinator, phase_correction=enabled)


async def _async_set_high_pass_mode(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Set the high-pass mode state."""
    client = get_initialized_client(coordinator)
    await client.async_set_high_pass_mode_enabled(enabled)
    apply_eq_profile_change(coordinator, high_pass_mode=enabled)


async def _async_set_auto_detect_placement(
    coordinator: KefCoordinator,
    enabled: bool,
) -> None:
    """Enable or disable automatic placement detection."""
    client = get_initialized_client(coordinator)
    await client.async_set_auto_detect_placement(enabled)
    coordinator.async_apply_local_change(auto_detect_placement=enabled)


async def _async_set_wall_mounted(
    coordinator: KefCoordinator,
    mounted: bool,
) -> None:
    """Set wall-mounted placement."""
    # While auto-detect is on the soundbar sets this itself (the KEF app has no
    # manual setting), so manual changes are only allowed with auto-detect off.
    if coordinator.data.auto_detect_placement is not False:
        raise ServiceValidationError(
            "Turn off auto-detect placement before changing wall mounted",
            translation_domain=DOMAIN, translation_key="automatic_placement_enabled",
        )
    client = get_initialized_client(coordinator)
    applied = await client.async_set_wall_mounted(mounted)
    apply_eq_profile_change(coordinator, wall_mounted=bool(applied["wallMounted"]))


@dataclass(frozen=True, kw_only=True)
class KefSwitchDescription(SwitchEntityDescription):
    """Describe a KEF configuration switch."""

    value_fn: Callable[[KefSnapshot], bool | None]
    async_set_fn: Callable[[KefCoordinator, bool], Awaitable[None]]
    model_feature: str | None = None


SWITCHES: tuple[KefSwitchDescription, ...] = (
    KefSwitchDescription(
        key="startup_tone",
        translation_key="startup_tone",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.startup_tone_enabled,
        async_set_fn=_async_set_startup_tone,
    ),
    KefSwitchDescription(
        key="auto_switch_hdmi",
        translation_key="auto_switch_hdmi",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.auto_switch_hdmi,
        async_set_fn=_async_set_auto_switch_hdmi,
    ),
    KefSwitchDescription(
        key="front_led",
        translation_key="front_led",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.front_led_enabled,
        async_set_fn=_async_set_front_led,
        model_feature="front_led",
    ),
    KefSwitchDescription(
        key="standby_led",
        translation_key="standby_led",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.standby_led_enabled,
        async_set_fn=_async_set_standby_led,
        model_feature="standby_led",
    ),
    KefSwitchDescription(
        key="top_panel",
        translation_key="top_panel",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.top_panel_enabled,
        async_set_fn=_async_set_top_panel,
        model_feature="top_panel",
    ),
    KefSwitchDescription(
        key="top_panel_led",
        translation_key="top_panel_led",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.top_panel_led_enabled,
        async_set_fn=_async_set_top_panel_led,
        model_feature="top_panel",
    ),
    KefSwitchDescription(
        key="top_panel_standby_led",
        translation_key="top_panel_standby_led",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.top_panel_standby_led_enabled,
        async_set_fn=_async_set_top_panel_standby_led,
        model_feature="top_panel",
    ),
    KefSwitchDescription(
        key="usb_charging",
        translation_key="usb_charging",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.usb_charging_enabled,
        async_set_fn=_async_set_usb_charging,
        model_feature="usb_charging",
    ),
    KefSwitchDescription(
        key="startup_volume",
        translation_key="startup_volume",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.startup_volume_enabled,
        async_set_fn=_async_set_startup_volume,
    ),
    KefSwitchDescription(
        key="per_input_startup_volume",
        translation_key="per_input_startup_volume",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.per_input_startup_volume_enabled,
        async_set_fn=_async_set_per_input_startup_volume,
    ),
    KefSwitchDescription(
        key="volume_limit",
        translation_key="volume_limit",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.volume_limit_enabled,
        async_set_fn=_async_set_volume_limit,
    ),
    KefSwitchDescription(
        key="subwoofer_wake",
        translation_key="subwoofer_wake",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.subwoofer_wake_enabled,
        async_set_fn=_async_set_subwoofer_wake,
    ),
    KefSwitchDescription(
        key="kw1_wake",
        translation_key="kw1_wake",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.kw1_wake_enabled,
        async_set_fn=_async_set_kw1_wake,
    ),
    KefSwitchDescription(
        key="subwoofer",
        translation_key="subwoofer",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.subwoofer_out if data.eq_profile else None
        ),
        async_set_fn=_async_set_subwoofer_enabled,
    ),
    KefSwitchDescription(
        key="kw1_adapter",
        translation_key="kw1_adapter",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.eq_profile.is_kw1 if data.eq_profile else None,
        async_set_fn=_async_set_kw1_adapter,
    ),
    KefSwitchDescription(
        key="sub_enable_stereo",
        translation_key="sub_enable_stereo",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.sub_enable_stereo if data.eq_profile else None
        ),
        async_set_fn=_async_set_sub_enable_stereo,
        model_feature="dual_subwoofer_stereo",
    ),
    KefSwitchDescription(
        key="remote_ir",
        translation_key="remote_ir",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.remote_ir_enabled,
        async_set_fn=_async_set_remote_ir,
    ),
    KefSwitchDescription(
        key="analytics",
        translation_key="analytics",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.analytics_enabled,
        async_set_fn=_async_set_analytics,
    ),
    KefSwitchDescription(
        key="app_analytics",
        translation_key="app_analytics",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.app_analytics_enabled,
        async_set_fn=_async_set_app_analytics,
    ),
    KefSwitchDescription(
        key="desk_mode",
        translation_key="desk_mode",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.eq_profile.desk_mode if data.eq_profile else None,
        async_set_fn=_async_set_desk_mode,
        model_feature="desk_mode",
    ),
    KefSwitchDescription(
        key="wall_mode",
        translation_key="wall_mode",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.eq_profile.wall_mode if data.eq_profile else None,
        async_set_fn=_async_set_wall_mode,
        model_feature="wall_mode",
    ),
    KefSwitchDescription(
        key="phase_correction",
        translation_key="phase_correction",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.phase_correction if data.eq_profile else None
        ),
        async_set_fn=_async_set_phase_correction,
    ),
    KefSwitchDescription(
        key="high_pass_mode",
        translation_key="high_pass_mode",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.high_pass_mode if data.eq_profile else None
        ),
        async_set_fn=_async_set_high_pass_mode,
    ),
    KefSwitchDescription(
        key="auto_detect_placement",
        translation_key="auto_detect_placement",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.auto_detect_placement,
        async_set_fn=_async_set_auto_detect_placement,
        model_feature="xio",
    ),
    KefSwitchDescription(
        key="wall_mounted",
        translation_key="wall_mounted",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            data.eq_profile.wall_mounted if data.eq_profile else None
        ),
        async_set_fn=_async_set_wall_mounted,
        model_feature="xio",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KefConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KEF configuration switches."""
    coordinator = entry.runtime_data
    if coordinator.data.device.backend is not KefBackend.MODERN:
        return

    entities = [
        KefSwitch(coordinator, description)
        for description in SWITCHES
        if description.value_fn(coordinator.data) is not None
        and model_supports_feature(
            coordinator.data.device.model, description.model_feature
        )
    ]
    async_add_entities(entities)


class KefSwitch(KefEntity, CoordinatorEntity[KefCoordinator], SwitchEntity):
    """Coordinator-backed KEF configuration switch."""

    entity_description: KefSwitchDescription

    def __init__(
        self,
        coordinator: KefCoordinator,
        description: KefSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        CoordinatorEntity.__init__(self, coordinator)
        KefEntity.__init__(self, coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.data.device.unique_id}_{description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the switch is on."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.async_call_kef(
            lambda: self.entity_description.async_set_fn(self.coordinator, True)
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.async_call_kef(
            lambda: self.entity_description.async_set_fn(self.coordinator, False)
        )
        await self.coordinator.async_request_refresh()
