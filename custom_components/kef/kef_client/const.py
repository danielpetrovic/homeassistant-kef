"""Protocol constants for the reusable KEF client."""

from __future__ import annotations

AUTH_MODE_ALL = "all"
AUTH_MODE_NONE = "none"
AUTH_MODE_SETDATA = "setData"

DEFAULT_PORT = 80
DEFAULT_LEGACY_PORT = 50001
LEGACY_PLAYBACK_SOURCES = frozenset({"Wifi", "Bluetooth"})

# Subwoofer preset gain/crossover values, extracted from the KEF Connect
# APK's SubwooferModelKt.java / SubwooferModelSubGainKt.java. Setting a
# preset alone has no audible effect; the app also recalculates these
# three fields for the speaker model and current (isKW1, subwooferCount)
# combination. Only covers models where this has been reverse-engineered
# and confirmed; models absent here fall back to writing the preset name
# alone rather than guessing values.
#
# Structure: SUBWOOFER_PRESET_VALUES[model][preset][(is_kw1, subwoofer_count)]
#   -> {"gain": float, "lowpass": float, "highpass": float}
_XIO_SUBWOOFER_PRESET_VALUES: dict[str, dict[tuple[bool, int], dict[str, float]]] = {
    "kc62": {
        (False, 1): {"gain": -1.0, "lowpass": 55.0, "highpass": 67.5},
        (False, 2): {"gain": -7.0, "lowpass": 55.0, "highpass": 67.5},
        (True, 1): {"gain": 4.0, "lowpass": 55.0, "highpass": 67.5},
        (True, 2): {"gain": -2.0, "lowpass": 55.0, "highpass": 67.5},
    },
    "kf92": {
        (False, 1): {"gain": -3.0, "lowpass": 55.0, "highpass": 67.5},
        (False, 2): {"gain": -9.0, "lowpass": 55.0, "highpass": 67.5},
        (True, 1): {"gain": 2.0, "lowpass": 55.0, "highpass": 67.5},
        (True, 2): {"gain": -4.0, "lowpass": 55.0, "highpass": 67.5},
    },
    "kube8b": {
        (False, 1): {"gain": 3.0, "lowpass": 62.5, "highpass": 67.5},
        (False, 2): {"gain": -3.0, "lowpass": 62.5, "highpass": 67.5},
        (True, 1): {"gain": 2.0, "lowpass": 62.5, "highpass": 67.5},
        (True, 2): {"gain": -4.0, "lowpass": 62.5, "highpass": 67.5},
    },
    "kube10b": {
        (False, 1): {"gain": 1.0, "lowpass": 55.0, "highpass": 67.5},
        (False, 2): {"gain": -5.0, "lowpass": 55.0, "highpass": 67.5},
        (True, 1): {"gain": 0.0, "lowpass": 55.0, "highpass": 67.5},
        (True, 2): {"gain": -6.0, "lowpass": 55.0, "highpass": 67.5},
    },
    "kube12b": {
        (False, 1): {"gain": -1.0, "lowpass": 52.5, "highpass": 65.0},
        (False, 2): {"gain": -7.0, "lowpass": 52.5, "highpass": 65.0},
        (True, 1): {"gain": -2.0, "lowpass": 52.5, "highpass": 65.0},
        (True, 2): {"gain": -8.0, "lowpass": 52.5, "highpass": 65.0},
    },
    "kube15mie": {
        (False, 1): {"gain": 0.0, "lowpass": 57.5, "highpass": 65.0},
        (False, 2): {"gain": -6.0, "lowpass": 57.5, "highpass": 65.0},
        (True, 1): {"gain": -1.0, "lowpass": 57.5, "highpass": 65.0},
        (True, 2): {"gain": -7.0, "lowpass": 57.5, "highpass": 65.0},
    },
    "t2": {
        (False, 1): {"gain": -1.0, "lowpass": 62.5, "highpass": 67.5},
        (False, 2): {"gain": -7.0, "lowpass": 62.5, "highpass": 67.5},
    },
}

# XIO and the observed LSX II / LSX II LT identifiers share this table.
_SubwooferPresetTable = dict[str, dict[tuple[bool, int], dict[str, float]]]
SUBWOOFER_PRESET_VALUES: dict[str, _SubwooferPresetTable] = {
    "XIO": _XIO_SUBWOOFER_PRESET_VALUES,
    "LSX2": _XIO_SUBWOOFER_PRESET_VALUES,
    "LSXII": _XIO_SUBWOOFER_PRESET_VALUES,
    "LSX2LT": _XIO_SUBWOOFER_PRESET_VALUES,
    "LSXIILT": _XIO_SUBWOOFER_PRESET_VALUES,
}


def model_has_subwoofer_preset_values(model: str) -> bool:
    """Return whether preset selection has verified tuning values for a model."""
    return model.upper() in SUBWOOFER_PRESET_VALUES

API_ROOT = "/api"
GET_DATA_ENDPOINT = "/getData"
SET_DATA_ENDPOINT = "/setData"
EVENT_MODIFY_QUEUE_ENDPOINT = "/event/modifyQueue"
EVENT_POLL_QUEUE_ENDPOINT = "/event/pollQueue"

STATE_OFF = "standby"

DEFAULT_MODERN_SOURCE_LIST = (
    "wifi",
    "bluetooth",
    "tv",
    "optical",
    "coaxial",
    "analog",
    "usb",
)

MODERN_MODEL_SOURCE_MAP: dict[str, tuple[str, ...]] = {
    "LSX2": ("wifi", "bluetooth", "tv", "optical", "analog", "usb"),
    "LSX2LT": ("wifi", "bluetooth", "tv", "optical", "usb"),
    "LSXIILT": ("wifi", "bluetooth", "tv", "optical", "usb"),
    "LSXII": ("wifi", "bluetooth", "tv", "optical", "analog", "usb"),
    "LS50W2": ("wifi", "bluetooth", "tv", "optical", "coaxial", "analog"),
    "LS50WII": ("wifi", "bluetooth", "tv", "optical", "coaxial", "analog"),
    # Older LS60 firmware reports the model as "LS60"; newer firmware
    # renamed it to "LS60W". Both are listed so either firmware generation
    # matches, without relying on normalization happening elsewhere.
    "LS60": ("wifi", "bluetooth", "tv", "optical", "coaxial", "analog"),
    "LS60W": ("wifi", "bluetooth", "tv", "optical", "coaxial", "analog"),
    "XIO": ("wifi", "bluetooth", "tv", "optical"),
}

DEFAULT_VOLUME_SOURCE_SUFFIX = {
    "wifi": "Wifi",
    "bluetooth": "Bluetooth",
    "optical": "Optical",
    "coaxial": "Coaxial",
    "usb": "USB",
    "analog": "Analogue",
    "tv": "TV",
}

LEGACY_SOURCE_LIST = (
    "Wifi",
    "Bluetooth",
    "Aux",
    "Opt",
    "Usb",
)

PROBE_PATHS = {
    "device_name": "settings:/deviceName",
    "version": "settings:/version",
    "release_text": "settings:/releasetext",
    "mac": "settings:/system/primaryMacAddress",
    "model_code": "settings:/kef/host/modelName",
    "serial_number": "settings:/kef/host/serialNumber",
    "kef_id": "settings:/kef/host/kefId",
    "hardware_version": "settings:/kef/host/hardwareVersion",
    "webserver_auth_mode": "settings:/webserver/authMode",
    "speaker_status": "settings:/kef/host/speakerStatus",
    "source": "settings:/kef/play/physicalSource",
    "cable_mode": "settings:/kef/host/cableMode",
    "master_channel": "settings:/kef/host/masterChannelMode",
    "volume": "player:volume",
    "mute": "settings:/mediaPlayer/mute",
    "play_mode": "settings:/mediaPlayer/playMode",
    "firmware_update_status": "firmwareupdate:updateStatus",
    "player_data": "player:player/data",
    "play_time": "player:player/data/playTime",
    "eq_profile": "kef:eqProfile",
    "eq_profile_v2": "kef:eqProfile/v2",
    "calibration_status": "settings:/kef/dsp/calibrationStatus",
    "calibration_result": "settings:/kef/dsp/calibrationResult",
    "calibration_start": "kefdsp:/calibration/start",
    "auto_detect_placement": "settings:/kef/host/autoDetectPlacement",
    "prefer_virtual_x": "settings:/kef/dsp/preferVirtualX",
    "virtual_x_active": "imx8af:decoderInfoVirtualXActive",
    "surround_mode": "settings:/kef/host/surroundMode",
    "surround_device_list": "settings:/kef/dsp/surroundMode/deviceList",
    "wireless_rear_mode": "settings:/kef/dsp/wirelessRearMode",
    "wireless_rear_gain": "settings:/kef/dsp/wirelessRearGain",
    "surround_master_channel": "settings:/kef/host/surroundModeMasterChannelMode",
    "network_info": "network:info",
    "standby_mode": "settings:/kef/host/standbyMode",
    "startup_tone": "settings:/kef/host/startupTone",
    "auto_switch_hdmi": "settings:/kef/host/autoSwitchToHDMI",
    "disable_front_led": "settings:/kef/host/disableFrontLED",
    "disable_front_standby_led": "settings:/kef/host/disableFrontStandbyLED",
    "disable_top_panel": "settings:/kef/host/disableTopPanel",
    "top_panel_led": "settings:/kef/host/topPanelLED",
    "top_panel_standby_led": "settings:/kef/host/topPanelStandbyLED",
    "wake_up_source": "settings:/kef/host/wakeUpSource",
    "subwoofer_force_on": "settings:/kef/host/subwooferForceOn",
    "subwoofer_force_on_kw1": "settings:/kef/host/subwooferForceOnKW1",
    "usb_charging": "settings:/kef/host/usbCharging",
    "startup_volume_enabled": "settings:/kef/host/standbyDefaultVol",
    "per_input_startup_volume_enabled": "settings:/kef/host/advancedStandbyDefaultVol",
    "default_volume_global": "settings:/kef/host/defaultVolumeGlobal",
    "maximum_volume": "settings:/kef/host/maximumVolume",
    "volume_step": "settings:/kef/host/volumeStep",
    "volume_limit": "settings:/kef/host/volumeLimit",
    "fixed_volume_level": "settings:/kef/host/remote/userFixedVolume",
    "remote_ir": "settings:/kef/host/remote/remoteIR",
    "remote_ir_code": "settings:/kef/host/remote/remoteIRCode",
    "favourite_button": "settings:/kef/host/remote/favouriteButton",
    "eq_button_1": "settings:/kef/host/remote/eqButton1",
    "eq_button_2": "settings:/kef/host/remote/eqButton2",
    "disable_analytics": "settings:/kef/host/disableAnalytics",
    "disable_app_analytics": "settings:/kef/host/disableAppAnalytics",
    "streaming_quality": "settings:/airable/bitrate",
    "ui_language": "settings:/ui/language",
    "speaker_location": "settings:/kef/host/speakerLocation",
    "network_ping": "kef:network/pingInternet",
    "network_stability": "kef:network/pingInternetStability",
    "speed_test_status": "kef:speedTest/status",
    "speed_test_average_download": "kef:speedTest/averageDownloadSpeed",
    "speed_test_current_download": "kef:speedTest/currentDownloadSpeed",
    "speed_test_packet_loss": "kef:speedTest/packetLoss",
    "alerts_list": "alerts:/list",
    "alert_snooze_time": "settings:/alerts/snoozeTime",
    "player_notification": "notifications:/player/playing",
}

EVENT_SUBSCRIPTIONS = (
    {"path": PROBE_PATHS["speaker_status"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["source"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["volume"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["mute"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["play_mode"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["firmware_update_status"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["player_data"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["play_time"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["eq_profile"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["eq_profile_v2"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["network_info"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["standby_mode"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["startup_tone"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["auto_switch_hdmi"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["disable_front_led"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["disable_front_standby_led"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["disable_top_panel"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["top_panel_led"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["top_panel_standby_led"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["wake_up_source"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["subwoofer_force_on"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["subwoofer_force_on_kw1"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["usb_charging"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["startup_volume_enabled"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["per_input_startup_volume_enabled"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["default_volume_global"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["maximum_volume"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["volume_step"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["volume_limit"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["fixed_volume_level"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["remote_ir"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["remote_ir_code"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["favourite_button"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["eq_button_1"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["eq_button_2"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["disable_analytics"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["disable_app_analytics"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["streaming_quality"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["ui_language"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["speaker_location"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["network_ping"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["network_stability"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["speed_test_status"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["speed_test_average_download"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["speed_test_current_download"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["speed_test_packet_loss"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["alerts_list"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["alert_snooze_time"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["player_notification"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["master_channel"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["cable_mode"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["auto_detect_placement"], "type": "itemWithValue"},
    {"path": PROBE_PATHS["prefer_virtual_x"], "type": "itemWithValue"},
    {"path": "notifications:/display/queue", "type": "rows"},
)
