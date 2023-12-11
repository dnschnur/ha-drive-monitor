"""Source implementation for MacOS.

On MacOS we use `diskutil` to query drives and RAIDs attached to the system,
including some additional information such as RAID status. To query the state
of individual drives we use `smartctl`.
"""

import asyncio

from functools import cached_property

from ..devices.device import DeviceNotFoundError
from ..devices.drive import DriveID, DriveInfo
from ..devices.raid import RAIDID, RAIDInfo

from ..tools.diskutil import DiskUtil
from ..tools.smartctl import SmartCtl

from .source import Source


class MacOSSource(Source):
  """Source implementation for MacOS."""

  @cached_property
  def _diskutil(self) -> DiskUtil:
    """Wrapper around the `diskutil` command-line tool."""
    return DiskUtil()

  @cached_property
  def _smartctl(self) -> SmartCtl:
    """Wrapper around the `smartctl` command-line tool."""
    return SmartCtl()

  async def get_drives(self) -> list[DriveID]:
    """Enumerates and returns all physical drives present on the system.

    This includes drives that are grouped together into RAIDs.
    """
    return await self._diskutil.get_drives()

  async def get_raids(self) -> list[RAIDID]:
    """Enumerates and returns all RAIDs present on the system."""
    return await self._diskutil.get_raids()

  async def get_drive_info(self, node: str) -> DriveInfo:
    """Returns details and S.M.A.R.T. attributes for the given drive.

    Args:
      node: The drive's Device Node, e.g. 'disk3'.
    """
    diskutil_info, smartctl_info = await asyncio.gather(
        self._diskutil.get_drive_info(node), self._smartctl.get_drive_info(node))

    if not (diskutil_info or smartctl_info):
      raise DeviceNotFoundError(f'There is no drive with node "{node}".')

    # We can get most drive info from smartctl, but name, capacity, and usage
    # are only reliably available via diskutil's APFS container stats.
    if diskutil_info and smartctl_info:
      smartctl_info.name = diskutil_info.name
      smartctl_info.capacity = diskutil_info.capacity
      smartctl_info.usage = diskutil_info.usage

    return smartctl_info or diskutil_info

  async def get_raid_info(self, node: str) -> RAIDInfo:
    """Returns details and state for the given RAID.

    Args:
      node: The RAID's Device Node, e.g. 'disk3'.
    """
    return await self._diskutil.get_raid_info(node)
