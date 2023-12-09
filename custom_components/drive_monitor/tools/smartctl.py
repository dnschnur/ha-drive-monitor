"""Wrapper around the Smartmontools 'smartctl' command."""

import asyncio
import json
import logging

from ..devices.drive import DriveInfo, SSDInfo
from ..manufacturers import get as get_manufacturer
from ..types import JSON
from ..utils import async_cache

LOGGER = logging.getLogger(__name__)


def parse_smart_state(info: JSON) -> bool:
  """Parses S.M.A.R.T. details into a pass/fail state."""
  smart_status = info.get('smart_status', None)
  if not smart_status:
    return False
  return smart_status.get('passed', False)


def parse_ssd_info(info: JSON) -> SSDInfo | None:
  """Parses additional SSD-specific fields, if any, into an SSDInfo."""
  if 'nvme_smart_health_information_log' not in info:
    return None

  nvme_info = info['nvme_smart_health_information_log']
  return SSDInfo(
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
        manufacturer=get_manufacturer(info['model_family'] or info['model_name']),
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
