"""Security utility functions for file handling."""
import os


def validate_path(base_path: str, requested_path: str) -> str:
    """
    Safely validate and resolve a file path, preventing path traversal attacks.

    Args:
        base_path: The base directory that should contain the file
        requested_path: The requested file path

    Returns:
        The validated full path

    Raises:
        ValueError: If the path would escape the base directory
    """
    base_path = os.path.normpath(base_path)
    full_path = os.path.normpath(os.path.join(base_path, requested_path))

    if not full_path.startswith(base_path):
        raise ValueError('Path traversal attempt detected')

    return full_path


def get_uploaded_file_path(upload_folder: str, filename: str) -> str:
    """
    Safely get the full path for an uploaded file.

    Args:
        upload_folder: The upload directory
        filename: The filename (will be sanitized)

    Returns:
        The validated full path

    Raises:
        ValueError: If the filename is invalid or path traversal detected
    """
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename.startswith('.'):
        raise ValueError('Invalid filename')

    return validate_path(upload_folder, safe_filename)
