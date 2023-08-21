# Contribution Guidelines

I built this integration mainly for my own personal use. I run HA Core on a Mac
Mini that acts as a central file/media/automation server for my home. It has an
external data drive, currently a dual M.2 NVMe SSD enclosure whose drives are
merged into a software RAID (mirrored) set.

This integration is built for that environment, designed to monitor the health
of the RAID and the temperature, TBW, and S.M.A.R.T. status of the two SSDs and
the main OS SSD, alerting me to any emerging issues.

There is of course existing software that can do that, but integrating it into
HA let me use my existing alerting setup, plus this was just a nice opportunity
to finally learn how to write a HA integration.

I've put this up here in case anyone finds it useful, but it's a hobby project,
and I don't want to spend much time maintaining it. So if you want to create a
pull request, you're going to have to put some extra thought and work into it,
to make it something that I can merge easily.

Please start by reading the [Rules](#rules) and [Architecture](#architecture)
sections below.

## Rules

1. Your changes must include docstrings, comments where needed, and updates
   to documentation (e.g. [README.md](README.md)) if it becomes out-of-date.

   Please check grammar, spelling, and punctuation before sending the PR.

2. Your changes must follow the style of the existing code, in terms of spacing,
   indentation, capitalization, line length, variable naming, etc.

3. If your change contains a bunch of intermediate commits that make it harder
   to understand, please rebase to clean it up before creating the PR.

## Architecture

On start-up, the integration creates a
[`DeviceManager`](drive_monitor/manager.py) and calls its `initialize` method.
That uses a [`Source`](drive_monitor/sources/source.py) to discover the storage
devices on the system, and creates a [`Device`](drive_monitor/devices/device.py)
for each one.

A [`Source`](drive_monitor/sources/source.py) is a wrapper around the logic for
discovering and updating devices for a particular operating system. The
[`sources`](drive_monitor/sources) package contains one module for each
supported OS, e.g. [`macos.py`](drive_monitor/sources/macos.py).

Discovering and updating devices usually requires running a command-line tool
and parsing its output. Since some tools, e.g. `smartctl`, are cross-platform,
rather than duplicating code across sources, it's factored out into a module
for each tool, under the [`tools`](drive_monitor/tools) package.

There is also a [`manufacturers`](drive_monitor/manufacturers) package that
helps map device model names or model families to manufacturers. For each
`Manufacturer` enum value there is a `.txt` file that holds a list of regexes
for known values for that manufacturer.

A [`Device`](drive_monitor/devices/device.py) is a wrapper around all of the
information for one storage device. It is an abstract base class, extended by
concrete device types such as [Drive](drive_monitor/devices/drive.py) and
[RAID](drive_monitor/devices/raid.py).

This information includes device attributes like the manufacturer, model, etc.
plus a list of HA Entities that record information about the device, like
temperature, disk capacity, S.M.A.R.T. status, etc.

Once the [`DeviceManager`](drive_monitor/manager.py) is initialized, and has
discovered attached devices, the integration asks HA to initialize the Platform
for each entity type; [`sensor`](drive_monitor/sensor.py), binary sensor, etc.
That iterates over all devices and adds all entities of that type to HA.

> Note: If you're thinking that this is a bit over-engineered, you're absolutely
> correct. Partly that's because over-engineering and making code unnecessarily
> extensible is fun. It's also because the HA developer docs are pretty awful,
> and abstractions like the `Device` class helped with the trial and error.
