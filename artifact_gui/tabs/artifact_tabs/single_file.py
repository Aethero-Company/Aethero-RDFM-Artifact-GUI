"""
Single-file Artifact Tab - Creation of single-file RDFM artifacts
"""

import tkinter as tk
from tkinter import ttk

from artifact_gui.tabs.base_tab import BaseTab
from artifact_gui.ui_constants import (
    STANDARD_PAD,
    SUPPORTED_DEVICE_TYPES,
)
from artifact_gui.utils import (
    FILETYPES_ALL,
    FILETYPES_RDFM,
)


class SingleFileCreator(BaseTab):
    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        pass

    def setup_ui(self) -> None:
        self.single_file_frame = ttk.Frame(self.frame)
        self.single_file_frame.pack(
            fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        self.setup_single_file_frame()

        # Bind selection clear to all readonly comboboxes
        self.bind_selection_clear(
            self.single_device_type_combo,
        )

    def setup_single_file_frame(self) -> None:
        """Setup UI components for single-file artifact creation"""
        # Configure grid columns for 2-column layout
        self.single_file_frame.columnconfigure(1, weight=3)
        self.single_file_frame.columnconfigure(4, weight=4)

        # Configure rows to expand vertically
        self.single_file_frame.rowconfigure(0, weight=1)
        self.single_file_frame.rowconfigure(1, weight=1)
        self.single_file_frame.rowconfigure(2, weight=1)

        # LEFT COLUMN
        # Input file
        self.single_file_input_var, _, _ = self.create_labeled_entry_with_browse(
            self.single_file_frame,
            "Input File:",
            row=0,
            browse_title="Select Input File",
            filetypes=FILETYPES_ALL,
        )

        # Device type
        self.device_type_var, self.single_device_type_combo = self.create_labeled_combo(
            self.single_file_frame, "Device Type:", row=1, values=SUPPORTED_DEVICE_TYPES
        )

        # Output path
        self.single_file_output_path_var, _, _ = self.create_labeled_entry_with_browse(
            self.single_file_frame,
            "Output Path:",
            row=2,
            entry_var=tk.StringVar(value="artifact.rdfm"),
            browse_title="Save Artifact As",
            browse_type="save",
            filetypes=FILETYPES_RDFM,
        )

        # RIGHT COLUMN
        # Destination directory
        ttk.Label(self.single_file_frame, text="Dest Directory:").grid(
            row=0, column=3, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.dest_dir_var = tk.StringVar()
        ttk.Entry(self.single_file_frame, textvariable=self.dest_dir_var).grid(
            row=0,
            column=4,
            columnspan=2,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="ew",
        )

        # Artifact name
        ttk.Label(self.single_file_frame, text="Artifact Name:").grid(
            row=1, column=3, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w"
        )
        self.artifact_name_var = tk.StringVar()
        ttk.Entry(self.single_file_frame, textvariable=self.artifact_name_var).grid(
            row=1,
            column=4,
            columnspan=2,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            sticky="ew",
        )

        # Rollback support checkbox
        self.rollback_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.single_file_frame, text="Rollback Support", variable=self.rollback_var
        ).grid(row=2, column=4, padx=STANDARD_PAD, pady=STANDARD_PAD, sticky="w")

        # Create button (centered at bottom)
        ttk.Button(
            self.single_file_frame,
            text="Create Artifact",
            command=self.create_single_file_artifact,
            style="Add.TButton",
        ).grid(row=3, column=0, columnspan=6, padx=STANDARD_PAD, pady=10)

    def create_single_file_artifact(self) -> None:
        """Create a single-file artifact using the rdfm-artifact CLI"""
        input_file = self.single_file_input_var.get().strip()
        dest_dir = self.dest_dir_var.get().strip()
        device_type = self.device_type_var.get().strip()
        artifact_name = self.artifact_name_var.get().strip()
        rollback = self.rollback_var.get()

        # Validate required fields
        if not self.validate_required_fields(
            {
                "Input File": input_file,
                "Dest Directory": dest_dir,
                "Device Type": device_type,
                "Artifact Name": artifact_name,
            }
        ):
            return

        # Resolve output path
        output_path = self.resolve_output_path(
            self.single_file_output_path_var.get().strip(), "artifact.rdfm"
        )

        # Build command arguments
        args = [
            "write",
            "single-file",
            "--file",
            input_file,
            "--dest-dir",
            dest_dir,
            "--device-type",
            device_type,
            "--artifact-name",
            artifact_name,
            "--output-path",
            str(output_path),
        ]

        if rollback:
            args.append("--rollback-support")

        self.cli_executor.run_artifact_command(
            *args, success_message=f"Artifact created successfully: {output_path}"
        )
