import requests
import logging
from typing import Tuple, Optional

logger = logging.getLogger("GameDrop.Updater")

def check_for_updates(current_version: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check for updates on GitHub.
    
    Args:
        current_version: The current version string (e.g., "1.2.0")
        
    Returns:
        Tuple containing:
        - bool: True if update is available, False otherwise
        - str: The latest version string (e.g., "1.2.1") or None if check failed
        - str: The URL to the latest release or None if check failed
    """
    url = "https://api.github.com/repos/ahiser24/GameDrop/releases/latest"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        latest_tag = data.get("tag_name", "").lstrip("v")
        html_url = data.get("html_url", "")
        
        if not latest_tag:
            logger.warning("Could not find tag_name in GitHub response")
            return False, None, None
            
        # simple semantic version comparison
        if _is_newer_version(current_version, latest_tag):
            logger.info(f"Update available: {latest_tag} (Current: {current_version})")
            return True, latest_tag, html_url
        else:
            logger.info(f"Up to date. Latest: {latest_tag} (Current: {current_version})")
            return False, latest_tag, html_url
            
    except requests.RequestException as e:
        logger.error(f"Error checking for updates: {e}")
        return False, None, None
    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {e}")
        return False, None, None

def _is_newer_version(current: str, latest: str) -> bool:
    """
    Compare two version strings.
    Returns True if latest is newer than current.
    """
    try:
        c_parts = [int(p) for p in current.split('.')]
        l_parts = [int(p) for p in latest.split('.')]
        
        # Pad with zeros if lengths differ (e.g., 1.2 vs 1.2.1)
        while len(c_parts) < len(l_parts):
            c_parts.append(0)
        while len(l_parts) < len(c_parts):
            l_parts.append(0)
            
        return l_parts > c_parts
    except ValueError:
        logger.warning(f"Version parsing failed for {current} or {latest}")
        return False
