"""
Zephyr Artifact Tab - Creation of Zephyr RDFM artifacts
"""

import tkinter as tk
from tkinter import ttk

from app.tabs.base_tab import BaseTab
from app.ui_constants import (
    STANDARD_PAD,
    SUPPORTED_DEVICE_TYPES,
)
from app.utils import (
    FILETYPES_RDFM,
    FILETYPES_ZEPHYR,
)


class ZephyrCreator(BaseTab):
    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        pass

    def setup_ui(self) -> None:
        self.zephyr_frame = ttk.Frame(self.frame)
        self.zephyr_frame.pack(
            fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        self.setup_zephyr_frame()

        # Bind selection clear to all readonly comboboxes
        self.bind_selection_clear(
            self.zephyr_device_type_combo,
        )

    def setup_zephyr_frame(self) -> None:
        """Setup UI components for Zephyr MCUBoot artifact creation"""
        # Configure grid columns for 2-column layout
        self.zephyr_frame.columnconfigure(1, weight=1)
        self.zephyr_frame.columnconfigure(4, weight=1)

        # Configure rows to expand vertically
        self.zephyr_frame.rowconfigure(0, weight=1)
        self.zephyr_frame.rowconfigure(1, weight=1)
        self.zephyr_frame.rowconfigure(2, weight=1)

        # LEFT COLUMN
        # Input file
        self.zephyr_bin_input_var, _, _ = self.create_labeled_entry_with_browse(
            self.zephyr_frame,
            "Input File:",
            row=0,
            browse_title="Select Signed Binary Image",
            filetypes=FILETYPES_ZEPHYR,
        )

        # Device type
        self.zephyr_device_type_var, self.zephyr_device_type_combo = (
            self.create_labeled_combo(
                self.zephyr_frame, "Device Type:", row=1, values=SUPPORTED_DEVICE_TYPES
            )
        )

        # RIGHT COLUMN
        # Output path
        self.zephyr_output_path_var, _, _ = self.create_labeled_entry_with_browse(
            self.zephyr_frame,
            "Output Path:",
            row=1,
            entry_var=tk.StringVar(value="zephyr-artifact.rdfm"),
            browse_title="Save Artifact As",
            browse_type="save",
            filetypes=FILETYPES_RDFM,
            start_col=3,
        )

        # Create button (centered at bottom)
        ttk.Button(
            self.zephyr_frame,
            text="Create Zephyr Artifact",
            command=self.create_zephyr_artifact,
            style="Add.TButton",
        ).grid(row=3, column=1, columnspan=4, padx=STANDARD_PAD, pady=10)

    def create_zephyr_artifact(self) -> None:
        """Create a Zephyr MCUBoot artifact"""
        input_file = self.zephyr_bin_input_var.get().strip()
        device_type = self.zephyr_device_type_var.get().strip()

        # Validate required fields
        if not self.validate_required_fields(
            {"Input File": input_file, "Device Type": device_type}
        ):
            return

        # Resolve output path
        output_path = self.resolve_output_path(
            self.zephyr_output_path_var.get().strip(), "zephyr-artifact.rdfm"
        )

        # Build command arguments
        args = [
            "write",
            "zephyr-image",
            "--file",
            input_file,
            "--device-type",
            device_type,
            "--output-path",
            str(output_path),
        ]

        self.cli_executor.run_artifact_command(
            *args, success_message=f"Artifact created successfully: {output_path}"
        )
