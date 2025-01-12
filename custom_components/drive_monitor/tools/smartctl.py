"""Wrapper around the Smartmontools 'smartctl' command."""

import asyncio
import json
import logging

from enum import IntEnum

from ..devices.drive import DriveInfo, SSDInfo
from ..manufacturers import get as get_manufacturer
from ..types import JSON
from ..utils import async_cache

LOGGER = logging.getLogger(__name__)


class ReturnValue(IntEnum):
  """Non-successful exit statuses produced by smartctl."""
  COMMAND_LINE_DID_NOT_PARSE = 1
  DEVICE_OPEN_FAILED = 2
  SMART_COMMAND_FAILED = 4
  DISK_FAILING = 8
  PREFAIL_BEYOND_THRESHOLD = 16
  PREFAIL_BEYOND_THRESHOLD_PREVIOUSLY = 32
  ERROR_LOG_PRESENT = 64
  DEVICE_SELF_TEST_ERROR = 128


def parse_data_units(info: JSON, key: str) -> int | None:
  """Parses the given 'data units' value into a value in bytes."""
  if key in info:
    return info[key] * 512000  # Number of bytes in a data unit
  return None


def parse_exit_status(status: int) -> set[ReturnValue]:
  """Parses the smartctl exit status bit into an enum of statuses."""
  return {value for value in ReturnValue if status & value}


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

  async def get_drive_info(self, node: str) -> DriveInfo | None:
    """Returns details and S.M.A.R.T. attributes for the given drive.

    Args:
      node: The drive's Device Node, e.g. 'disk3'.
    """
    info = await self._execute('-a', node)

    exit_status = parse_exit_status(info['smartctl']['exit_status'])
    if exit_status & {ReturnValue.COMMAND_LINE_DID_NOT_PARSE, ReturnValue.DEVICE_OPEN_FAILED}:
      return None

    manufacturer = await get_manufacturer(info.get('model_family', info['model_name']))
    temperature = info.get('temperature')

    return DriveInfo(
        name=info['device']['name'],
        type=info['device']['type'],
        manufacturer=manufacturer,
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
        'smartctl', *args, '--json', close_fds=True, stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()

    try:
      return json.loads(stdout)
    except json.JSONDecodeError:
      LOGGER.error('Invalid output from "smartctl": %s', stdout)
      raise
