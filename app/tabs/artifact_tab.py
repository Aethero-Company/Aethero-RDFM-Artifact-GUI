"""
Artifact Tab - RDFM artifact creation and inspection interface
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.tabs.base_tab import BaseTab
from app.tabs.artifact_tabs import (
    SingleFileCreator,
    DeltaRootfsCreator,
    DockerCreator,
    ZephyrCreator,
)
from app.theme import AetheroTheme
from app.ui_constants import (
    STANDARD_PAD,
)
from app.utils import (
    FILETYPES_RDFM,
    resolve_path_str,
)


class ArtifactTab(BaseTab):
    """Tab for creating and reading RDFM artifacts"""

    def setup_ui(self):
        """Setup the artifact tab UI with sub-tabs for different artifact creators"""
        # Main container frame
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD)

        # Read Artifact section at the top (full width)
        read_frame = ttk.LabelFrame(main_frame, text="Read Artifact")
        read_frame.pack(fill=tk.X, padx=STANDARD_PAD, pady=STANDARD_PAD)

        self.read_path_var, _, _ = self.create_labeled_entry_with_browse(
            read_frame,
            "Artifact File:",
            row=0,
            browse_title="Select Artifact File",
            browse_type="file",
            filetypes=FILETYPES_RDFM,
        )
        ttk.Button(read_frame, text="Read", command=self.read_artifact).grid(
            row=0, column=3, padx=STANDARD_PAD, pady=STANDARD_PAD
        )

        # Make the entry field expand
        read_frame.columnconfigure(1, weight=1)

        # Create notebook for artifact creation tabs
        self.creator_notebook = ttk.Notebook(main_frame)
        self.creator_notebook.pack(
            fill=tk.BOTH, expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD
        )

        # Create tabs for different artifact types
        self.setup_single_file_tab()
        self.setup_delta_tab()
        self.setup_docker_tab()
        self.setup_zephyr_tab()

        # Output area at the bottom (40% of available space)
        output_frame = ttk.LabelFrame(main_frame, text="Output")
        output_frame.pack(
            fill=tk.BOTH, expand=False, padx=STANDARD_PAD, pady=STANDARD_PAD
        )

        self.output = tk.Text(output_frame, wrap=tk.WORD, height=18)
        self.output.pack(
            fill=tk.BOTH,
            expand=True,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            side=tk.LEFT,
        )

        scrollbar = ttk.Scrollbar(
            output_frame, orient=tk.VERTICAL, command=self.output.yview
        )
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.output.config(yscrollcommand=scrollbar.set)

        # Apply theme styling to output text widget
        AetheroTheme.configure_text_widget(self.output)

    def setup_single_file_tab(self) -> None:
        """Setup the Single-File artifact tab"""
        self.single_file_creator = SingleFileCreator(
            self.creator_notebook, self.cli_executor
        )
        self.creator_notebook.add(
            self.single_file_creator.frame, text="Single-File Artifact"
        )

    def setup_delta_tab(self) -> None:
        """Setup the Delta Rootfs artifact tab"""
        self.delta_creator = DeltaRootfsCreator(
            self.creator_notebook, self.cli_executor
        )
        self.creator_notebook.add(
            self.delta_creator.frame, text="Delta Rootfs Artifact"
        )

    def setup_docker_tab(self) -> None:
        """Setup the Docker Container artifact tab"""
        self.docker_creator = DockerCreator(self.creator_notebook, self.cli_executor)
        self.creator_notebook.add(
            self.docker_creator.frame, text="Docker Container Artifact"
        )

    def setup_zephyr_tab(self) -> None:
        """Setup the Zephyr MCUBoot artifact tab"""
        self.zephyr_creator = ZephyrCreator(self.creator_notebook, self.cli_executor)
        self.creator_notebook.add(
            self.zephyr_creator.frame, text="Zephyr MCUBoot Artifact"
        )

    def read_artifact(self) -> None:
        """Read and display artifact information"""
        artifact_path_str = self.read_path_var.get().strip()

        if not artifact_path_str:
            messagebox.showwarning(
                "Input Error", "Please select an artifact file to read"
            )
            return

        # Handle path - convert to absolute path
        artifact_path = resolve_path_str(artifact_path_str)
        if not artifact_path:
            messagebox.showerror("Error", "Invalid path provided")
            return

        self.cli_executor.run_artifact_command("read", artifact_path)
