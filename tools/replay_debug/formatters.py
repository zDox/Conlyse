"""
Formatting utilities for the Replay Debug CLI Tool.
"""
from datetime import datetime, UTC
from .constants import *


def format_timestamp(ts_ms: int) -> str:
    """Format a timestamp in milliseconds to ISO format string.
    
    Args:
        ts_ms: Timestamp in milliseconds
        
    Returns:
        ISO formatted timestamp string
    """
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).isoformat()


def format_patch_label(from_ts: int, to_ts: int, max_width: int) -> str:
    """Format a patch label with timestamps.
    
    Args:
        from_ts: Starting timestamp
        to_ts: Ending timestamp
        max_width: Maximum width for the label
        
    Returns:
        Formatted patch label
    """
    label = f"{from_ts}→{to_ts}"
    if len(label) > max_width:
        label = f"...{label[-(max_width-3):]}"
    return label


def truncate_string(s: str, max_length: int) -> str:
    """Truncate a string to a maximum length.
    
    Args:
        s: String to truncate
        max_length: Maximum length
        
    Returns:
        Truncated string with "..." if needed
    """
    if len(s) > max_length:
        return s[:(max_length-3)] + "..."
    return s


def format_operation_path(path: list) -> str:
    """Format an operation path as a string.
    
    Args:
        path: Path components as a list
        
    Returns:
        Path joined with "/"
    """
    return "/".join(str(p) for p in path)


def print_separator(width: int):
    """Print a separator line.
    
    Args:
        width: Width of the separator
    """
    print("-" * width)


def print_patch_list_header():
    """Print the header for patch list output."""
    print(f"{'#':<{COLUMN_WIDTH_INDEX}} {'From Timestamp':<{COLUMN_WIDTH_TIMESTAMP}} {'To Timestamp':<{COLUMN_WIDTH_TIMESTAMP}} {'Direction':<{COLUMN_WIDTH_DIRECTION}} {'Ops':<{COLUMN_WIDTH_OPS}}")
    print_separator(SEPARATOR_WIDTH_COMPACT)


def print_patch_list_row(index: int, from_ts: int, to_ts: int, direction: str, ops_count: int):
    """Print a single row in the patch list.
    
    Args:
        index: 1-based index of the patch
        from_ts: Starting timestamp
        to_ts: Ending timestamp
        direction: "Forward" or "Backward"
        ops_count: Number of operations
    """
    from_dt = format_timestamp(from_ts)
    to_dt = format_timestamp(to_ts)
    print(f"{index:<{COLUMN_WIDTH_INDEX}} {from_dt:<{COLUMN_WIDTH_TIMESTAMP}} {to_dt:<{COLUMN_WIDTH_TIMESTAMP}} {direction:<{COLUMN_WIDTH_DIRECTION}} {ops_count:<{COLUMN_WIDTH_OPS}}")


def print_operations_header(full_width: bool):
    """Print the header for operations output.
    
    Args:
        full_width: If True, use full width format
    """
    if full_width:
        print_separator(SEPARATOR_WIDTH_FULL)
        print(f"{'#':<{COLUMN_WIDTH_INDEX}} {'Patch':<{COLUMN_WIDTH_PATCH_FULL}} {'Idx':<{COLUMN_WIDTH_INDEX}} {'Dir':<{COLUMN_WIDTH_DIRECTION}} {'Type':<{COLUMN_WIDTH_TYPE}} {'Path':<{COLUMN_WIDTH_PATH_FULL}} {'Value'}")
        print_separator(SEPARATOR_WIDTH_FULL)
    else:
        print_separator(SEPARATOR_WIDTH_COMPACT)
        print(f"{'#':<{COLUMN_WIDTH_INDEX}} {'Patch':<{COLUMN_WIDTH_PATCH}} {'Idx':<{COLUMN_WIDTH_INDEX}} {'Dir':<{COLUMN_WIDTH_DIRECTION}} {'Type':<{COLUMN_WIDTH_TYPE}} {'Path':<{COLUMN_WIDTH_PATH_COMPACT}} {'Value':<{COLUMN_WIDTH_VALUE_COMPACT}}")
        print_separator(SEPARATOR_WIDTH_COMPACT)


def print_operation_row(op_num: int, patch_label: str, patch_index: int, direction: str, 
                        op_type: str, path_str: str, value_str: str, full_width: bool):
    """Print a single operation row.
    
    Args:
        op_num: Operation number
        patch_label: Formatted patch label
        patch_index: Index of the patch (1-based)
        direction: "Forward" or "Backward"
        op_type: Operation type (a/p/r)
        path_str: Formatted path string
        value_str: Formatted value string
        full_width: If True, don't truncate values
    """
    if full_width:
        print(f"{op_num:<{COLUMN_WIDTH_INDEX}} {patch_label:<{COLUMN_WIDTH_PATCH_FULL}} {patch_index:<{COLUMN_WIDTH_INDEX}} {direction:<{COLUMN_WIDTH_DIRECTION}} {op_type:<{COLUMN_WIDTH_TYPE}} {path_str:<{COLUMN_WIDTH_PATH_FULL}} {value_str}")
    else:
        print(f"{op_num:<{COLUMN_WIDTH_INDEX}} {patch_label:<{COLUMN_WIDTH_PATCH}} {patch_index:<{COLUMN_WIDTH_INDEX}} {direction:<{COLUMN_WIDTH_DIRECTION}} {op_type:<{COLUMN_WIDTH_TYPE}} {path_str:<{COLUMN_WIDTH_PATH_COMPACT}} {value_str:<{COLUMN_WIDTH_VALUE_COMPACT}}")


def print_overview_header():
    """Print the header for operations overview."""
    print()
    print(f"{'State':<{COLUMN_WIDTH_STATE}} {'Add':<{COLUMN_WIDTH_COUNT}} {'Replace':<{COLUMN_WIDTH_COUNT}} {'Remove':<{COLUMN_WIDTH_COUNT}} {'Total':<{COLUMN_WIDTH_COUNT}}")
    print_separator(SEPARATOR_WIDTH_OVERVIEW)


def print_overview_row(state_name: str, add_count: int, replace_count: int, remove_count: int, total_count: int):
    """Print a single row in the overview.
    
    Args:
        state_name: Name of the state
        add_count: Number of add operations
        replace_count: Number of replace operations
        remove_count: Number of remove operations
        total_count: Total operations
    """
    print(f"{state_name:<{COLUMN_WIDTH_STATE}} {add_count:<{COLUMN_WIDTH_COUNT}} {replace_count:<{COLUMN_WIDTH_COUNT}} {remove_count:<{COLUMN_WIDTH_COUNT}} {total_count:<{COLUMN_WIDTH_COUNT}}")
