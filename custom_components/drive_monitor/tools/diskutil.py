"""Wrapper around the MacOS Disk Utility 'diskutil' command."""

import asyncio
import logging
import plistlib
import re

from ..devices.device import NodeNotFoundError, StoreID
from ..devices.drive import DriveInfo
from ..devices.raid import RAIDDriveInfo, RAIDInfo, RAIDState, RAIDType
from ..types import PList
from ..utils import async_cache

BASE_NODE_REGEX = re.compile(r'disk\d+')

LOGGER = logging.getLogger(__name__)


def base_node(node: str) -> str:
  """Returns the base of a disk node, with any suffixes stripped.

  For example, 'disk1s0' is returned as simply 'disk1'.

  If an invalid node value is passed, it is returned unchanged.
  """
  if match := BASE_NODE_REGEX.match(node):
    return match[0]
  return node


def parse_drive_info(drive: PList) -> RAIDDriveInfo:
  """Parses a diskutil RAID Member plist into a RAIDDriveInfo."""
  return RAIDDriveInfo(
      id=drive['AppleRAIDMemberUUID'],
      node=drive['BSD Name'],
      state=parse_state(drive['MemberStatus']))


def parse_state(state: str) -> RAIDState:
  """Parses a diskutil RAID or RAID Member status into a RAIDState."""
  return {
    'Online': RAIDState.ONLINE,
    'Offline': RAIDState.OFFLINE,
    'Rebuild': RAIDState.REBUILD,
  }.get(type, RAIDState.UNKNOWN)


def parse_type(type: str) -> RAIDType:
  """Parses a diskutil RAID level into a RAIDType."""
  return {
    'Span': RAIDType.SPAN,
    'Stripe': RAIDType.STRIPE,
    'Mirror': RAIDType.MIRROR,
  }.get(type, RAIDType.UNKNOWN)


class DiskUtil:
  """Wrapper around the MacOS Disk Utility 'diskutil' command."""

  async def get_drives(self) -> list[StoreID]:
    """Enumerates and returns all physical drives present on the system.

    This includes drives that are grouped together into RAIDs.
    """
    info, raid_ids = await asyncio.gather(self._execute('apfs', 'list'), self.get_raids())

    # Unfortunately 'apfs list' doesn't include RAID members. Query those
    # separately, and generate a mapping that we can then use to merge them.
    raids = await asyncio.gather(*[self.get_raid_info(raid_id.node) for raid_id in raid_ids])
    raid_members = {raid.id: raid.members for raid in raids}

    drives = []
    for container in info['Containers']:
      for drive in container['PhysicalStores']:
        drive_id = drive['DiskUUID']
        if drive_id in raid_members:
          drives.extend(StoreID(member.id, member.node) for member in raid_members[drive_id])
        else:
          drives.append(StoreID(drive_id, base_node(drive['DeviceIdentifier'])))

    return drives

  async def get_raids(self) -> list[StoreID]:
    """Enumerates and returns all RAIDs present on the system."""
    info = await self._execute('appleraid', 'list')
    return [StoreID(id=raid['AppleRAIDSetUUID'], node=base_node(raid['BSD Name']))
            for raid in info.get('AppleRAIDSets', [])]

  async def get_drive_info(self, node: str) -> DriveInfo:
    """Returns capacity and usage for the given drive.

    Args:
      node: The drive's Device Node, e.g. 'disk3'.
    """
    info = await self._execute('apfs', 'list')

    for container in info['Containers']:
      for drive in container['PhysicalStores']:
        if node == base_node(drive['DeviceIdentifier']):
          return DriveInfo(
              capacity=container['CapacityCeiling'],
              usage=container['CapacityCeiling'] - container['CapacityFree'])

    raise NodeNotFoundError(f'There is no drive with node "{node}".')

  async def get_raid_info(self, node: str) -> RAIDInfo:
    """Returns details and state for the given RAID.

    Args:
      node: The RAID's Device Node, e.g. 'disk3'.
    """
    info = await self._execute('appleraid', 'list')

    for raid in info.get('AppleRAIDSets', []):
      if base_node(raid['BSD Name']) == node:
        return RAIDInfo(
            name=raid['Name'],
            type=parse_type(raid['Level']),
            state=parse_state(raid['Status']),
            members=[parse_drive_info(drive) for drive in raid['Members']],
            capacity=int(raid['Size']))

    raise NodeNotFoundError(f'There is no RAID with node "{node}".')

  @async_cache(ttl=10)  # Cache the result and re-execute only every 10 seconds
  async def _execute(self, *args: list[str]) -> PList:
    """Executes 'diskutil' with the given arguments, returning parsed output."""
    LOGGER.debug(f'Executing "diskutil %s -plist"', ' '.join(args))
    process = await asyncio.create_subprocess_exec(
        'diskutil', *args, '-plist', stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()

    try:
      return plistlib.loads(stdout)
    except plistlib.InvalidFileException:
      LOGGER.error('Invalid output from "diskutil": %s', stdout)
      raise
