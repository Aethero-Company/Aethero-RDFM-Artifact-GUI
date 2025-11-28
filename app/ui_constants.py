"""
UI Constants - Centralized configuration for UI dimensions,
    timing, and other magic numbers

This module provides a single source of truth for all UI-related constants
to improve maintainability and consistency across the application.
"""

# =============================================================================
# GRID & SPACING
# =============================================================================

# Standard padding values used throughout the application
STANDARD_PAD: int = 5  # Standard padx/pady for most widgets
BUTTON_PAD: int = 2  # Padding between buttons in button frames
SMALL_PAD: int = 2  # Small padding for compact layouts
MEDIUM_PAD: int = 10  # Medium padding for section spacing
LARGE_PAD: int = 15  # Large padding for major sections

# Pack side padding
PACK_PADX: int = 5
PACK_PADY: int = 5

# =============================================================================
# WINDOW SIZES
# =============================================================================

# Loading/splash window
LOADING_WINDOW_WIDTH: int = 450
LOADING_WINDOW_HEIGHT: int = 220

# Main application window
MAIN_WINDOW_WIDTH: int = 1400
MAIN_WINDOW_HEIGHT: int = 950
MAIN_WINDOW_GEOMETRY: str = f"{MAIN_WINDOW_WIDTH}x{MAIN_WINDOW_HEIGHT}"

# Header dimensions
HEADER_HEIGHT: int = 50

# =============================================================================
# LOGO & IMAGE SIZES
# =============================================================================

# Logo thumbnail sizes (width, height)
SPLASH_LOGO_SIZE: tuple[int, int] = (200, 60)
HEADER_LOGO_SIZE: tuple[int, int] = (160, 40)

# =============================================================================
# OUTPUT AREA DIMENSIONS
# =============================================================================

# Default output text area dimensions (in characters)
OUTPUT_AREA_HEIGHT: int = 15
OUTPUT_AREA_WIDTH: int = 80

# =============================================================================
# TIMING VALUES (MILLISECONDS)
# =============================================================================

# Queue processing interval
QUEUE_POLL_INTERVAL_MS: int = 100

# Auto-refresh interval for data (in seconds)
AUTO_REFRESH_INTERVAL_SEC: int = 300  # 5 minutes

# Status message display durations
STATUS_MESSAGE_SHORT_MS: int = 3000  # 3 seconds
STATUS_MESSAGE_LONG_MS: int = 5000  # 5 seconds
LOADING_COMPLETE_DELAY_MS: int = 200  # Brief delay to show completion

# Command execution timeout (in seconds)
COMMAND_TIMEOUT_SEC: int = 10

# =============================================================================
# COMMAND DISPLAY
# =============================================================================

# Maximum length for command display before truncation
COMMAND_DISPLAY_MAX_LENGTH: int = 100
COMMAND_TRUNCATE_LENGTH: int = 97  # Length before adding "..."

# =============================================================================
# DEVICE TYPES
# =============================================================================

# Supported device types for artifact creation
SUPPORTED_DEVICE_TYPES: list[str] = ["p3509-a02-p3767-0000"]

# =============================================================================
# DOCKER ARTIFACT SETTINGS
# =============================================================================

# Default destination directory for Docker container updates on the device
DOCKER_CONTAINER_DEST_DIR: str = "/data/container-updates"

# Default Docker image filename when exporting
DOCKER_IMAGE_FILENAME: str = "docker-image.tar.gz"

# Default app name for Docker artifacts
DEFAULT_DOCKER_APP_NAME: str = "docker-app"

# =============================================================================
# PROGRESS BAR
# =============================================================================

# Progress bar configuration
PROGRESS_BAR_LENGTH: int = 350
PROGRESS_BAR_MAX: int = 100

# Loading progress steps
LOADING_PROGRESS_INIT: int = 0
LOADING_PROGRESS_SETTINGS: int = 5
LOADING_PROGRESS_INTERFACE: int = 10
LOADING_PROGRESS_PACKAGES: int = 20
LOADING_PROGRESS_DEVICES: int = 40
LOADING_PROGRESS_GROUPS: int = 80
LOADING_PROGRESS_COMPLETE: int = 100

# =============================================================================
# BUTTON WIDTHS
# =============================================================================

# Standard button widths (in characters)
BUTTON_WIDTH_SMALL: int = 8
BUTTON_WIDTH_MEDIUM: int = 12
BUTTON_WIDTH_LARGE: int = 15

# =============================================================================
# FONT SIZES
# =============================================================================

FONT_SIZE_SMALL: int = 9
FONT_SIZE_NORMAL: int = 10
FONT_SIZE_MEDIUM: int = 12
FONT_SIZE_LARGE: int = 14
FONT_SIZE_TITLE: int = 16

# =============================================================================
# ENTRY FIELD WIDTHS
# =============================================================================

ENTRY_WIDTH_SMALL: int = 20
ENTRY_WIDTH_MEDIUM: int = 30
ENTRY_WIDTH_LARGE: int = 40
ENTRY_WIDTH_XLARGE: int = 50
