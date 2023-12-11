"""This package holds a database of model-to-manufacturer mappings.

The `manufacturers` directory contains .txt files for each Manufacturer enum
value, except for UNKNOWN. Each line in these files is a regular expression that
matches the model name or family for one of that manufacturer's devices.
"""

from __future__ import annotations

import os
import re

from collections import defaultdict
from enum import unique, Enum
from functools import cached_property
from re import Pattern

# Path to the directory containing manufacturer .txt files.
DB_PATH = os.path.dirname(__file__)

# Global mapping from manufacturer name to list of model family regexes.
_manufacturers: dict[Manufacturer, list[Pattern]] = defaultdict(list)


@unique
class Manufacturer(Enum):
  """Device manufacturer."""
  UNKNOWN = 'Unknown'
  # Please keep the remaining names sorted alphabetically.
  APPLE = 'Apple'
  TEAMGROUP = 'TeamGroup'


def get(model: str) -> Manufacturer:
  """Returns the manufacturer of a given model of device.

  This method matches the given model against each regex in the manufacturer
  database. It returns the corresponding manufacturer enum value for the first
  match. If no regex matches, it returns Manufacturer.UNKNOWN.

  Args:
    The model name or family of a device, e.g. "Apple SD/SM/TS...E/F/G SSDs".
  """
  if not _manufacturers:
    for manufacturer in Manufacturer:
      if manufacturer != Manufacturer.UNKNOWN:
        with open(os.path.join(DB_PATH, f'{manufacturer.name.lower()}.txt'), 'rt') as f:
          _manufacturers[manufacturer].extend(
              re.compile(line, flags=re.IGNORECASE) for line in f.read().splitlines())

  for manufacturer, regexes in _manufacturers.items():
    if any(regex.match(model) for regex in regexes):
      return manufacturer

  return Manufacturer.UNKNOWN
