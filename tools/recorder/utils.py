"""
Utility functions for the recorder.
"""
import re
from typing import Union


def parse_duration(duration: Union[str, int, float]) -> float:
    """
    Parse a duration value to seconds.
    
    Args:
        duration: Duration as a number (seconds) or string with suffix (e.g., "5m", "30s")
                 Supported suffixes: 's' for seconds, 'm' for minutes
                 Default unit is seconds if no suffix is provided
    
    Returns:
        float: Duration in seconds
    
    Examples:
        >>> parse_duration(10)      # 10 seconds
        10.0
        >>> parse_duration("5m")    # 5 minutes = 300 seconds
        300.0
        >>> parse_duration("30s")   # 30 seconds
        30.0
        >>> parse_duration("1.5m")  # 1.5 minutes = 90 seconds
        90.0
        >>> parse_duration("1h")    # 1 hour
        3600.0
        >>> parse_duration("1d")    # 1 day
        86400.0
    """
    if isinstance(duration, (int, float)):
        return float(duration)
    
    if isinstance(duration, str):
        # Try to match pattern: number followed by optional suffix (s or m)
        match = re.match(r'^(\d+\.?\d*)\s*([smhd]?)$', duration.strip(), re.IGNORECASE)
        if match:
            value = float(match.group(1))
            suffix = match.group(2).lower()
            
            if suffix == 's':
                return value
            elif suffix == 'm':
                return value * 60
            elif suffix == 'h':
                return value * 3600
            elif suffix == 'd':
                return value * 86400
            else:
                return value  # Default to seconds if no suffix
    
    # If parsing fails, try to convert directly to float (fallback)
    try:
        return float(duration)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid duration format: {duration}. Use a number (seconds) or string with suffix (e.g., '5m', '30s')")

def format_duration(duration: float) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        duration: Duration in seconds

    Returns:
        str: Formatted duration string (e.g., "5m", "30s")

    Examples:
        >>> format_duration(300)   # 5 minutes
        '5m'
        >>> format_duration(30)    # 30 seconds
        '30s'
        >>> format_duration(90)    # 1.5 minutes
        '1m30s'
        >>> format_duration(3600)  # 1 hour
        '1h'
        >>> format_duration(86400) # 1 day
        '1d'
    """
    if duration < 60:
        return f"{duration:.1f}s"
    elif duration < 3600:
        minutes = int(duration // 60)
        sec = duration % 60
        return f"{minutes}m {sec:.0f}s"
    elif duration < 86400:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(duration // 86400)
        hours = int((duration % 86400) // 3600)
        return f"{days}d {hours}h"