# Drive Monitor

Drive Monitor is a [Home Assistant](https://home-assistant.io) (HA) integration
that monitors storage devices attached to the HA host machine.

Unlike the built-in
[System Monitor](https://www.home-assistant.io/integrations/systemmonitor/)
integration, this includes all drives attached to the system, including RAIDs.
It also exposes far more information about each, including temperature, SSD
endurance, RAID health, etc.

This lets you set up alerts that provide advance warning before a drive fails.

## Installation

1. Install dependencies for your platform:

   ### MacOS

   * [smartmontools](https://www.smartmontools.org/)

     The easiest way to install is via [Homebrew](https://brew.sh/):

     ```shell
     brew install smartmontools
     ```

2. Copy the `drive_monitor` directory to your `custom_components` directory.

3. [<img src="https://my.home-assistant.io/badges/config_flow_start.svg">](https://my.home-assistant.io/redirect/config_flow_start?domain=drive_monitor
   from the HA UI.

This integration is not yet available on [HACS](https://hacs.xyz/).

> Warning: Currently this integration only supports Home Assistant Core on a
> MacOS host, since it uses `diskutil` for discovery of attached devices. It's
> designed to be extensible to other platforms, but that does require some code
> and understanding of tools or system commands similar to `diskutil`. See the
> [Contribution Guidelines](CONTRIBUTING.md) for details.

## Usage

On start-up, the integration discovers all drives and RAIDs attached to the host
machine. Each drive and RAID is exposed as a Device in HA.

For software RAIDs on platforms that support it (e.g. MacOS), the set of drives
includes those that are part of a RAID. That enables monitoring of per-drive
health metrics such as temperature and SSD wear thresholds, which wouldn't
appear in the overall RAID status until after a drive fails.

Each Drive has the following entities:

- **State**: State of the drive, one of the following values:

  - *Healthy*: Drive is passing S.M.A.R.T. checks.
  - *Unhealthy*: Drive is failing S.M.A.R.T. checks.
  - *Unknown*: Unable to query the drive's state, probably because it doesn't
    support S.M.A.R.T or this integration doesn't support querying it.

- **Capacity**: Total capacity of the drive, in bytes.

- **Usage**: Usage across all volumes on the drive, in bytes. 

- **Temperature**: Internal drive temperature.

Each RAID has the following entities:

- **State**: State of the RAID, one of the following values:

  - *Online*: All RAID members are healthy.
  - *Offline*: One or more RAID members are unhealthy, and the RAID is degraded.
  - *Rebuild*: All RAID members are healthy, but some previous issue caused the
    overall state of the RAID to become degraded, and it is rebuilding itself.
  - *Unknown*: Unable to query the RAID's state.

- **Capacity**: Total capacity of the drive, in bytes.

- **Usage**: Usage across all volumes on the drive, in bytes. 

Drives and RAIDs also populate standard Device attributes such as Manufacturer,
Model, and Firmware Version, if available.

> Warning: If you have a managed installation, i.e. HA OS/Container/Supervised,
> then some of these entities may have unknown / missing values, and you may not
> be able to discover underlying RAIDs. Although I haven't tested a VM myself,
> the hosts that I'm familiar with don't support S.M.A.R.T. on virtual disks,
> so at minimum drive health status will appear as *Unknown*.

## Contributing

Please read the [Contribution Guidelines](CONTRIBUTING.md) before creating a
pull request.
