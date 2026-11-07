"""Constants for the KEF integration."""

from __future__ import annotations

from .kef_client.const import EVENT_SUBSCRIPTIONS as EVENT_SUBSCRIPTIONS
from .kef_client.const import PROBE_PATHS as PROBE_PATHS

AUTH_MODE_ALL = "all"
AUTH_MODE_NONE = "none"
AUTH_MODE_SETDATA = "setData"

DOMAIN = "kef"

AUTH_FAILURE_MESSAGE = (
    "KEF speaker requires a valid web UI password. Reconfigure the KEF "
    "integration and enter the password configured in the speaker web interface."
)

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL_SECONDS = 10
MIN_SCAN_INTERVAL_SECONDS = 5
MAX_SCAN_INTERVAL_SECONDS = 120
DEFAULT_OFFLINE_RETRY_INTERVAL_SECONDS = 60
MIN_OFFLINE_RETRY_INTERVAL_SECONDS = 30
MAX_OFFLINE_RETRY_INTERVAL_SECONDS = 600

CONF_BACKEND = "backend"
CONF_DEVICE_ID = "device_id"
CONF_DISCOVERY_ID = "discovery_id"
CONF_ENABLE_DIAGNOSTICS = "enable_diagnostics"
CONF_OFFLINE_RETRY_INTERVAL = "offline_retry_interval"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TCP_PORT = "tcp_port"

DEFAULT_ENABLE_DIAGNOSTICS = False

AIRPLAY_ZEROCONF_TYPE = "_airplay._tcp.local."
DEFAULT_LEGACY_PORT = 50001

API_ROOT = "/api"
GET_DATA_ENDPOINT = "/getData"
GET_ROWS_ENDPOINT = "/getRows"
SET_DATA_ENDPOINT = "/setData"
EVENT_MODIFY_QUEUE_ENDPOINT = "/event/modifyQueue"
EVENT_POLL_QUEUE_ENDPOINT = "/event/pollQueue"

STATE_ON = "powerOn"
STATE_OFF = "standby"

# Only list capabilities known to be unsupported. Models and capabilities that
# have not been verified remain visible instead of being hidden by inference.
MODEL_UNSUPPORTED_FEATURES: dict[str, frozenset[str]] = {
    "KEF LEGACY": frozenset({"dual_subwoofer_stereo", "xio"}),
    "LSX2": frozenset(
        {
            "dual_subwoofer_stereo",
            "eq_button",
            "front_led",
            "top_panel",
            "xio",
        }
    ),
    "LSXII": frozenset(
        {
            "dual_subwoofer_stereo",
            "eq_button",
            "front_led",
            "top_panel",
            "xio",
        }
    ),
    "LSX2LT": frozenset(
        {
            "cable_mode",
            "dual_subwoofer_stereo",
            "eq_button",
            "front_led",
            "top_panel",
            "xio",
        }
    ),
    "LSXIILT": frozenset(
        {
            "cable_mode",
            "dual_subwoofer_stereo",
            "eq_button",
            "front_led",
            "top_panel",
            "xio",
        }
    ),
    "LS50W2": frozenset({"eq_button", "xio"}),
    "LS50WII": frozenset({"eq_button", "xio"}),
    "LS60": frozenset(
        {"desk_mode", "eq_button", "top_panel", "xio"}
    ),
    "LS60W": frozenset(
        {"desk_mode", "eq_button", "top_panel", "xio"}
    ),
    "XIO": frozenset(
        {
            "cable_mode",
            "desk_mode",
            "dual_subwoofer_stereo",
            "front_led",
            "standby_led",
            "stereo_pair",
            "usb_charging",
            "wall_mode",
        }
    ),
}


def model_supports_feature(model: str, feature: str | None) -> bool:
    """Return whether a model should expose an optional configuration feature."""
    return feature is None or feature not in MODEL_UNSUPPORTED_FEATURES.get(
        model.upper(), frozenset()
    )

STANDBY_MODE_OPTIONS = {
    "standby_none": "Never",
    "standby_20mins": "20 minutes",
    "standby_30mins": "30 minutes",
    "standby_60mins": "60 minutes",
}

WAKE_SOURCE_OPTIONS = {
    "wakeup_default": "Default",
    "wifi": "Wi-Fi",
    "bluetooth": "Bluetooth",
    "usb": "USB",
    "optical": "Optical",
    "tv": "TV",
}

BASS_EXTENSION_OPTIONS = {
    "less": "Less",
    "standard": "Standard",
    "extra": "Extra",
}

CABLE_MODE_OPTIONS = {
    "wired": "Wired",
    "wireless": "Wireless",
}

POLARITY_OPTIONS = {
    "normal": "Normal",
    "inverted": "Inverted",
}

SUBWOOFER_PRESET_OPTIONS = {
    "custom": "Custom",
    "kc62": "KEF KC62",
    "kf92": "KEF KF92 / KC92",
    "kube8b": "KEF KUBE 8B / 8 MIE",
    "kube10b": "KEF KUBE 10B / 10 MIE",
    "kube12b": "KEF KUBE 12B / 12 MIE",
    "kube15mie": "KEF KUBE 15 MIE",
    "t2": "KEF T2 Subwoofer",
    "other": "Other",
}

SOUND_PROFILE_OPTIONS = {
    "default": "Default",
    "music": "Music",
    "movie": "Movie",
    "night": "Night",
    "dialogue": "Dialogue",
    "direct": "Direct",
}

MASTER_CHANNEL_OPTIONS = {
    "left": "Left",
    "right": "Right",
}

# The XIO prefers one virtualiser. The speaker itself names the Dolby processing
# "Dolby Surround" (the KEF Connect app says "Dolby virtualiser").
PREFERRED_VIRTUALISER_OPTIONS = {
    "dolby": "Dolby Surround",
    "dts_virtual_x": "DTS Virtual:X",
}

# With DTS Virtual:X preferred the soundbar renders 12 output channels, whatever
# surround layout it has stored.
DTS_VIRTUAL_X_LAYOUT = "7.1.4"

# The KEF Connect app calls these the channel layouts 5.1.2 and 7.1.2.
WIRELESS_REAR_MODE_OPTIONS = {
    "surround": "5.1.2",
    "rearSurround": "7.1.2",
}

IR_CODE_OPTIONS = {
    "ir_code_set_a": "Set A",
    "ir_code_set_b": "Set B",
    "ir_code_set_c": "Set C",
}

STREAMING_QUALITY_OPTIONS = {
    "unlimited": "Unlimited",
    "320": "320 kbps",
    "256": "256 kbps",
    "192": "192 kbps",
    "128": "128 kbps",
}

FAVOURITE_BUTTON_OPTIONS = {
    "nextSource": "Next source",
}

EQ_BUTTON_OPTIONS = {
    "dialogue": "Dialogue",
    "night": "Night",
    "music": "Music",
    "movie": "Movie",
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
