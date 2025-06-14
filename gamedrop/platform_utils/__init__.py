"""
Platform utilities for GameDrop
Makes cross-platform functions available throughout the app
"""
from .detection import (
    is_windows,
    is_linux,
    is_steam_deck,
    get_linux_distro_info,
    has_vaapi_support,
    get_display_server
)

__all__ = [
    'is_windows',
    'is_linux',
    'is_steam_deck',
    'get_linux_distro_info',
    'has_vaapi_support',
    'get_display_server'
]