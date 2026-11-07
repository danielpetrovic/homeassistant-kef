"""Compatibility wrapper for reusable KEF models."""

from .kef_client import (
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
    "KefBackend",
    "KefCalibrationStatus",
    "KefDeviceInfo",
    "KefEqProfile",
    "KefFirmwareUpdateInfo",
    "KefPlaybackInfo",
    "KefSnapshot",
    "KefSurroundDevice",
    "KefWifiInfo",
]
