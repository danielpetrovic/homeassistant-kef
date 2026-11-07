"""Reusable KEF local control client package."""

from .client import (
    BaseKefClient,
    LegacyBinaryClient,
    ModernKefClient,
    async_create_client,
)
from .exceptions import (
    KefAuthenticationRequiredError,
    KefCommandRejectedError,
    KefConnectionError,
    KefError,
    KefResponseError,
    KefUnsupportedDeviceError,
)
from .models import (
    KefBackend,
    KefCalibrationStatus,
    KefDeviceInfo,
    KefEqProfile,
    KefFirmwareUpdateInfo,
    KefPlaybackInfo,
    KefSnapshot,
    KefSurroundDevice,
    KefWifiInfo,
)

__all__ = [
    "BaseKefClient",
    "KefBackend",
    "KefAuthenticationRequiredError",
    "KefCalibrationStatus",
    "KefCommandRejectedError",
    "KefConnectionError",
    "KefDeviceInfo",
    "KefEqProfile",
    "KefError",
    "KefFirmwareUpdateInfo",
    "KefPlaybackInfo",
    "KefResponseError",
    "KefSnapshot",
    "KefSurroundDevice",
    "KefUnsupportedDeviceError",
    "KefWifiInfo",
    "LegacyBinaryClient",
    "ModernKefClient",
    "async_create_client",
]
