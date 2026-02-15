"""
Starfy4 Translation Overlay Utils
"""

from . import systemcheck

def check_for_vlc() -> bool:
    """"
    Checks if VLC is installed.

    Returns:
        bool: True if VLC is installed, False otherwise.
    """

    return systemcheck.vlc_installed()