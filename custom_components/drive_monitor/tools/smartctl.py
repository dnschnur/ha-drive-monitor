"""Wrapper around the Smartmontools 'smartctl' command."""

import asyncio
import json
import logging

from ..devices.drive import DriveInfo, SSDInfo
from ..manufacturers import get as get_manufacturer
from ..types import JSON
from ..utils import async_cache

LOGGER = logging.getLogger(__name__)


def parse_data_units(info: JSON, key: str) -> int | None:
  """Parses the given 'data units' value into a value in bytes."""
  if key in info:
    return info[key] * 512000  # Number of bytes in a data unit
  return None

def parse_smart_state(info: JSON) -> bool:
  """Parses S.M.A.R.T. details into a pass/fail state."""
  if smart_status := info.get('smart_status'):
    return smart_status.get('passed', False)
  return False


def parse_ssd_info(info: JSON) -> SSDInfo | None:
  """Parses additional SSD-specific fields, if any, into an SSDInfo."""
  if 'nvme_smart_health_information_log' not in info:
    return None

  nvme_info = info['nvme_smart_health_information_log']
  return SSDInfo(
      bytes_read=parse_data_units(nvme_info, 'data_units_read'),
      bytes_written=parse_data_units(nvme_info, 'data_units_written'),
      available_spare=nvme_info.get('available_spare'),
      available_spare_threshold=nvme_info.get('available_spare_threshold'),
      unsafe_shutdowns=nvme_info.get('unsafe_shutdowns'))


class SmartCtl:
  """Wrapper around the Smartmontools 'smartctl' command."""

  async def get_drive_info(self, node: str) -> DriveInfo:
    """Returns details and S.M.A.R.T. attributes for the given drive.

    Args:
      node: The drive's Device Node, e.g. 'disk3'.
    """
    info = await self._execute('-a', node)

    exit_code = info['smartctl']['exit_status']
    if exit_code != 0:
      return DriveInfo(name=node)

    temperature = info.get('temperature')

    return DriveInfo(
        name=info['device']['name'],
        type=info['device']['type'],
        manufacturer=get_manufacturer(info.get('model_family', info['model_name'])),
        model=info['model_name'],
        serial_number=info['serial_number'],
        firmware_version=info['firmware_version'],
        smart_passed=parse_smart_state(info),
        temperature=temperature['current'] if temperature else None,
        ssd_info=parse_ssd_info(info))

  @async_cache(ttl=10)  # Cache the result and re-execute only every 10 seconds
  async def _execute(self, *args: list[str]) -> JSON:
    """Executes 'smartctl' with the given arguments, returning parsed output."""
    LOGGER.debug('Executing "smartctl %s --json"', ' '.join(args))
    process = await asyncio.create_subprocess_exec(
        'smartctl', *args, '--json', stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()

    try:
      return json.loads(stdout)
    except json.JSONDecodeError:
      LOGGER.error('Invalid output from "smartctl": %s', stdout)
      raise
