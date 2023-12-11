"""Wrapper around the MacOS Disk Utility 'diskutil' command."""

import asyncio
import logging
import plistlib
import re

from ..devices.drive import DriveID, DriveInfo
from ..devices.raid import RAIDDriveInfo, RAIDID, RAIDInfo, RAIDState, RAIDType
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


def get_first_visible_volume(container: PList) -> PList | None:
  """Returns the first user-visible volume in the given APFS container.

  A user-visible volume is one that would show up in the Disk Utility tree at
  the top level, i.e. it either has the System role or no role at all.
  """
  for volume in container['Volumes']:
    roles = set(volume['Roles'])
    if not roles or 'System' in roles:
      return volume
  return None


def parse_drive_info(drive: PList) -> RAIDDriveInfo:
  """Parses a diskutil RAID Member plist into a RAIDDriveInfo."""
  return RAIDDriveInfo(
      id=drive['AppleRAIDMemberUUID'],
      # Use only the base node, i.e. 'disk5' instead of 'disk5s2'. That tends to
      # look cleaner, and since RAID member drives don't show up in 'afps list'
      # there's no point in keeping the full node name.
      node=base_node(drive['BSD Name']),
      state=parse_state(drive['MemberStatus']))


def parse_state(state: str) -> RAIDState:
  """Parses a diskutil RAID or RAID Member status into a RAIDState."""
  return {
    'Online': RAIDState.ONLINE,
    'Offline': RAIDState.OFFLINE,
    'Rebuild': RAIDState.REBUILD,
  }.get(state, RAIDState.UNKNOWN)


def parse_type(type: str) -> RAIDType:
  """Parses a diskutil RAID level into a RAIDType."""
  return {
    'Span': RAIDType.SPAN,
    'Stripe': RAIDType.STRIPE,
    'Mirror': RAIDType.MIRROR,
  }.get(type, RAIDType.UNKNOWN)


class DiskUtil:
  """Wrapper around the MacOS Disk Utility 'diskutil' command."""

  async def get_drives(self) -> list[DriveID]:
    """Enumerates and returns all physical drives present on the system.

    This includes drives that are grouped together into RAIDs.
    """
    info, raid_ids = await asyncio.gather(self._execute('apfs', 'list'), self.get_raids())

    # Unfortunately 'apfs list' doesn't include RAID members. Query those
    # separately, and generate a mapping that we can then use to merge them.
    raids = {raid.id: await self.get_raid_info(raid.node) for raid in raid_ids}

    drives = []
    for container in info['Containers']:
      # Ignore containers that don't have any user-visible volumes
      if not get_first_visible_volume(container):
        continue
      for drive in container['PhysicalStores']:
        device_identifier = drive['DeviceIdentifier']
        if device_identifier == container['DesignatedPhysicalStore']:
          drive_id = drive['DiskUUID']
          if drive_id in raids:
            drives.extend(DriveID(member.id, member.node, raid=drive_id)
                          for member in raids[drive_id].members)
          else:
            drives.append(DriveID(drive_id, device_identifier))

    return drives

  async def get_raids(self) -> list[RAIDID]:
    """Enumerates and returns all RAIDs present on the system."""
    info = await self._execute('appleraid', 'list')
    return [RAIDID(id=raid['AppleRAIDSetUUID'], node=raid['BSD Name'])
            for raid in info.get('AppleRAIDSets', [])]

  async def get_drive_info(self, node: str) -> DriveInfo | None:
    """Returns capacity and usage for the given drive.

    Args:
      node: The drive's Device Node, e.g. 'disk3'.
    """
    info = await self._execute('apfs', 'list')

    for container in info['Containers']:
      if node == container['DesignatedPhysicalStore']:
        return DriveInfo(
            name=get_first_visible_volume(container)['Name'],
            capacity=container['CapacityCeiling'],
            usage=container['CapacityCeiling'] - container['CapacityFree'])

    return None

  async def get_raid_info(self, node: str) -> RAIDInfo:
    """Returns details and state for the given RAID.

    Args:
      node: The RAID's Device Node, e.g. 'disk3'.
    """
    info = await self._execute('appleraid', 'list')

    for raid in info.get('AppleRAIDSets', []):
      if raid['BSD Name'] == node:
        return RAIDInfo(
            name=raid['Name'],
            type=parse_type(raid['Level']),
            state=parse_state(raid['Status']),
            members=[parse_drive_info(drive) for drive in raid['Members']],
            capacity=int(raid['Size']))

    raise DeviceNotFoundError(f'There is no RAID with node "{node}".')

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
