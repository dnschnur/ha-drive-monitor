"""Common data classes and type aliases shared across the component."""

from typing import Any


# JSON parsed by the stdlib 'json' library
JSON = dict[str, Any]

# PLists parsed by the stdlib 'plistlib' library
PList = dict[str, Any]

# Home Assistant configuration YAML
YAML = dict[str, Any]
