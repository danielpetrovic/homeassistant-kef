# KEF model notes

What individual KEF models report and how they behave, as observed on real
speakers. Protocol details shared by all modern models are in
[API notes](api-notes.md).

Unless dated otherwise, observations are from September 2026 on an LSX II
(firmware `3.0.137.0xf884312`), an LSX II LT (`2.1.86.0xdc74e88`), and an XIO
(`1.4.135.0xd4e9dfd`). Earlier observations, from late 2025, are marked as
such; firmware has changed since. The wireless surround notes are from November
2026, with an XIO on `1.5.160.0x00f793d` and an LSX II on `3.1.141.0x0a4f556`.
The LS50 Wireless II and LS60 have not been tested on hardware. Device identifiers are omitted.

## Identification

| Model | `settings:/kef/host/modelName` | Model string reported | Release text example |
| --- | --- | --- | --- |
| LSX II | `SP4041` | `LSXII` (older firmware: `LSX2`) | `LSXII_V30137` |
| LSX II LT | `SP4077` | `LSXIILT` (older firmware: `LSX2LT`) | `LSXIILT_V2186` |
| XIO | `SP4083` | `XIO` | `XIO_V14135` |
| LS50 Wireless II | Not confirmed | `LS50WII` or `LS50W2` | |
| LS60 | Not confirmed | `LS60W` (older firmware: `LS60`) | |

The version string (`settings:/version`) has the form `3.0.137.0xf884312`.
`settings:/system/memberId` starts with a model prefix: `lsxii-`, `lsxlite-`,
or `xio-`. Coda W and Muo have Bluetooth connectivity but no supported network
API for this integration.

## Inputs

| Model | Inputs |
| --- | --- |
| LSX II | `wifi`, `bluetooth`, `tv`, `optical`, `analog`, `usb` |
| LSX II LT | `wifi`, `bluetooth`, `tv`, `optical`, `usb` |
| LS50 Wireless II, LS60 | `wifi`, `bluetooth`, `tv`, `optical`, `coaxial`, `analog` |
| XIO | `wifi`, `bluetooth`, `tv`, `optical` |

Every model has HDMI eARC as `tv`. Only the XIO decodes surround formats (Dolby
Atmos, DTS:X); the others take LPCM 2.0 over HDMI. The API accepts every input
name on every model because the firmware is shared, so the integration only
offers the inputs a model physically has. Per-input startup volumes follow the
same list.

On physical inputs, the LSX II reports no artwork and uses the input name as
the track title.

## Shared firmware and schema

All modern models run closely related firmware and report the same EQ profile
v2 schema. The LSX II and LSX II LT include `soundProfile`, `dialogueMode`, and
`wallMounted`, and answer the XIO settings paths
`settings:/kef/host/autoDetectPlacement`, `settings:/kef/dsp/preferVirtualX`,
and `settings:/kef/dsp/v2/soundProfile`, even though the KEF Connect app only
offers these on the XIO. A field or path being present does not mean the model
uses it, so the integration gates these controls by model rather than by value.

`dialogueMode` is accepted and persisted on the LSX II and the XIO, but a live
listening test on each produced no audible change. The KEF Connect app has no
separate dialogue setting; dialogue enhancement on the XIO is the `dialogue`
value of `soundProfile`. The integration does not expose `dialogueMode`.

In late 2025, `disableFrontLED` had no visible effect on an LSX II, LSX II LT,
or XIO, and `subEnableStereo` had no audible effect on an LSX II.

## Standby and wake

The KEF Connect app shows the `standbyMode` values as:

| API value | App label |
| --- | --- |
| `standby_20mins` | ECO |
| `standby_30mins` | 30 |
| `standby_60mins` | 60 |
| `standby_none` | Never |

In late 2025, ECO was only available with wake source `wakeup_default`; with
`tv`, `optical`, or `bluetooth` as wake source the minimum was 30 minutes. The
LSX II models defaulted to ECO; the XIO defaulted to 30 minutes with wake
source `tv`.

An October 2026 LSX II check on firmware `3.0.137.0xf884312` found the speaker
reachable over the network with `speakerStatus=powerOn`, physical source `wifi`,
`powermanager:target` reporting `online`, and
`settings:/imx8AudioFramework/afInStandby=false`, while Windows had no present
KEF USB audio device. Selecting `usb` through Home Assistant restored the USB
audio interface and sound output endpoint without changing volume, restarting
the speaker, or resetting Windows devices. This demonstrates USB recovery by
input selection on that speaker; it does not establish that every missing USB
device is caused by standby or input selection.

## LSX II and LSX II LT

The two models expose the same settings apart from their inputs and the
stereo-pair cable mode, which the integration does not offer on the LT.
`settings:/kef/dsp/subwooferCount` answers on the LSX II but returns 500 on the
LT and the XIO; the same field is always present inside the EQ profile.

Both models take part in KEF grouping: `grouping:members` returns `null` while
ungrouped.

## XIO

### Placement

`settings:/kef/host/autoDetectPlacement` lets the soundbar's gravity sensor set
`wallMounted` in the EQ profile. The KEF Connect app has only the auto-detect
switch; it has no manual wall-mounted setting. With auto-detect off, writing
`wallMounted` works and is audible: `false` projects the sound upward, as for a
table, `true` projects it forward. The integration only accepts wall-mounted
changes once auto-detect is confirmed off. Turning auto-detect off through the API kept the
existing room calibration; the recalibration prompt in the app is part of the
app's own flow.

The desk and wall mode EQ settings of the bookshelf models do not apply to the
XIO; placement is handled by `wallMounted`.

### Sound profiles and EQ buttons

`soundProfile` takes `default`, `music`, `movie`, `night`, `dialogue`, or
`direct`. The C2 remote's EQ1 and EQ2 buttons
(`settings:/kef/host/remote/eqButton1` and `eqButton2`) are assigned one of
these profiles.

### Codec and virtualizer

The codec string in `activeResource.codec` has the form
`<codec> - <processing>`, for example `Dolby Digital Plus - Dolby Surround`.
`Dolby PCM` is plain PCM. Native Dolby Atmos reports exactly `Dolby Atmos` with
no processing part, `streamChannels` 0, and `nrAudioChannels` 8. With the
surround channel layout set to 7.1.2 (`settings:/kef/dsp/wirelessRearMode` =
`rearSurround`), the same Atmos stream reports `nrAudioChannels` 10, and the
virtualizer sensor shows 7.1.2 instead of 5.1.2.

The processing part only names the Dolby upmixer. Whether DTS Virtual:X is also
processing is a separate flag, `imx8af:decoderInfoVirtualXActive`, which turns
true when `settings:/kef/dsp/preferVirtualX` is enabled. The KEF Connect app
then lists both ("Dolby Surround, Virtual:X"). That setting is the app's
"Preferred virtualiser" (Dolby virtualiser or DTS Virtual:X, on its Surround
controls screen, KEF Connect 1.32.0); the integration calls the Dolby option
"Dolby Surround", the name the speaker uses in its codec string.

DTS content reports a bare `DTS` codec string with no processing part, and the
flag is true even with `preferVirtualX` off (observed with DTS 5.1: six stream
channels, `nrAudioChannels` 12). The Dolby upmixer cannot process DTS, so
Virtual:X renders it; the KEF Connect app shows just "DTS Virtual:X". The
virtualizer sensor reports this as "DTS Virtual:X 7.1.4".

The channel layout follows `nrAudioChannels`, the count of rendered output
channels: 8 is 5.1.2, 10 is 7.1.2 and 12 is 7.1.4. Dolby rendering gives 8 or 10
depending on the surround channel layout; with DTS Virtual:X preferred the same
Atmos stream reports 12 in both layouts, so the sensor shows "Dolby Atmos +
Virtual:X 7.1.4". Any other count is shown as 5.1.2.

### Artwork

On the TV input the track icon is `skin:iconTv`, a firmware skin reference
rather than a URL. The integration ignores artwork that is not an `http` or
`https` URL.

### Room calibration

`settings:/kef/dsp/calibrationStatus` reports whether and when the soundbar was
calibrated, and `settings:/kef/dsp/calibrationResult` the adjustment in dB.
`settings:/kef/dsp/calibrationStep` moves through `step_1_start`,
`step_2_processing`, and `step_3_complete` during a calibration and reports
`idle` on models without calibration. `kefdsp:/calibration/start` starts one.

### Wireless subwoofer

The XIO has a built-in KW2 transmitter for its wireless subwoofer. Pairing
between the transmitter and the subwoofer's receiver happens at hardware level;
the KEF Connect app does not model a paired or connected state at all, only a
firmware update lifecycle. Selecting KW2 in the app goes over the app's
separate encrypted connection, and writing `wirelessSub` or `subwooferCount`
over the HTTP API returns 403, as does activating
`kef:ble/ui/<device>/connect`. The `wirelessSub` field (`none`) is not used by
the app.

Reading `kef:ble/updateStatus`, `kef:ble/updateServer/txVersion`, and
per-device `kef:ble/ui/<device>/version` and `/updateProgress` is safe. `kef:ble/updateStatus` moves
through `startUp`, `downloading`, `installing`, and `complete`. Activating
`kef:ble/checkForUpdates` is not: on a live XIO it woke the soundbar from
standby and disconnected the paired KW2 receiver until the subwoofer was
power-cycled. The receiver also disappeared from the `kef:ble/ui` device list,
so that list is update bookkeeping, not connection state. Leave firmware checks
and updates for the wireless subwoofer module to the KEF Connect app.

Wireless rear speakers are covered under [wireless surround](#wireless-surround).

### Wireless surround

Firmware 1.5.160 (5 November 2026) adds wireless surround. A rear speaker needs
its own KW2 module, an LSX II as rear speaker needs firmware 3.1.141, and the KW2
and the soundbar transmitter need firmware 2.0.0.0. KEF Connect 1.32.0 does the
pairing; with one KW2 the rear speaker is a single stereo signal, which the XIO
lists as `stereoRear`. A KW2 can also be paired to a subwoofer, and two
subwoofers can be used. On the XIO the integration reads which devices are paired and
connected, and reads and writes the channel layout (wireless rear mode) and the
wireless rear gain; on a rear speaker
it reads whether the speaker is in surround mode; see the [API notes](api-notes.md#wireless-surround) for the values
and what is still unverified.

The XIO reports the paired LSX II in `settings:/kef/dsp/surroundMode/deviceList`
with the speaker's own address, so the same LSX II is also a normal Home
Assistant entry of its own. The app refuses most setting changes on a speaker
that is used as a rear speaker, so writes to that LSX II can be rejected. A rear
LSX II reports `settings:/kef/host/surroundMode` as `true`, which is how it can
be told apart from a normal speaker.

### Other XIO behaviour

- `balance` reports `0` and has no effect; the soundbar has no stereo pair.
- The standby LED setting has no effect; the top panel LED settings
  (`topPanelLED`, `topPanelStandbyLED`) and the panel lock (`disableTopPanel`)
  apply instead.
- There is no USB port, so USB charging does not apply.
- `grouping:members` returns 500: the XIO does not take part in KEF grouping.
- `settings:/kef/host/iptSwitch` is `true`, against `false` on the LSX II
  models; its purpose is unknown.
- `kef:fwupgrade/info` lists `topPanel` and `bTLE` components besides
  `systemMCU`.
- On the TV input, play, pause, next, and previous are not available.
- In late 2025, next and previous failed during AirPlay playback with "Control
  is not supported", in the KEF Connect app as well; an LSX II was not
  affected.
- In late 2025 (firmware `1.3.120`), adding, removing, enabling, or disabling
  alarms and timers, making Bluetooth discoverable, and the Google Cast usage
  report were not implemented; listing alerts, the snooze time, and the default
  alert sound worked.

## LS50 Wireless II and LS60

Not tested on hardware here. Newer LS60 firmware reports its model as `LS60W`
instead of `LS60`; both names are handled. The LS60 has no desk mode. The
integration offers `subEnableStereo` (dual subwoofer stereo) only on these two
models.

## Remote controls

| Remote | Supplied with | Extra buttons | Related settings |
| --- | --- | --- | --- |
| Standard remote | LSX II, LSX II LT | None | `remoteIR`, `remoteIRCode` |
| C3 | Optional, any model | Favourite | `favouriteButton` |
| C2 | XIO | EQ1, EQ2 | `eqButton1`, `eqButton2` |

`remoteIRCode` selects `ir_code_set_a`, `ir_code_set_b`, or `ir_code_set_c` to
avoid clashing with other IR devices. Because the C3 can be used with any model,
the favourite button setting cannot be gated by model.

## Firmware updates

The speaker's own update check is the source of truth for available firmware.
KEF's published release notes listed LSX II `3.0.138` while the speakers still
reported no update.

`firmwareupdate:updateStatus` reports `idle` when nothing is pending,
`newUpdateAvailable` once the speaker has found an image, and `downloaded` after
it has fetched it. Speakers check on their own overnight: one LSX II reported
`downloaded` at 02:38. On that speaker the download later reverted to `idle`
about five hours afterwards, without any firmware request from Home Assistant,
and `newUpdateAvailable` returned about twenty minutes after that. The cause is
not known.

Speakers also update themselves overnight. Four LSX II speakers became
unreachable for about two minutes between 02:32 and 03:59, without any request
from Home Assistant, and came back on the newest version, which fits an install
reboot. One LSX II that was playing overnight received the download on two
nights (at 03:29 and at 02:38) and had lost it again by morning.

Activating `firmwareupdate:checkForUpdate` on an LSX II answered within a few
seconds in both states tested. In standby (`networkStandby`) it answered `idle`
and the speaker stayed in standby for the following minute. On a playing LSX II
that already reported `newUpdateAvailable` the status did not change and playback
was not affected. A playing LSX II LT answered `idle` as well.

On the XIO in standby the check left the speaker in standby with the status
`idle`. The wireless subwoofer module's own status (`kef:ble/updateStatus` and
`kef:ble/updateServer/txVersion`) was unchanged afterwards. The main firmware
check is a separate action from the subwoofer module's check
(`kef:ble/checkForUpdates`, a different menu in the KEF Connect app), which must
not be activated. A check on an LSX II LT in standby has not been tried.
