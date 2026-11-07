# Open KEF development work

For implemented controls and model support, use [configuration](configuration.md)
and [device support](device-support.md). The reusable client and Home Assistant
integration already exist; this list tracks remaining work.

## Device and firmware coverage

- [ ] Capture sanitized first-generation LSX/LS50 Wireless fixtures and validate
  legacy playback, source selection, and DSP behavior on real hardware.
- [ ] Validate firmware 4.x local authentication on LS50 Wireless II hardware.
- [ ] Broaden event-queue and recovery testing across modern KEF families.
- [ ] Refine capability detection where a model advertises fewer settings than
  other speakers using the same protocol.

## Undocumented capabilities

- [ ] Investigate alert, timer, and alarm writes before exposing actions.
- [ ] Determine whether KEF grouping (`grouping:members`, answered by the LSX II
  models but not the XIO) and the notification queue provide useful,
  controllable features.
- [ ] Consider exposing the scheduled reboot settings
  (`settings:/kef/scheduledReboot/*`), present on the LSX II, LSX II LT, and
  XIO, and the Bluetooth connection state from `bluetooth:state`.
- [ ] Revisit XIO wireless subwoofer (BLE) firmware versions now that wireless
  rear speakers have shipped. Reads are safe, but activating an update check
  disconnected the KW2 receiver; see the [model notes](model-notes.md#wireless-subwoofer).
- [ ] Test whether a rear speaker accepts a
  write of `surroundModeMasterChannelMode` outside the app's pairing test; see
  [wireless surround](api-notes.md#wireless-surround).

## Home Assistant usability

- [ ] Improve grouping and descriptions of advanced DSP controls where the
  current entities are difficult to navigate.
- [ ] Add actionable repair guidance for authenticated or partially supported
  devices when the existing setup errors do not explain recovery.

Keep new settings capability-gated. Add fixture and device proof before widening
support, and remove completed items from this list rather than retaining a
second inventory of implemented features.
