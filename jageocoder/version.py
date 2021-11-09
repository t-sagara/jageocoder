import re
from typing import Optional

import jageocoder

VERSION_REGEX = re.compile(
    r'^'               # start of string
    r'v?'              # literal v character
    r'(?P<major>\d+)'  # major number
    r'\.'              # literal . character
    r'(?P<minor>\d+)'  # minor number
    r'(\.?)'           # literal . character
    r'(?P<micro>\d+)'  # micro number
    r'(?P<release>.+)'  # release level
)


def version_info(version_str: Optional[str] = None):
    """
    Get the version information in dict.

    Parameters
    ----------
    version_str: str, optional
        The version string to be parsed.
        If ommitted, use the package version.

    Return
    ------
    dict
        Version information with major, minor, micro and
        release fields.
    """
    if version_str is None:
        version_str = jageocoder.__version__

    match = VERSION_REGEX.search(version_str)
    if match:
        return match.groupdict()

    return {
        "major": None, "minor": None,
        "micro": None, "release": None
    }


def version():
    return jageocoder.__version__


def dictionary_version():
    return jageocoder.__dictionary_version__
