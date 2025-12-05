"""
Docker Artifact Tab - Creation of Docker RDFM artifacts
"""

import shutil
import subprocess
import tarfile
import tempfile
import threading
import tkinter as tk
from functools import partial
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TypedDict, Unpack

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
    try_copy_file,
)


class ArtifactParams(TypedDict):
    """Parameters for Docker artifact creation"""

    app_name: str
    compose_file: Path
    image_source: str
    image_tarball: Path | None
    docker_image_name: str
    artifact_name: str
    device_type: str
    output_path: Path
    additional_files: list[str]


class DockerCreator(BaseTab):
    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        pass

    def setup_ui(self) -> None:
        self.docker_frame = ttk.Frame(self.frame)
        self.docker_frame.pack(
            fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        self.setup_docker_frame()

        # Bind selection clear to all readonly comboboxes
        self.bind_selection_clear(
            self.docker_device_type_combo, self.docker_image_combo
        )

    def setup_docker_frame(self) -> None:
        """Setup UI components for Docker container artifact creation"""
        # Configure grid columns for balanced 2-column layout (50/50 split)
        self.docker_frame.columnconfigure(1, weight=2)  # Left column entry fields
        self.docker_frame.columnconfigure(4, weight=2)  # Right column listbox

        # LEFT COLUMN
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

        # Docker image source selection
        ttk.Label(self.docker_frame, text="Image Source:").grid(
            row=2, column=0, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.docker_image_source_var = tk.StringVar(value="tarball")
        image_source_frame = ttk.Frame(self.docker_frame)
        image_source_frame.grid(
            row=2,
            column=1,
            columnspan=2,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="w",
        )
        ttk.Radiobutton(
            image_source_frame,
            text="Existing Tarball",
            variable=self.docker_image_source_var,
            value="tarball",
            command=self.toggle_image_source,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            image_source_frame,
            text="Export from Docker",
            variable=self.docker_image_source_var,
            value="export",
            command=self.toggle_image_source,
        ).pack(side=tk.LEFT, padx=10)

        # Image tarball path (for existing tarball)
        (
            self.docker_image_tarball_var,
            self.docker_tarball_entry,
            self.docker_tarball_browse,
        ) = self.create_labeled_entry_with_browse(
            self.docker_frame,
            "Image Tarball:",
            row=3,
            browse_title="Select Docker Image Tarball",
            filetypes=FILETYPES_TAR,
        )

        # Docker image name (for export from Docker)
        ttk.Label(self.docker_frame, text="Docker Image:").grid(
            row=4, column=0, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.docker_image_name_var = tk.StringVar()
        self.docker_image_combo = ttk.Combobox(
            self.docker_frame, textvariable=self.docker_image_name_var, state="disabled"
        )
        self.docker_image_combo.grid(
            row=4, column=1, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="ew"
        )
        self.docker_refresh_images_btn = ttk.Button(
            self.docker_frame,
            text="Refresh",
            command=self.refresh_docker_images,
            state="disabled",
        )
        self.docker_refresh_images_btn.grid(
            row=4, column=2, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )

        # RIGHT COLUMN
        # Additional files section
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

        # BOTTOM ROW (spans both columns)
        # Artifact name for docker
        ttk.Label(self.docker_frame, text="Artifact Name:").grid(
            row=5, column=0, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.docker_artifact_name_var = tk.StringVar()
        ttk.Entry(self.docker_frame, textvariable=self.docker_artifact_name_var).grid(
            row=5,
            column=1,
            columnspan=2,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="ew",
        )

        # Device type for docker
        self.docker_device_type_var, self.docker_device_type_combo = (
            self.create_labeled_combo(
                self.docker_frame,
                "Device Type:",
                row=5,
                values=SUPPORTED_DEVICE_TYPES,
                start_col=3,
            )
        )

        # Output path for docker
        self.docker_output_path_var, _, _ = self.create_labeled_entry_with_browse(
            self.docker_frame,
            "Output Path:",
            row=6,
            entry_var=tk.StringVar(value="docker-artifact.rdfm"),
            browse_title="Save Docker Artifact As",
            browse_type="save",
            filetypes=FILETYPES_RDFM,
        )

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

    def toggle_image_source(self) -> None:
        """Toggle between tarball and Docker export modes.

        Enables/disables the appropriate UI elements based on whether the user
        wants to use an existing tarball or export from Docker.
        """
        source = self.docker_image_source_var.get()
        if source == "tarball":
            self.docker_tarball_entry.config(state="normal")
            self.docker_tarball_browse.config(state="normal")
            self.docker_image_combo.config(state="disabled")
            self.docker_refresh_images_btn.config(state="disabled")
        else:
            self.docker_tarball_entry.config(state="disabled")
            self.docker_tarball_browse.config(state="disabled")
            self.docker_image_combo.config(state="readonly")
            self.docker_refresh_images_btn.config(state="normal")
            # Auto-refresh images when switching to export mode
            self.refresh_docker_images()

    def refresh_docker_images(self) -> None:
        """Refresh the list of available Docker images from the local Docker daemon.

        Runs 'docker images' command in a background thread to get the list of
        available images and updates the Docker image combobox with the results.
        """

        # Show loading state immediately
        self.docker_refresh_images_btn.config(state="disabled", text="Loading...")
        self.cli_executor.output_queue.put(("status", "Loading Docker images..."))

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

                    # Schedule UI update on main thread
                    self.docker_image_combo.after(
                        0, lambda: self._update_docker_images(sorted(images))
                    )
                else:
                    error_msg = result.stderr or "Unknown error"
                    self.cli_executor.output_queue.put(
                        ("status", f"Failed to list Docker images: {error_msg[:50]}")
                    )
                    self.docker_image_combo.after(
                        0, lambda: self._update_docker_images([])
                    )

            except FileNotFoundError:
                self.cli_executor.output_queue.put(
                    ("status", "Docker command not found")
                )
                self.docker_image_combo.after(0, lambda: self._update_docker_images([]))
            except subprocess.TimeoutExpired:
                self.cli_executor.output_queue.put(
                    ("status", "Docker command timed out")
                )
                self.docker_image_combo.after(0, lambda: self._update_docker_images([]))
            except Exception as e:
                self.cli_executor.output_queue.put(
                    ("status", f"Error listing images: {str(e)[:50]}")
                )
                self.docker_image_combo.after(0, lambda: self._update_docker_images([]))

        # Run in background thread
        thread = threading.Thread(target=fetch_images, daemon=True)
        thread.start()

    def _update_docker_images(self, images: list[str]) -> None:
        """Update the Docker images combobox (called from main thread).

        This method must be called from the main thread to safely update
        the UI with the fetched Docker images.

        Args:
            images: List of Docker image names in "repository:tag" format
        """
        # Update the combobox values
        self.docker_image_combo["values"] = images

        # Set first image as default if available and no current selection
        if images and not self.docker_image_name_var.get():
            self.docker_image_name_var.set(images[0])

        # Clear selection highlight on combobox after event processing
        self.docker_image_combo.after_idle(self.docker_image_combo.selection_clear)

        # Show count in status
        if images:
            self.cli_executor.output_queue.put(
                ("status", f"Found {len(images)} Docker images")
            )

        # Re-enable refresh button
        self.docker_refresh_images_btn.config(state="normal", text="Refresh")

    def remove_docker_file(self) -> None:
        """Remove the currently selected file from the additional files list.

        Removes the selected item from the Docker additional files listbox.
        Does nothing if no item is selected.
        """
        selection = self.docker_files_listbox.curselection()
        if selection:
            self.docker_files_listbox.delete(selection[0])

    def _validate_docker_fields(self, image_src: str) -> bool:
        # Validate required fields based on image source
        required_fields = {
            "App Name": self.docker_app_name_var.get().strip(),
            "Compose File": self.docker_compose_path_var.get().strip(),
            "Artifact Name": self.docker_artifact_name_var.get().strip(),
            "Device Type": self.docker_device_type_var.get().strip(),
        }

        # Add conditional validation based on image source
        if image_src == "tarball":
            required_fields["Image Tarball"] = (
                self.docker_image_tarball_var.get().strip()
            )
        else:  # export
            required_fields["Docker Image Name"] = (
                self.docker_image_name_var.get().strip()
            )

        return self.validate_required_fields(required_fields)

    def _resolve_paths(
        self, compose_file: str, image_src: str, image_tarball: str, output_path: str
    ) -> tuple[bool, Path | None, Path | None, Path]:
        # Validate compose file exists
        compose_path = resolve_path(compose_file)
        if not compose_path or not compose_path.exists():
            messagebox.showerror("Error", f"Compose file not found: {compose_file}")
            return False, None, None, None

        # Validate image tarball if using existing
        image_tarball_path: Path | None = None
        if image_src == "tarball":
            image_tarball_path = resolve_path(image_tarball)
            if not image_tarball_path or not image_tarball_path.exists():
                messagebox.showerror(
                    "Error", f"Image tarball not found: {image_tarball}"
                )
                return False, None, None, None

        # Resolve output path
        output_path = self.resolve_output_path(output_path, "docker-artifact.rdfm")

        return True, compose_path, image_tarball_path, output_path

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

    def _generate_index_files(
        self,
        compose_file: Path,
        image_filename: str,
        app_dir: Path,
        app_name: str,
        temp_dir: str,
    ) -> Path:
        # Create inner index file (app_name/index)
        inner_index_content = f"{compose_file.name}\n{image_filename}\n"
        inner_index_path = app_dir / "index"
        inner_index_path.write_text(inner_index_content)
        self.cli_executor.output_queue.put(
            ("output", f"Created inner index: {app_name}/index\n")
        )
        self.cli_executor.output_queue.put(
            (
                "output",
                (f"  Contents: {compose_file.name} {image_filename}\n"),
            )
        )

        # Create outer index file
        outer_index_content = f"{app_name}/index\n"
        outer_index_path = Path(temp_dir) / "index"
        outer_index_path.write_text(outer_index_content)
        self.cli_executor.output_queue.put(("output", "Created outer index: index\n"))
        self.cli_executor.output_queue.put(
            ("output", f"  Contents: {app_name}/index\n")
        )
        return outer_index_path

    def _try_create_tarball(
        self,
        artifact_name: str,
        temp_dir: str,
        app_dir: Path,
        app_name: str,
        index_path: Path,
    ) -> Path | None:
        tarball_name = f"{artifact_name}.tar.gz"
        tarball_path = Path(temp_dir) / tarball_name
        self.cli_executor.output_queue.put(
            ("output", f"\nCreating tarball: {tarball_name}\n")
        )

        try:
            with tarfile.open(tarball_path, "w:gz") as tar:
                # Add app directory
                tar.add(app_dir, arcname=app_name)
                # Add outer index
                tar.add(index_path, arcname="index")

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

    def _handle_docker_image(
        self,
        image_source: str,
        image_tarball: Path | None,
        docker_image_name: str,
        app_dir: Path,
    ) -> str | None:
        """Handle Docker image (tarball or export).

        Args:
            image_source: Either "tarball" or "export"
            image_tarball: Path to tarball if using existing
            docker_image_name: Docker image name if exporting
            app_dir: App directory to save image to

        Returns:
            Image filename if successful, None if failed
        """
        if image_source == "tarball":
            if not try_copy_file(
                image_tarball,
                app_dir / image_tarball.name,
                self.cli_executor,
            ):
                return None
            return image_tarball.name

        # Export from Docker
        self.cli_executor.output_queue.put(
            ("output", f"Exporting Docker image: {docker_image_name}\n")
        )
        image_filename = docker_image_name.replace("/", "_").replace(":", "_") + ".tar.gz"  # noqa: E501
        image_dest = app_dir / image_filename

        success, message = self._export_docker_image(docker_image_name, image_dest)
        if not success:
            self.cli_executor.output_queue.put(("output", message + "\n"))
            self.cli_executor.output_queue.put(("status", "Docker export failed"))
            self.cli_executor.output_queue.put(("command_finished", None))
            return None

        self.cli_executor.output_queue.put(
            ("output", f"Exported Docker image to: {image_filename} - {message}\n")
        )
        return image_filename

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
        2. Copying the compose file and image (either from tarball or Docker export)
        3. Copying additional files
        4. Generating index files for RDFM
        5. Creating a tarball
        6. Running rdfm-artifact to create the final artifact
        """

        # Get values from UI
        app_name = self.docker_app_name_var.get().strip()
        compose_file = self.docker_compose_path_var.get().strip()
        image_source = self.docker_image_source_var.get()
        image_tarball = self.docker_image_tarball_var.get().strip()
        docker_image_name = self.docker_image_name_var.get().strip()
        artifact_name = self.docker_artifact_name_var.get().strip()
        device_type = self.docker_device_type_var.get().strip()
        output_path = self.docker_output_path_var.get().strip()

        # Get additional files from listbox
        additional_files = list(self.docker_files_listbox.get(0, tk.END))

        if not self._validate_docker_fields(image_source):
            return

        success, compose_file, image_tarball, output_path = self._resolve_paths(
            compose_file, image_source, image_tarball, output_path
        )
        if not success:
            return

        params: ArtifactParams = {
            "app_name": app_name,
            "compose_file": compose_file,
            "image_source": image_source,
            "image_tarball": image_tarball,
            "docker_image_name": docker_image_name,
            "artifact_name": artifact_name,
            "device_type": device_type,
            "output_path": output_path,
            "additional_files": additional_files,
        }

        artifact_creator = partial(self.create_artifact, **params)

        # Start in a new thread
        thread = threading.Thread(target=artifact_creator, daemon=True)
        thread.start()

    def _execute_artifact_steps(
        self, params: ArtifactParams, app_dir: Path, temp_dir: str
    ) -> bool:
        """Execute the main artifact creation steps.

        Args:
            params: Artifact creation parameters
            app_dir: App directory path
            temp_dir: Temporary directory path

        Returns:
            True if all steps succeeded, False otherwise
        """
        # Copy compose file
        if not try_copy_file(
            params["compose_file"],
            app_dir / params["compose_file"].name,
            self.cli_executor,
        ):
            return False

        # Handle Docker image
        if not self._check_cancellation():
            image_filename = self._handle_docker_image(
                params["image_source"],
                params["image_tarball"],
                params["docker_image_name"],
                app_dir,
            )
        if not image_filename:
            return False

        # Copy additional files
        if not self._check_cancellation or not self._try_copy_additional_files(
            params["additional_files"], app_dir
        ):
            return False

        # Generate index files
        if not self._check_cancellation():
            outer_index_path = self._generate_index_files(
                params["compose_file"],
                image_filename,
                app_dir,
                params["app_name"],
                temp_dir,
            )

        # Create tarball
        if not self._check_cancellation():
            tarball_path = self._try_create_tarball(
                params["artifact_name"],
                temp_dir,
                app_dir,
                params["app_name"],
                outer_index_path,
            )
        if not tarball_path:
            return False

        # Run rdfm-artifact
        if not self._check_cancellation():
            return self._run_rdfm_artifact(
                params["artifact_name"],
                params["device_type"],
                tarball_path,
                params["output_path"],
            )
        return False

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

            # Setup directories
            temp_dir, app_dir = self._setup_directories(params["app_name"])

            # Execute steps with cancellation checks
            if not self._check_cancellation():
                self._execute_artifact_steps(params, app_dir, temp_dir)

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
