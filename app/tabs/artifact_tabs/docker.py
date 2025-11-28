"""
Docker Artifact Tab - Creation of Docker RDFM artifacts
"""

import shutil
import subprocess
import tarfile
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from app.tabs.base_tab import BaseTab
from app.theme import AetheroTheme
from app.ui_constants import (
    DEFAULT_DOCKER_APP_NAME,
    DOCKER_CONTAINER_DEST_DIR,
    DOCKER_IMAGE_FILENAME,
    STANDARD_PAD,
    SUPPORTED_DEVICE_TYPES,
)
from app.utils import (
    FILETYPES_ALL,
    FILETYPES_COMPOSE,
    FILETYPES_RDFM,
    FILETYPES_TAR,
    browse_directory,
    browse_file,
    resolve_path,
)


class DockerCreator(BaseTab):
    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        pass

    def setup_ui(self) -> Any | None:
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

            # Check if cancelled
            if (
                docker_returncode == -15 or docker_returncode == -9
            ):  # SIGTERM or SIGKILL
                return False, "Export cancelled"

            # Check for errors
            if docker_returncode != 0:
                error_msg = docker_stderr.decode() if docker_stderr else "Unknown error"
                return False, (
                    f"Error exporting Docker image: {error_msg}\n\n"
                    "Note: Docker export may fail if:\n"
                    "- Docker is not installed or running\n"
                    "- The image doesn't exist locally\n"
                    "- Running in a containerized environment without Docker access\n"
                )

            if gzip_process.returncode != 0:
                error_msg = gzip_stderr.decode() if gzip_stderr else "Gzip error"
                return False, f"Error compressing image: {error_msg}"

            # Check if we got any data
            if len(gzip_output) == 0:
                return False, (
                    "Error: Docker save produced no output.\n"
                    "The image may not exist or Docker may not be accessible."
                )

            # Write the output to file
            with open(output_path, "wb") as f:
                f.write(gzip_output)

            # Report size
            size_mb = len(gzip_output) / (1024 * 1024)
            return True, f"Exported Docker image ({size_mb:.1f} MB)"

        except FileNotFoundError as e:
            return False, (
                f"Error: {e}\n"
                "Docker or gzip command not found. Ensure Docker is installed."
            )
        except Exception as e:
            return False, f"Error during Docker export: {str(e)}"
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
        import threading

        # Show loading state immediately
        self.docker_refresh_images_btn.config(state="disabled", text="Loading...")
        self.cli_executor.output_queue.put(("status", "Loading Docker images..."))

        def fetch_images():
            try:
                # Run docker images command to get list of images
                result = subprocess.run(
                    ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
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
        import threading

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

        # Validate required fields based on image source
        required_fields = {
            "App Name": app_name,
            "Compose File": compose_file,
            "Artifact Name": artifact_name,
            "Device Type": device_type,
        }

        # Add conditional validation based on image source
        if image_source == "tarball":
            required_fields["Image Tarball"] = image_tarball
        else:  # export
            required_fields["Docker Image Name"] = docker_image_name

        if not self.validate_required_fields(required_fields):
            return

        # Validate compose file exists
        compose_path = resolve_path(compose_file)
        if not compose_path or not compose_path.exists():
            messagebox.showerror("Error", f"Compose file not found: {compose_file}")
            return

        # Validate image tarball if using existing
        image_tarball_path: Path | None = None
        if image_source == "tarball":
            image_tarball_path = resolve_path(image_tarball)
            if not image_tarball_path or not image_tarball_path.exists():
                messagebox.showerror(
                    "Error", f"Image tarball not found: {image_tarball}"
                )
                return

        # Resolve output path
        output_path = self.resolve_output_path(output_path, "docker-artifact.rdfm")

        # Run the creation in a separate thread
        def create_artifact():
            temp_dir = None
            try:
                # Mark as running for cancellation support
                self.cli_executor.set_current_process(None, is_running=True)

                self.cli_executor.output_queue.put(("clear", None))
                self.cli_executor.output_queue.put(
                    ("status", "Creating Docker container artifact...")
                )
                self.cli_executor.output_queue.put(("command_started", None))

                # Create temporary directory for building the artifact structure
                temp_dir = tempfile.mkdtemp(prefix="rdfm_docker_")
                self.cli_executor.output_queue.put(
                    ("output", f"Creating temporary directory: {temp_dir}\n")
                )

                # Create app directory
                app_dir = Path(temp_dir) / app_name
                app_dir.mkdir()
                self.cli_executor.output_queue.put(
                    ("output", f"Created app directory: {app_name}/\n")
                )

                # Copy compose file
                # Check for cancellation before proceeding
                if self.cli_executor.cancel_requested:
                    self.cli_executor.output_queue.put(
                        ("output", "\nOperation cancelled by user\n")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

                try:
                    compose_dest = app_dir / compose_path.name
                    shutil.copy2(compose_path, compose_dest)
                    self.cli_executor.output_queue.put(
                        ("output", f"Copied compose file: {compose_path.name}\n")
                    )
                except (OSError, PermissionError) as e:
                    self.cli_executor.output_queue.put(
                        ("output", f"Error copying compose file: {e}\n")
                    )
                    self.cli_executor.output_queue.put(
                        ("status", "Failed to copy compose file")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

                # Handle Docker image
                # Check for cancellation before proceeding
                if self.cli_executor.cancel_requested:
                    self.cli_executor.output_queue.put(
                        ("output", "\nOperation cancelled by user\n")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

                if image_source == "tarball":
                    # Copy existing tarball
                    try:
                        image_dest = app_dir / image_tarball_path.name
                        shutil.copy2(image_tarball_path, image_dest)
                        image_filename = image_tarball_path.name
                        self.cli_executor.output_queue.put(
                            ("output", f"Copied image tarball: {image_filename}\n")
                        )
                    except (OSError, PermissionError) as e:
                        self.cli_executor.output_queue.put(
                            ("output", f"Error copying image tarball: {e}\n")
                        )
                        self.cli_executor.output_queue.put(
                            ("status", "Failed to copy image tarball")
                        )
                        self.cli_executor.output_queue.put(("command_finished", None))
                        return
                else:
                    # Export from Docker
                    self.cli_executor.output_queue.put(
                        ("output", f"Exporting Docker image: {docker_image_name}\n")
                    )
                    image_filename = DOCKER_IMAGE_FILENAME
                    image_dest = app_dir / image_filename

                    success, message = self._export_docker_image(
                        docker_image_name, image_dest
                    )
                    if not success:
                        self.cli_executor.output_queue.put(("output", message + "\n"))
                        self.cli_executor.output_queue.put(
                            ("status", "Docker export failed")
                        )
                        self.cli_executor.output_queue.put(("command_finished", None))
                        return

                    self.cli_executor.output_queue.put(
                        (
                            "output",
                            f"Exported Docker image to: {image_filename} - {message}\n",
                        )
                    )

                # Copy additional files
                # Check for cancellation before proceeding
                if self.cli_executor.cancel_requested:
                    self.cli_executor.output_queue.put(
                        ("output", "\nOperation cancelled by user\n")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

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
                        return

                # Create inner index file (app_name/index)
                inner_index_content = f"{compose_path.name}\n{image_filename}\n"
                inner_index_path = app_dir / "index"
                inner_index_path.write_text(inner_index_content)
                self.cli_executor.output_queue.put(
                    ("output", f"Created inner index: {app_name}/index\n")
                )
                self.cli_executor.output_queue.put(
                    ("output", f"  Contents: {compose_path.name}, {image_filename}\n")
                )

                # Create outer index file
                outer_index_content = f"{app_name}/index\n"
                outer_index_path = Path(temp_dir) / "index"
                outer_index_path.write_text(outer_index_content)
                self.cli_executor.output_queue.put(
                    ("output", "Created outer index: index\n")
                )
                self.cli_executor.output_queue.put(
                    ("output", f"  Contents: {app_name}/index\n")
                )

                # Create tarball
                # Check for cancellation before proceeding
                if self.cli_executor.cancel_requested:
                    self.cli_executor.output_queue.put(
                        ("output", "\nOperation cancelled by user\n")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

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
                        tar.add(outer_index_path, arcname="index")

                    self.cli_executor.output_queue.put(
                        ("output", "Tarball created successfully\n")
                    )
                except (OSError, tarfile.TarError) as e:
                    self.cli_executor.output_queue.put(
                        ("output", f"Error creating tarball: {e}\n")
                    )
                    self.cli_executor.output_queue.put(
                        ("status", "Failed to create tarball")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

                # Run rdfm-artifact to create the final artifact
                # Check for cancellation before proceeding
                if self.cli_executor.cancel_requested:
                    self.cli_executor.output_queue.put(
                        ("output", "\nOperation cancelled by user\n")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

                self.cli_executor.output_queue.put(
                    ("output", "\nRunning rdfm-artifact...\n")
                )

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

                # Use Popen instead of run so we can cancel it
                process = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                # Register the process for cancellation
                self.cli_executor.set_current_process(process, is_running=True)

                # Wait for process and capture output
                stdout, stderr = process.communicate()

                # Clear the process reference
                self.cli_executor.set_current_process(None, is_running=True)

                # Check if cancelled
                if (
                    process.returncode == -15 or process.returncode == -9
                ):  # SIGTERM or SIGKILL
                    self.cli_executor.output_queue.put(
                        ("output", "\nOperation cancelled by user\n")
                    )
                    self.cli_executor.output_queue.put(("command_finished", None))
                    return

                if stdout:
                    self.cli_executor.output_queue.put(("output", stdout))
                if stderr:
                    self.cli_executor.output_queue.put(("output", stderr))

                if process.returncode == 0:
                    self.cli_executor.output_queue.put(
                        (
                            "output",
                            f"\nDocker container artifact created successfully: {output_path}\n",
                        )
                    )
                    self.cli_executor.output_queue.put(
                        ("status", "Docker artifact created successfully")
                    )
                else:
                    self.cli_executor.output_queue.put(
                        ("status", f"Command failed with code {process.returncode}")
                    )

                self.cli_executor.output_queue.put(("command_finished", None))

            except Exception as e:
                self.cli_executor.output_queue.put(("output", f"Error: {str(e)}\n"))
                self.cli_executor.output_queue.put(
                    ("status", "Docker artifact creation failed")
                )
                self.cli_executor.output_queue.put(("command_finished", None))
            finally:
                # Reset process tracking
                self.cli_executor.clear_current_process()

                # Cleanup temp directory
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

        # Start in a new thread
        thread = threading.Thread(target=create_artifact, daemon=True)
        thread.start()
