"""Utility functions"""

from .logger import get_logger
from .helpers import (
    flatten_dict,
    chunk_list,
    safe_get,
    format_bytes,
    validate_taxpayer_id,
    clean_taxpayer_id,
    normalize_field_name,
    extract_taxpayer_id_from_record,
    normalize_record_fields,
    smart_merge_records,
    retry_on_exception
)
from .menu import (
    MenuItem,
    Menu,
    ProgressMenu,
    show_banner,
    show_success,
    show_error,
    show_warning,
    show_info,
    confirm_action,
    select_from_list,
    display_stats,
    create_panel
)
from .progress_manager import ProgressManager
from .checksum import generate_export_checksum, verify_export_file, FileChecksum

__all__ = [
    'get_logger',
    'flatten_dict',
    'chunk_list',
    'safe_get',
    'format_bytes',
    'validate_taxpayer_id',
    'clean_taxpayer_id',
    'normalize_field_name',
    'extract_taxpayer_id_from_record',
    'normalize_record_fields',
    'smart_merge_records',
    'retry_on_exception',
    'MenuItem',
    'Menu',
    'ProgressMenu',
    'show_banner',
    'show_success',
    'show_error',
    'show_warning',
    'show_info',
    'confirm_action',
    'select_from_list',
    'display_stats',
    'create_panel',
    'ProgressManager',
    'generate_export_checksum',
    'verify_export_file',
    'FileChecksum'
]