# Configuration and troubleshooting

[Back to the README](../README.md) · [Device support](device-support.md)

## Connect a speaker

Accept Home Assistant's discovered KEF device, or add **KEF** from **Settings →
Devices & services** and enter the host/IP address. Keep the speaker reachable
on your local network. Modern speakers use their local HTTP API on TCP port 80;
first-generation speakers use the IPv4 binary API on TCP port 50001. Discovery
uses the speaker's AirPlay/Bonjour announcement. Across network segments, allow
the required local traffic and make sure Home Assistant can resolve any `.local`
hostname you enter.

| Setup field | Required | Purpose |
| --- | --- | --- |
| Host | Yes for manual setup; supplied by discovery otherwise | Speaker IP address or resolvable hostname |
| Speaker password | Only when the local API requires it | Password for the speaker's web interface; blank by default |

First-generation LSX and LS50 Wireless speakers use the passwordless legacy
protocol. Leave the password blank when adding one manually. When discovery
identifies a legacy speaker, its confirmation form has no password field.

Legacy mute preserves the volume level. Source and power controls preserve the
speaker's channel orientation and standby setting. Power-off follows the
original legacy client's workaround: an active speaker using 20-minute standby
is switched to 60 minutes before being turned off. An already-off speaker is
left off.

If the speaker's web UI is password-protected, enter that password during setup.
This is the speaker web-interface password, not a request to put your credentials
into YAML. Firmware updates that enable authentication can trigger a Home
Assistant reauthentication prompt.

Modern speakers found through Bonjour use their `.local` hostname so Home
Assistant can try IPv4 or IPv6 and follow address changes. If an older entry
still points to an unreachable IP address, use **Reconfigure** and enter the
speaker's advertised `.local` hostname. The speaker must be reachable during
reconfiguration. Modern speakers must match the existing entry. First-generation
speakers continue to use IPv4 for their binary control protocol. Their existing entries
learn a stable AirPlay identifier when rediscovered at the saved address, then
can follow later IPv4 changes. If the address changed before that rediscovery,
use **Reconfigure** with the current IPv4 address and confirm it belongs to
the same speaker; the legacy binary API does not provide a stable device ID.

## Options

Open the integration's **Configure** dialog. Saving options reloads the entry;
its entities retain their identities. Use **Reconfigure** to change the host.

| Option | Default and purpose |
| --- | --- |
| Speaker password | Used when the local web/API interface requires authentication |
| Polling interval | 10 seconds; accepts 5–120 seconds |
| Offline retry interval | 60 seconds; accepts 30–600 seconds. How often an offline speaker is retried |
| Diagnostics | Off by default; enables optional diagnostic entities |

## Data updates

The integration reads a speaker snapshot every 10 seconds by default. The
polling option accepts whole seconds from 5 to 120. A snapshot can require
several local API requests; the interval is not a per-request rate limit.

Modern speakers also have an event-queue listener. An event requests a fresh
snapshot between scheduled polls, so a change can appear before the next poll.
Polling continues alongside the listener and remains available if the event
queue fails. Legacy speakers use polling without this event listener.

Shorter intervals increase requests to the speaker. Leave the default unless
you need a different update cadence; no measured per-model request budget is
currently published. Network latency, retries, and speaker response time affect
when Home Assistant receives a fresh state.

### Offline speakers

A speaker on a switched-off power strip or desk socket goes offline without
warning. One or two missed polls keep the last known state, so a brief network
hiccup does not flip every entity to unavailable. After three missed polls in a
row the entities become unavailable and the integration retries at the offline
retry interval instead of the polling interval. The live event queue pauses
while the speaker is offline. Home Assistant logs one error when the speaker
goes offline and one message when it comes back.

When a discovery announcement matches an existing offline entry, the integration
requests a refresh without waiting for the offline retry interval. If the
announcement is missed or cannot be matched, recovery uses the next scheduled
retry. During initial setup there is no previous state to retain: Home Assistant
retries setup if the first connection fails.

## Daily controls and settings

The media player provides the supported power, volume, mute, source, and playback
actions. Select the speaker from your device page when adding a dashboard or
automation; do not copy an example entity ID unchanged.

Additional entities expose supported startup-volume, standby, wake-source, LED,
hardware, privacy, streaming-quality, and regional settings. Not every family or
firmware provides every setting. Use the controls visible on your own device.

On the XIO, **Wall mounted** can only be changed while **Auto-detect placement**
is off; with auto-detect on, the soundbar sets it itself. The KEF Connect app
has no manual wall-mounted setting, so this switch is the only way to override
the detected placement. Turning auto-detect off here keeps the existing room
calibration; run **Start calibration** if the soundbar is physically moved.

The surround entities use the `SUR:` prefix, like the KEF Connect app's
"Surround controls" screen. An XIO on firmware 1.5 or newer, which supports
wireless surround, gets a **Channel layout** select (5.1.2 or 7.1.2), a **Rear
volume** slider (-10 to 10 in steps of 0.5), and a **Connected** sensor for each
paired surround speaker. The **Preferred virtualiser** select (Dolby Surround or
DTS Virtual:X) uses the same prefix; it replaces the earlier "Prefer DTS Virtual:X"
switch. Update automations and dashboards targeting the old switch to use
the **Preferred virtualiser** select with `Dolby Surround` or `DTS Virtual:X`.
The KEF Connect app notes that most content is mixed for 5.1.2 and that the
preferred virtualiser has no effect in Direct mode or while DTS content plays.
While DTS Virtual:X is preferred, the app greys out the channel layout. The
channel layout select shows 7.1.4 and offers no other
choice, because DTS Virtual:X renders 7.1.4 whatever layout is stored; the stored
layout returns when Dolby Surround is preferred again. Changing the channel
layout or the preferred virtualiser interrupts the sound briefly.
A speaker that is used as a rear speaker gets a **Mode** sensor (added when the
speaker reports it on, so other speakers do not have one) and a **Master
channel** sensor, which shows the left or right orientation that the pairing test
in the KEF Connect app set. They appear once the speaker reports surround data. Pairing and changing
the other surround settings stay in the KEF Connect app.

### Standby, USB audio, and computer visibility

Home Assistant connects to the speaker over the network. A reachable speaker can
be in standby, and a powered-on speaker can be reachable while its USB audio
device is absent from Windows or macOS. The media player's availability confirms
network communication, not the computer's USB connection. Check `speaker_status`
and `source` separately from the computer's audio-device list.

For an LSX II used as a USB speaker:

- Select **USB** as the active input when returning to the computer. On modern
  speakers, **Turn on** leaves an active input alone. From standby it selects
  the last input remembered by the running client once, falling back to Wi-Fi
  if none is known. It does not cycle the speaker off and on.
  Use [explicit USB selection](automations.md#select-usb-for-a-computer)
  when the computer needs that input, including after an integration restart
  while the speaker is in standby.
- Set **Second wake-up source** to **USB** if USB audio should wake the speaker.
  This is separate from selecting USB as the current input. **Default** leaves
  Wi-Fi wake available without adding a physical wake input.
- KEF calls the 20-minute standby option **ECO**. A second wake-up source is
  unavailable in ECO mode. The controls exclude incompatible choices; select
  **Default** as the additional wake source before selecting ECO, or leave ECO
  before enabling USB wake.
  **Never** disables the inactivity timer; it does not prevent manual standby.
- Keep **USB power / KW-1 mode** off for USB audio. Enabling it changes
  the primary speaker's USB port from audio input to power output.

These settings follow the [LSX II manual, sections 12 and 14.7](https://assets.kef.com/product-support/lsx-2/LSX_II_Product_Manual_EN_v9.pdf).
Other models can have different inputs and wake behavior.

Existing entity IDs and automation values remain unchanged. The control names
explain that `20 minutes` means ECO and `Default` means no additional wake input.
Use those same values in `select.select_option` actions.

If the USB device disappears, collect diagnostics before changing the input.
Select USB once and check whether the computer detects the speaker again. If KEF
reports `powerOn` and `usb` but the computer still has no USB device, investigate
the USB connection, hub, cable, and speaker's USB interface. Reloading the Home
Assistant integration does not reconnect a USB device to the computer. Avoid an
automation that repeatedly forces USB, since it would interrupt other inputs.

## Firmware updates

The update entity exposes supported firmware updates. Use a maintenance window
and follow the speaker's update requirements.

Update availability and versions always come from the speaker itself. When the
update dialog is opened, KEF's published release notes for the reported version
are fetched from kef.com; if that page is unreachable, the dialog simply shows
no notes. **Read release announcements** opens KEF's release notes page at the
section for the speaker's model.

Once a night, and whenever **Check for updates** is used in Settings > Updates
(or the `homeassistant.update_entity` action), the integration asks the speaker
to run its own firmware check. Nothing is installed by a check. The nightly
check falls between 02:30 and 04:00 Home Assistant time, when the speakers run
their own overnight update cycle, and each speaker has its own fixed time in
that window. A speaker that is offline, or is already checking, downloading, or
installing, is not asked. The XIO's wireless
subwoofer module has its own separate update check, which this integration does
not use; check it in the KEF Connect app.

Advanced users can upload a local `.swu` using `kef.install_firmware_file`.
The action requires the KEF **update entity** in `entity_id` and a `file_path`
accessible to Home Assistant. Use a file intended for the exact speaker model;
do not run firmware installation as a routine unattended automation.

## Troubleshooting

- **Speaker not found:** check its current IP and local connectivity. Manual
  setup does not depend on discovery succeeding.
- **Original LSX or LS50 Wireless fails to connect:** these speakers use the
  passwordless control service on TCP port 50001. A working speaker webpage or
  discovery announcement does not prove that this service is reachable from
  Home Assistant. Close other KEF clients, including KEF Control and any older
  integration, and retry setup with the current IPv4 address and a blank
  password. The integration briefly retries refused connections while the
  speaker releases a previous connection. If the control service stays
  unavailable, check network access from Home Assistant to port 50001 and try
  one speaker power-cycle while no firmware update is running.
- **Read works but control fails:** check whether firmware enabled a web UI
  password, then reauthenticate or reconfigure.
- **Playback action unavailable:** check the selected source and whether that
  source exposes the action.
- **Speaker unavailable:** check whether its saved address still responds. If
  its IPv4 address times out but its `.local` hostname works, reconfigure a
  modern speaker with that hostname. The integration retries without requiring
  the speaker to be removed.

Reproduce the problem once, then collect diagnostics before reloading or
restarting Home Assistant:

1. If setup fails, choose **Download setup diagnostics** on the failed setup
   form. The download works before a speaker entry exists. The link expires
   after 15 minutes; retry setup to get a new one.
2. For an existing speaker, open **Settings → Devices & services → KEF**, open
   the integration entry's menu, and choose **Download diagnostics**.
3. Attach the JSON file to your issue with the speaker model, firmware, and the
   action that failed.

Diagnostics collect recent failure types and recovery events automatically.
Connection failures identify the backend, port, and operation when available.
Legacy failures also identify the source, volume, or playback command, whether
the failure happened while connecting or waiting for a reply, the number of
connection attempts, and elapsed time. Source changes record the previous and
requested input, write acknowledgement, and the next device refresh outcome.
If another source write supersedes a pending refresh, the history records that
explicitly rather than claiming an intermediate input was observed.
An acknowledgement alone does not establish that the input changed successfully.
The health section distinguishes the actual last device refresh from Home
Assistant's cached-state health, which can stay successful during brief failures.
History is limited to 32 recent events, with repeated failures coalesced. Counts
and timestamps survive initialization retries and entry reloads in the current
Home Assistant session; restarting Home Assistant or removing the entry clears
them.
If automatic detection fails, the report retains both the modern HTTP and
legacy TCP probe failures so a closed control port can be distinguished from
an HTTP authentication or response problem.
Reports include version and connection-health details without passwords, speaker
addresses, private media details, or raw response bodies. Setup reports expire
after 15 minutes and only the latest 20 reports are retained. Review any file
before sharing it.

To capture a connection lost when switching an original LSX from Wi-Fi to Optical:

1. Select **Wi-Fi** using KEF Control or the remote and let the integration
   connect. Close KEF Control after that.
2. In the KEF entry's menu, choose **Enable debug logging**, then download a
   baseline diagnostics file.
3. Select **Opt** from Home Assistant. While the connection is failing, download
   diagnostics again, before reloading the entry or restarting Home Assistant.
4. Restore Wi-Fi using the remote, wait for the integration to recover, then
   choose **Disable debug logging** to download the log covering the transition
   and recovery. Download a final diagnostics file if recovery is incomplete.
5. Include whether selecting Optical with the physical remote causes the same
   loss of connection. Review logs for private details before sharing them.

For detailed logs on an existing entry, use **Enable debug logging** in that
same menu, reproduce the problem once, then choose **Disable debug logging**.
Home Assistant offers the log download. This does not require YAML edits or a
restart. Debug logs can include addresses and protocol data; remove personal
information before sharing them. The **Expose diagnostic sensors** option
controls extra entities and is not required for either download.

## Remove the integration

1. Disable or update automations and dashboard cards that reference the speaker.
2. Open **Settings → Devices & services → KEF**, open the menu for the speaker's
   integration entry, and choose **Delete**. Repeat for any other speakers you
   want to remove.
3. To uninstall the custom integration, delete all KEF entries first, then
   uninstall **KEF** through **Settings → Marketplace** on HA 2026.11 or newer,
   or through HACS on older HA versions. For a manual installation, remove
   `config/custom_components/kef`. Restart Home Assistant.

Entry deletion removes the HA connection configuration. KEF does not keep a
separate on-disk speaker cache. Recorder history, exported diagnostics, and
backups follow Home Assistant's retention or your own file-management settings;
they are not erased by this integration. Deletion does not factory-reset the
speaker, change its saved settings, or turn it off. It remains usable through
the vendor app and its other inputs.
