"""
Docker Artifact Tab - Creation of Docker RDFM artifacts
"""

import io
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import tkinter as tk
from collections.abc import Callable
from functools import partial
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TypedDict, Unpack

import yaml

from artifact_gui.tabs.base_tab import BaseTab
from artifact_gui.theme import AetheroTheme
from artifact_gui.ui_constants import (
    DEFAULT_DOCKER_APP_NAME,
    DOCKER_CONTAINER_DEST_DIR,
    STANDARD_PAD,
    SUPPORTED_DEVICE_TYPES,
)
from artifact_gui.utils import (
    FILETYPES_ALL,
    FILETYPES_COMPOSE,
    FILETYPES_RDFM,
    FILETYPES_TAR,
    browse_directory,
    browse_file,
    resolve_path,
)

# Cache timeout for Docker images (2 minutes)
DOCKER_IMAGE_CACHE_TIMEOUT = 120

# Docker image format expected column count
DOCKER_IMAGE_COLUMN_COUNT = 3


class DockerImageSelectionDialog:
    """Dialog for selecting multiple Docker images."""

    def __init__(self, parent: tk.Widget) -> None:
        """Initialize the Docker image selection dialog.

        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.result: list[str] = []  # List of selected image names
        self.dialog: tk.Toplevel | None = None
        self.treeview: ttk.Treeview | None = None

    def show(self) -> list[str]:
        """Show the dialog and return selected images.

        Returns:
            List of selected Docker image names (e.g., ["nginx:latest", "redis:alpine"])
        """
        # Create dialog window
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Select Docker Images")
        self.dialog.geometry("700x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Apply theme
        style = AetheroTheme.apply_theme(self.dialog)

        # Create main frame
        main_frame = ttk.Frame(self.dialog, padding=STANDARD_PAD)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title label
        ttk.Label(
            main_frame,
            text="Select Docker images to add:",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(pady=(0, STANDARD_PAD))

        # Create treeview with columns
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, STANDARD_PAD))

        self.treeview = ttk.Treeview(
            tree_frame,
            columns=("image", "created", "size"),
            show="headings",
            selectmode="extended",
            height=12,
        )

        # Define column headings
        self.treeview.heading("image", text="Image Name:Tag")
        self.treeview.heading("created", text="Created")
        self.treeview.heading("size", text="Size")

        # Define column widths
        self.treeview.column("image", width=300)
        self.treeview.column("created", width=200)
        self.treeview.column("size", width=100)

        # Apply dark theme to treeview
        AetheroTheme.configure_treeview(self.treeview, style)

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.treeview.yview
        )
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.treeview.config(yscrollcommand=y_scrollbar.set)

        self.treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Loading Docker images...")
        self.status_label.pack(pady=(0, STANDARD_PAD))

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, pady=(STANDARD_PAD, 0))

        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            style="Add.TButton",
            width=10,
        ).pack(side=tk.LEFT, padx=(0, STANDARD_PAD))
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel, width=10).pack(
            side=tk.LEFT
        )

        # Start loading images
        self._load_images()

        # Center dialog on parent
        self.dialog.update_idletasks()
        x = (
            self.parent.winfo_rootx()
            + (self.parent.winfo_width() - self.dialog.winfo_width()) // 2
        )
        y = (
            self.parent.winfo_rooty()
            + (self.parent.winfo_height() - self.dialog.winfo_height()) // 2
        )
        self.dialog.geometry(f"+{x}+{y}")

        # Wait for dialog to close
        self.dialog.wait_window()

        return self.result

    def _load_images(self) -> None:
        """Load Docker images in background thread."""

        def fetch_images() -> None:
            error_message = None
            images: list[dict[str, str]] = []

            try:
                # Run docker images command with detailed format
                result = subprocess.run(
                    [
                        "docker",
                        "images",
                        "--format",
                        "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                # Parse output if successful
                if result.returncode == 0:
                    images = self._parse_docker_images(result.stdout)
                    if not images:
                        error_message = "Failed to list Docker images"

            except FileNotFoundError:
                error_message = "Docker command not found"
            except subprocess.TimeoutExpired:
                error_message = "Docker command timed out"
            except Exception:
                error_message = "Error loading Docker images"

            # Update UI on main thread
            self._update_dialog_ui(images, error_message)

        # Run in background thread
        thread = threading.Thread(target=fetch_images, daemon=True)
        thread.start()

    def _parse_docker_images(self, stdout: str) -> list[dict[str, str]]:
        """Parse docker images command output.

        Args:
            stdout: Output from docker images command

        Returns:
            List of image dictionaries with name, created, and size fields
        """
        images = []
        for line in stdout.strip().split("\n"):
            if line and "<none>" not in line:
                parts = line.split("\t")
                if len(parts) >= DOCKER_IMAGE_COLUMN_COUNT:
                    # Remove timezone suffix from timestamp (e.g., "+0000 UTC")
                    created = parts[1]
                    if " +" in created:
                        created = created.split(" +")[0]
                    images.append(
                        {"name": parts[0], "created": created, "size": parts[2]}
                    )
        return images

    def _update_dialog_ui(
        self, images: list[dict[str, str]], error_message: str | None
    ) -> None:
        """Update dialog UI with images or error message.

        Args:
            images: List of Docker images
            error_message: Error message to display, or None if successful
        """
        if not self.dialog:
            return

        if error_message:
            self.dialog.after(0, lambda: self._show_error(error_message))
        elif images:
            self.dialog.after(0, lambda: self._populate_treeview(images))
        else:
            self.dialog.after(0, lambda: self._show_error("No Docker images found"))

    def _populate_treeview(self, images: list[dict[str, str]]) -> None:
        """Populate treeview with images (called from main thread).

        Args:
            images: List of image dictionaries with name, created, size
        """
        if not self.treeview:
            return

        # Clear existing items
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        # Add images
        for img in images:
            self.treeview.insert(
                "",
                tk.END,
                values=(img["name"], img["created"], img["size"]),
            )

        # Update status
        count = len(images)
        if count == 0:
            self.status_label.config(
                text="No Docker images found", foreground=AetheroTheme.CYAN_ACCENT
            )
        else:
            plural = "s" if count != 1 else ""
            status_text = f"Found {count} Docker image{plural}. Select and click OK."
            self.status_label.config(text=status_text, foreground="")

    def _show_error(self, message: str) -> None:
        """Show error message in status label.

        Args:
            message: Error message to display
        """
        if self.status_label:
            self.status_label.config(text=message, foreground=AetheroTheme.CYAN_ACCENT)

    def _on_ok(self) -> None:
        """Handle OK button click."""
        if self.treeview:
            # Get selected items
            selected_items = self.treeview.selection()
            self.result = [
                self.treeview.item(item)["values"][0] for item in selected_items
            ]

        if self.dialog:
            self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle Cancel button click."""
        self.result = []
        if self.dialog:
            self.dialog.destroy()


class ArtifactParams(TypedDict):
    """Parameters for Docker artifact creation"""

    app_name: str
    compose_file: Path
    docker_images: list[tuple[str, str]]  # List of (type, source) tuples
    artifact_name: str
    device_type: str
    output_path: Path
    additional_files: list[str]


class TarballParams(TypedDict):
    """Parameters for tarball creation"""

    artifact_name: str
    temp_dir: str
    compose_file: Path
    docker_images: list[tuple[str, str, Path]]  # List of (type, source, path) tuples
    additional_files: list[str]
    inner_index_content: str
    outer_index_content: str
    app_name: str


class DockerCreator(BaseTab):
    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        pass

    def setup_ui(self) -> None:
        # Initialize instance variables for multi-container support
        self.docker_images: list[tuple[str, str]] = []  # List of (type, source) tuples
        self.compose_service_count: int = 0  # Number of services in compose file

        self.docker_frame = ttk.Frame(self.frame)
        self.docker_frame.pack(
            fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        self.setup_docker_frame()

    def setup_docker_frame(self) -> None:
        """Setup UI components for Docker container artifact creation"""
        # Configure grid columns for balanced 2-column layout (50/50 split)
        self.docker_frame.columnconfigure(1, weight=2)  # Left column entry fields
        self.docker_frame.columnconfigure(4, weight=2)  # Right column listbox

        # Setup UI sections
        self._setup_app_name_and_compose()
        self._setup_docker_images_section()
        self._setup_additional_files_section()
        self._setup_bottom_fields()
        self._setup_create_button()

        # Bind selection clear to all readonly comboboxes
        self.bind_selection_clear(self.docker_device_type_combo)

    def _setup_app_name_and_compose(self) -> None:
        """Setup app name and compose file fields."""
        # App name
        ttk.Label(self.docker_frame, text="App Name:").grid(
            row=0, column=0, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.docker_app_name_var = tk.StringVar(value=DEFAULT_DOCKER_APP_NAME)
        ttk.Entry(self.docker_frame, textvariable=self.docker_app_name_var).grid(
            row=0,
            column=1,
            columnspan=2,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="ew",
        )

        # Compose file
        self.docker_compose_path_var, _, _ = self.create_labeled_entry_with_browse(
            self.docker_frame,
            "Compose File:",
            row=1,
            browse_title="Select Compose File",
            filetypes=FILETYPES_COMPOSE,
        )
        # Add trace to parse compose file when it changes
        self.docker_compose_path_var.trace_add("write", self._on_compose_file_changed)

    def _setup_docker_images_section(self) -> None:
        """Setup Docker images listbox and buttons."""
        # Docker Images section (rows 2-5, LEFT COLUMN)
        ttk.Label(self.docker_frame, text="Docker Images:").grid(
            row=2, column=0, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="nw"
        )

        # Listbox with scrollbars for Docker images
        images_listbox_frame = ttk.Frame(self.docker_frame)
        images_listbox_frame.grid(
            row=2,
            column=1,
            rowspan=4,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="nsew",
        )
        images_listbox_frame.columnconfigure(0, weight=1)
        images_listbox_frame.rowconfigure(0, weight=1)

        self.docker_images_listbox = tk.Listbox(
            images_listbox_frame, height=8, exportselection=False, selectmode=tk.SINGLE
        )
        self.docker_images_listbox.grid(row=0, column=0, sticky="nsew")

        images_y_scrollbar = ttk.Scrollbar(
            images_listbox_frame,
            orient=tk.VERTICAL,
            command=self.docker_images_listbox.yview,
        )
        images_y_scrollbar.grid(row=0, column=1, sticky="ns")

        images_x_scrollbar = ttk.Scrollbar(
            images_listbox_frame,
            orient=tk.HORIZONTAL,
            command=self.docker_images_listbox.xview,
        )
        images_x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.docker_images_listbox.config(
            yscrollcommand=images_y_scrollbar.set, xscrollcommand=images_x_scrollbar.set
        )

        # Apply theme styling to listbox
        AetheroTheme.configure_listbox(self.docker_images_listbox)

        # Buttons for adding/removing Docker images
        images_buttons = ttk.Frame(self.docker_frame)
        images_buttons.grid(
            row=2,
            column=2,
            rowspan=4,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="nw",
        )

        ttk.Button(
            images_buttons,
            text="Add from Docker",
            command=self.add_docker_image_from_docker,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            images_buttons,
            text="Add from File",
            command=self.add_docker_image_from_file,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            images_buttons, text="Remove", command=self.remove_docker_image
        ).pack(fill=tk.X, pady=2)

        # Warning label for service count mismatch (initially hidden)
        self.docker_images_warning_label = ttk.Label(
            images_buttons,
            text="",
            foreground=AetheroTheme.CYAN_ACCENT,
            wraplength=120,
            justify=tk.LEFT,
        )
        self.docker_images_warning_label.pack(fill=tk.X, pady=(10, 2))

    def _setup_additional_files_section(self) -> None:
        """Setup additional files listbox and buttons."""
        # Additional files section (rows 0-3, RIGHT COLUMN)
        ttk.Label(self.docker_frame, text="Additional Files:").grid(
            row=0, column=3, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="nw"
        )

        # Listbox with scrollbars for additional files
        listbox_frame = ttk.Frame(self.docker_frame)
        listbox_frame.grid(
            row=0,
            column=4,
            rowspan=4,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="nsew",
        )
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)

        self.docker_files_listbox = tk.Listbox(
            listbox_frame, height=8, exportselection=False, selectmode=tk.SINGLE
        )
        self.docker_files_listbox.grid(row=0, column=0, sticky="nsew")

        files_y_scrollbar = ttk.Scrollbar(
            listbox_frame, orient=tk.VERTICAL, command=self.docker_files_listbox.yview
        )
        files_y_scrollbar.grid(row=0, column=1, sticky="ns")

        files_x_scrollbar = ttk.Scrollbar(
            listbox_frame, orient=tk.HORIZONTAL, command=self.docker_files_listbox.xview
        )
        files_x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.docker_files_listbox.config(
            yscrollcommand=files_y_scrollbar.set, xscrollcommand=files_x_scrollbar.set
        )

        # Apply theme styling to listbox
        AetheroTheme.configure_listbox(self.docker_files_listbox)

        # Buttons for adding/removing files
        files_buttons = ttk.Frame(self.docker_frame)
        files_buttons.grid(
            row=0,
            column=5,
            rowspan=4,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="nw",
        )

        ttk.Button(
            files_buttons,
            text="Add File",
            command=lambda: browse_file(
                title="Select File to Add",
                filetypes=FILETYPES_ALL,
                list_insert=self.docker_files_listbox,
            ),
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            files_buttons,
            text="Add Dir",
            command=lambda: browse_directory(
                title="Select Directory to Add", list_insert=self.docker_files_listbox
            ),
        ).pack(fill=tk.X, pady=2)
        ttk.Button(files_buttons, text="Remove", command=self.remove_docker_file).pack(
            fill=tk.X, pady=2
        )

    def _setup_bottom_fields(self) -> None:
        """Setup artifact name, output path, and device type fields."""
        # Artifact name for docker (row 4, RIGHT)
        ttk.Label(self.docker_frame, text="Artifact Name:").grid(
            row=4, column=3, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.docker_artifact_name_var = tk.StringVar()
        ttk.Entry(self.docker_frame, textvariable=self.docker_artifact_name_var).grid(
            row=4,
            column=4,
            columnspan=2,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="ew",
        )

        # Output path for docker (row 5, RIGHT)
        self.docker_output_path_var, _, _ = self.create_labeled_entry_with_browse(
            self.docker_frame,
            "Output Path:",
            row=5,
            entry_var=tk.StringVar(value="docker-artifact.rdfm"),
            browse_title="Save Docker Artifact As",
            browse_type="save",
            filetypes=FILETYPES_RDFM,
            start_col=3,
        )

        # Device type for docker (row 6, LEFT)
        self.docker_device_type_var, self.docker_device_type_combo = (
            self.create_labeled_combo(
                self.docker_frame,
                "Device Type:",
                row=6,
                values=SUPPORTED_DEVICE_TYPES,
                start_col=0,
            )
        )

    def _setup_create_button(self) -> None:
        """Setup create docker artifact button."""
        # Create docker artifact button (centered at bottom)
        ttk.Button(
            self.docker_frame,
            text="Create Docker Artifact",
            command=self.create_docker_container_artifact,
            style="Add.TButton",
        ).grid(row=7, column=1, columnspan=4, padx=STANDARD_PAD, pady=10)

    def _export_docker_image(
        self, docker_image_name: str, output_path: Path
    ) -> tuple[bool, str]:
        """Export a Docker image to a tar.gz file

        Args:
            docker_image_name: Name of the Docker image to export
            output_path: Path where the tar.gz file should be saved

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            # First, run docker save and pipe to gzip
            docker_process = subprocess.Popen(
                ["docker", "save", docker_image_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            gzip_process = subprocess.Popen(
                ["gzip"],
                stdin=docker_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Allow docker_process to receive SIGPIPE if gzip exits
            docker_process.stdout.close()

            # Register gzip process for cancellation
            self.cli_executor.set_current_process(gzip_process, is_running=True)

            # Get the gzipped output
            gzip_output, gzip_stderr = gzip_process.communicate()

            # Terminate docker process if it's still running
            if docker_process.poll() is None:
                docker_process.terminate()
                docker_process.wait()

            # Wait for docker process to finish and get stderr
            docker_stderr = docker_process.stderr.read()
            docker_process.stderr.close()
            docker_returncode = docker_process.wait()

            return_tuple: tuple[bool, str]

            # Check if cancelled
            if docker_returncode in (-15, -9):  # SIGTERM or SIGKILL
                return_tuple = False, "Export cancelled"

            # Check for errors
            elif docker_returncode != 0:
                error_msg = docker_stderr.decode() if docker_stderr else "Unknown error"
                return_tuple = (
                    False,
                    (
                        f"Error exporting Docker image: {error_msg}\n\n"
                        "Note: Docker export may fail if:\n"
                        "- Docker is not installed or running\n"
                        "- The image doesn't exist locally\n"
                        "- Running in a containerized environment"
                        "without Docker access\n"
                    ),
                )

            elif gzip_process.returncode != 0:
                error_msg = gzip_stderr.decode() if gzip_stderr else "Gzip error"
                return_tuple = False, f"Error compressing image: {error_msg}"

            # Check if we got any data
            elif len(gzip_output) == 0:
                return_tuple = (
                    False,
                    (
                        "Error: Docker save produced no output.\n"
                        "The image may not exist or Docker may not be accessible."
                    ),
                )

            # Write the output to file
            with Path.open(output_path, "wb") as f:
                f.write(gzip_output)

            # Report size
            size_mb = len(gzip_output) / (1024 * 1024)
            return_tuple = True, f"Exported Docker image ({size_mb:.1f} MB)"
            return return_tuple

        except FileNotFoundError as e:
            return False, (
                f"Error: {e}\n"
                "Docker or gzip command not found. Ensure Docker is installed."
            )
        except Exception as e:
            return False, f"Error during Docker export: {e!s}"
        finally:
            # Clear the process reference
            self.cli_executor.set_current_process(None, is_running=True)

    def refresh_docker_images(
        self, callback: Callable[[list[str]], None] | None = None
    ) -> None:
        """Refresh the list of available Docker images from the local Docker daemon.

        Runs 'docker images' command in a background thread to get the list of
        available images and updates the cache.

        Args:
            callback: Optional callback function to call after images are refreshed
        """

        def fetch_images() -> None:
            try:
                # Run docker images command to get list of images
                result = subprocess.run(
                    ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    # Parse the output and filter out <none> entries
                    images = []
                    for line in result.stdout.strip().split("\n"):
                        if line and "<none>" not in line:
                            images.append(line)

                    # Update cache on main thread
                    self.docker_images_listbox.after(
                        0,
                        lambda: self._update_docker_images_cache(
                            sorted(images), callback
                        ),
                    )
                else:
                    self.docker_images_listbox.after(
                        0, lambda: self._update_docker_images_cache([], callback)
                    )

            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                self.docker_images_listbox.after(
                    0, lambda: self._update_docker_images_cache([], callback)
                )

        # Run in background thread
        thread = threading.Thread(target=fetch_images, daemon=True)
        thread.start()

    def _update_docker_images_cache(
        self, images: list[str], callback: Callable[[list[str]], None] | None = None
    ) -> None:
        """Update the Docker images cache (called from main thread).

        This method must be called from the main thread to safely update
        the cache with the fetched Docker images.

        Args:
            images: List of Docker image names in "repository:tag" format
            callback: Optional callback function to call after cache is updated
        """
        # Update cache
        self.docker_images_cache = images
        self.docker_images_cache_time = time.time()

        # Call callback if provided
        if callback:
            callback(images)

    def _on_compose_file_changed(self, *args: object) -> None:  # noqa: ARG002
        """Called when compose file path changes.

        Parses the file and updates warning.
        """
        compose_path_str = self.docker_compose_path_var.get().strip()
        if not compose_path_str:
            self.compose_service_count = 0
            self._update_images_warning()
            return

        compose_path = resolve_path(compose_path_str)
        if not compose_path or not compose_path.exists():
            self.compose_service_count = 0
            self._update_images_warning()
            return

        try:
            with Path.open(compose_path) as f:
                compose_data = yaml.safe_load(f)

            # Count services in compose file
            if compose_data and "services" in compose_data:
                self.compose_service_count = len(compose_data["services"])
            else:
                self.compose_service_count = 0

            self._update_images_warning()

        except (yaml.YAMLError, OSError, KeyError):
            # If parsing fails, just set count to 0
            self.compose_service_count = 0
            self._update_images_warning()

    def _update_images_warning(self) -> None:
        """Update the warning label based on image count vs service count."""
        image_count = len(self.docker_images)

        if self.compose_service_count > 0 and image_count != self.compose_service_count:
            warning_text = (
                f"⚠ Compose has {self.compose_service_count} "
                f"service{'s' if self.compose_service_count != 1 else ''} "
                f"but {image_count} image{'s' if image_count != 1 else ''} provided"
            )
            self.docker_images_warning_label.config(text=warning_text)
        else:
            self.docker_images_warning_label.config(text="")

    def add_docker_image_from_file(self) -> None:
        """Add a Docker image from a tarball file."""
        file_path = browse_file(
            title="Select Docker Image Tarball", filetypes=FILETYPES_TAR
        )
        if file_path:
            # Add to internal list
            self.docker_images.append(("file", file_path))
            # Add to listbox (display only)
            self.docker_images_listbox.insert(tk.END, file_path)
            # Update warning
            self._update_images_warning()

    def remove_docker_image(self) -> None:
        """Remove the currently selected image from the Docker images list."""
        selection = self.docker_images_listbox.curselection()
        if selection:
            index = selection[0]
            # Remove from listbox
            self.docker_images_listbox.delete(index)
            # Remove from internal list
            del self.docker_images[index]
            # Update warning
            self._update_images_warning()

    def add_docker_image_from_docker(self) -> None:
        """Add Docker images from the Docker daemon via selection dialog."""
        # Show selection dialog
        dialog = DockerImageSelectionDialog(self.docker_frame)
        selected_images = dialog.show()

        # Add selected images to the list
        for image_name in selected_images:
            # Add to internal list
            self.docker_images.append(("docker", image_name))
            # Add to listbox (display only)
            self.docker_images_listbox.insert(tk.END, image_name)

        # Update warning if any images were added
        if selected_images:
            self._update_images_warning()

    def remove_docker_file(self) -> None:
        """Remove the currently selected file from the additional files list.

        Removes the selected item from the Docker additional files listbox.
        Does nothing if no item is selected.
        """
        selection = self.docker_files_listbox.curselection()
        if selection:
            self.docker_files_listbox.delete(selection[0])

    def _validate_docker_fields(self) -> bool:
        # Validate required fields
        required_fields = {
            "App Name": self.docker_app_name_var.get().strip(),
            "Compose File": self.docker_compose_path_var.get().strip(),
            "Artifact Name": self.docker_artifact_name_var.get().strip(),
            "Device Type": self.docker_device_type_var.get().strip(),
        }

        if not self.validate_required_fields(required_fields):
            return False

        forbidden_pattern = r'[^a-zA-Z0-9\._]'
        if re.search(forbidden_pattern, required_fields["Artifact Name"]):
            self.show_warning(
                "Validation Error",
                "Artifact name can only contain characters (a-z A-Z 0-9 . _)",
            )
            return False

        # Validate that at least one Docker image is provided
        if len(self.docker_images) == 0:
            self.show_warning(
                "Validation Error", "Please add at least one Docker image"
            )
            return False

        return True

    def _resolve_paths(
        self, compose_file: str, output_path: str
    ) -> tuple[bool, Path | None, Path]:
        # Validate compose file exists
        compose_path = resolve_path(compose_file)
        if not compose_path or not compose_path.exists():
            messagebox.showerror("Error", f"Compose file not found: {compose_file}")
            return False, None, None

        # Resolve output path
        output_path = self.resolve_output_path(output_path, "docker-artifact.rdfm")

        return True, compose_path, output_path

    def _try_copy_additional_files(
        self, additional_files: list[str], app_dir: Path
    ) -> bool:
        for file_path_str in additional_files:
            src_path = resolve_path(file_path_str)
            if not src_path or not src_path.exists():
                self.cli_executor.output_queue.put(
                    (
                        "output",
                        f"Warning: File not found, skipping: {file_path_str}\n",
                    )
                )
                continue

            try:
                dest_path = app_dir / src_path.name
                if src_path.is_dir():
                    shutil.copytree(src_path, dest_path)
                    self.cli_executor.output_queue.put(
                        ("output", f"Copied directory: {src_path.name}/\n")
                    )
                else:
                    shutil.copy2(src_path, dest_path)
                    self.cli_executor.output_queue.put(
                        ("output", f"Copied file: {src_path.name}\n")
                    )
            except (OSError, PermissionError, FileExistsError) as e:
                self.cli_executor.output_queue.put(
                    ("output", f"Error copying {src_path.name}: {e}\n")
                )
                self.cli_executor.output_queue.put(
                    ("status", f"Failed to copy {src_path.name}")
                )
                self.cli_executor.output_queue.put(("command_finished", None))
                return False
        return True

    def _generate_index_contents(
        self,
        compose_file: Path,
        image_paths: list[tuple[str, str, Path]],
        app_name: str,
    ) -> tuple[str, str]:
        """Generate index file contents without writing to disk.

        Args:
            compose_file: Path to compose file
            image_paths: List of (type, source, path) tuples for images
            app_name: App directory name

        Returns:
            Tuple of (inner_index_content, outer_index_content)
        """
        # Create inner index content (app_name/index)
        # Format: compose_file.name followed by all image filenames (one per line)
        image_filenames = [path.name for _, _, path in image_paths]
        inner_index_lines = [compose_file.name, *image_filenames]
        inner_index_content = "\n".join(inner_index_lines) + "\n"

        # Create outer index content
        outer_index_content = f"{app_name}/index\n"

        # Log what we're adding
        self.cli_executor.output_queue.put(
            ("output", f"Generating index: {app_name}/index\n")
        )
        self.cli_executor.output_queue.put(
            ("output", f"  Contents: {compose_file.name}")
        )
        for filename in image_filenames:
            self.cli_executor.output_queue.put(("output", f", {filename}"))
        self.cli_executor.output_queue.put(("output", "\n"))

        return inner_index_content, outer_index_content

    def _try_create_tarball(self, **kwargs: Unpack[TarballParams]) -> Path | None:
        """Create tarball directly from source files without staging copies.

        Args:
            **kwargs: Tarball creation parameters (see TarballParams TypedDict)

        Returns:
            Path to created tarball, or None if failed
        """
        params: TarballParams = kwargs  # type: ignore[assignment]

        artifact_name = params["artifact_name"]
        temp_dir = params["temp_dir"]
        compose_file = params["compose_file"]
        docker_images = params["docker_images"]
        additional_files = params["additional_files"]
        inner_index_content = params["inner_index_content"]
        outer_index_content = params["outer_index_content"]
        app_name = params["app_name"]

        tarball_name = f"{artifact_name}.tar.gz"
        tarball_path = Path(temp_dir) / tarball_name
        self.cli_executor.output_queue.put(
            ("output", f"\nCreating tarball: {tarball_name}\n")
        )

        try:
            with tarfile.open(tarball_path, "w:gz") as tar:
                # Add compose file directly
                tar.add(compose_file, arcname=f"{app_name}/{compose_file.name}")

                # Add Docker images directly from source
                for _, _, image_path in docker_images:
                    self.cli_executor.output_queue.put(
                        ("output", f"Adding image: {image_path.name}\n")
                    )
                    tar.add(image_path, arcname=f"{app_name}/{image_path.name}")

                # Add additional files directly
                for file_path_str in additional_files:
                    file_path = resolve_path(file_path_str)
                    if file_path and file_path.exists():
                        self.cli_executor.output_queue.put(
                            ("output", f"Adding file/directory: {file_path.name}\n")
                        )
                        tar.add(file_path, arcname=f"{app_name}/{file_path.name}")

                # Add inner index from memory
                self._add_index_to_tar(tar, f"{app_name}/index", inner_index_content)

                # Add outer index from memory
                self._add_index_to_tar(tar, "index", outer_index_content)

            self.cli_executor.output_queue.put(
                ("output", "Tarball created successfully\n")
            )
            return tarball_path
        except (OSError, tarfile.TarError) as e:
            self.cli_executor.output_queue.put(
                ("output", f"Error creating tarball: {e}\n")
            )
            self.cli_executor.output_queue.put(("status", "Failed to create tarball"))
            self.cli_executor.output_queue.put(("command_finished", None))
            return None

    def _add_index_to_tar(
        self, tar: tarfile.TarFile, arcname: str, content: str
    ) -> None:
        """Add an index file to tar from memory.

        Args:
            tar: Open tarfile to add to
            arcname: Archive name for the file
            content: String content of the file
        """
        content_bytes = content.encode("utf-8")
        tarinfo = tarfile.TarInfo(name=arcname)
        tarinfo.size = len(content_bytes)
        tar.addfile(tarinfo, io.BytesIO(content_bytes))

    def _check_cancellation(self) -> bool:
        """Check if operation was cancelled.

        Returns:
            True if cancelled, False otherwise
        """
        if self.cli_executor.cancel_requested:
            self.cli_executor.output_queue.put(
                ("output", "\nOperation cancelled by user\n")
            )
            self.cli_executor.output_queue.put(("command_finished", None))
            return True
        return False

    def _setup_directories(self, app_name: str) -> tuple[str, Path]:
        """Create temporary directory structure.

        Args:
            app_name: Name of the app directory to create

        Returns:
            Tuple of (temp_dir path, app_dir Path)
        """
        temp_dir = tempfile.mkdtemp(prefix="rdfm_docker_")
        self.cli_executor.output_queue.put(
            ("output", f"Creating temporary directory: {temp_dir}\n")
        )

        app_dir = Path(temp_dir) / app_name
        app_dir.mkdir()
        self.cli_executor.output_queue.put(
            ("output", f"Created app directory: {app_name}/\n")
        )

        return temp_dir, app_dir

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted string like "123.4 MB" or "1.2 GB"
        """
        gb = size_bytes / (1024**3)
        if gb >= 1.0:
            return f"{gb:.1f} GB"
        mb = size_bytes / (1024**2)
        return f"{mb:.1f} MB"

    def _handle_docker_images(
        self,
        docker_images: list[tuple[str, str]],
        temp_dir: str,
    ) -> list[tuple[str, str, Path]] | None:
        """Handle multiple Docker images (validate tarballs or export from Docker).

        Args:
            docker_images: List of (type, source) tuples
            temp_dir: Temporary directory for Docker exports

        Returns:
            List of (type, source, path) tuples if successful, None if any failed
        """
        image_paths = []

        for image_type, image_source in docker_images:
            if image_type == "file":
                # Validate tarball file exists
                source_path = resolve_path(image_source)
                if not source_path or not source_path.exists():
                    self.cli_executor.output_queue.put(
                        ("output", f"Error: Image file not found: {image_source}\n")
                    )
                    return None

                # Get file size and report it
                file_size = source_path.stat().st_size
                size_str = self._format_file_size(file_size)
                msg = f"Using image tarball {source_path.name} ({size_str})\n"
                self.cli_executor.output_queue.put(("output", msg))

                image_paths.append((image_type, image_source, source_path))

            elif image_type == "docker":
                # Export from Docker to temp directory
                self.cli_executor.output_queue.put(
                    ("output", f"Exporting Docker image: {image_source}\n")
                )
                image_filename = (
                    image_source.replace("/", "_").replace(":", "_") + ".tar.gz"
                )
                image_dest = Path(temp_dir) / image_filename

                success, message = self._export_docker_image(image_source, image_dest)
                if not success:
                    self.cli_executor.output_queue.put(("output", message + "\n"))
                    self.cli_executor.output_queue.put(
                        ("status", "Docker export failed")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return None

                self.cli_executor.output_queue.put(
                    ("output", f"Exported Docker image: {image_filename} - {message}\n")
                )
                image_paths.append((image_type, image_source, image_dest))

        return image_paths

    def _run_rdfm_artifact(
        self,
        artifact_name: str,
        device_type: str,
        tarball_path: Path,
        output_path: Path,
    ) -> bool:
        """Run rdfm-artifact to create final artifact.

        Args:
            artifact_name: Name of the artifact
            device_type: Device type
            tarball_path: Path to the tarball
            output_path: Output path for the artifact

        Returns:
            True if successful, False otherwise
        """
        self.cli_executor.output_queue.put(("output", "\nRunning rdfm-artifact...\n"))

        args = [
            "rdfm-artifact",
            "write",
            "single-file",
            "--artifact-name",
            artifact_name,
            "--device-type",
            device_type,
            "--file",
            str(tarball_path),
            "--dest-dir",
            DOCKER_CONTAINER_DEST_DIR,
            "--output-path",
            str(output_path),
        ]

        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        self.cli_executor.set_current_process(process, is_running=True)
        stdout, stderr = process.communicate()
        self.cli_executor.set_current_process(None, is_running=True)

        # Check if cancelled
        if process.returncode in (-15, -9):  # SIGTERM or SIGKILL
            self.cli_executor.output_queue.put(
                ("output", "\nOperation cancelled by user\n")
            )
            return False

        if stdout:
            self.cli_executor.output_queue.put(("output", stdout))
        if stderr:
            self.cli_executor.output_queue.put(("output", stderr))

        if process.returncode == 0:
            success_msg = (
                f"\nDocker container artifact created successfully: {output_path}\n"
            )
            self.cli_executor.output_queue.put(("output", success_msg))
            self.cli_executor.output_queue.put(
                ("status", "Docker artifact created successfully")
            )
            return True

        self.cli_executor.output_queue.put(
            ("status", f"Command failed with code {process.returncode}")
        )
        return False

    def create_docker_container_artifact(self) -> None:
        """Create a Docker container artifact with auto-generated index files

        This method creates a Docker container artifact by:
        1. Creating a temporary directory structure
        2. Copying the compose file and images (either from tarballs or Docker export)
        3. Copying additional files
        4. Generating index files for RDFM
        5. Creating a tarball
        6. Running rdfm-artifact to create the final artifact
        """

        # Get values from UI
        app_name = self.docker_app_name_var.get().strip()
        compose_file = self.docker_compose_path_var.get().strip()
        artifact_name = self.docker_artifact_name_var.get().strip()
        device_type = self.docker_device_type_var.get().strip()
        output_path = self.docker_output_path_var.get().strip()

        # Get additional files from listbox
        additional_files = list(self.docker_files_listbox.get(0, tk.END))

        if not self._validate_docker_fields():
            return

        success, compose_path, resolved_output_path = self._resolve_paths(
            compose_file, output_path
        )
        if not success:
            return

        params: ArtifactParams = {
            "app_name": app_name,
            "compose_file": compose_path,
            "docker_images": self.docker_images.copy(),  # Copy the list
            "artifact_name": artifact_name,
            "device_type": device_type,
            "output_path": resolved_output_path,
            "additional_files": additional_files,
        }

        artifact_creator = partial(self.create_artifact, **params)

        # Start in a new thread
        thread = threading.Thread(target=artifact_creator, daemon=True)
        thread.start()

    def _execute_artifact_steps(self, params: ArtifactParams, temp_dir: str) -> bool:
        """Execute artifact creation steps without staging directory copies.

        Args:
            params: Artifact creation parameters
            temp_dir: Temporary directory path

        Returns:
            True if all steps succeeded, False otherwise
        """
        # Step 1: Validate compose file exists
        if not params["compose_file"].exists() or self._check_cancellation():
            self.cli_executor.output_queue.put(
                ("output", f"Error: Compose file not found: {params['compose_file']}\n")
            )
            return False

        # Step 2: Handle Docker images (validate or export)
        image_paths = self._handle_docker_images(params["docker_images"], temp_dir)
        if not image_paths or self._check_cancellation():
            return False

        # Step 3: Validate additional files exist
        for file_path_str in params["additional_files"]:
            file_path = resolve_path(file_path_str)
            if not file_path or not file_path.exists():
                self.cli_executor.output_queue.put(
                    ("output", f"Warning: File not found, skipping: {file_path_str}\n")
                )

        if self._check_cancellation():
            return False

        # Step 4: Generate index contents
        inner_index, outer_index = self._generate_index_contents(
            params["compose_file"],
            image_paths,
            params["app_name"],
        )

        if self._check_cancellation():
            return False

        # Step 5: Create tarball directly from source files
        tarball_params: TarballParams = {
            "artifact_name": params["artifact_name"],
            "temp_dir": temp_dir,
            "compose_file": params["compose_file"],
            "docker_images": image_paths,
            "additional_files": params["additional_files"],
            "inner_index_content": inner_index,
            "outer_index_content": outer_index,
            "app_name": params["app_name"],
        }
        tarball_path = self._try_create_tarball(**tarball_params)
        if not tarball_path or self._check_cancellation():
            return False

        # Step 6: Run rdfm-artifact to create final artifact
        return self._run_rdfm_artifact(
            params["artifact_name"],
            params["device_type"],
            tarball_path,
            params["output_path"],
        )

    # Run the creation in a separate thread
    def create_artifact(self, **kwargs: Unpack[ArtifactParams]) -> None:
        """Create Docker artifact in a background thread.

        Args:
            **kwargs: Artifact creation parameters (see ArtifactParams)
        """
        temp_dir = None
        try:
            params: ArtifactParams = kwargs  # type: ignore[assignment]

            self.cli_executor.set_current_process(None, is_running=True)
            self.cli_executor.output_queue.put(("clear", None))
            self.cli_executor.output_queue.put(
                ("status", "Creating Docker container artifact...")
            )
            self.cli_executor.output_queue.put(("command_started", None))

            # Create temporary directory (only for Docker exports and final tarball)
            temp_dir = tempfile.mkdtemp(prefix="rdfm_docker_")
            self.cli_executor.output_queue.put(
                ("output", f"Created temporary directory: {temp_dir}\n")
            )

            # Execute steps (no staging copies needed)
            if not self._check_cancellation():
                self._execute_artifact_steps(params, temp_dir)

            self.cli_executor.output_queue.put(("command_finished", None))

        except Exception as e:
            self.cli_executor.output_queue.put(("output", f"Error: {e!s}\n"))
            self.cli_executor.output_queue.put(
                ("status", "Docker artifact creation failed")
            )
            self.cli_executor.output_queue.put(("command_finished", None))
        finally:
            self.cli_executor.clear_current_process()
            if temp_dir and Path(temp_dir).exists():
                try:
                    shutil.rmtree(temp_dir)
                    self.cli_executor.output_queue.put(
                        ("output", "\nCleaned up temporary directory\n")
                    )
                except Exception as e:
                    self.cli_executor.output_queue.put(
                        ("output", f"Warning: Could not clean up temp dir: {e}\n")
                    )
