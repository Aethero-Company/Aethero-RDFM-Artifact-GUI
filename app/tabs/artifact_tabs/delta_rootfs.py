"""
Delta Rootfs Artifact Tab - Creation of delta rootfs RDFM artifacts
"""

import tkinter as tk
from tkinter import ttk
from typing import Any

from app.tabs.base_tab import BaseTab
from app.ui_constants import (
    STANDARD_PAD,
    SUPPORTED_DEVICE_TYPES,
)
from app.utils import (
    FILETYPES_RDFM,
)


class DeltaRootfsCreator(BaseTab):
    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        pass

    def setup_ui(self) -> Any | None:
        self.delta_frame = ttk.Frame(self.frame)
        self.delta_frame.pack(
            fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        self.setup_delta_rootfs_frame()

        # Bind selection clear to all readonly comboboxes
        self.bind_selection_clear(
            self.delta_device_type_combo,
            self.delta_algo_combo,
        )

    def setup_delta_rootfs_frame(self) -> None:
        """Setup UI components for delta rootfs artifact creation"""
        # Configure grid columns for 2-column layout
        self.delta_frame.columnconfigure(1, weight=1)
        self.delta_frame.columnconfigure(4, weight=1)

        # Configure rows to expand vertically
        self.delta_frame.rowconfigure(0, weight=1)
        self.delta_frame.rowconfigure(1, weight=1)
        self.delta_frame.rowconfigure(2, weight=1)

        # LEFT COLUMN
        # Base artifact
        self.base_artifact_var, _, _ = self.create_labeled_entry_with_browse(
            self.delta_frame,
            "Base Artifact:",
            row=0,
            browse_title="Select Base Artifact",
            filetypes=FILETYPES_RDFM,
        )

        # Device type for delta
        self.delta_device_type_var, self.delta_device_type_combo = (
            self.create_labeled_combo(
                self.delta_frame, "Device Type:", row=1, values=SUPPORTED_DEVICE_TYPES
            )
        )

        # Delta algorithm
        self.delta_algorithm_var, self.delta_algo_combo = self.create_labeled_combo(
            self.delta_frame, "Delta Algorithm:", row=2, values=["rsync", "xdelta"]
        )

        # RIGHT COLUMN
        # Target artifact
        self.target_artifact_var, _, _ = self.create_labeled_entry_with_browse(
            self.delta_frame,
            "Target Artifact:",
            row=0,
            browse_title="Select Target Artifact",
            filetypes=FILETYPES_RDFM,
            start_col=3,
        )

        # Artifact name for delta
        ttk.Label(self.delta_frame, text="Artifact Name:").grid(
            row=1, column=3, sticky="w", padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        self.delta_artifact_name_var = tk.StringVar()
        ttk.Entry(self.delta_frame, textvariable=self.delta_artifact_name_var).grid(
            row=1,
            column=4,
            columnspan=2,
            sticky="ew",
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
        )

        # Output path for delta
        self.delta_output_path_var, _, _ = self.create_labeled_entry_with_browse(
            self.delta_frame,
            "Output Path:",
            row=2,
            entry_var=tk.StringVar(value="delta-artifact.rdfm"),
            browse_title="Save Delta Artifact As",
            browse_type="save",
            filetypes=FILETYPES_RDFM,
            start_col=3,
        )

        # Create delta button (centered at bottom)
        ttk.Button(
            self.delta_frame,
            text="Create Delta Artifact",
            command=self.create_delta_artifact,
            style="Add.TButton",
        ).grid(row=3, column=1, columnspan=4, padx=STANDARD_PAD, pady=10)

    def create_delta_artifact(self) -> None:
        """Create a delta rootfs artifact from base and target artifacts"""
        base_artifact = self.base_artifact_var.get().strip()
        target_artifact = self.target_artifact_var.get().strip()
        device_type = self.delta_device_type_var.get().strip()
        artifact_name = self.delta_artifact_name_var.get().strip()
        delta_algorithm = self.delta_algorithm_var.get().strip()

        # Validate required fields
        if not self.validate_required_fields(
            {"Base Artifact": base_artifact, "Target Artifact": target_artifact}
        ):
            return

        # Resolve output path
        output_path = self.resolve_output_path(
            self.delta_output_path_var.get().strip(), "delta-artifact.rdfm"
        )

        # Build command arguments
        args = [
            "write",
            "delta-rootfs-image",
            "--base-artifact",
            base_artifact,
            "--target-artifact",
            target_artifact,
            "--output-path",
            str(output_path),
        ]

        if device_type:
            args.extend(["--device-type", device_type])

        if artifact_name:
            args.extend(["--artifact-name", artifact_name])

        if delta_algorithm:
            args.extend(["--delta-algorithm", delta_algorithm])

        self.cli_executor.run_artifact_command(
            *args, success_message=f"Delta artifact created successfully: {output_path}"
        )
