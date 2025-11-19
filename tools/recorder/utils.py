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
    """
    if isinstance(duration, (int, float)):
        return float(duration)
    
    if isinstance(duration, str):
        # Try to match pattern: number followed by optional suffix (s or m)
        match = re.match(r'^(\d+\.?\d*)\s*([sm]?)$', duration.strip(), re.IGNORECASE)
        if match:
            value = float(match.group(1))
            suffix = match.group(2).lower()
            
            if suffix == 'm':
                return value * 60
            else:  # 's' or no suffix defaults to seconds
                return value
    
    # If parsing fails, try to convert directly to float (fallback)
    try:
        return float(duration)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid duration format: {duration}. Use a number (seconds) or string with suffix (e.g., '5m', '30s')")
