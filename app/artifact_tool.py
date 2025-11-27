#!/usr/bin/env python3
"""
RDFM Artifact Tool - Standalone GUI for artifact creation and inspection

This tool can be run independently of the main RDFM Management GUI.
It provides functionality to read and create RDFM artifacts.
"""

import queue
import tkinter as tk
from tkinter import ttk

from app.cli_executor import CLIExecutor
from app.logger import get_logger, setup_logging
from app.tabs.artifact_tab import ArtifactTab
from app.theme import AetheroTheme

# Initialize logging
logger = get_logger(__name__)


class ArtifactTool:
    """Standalone artifact creation and inspection tool"""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the Artifact Tool application

        Args:
            root: The main Tkinter window
        """
        logger.info("Initializing RDFM Artifact Tool")
        self.root = root
        self.root.title("RDFM Artifact Tool")
        self.root.geometry("1400x900")

        # Apply Aethero theme
        logger.debug("Applying Aethero theme")
        self.style = AetheroTheme.apply_theme(root)

        # Set application icon
        self.app_icon = AetheroTheme.set_app_icon(root)

        # Queue for thread-safe GUI updates
        self.output_queue: "queue.Queue[tuple]" = queue.Queue()

        # Initialize managers (settings manager needed for CLIExecutor but not used for artifacts)
        self.cli_executor = CLIExecutor(self.output_queue)

        # Create the main interface
        self.setup_ui()

        # Start output queue processor
        self.process_output_queue()

    def setup_ui(self) -> None:
        """Setup the main UI components"""
        # Use grid layout to ensure status bar is always visible
        self.root.grid_rowconfigure(0, weight=0)  # Header fixed height
        self.root.grid_rowconfigure(1, weight=1)  # Main content expands
        self.root.grid_rowconfigure(2, weight=0)  # Status bar fixed height
        self.root.grid_columnconfigure(0, weight=1)

        # Create header frame
        header_frame = tk.Frame(self.root, background=AetheroTheme.DARK_GRAY, height=50)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)

        # Load and display the logo in header
        self.logo_image = None
        logo_path = AetheroTheme.get_logo_path()
        if logo_path:
            from PIL import Image, ImageTk

            img = Image.open(logo_path)
            img.thumbnail((160, 40), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img)
            logo_label = tk.Label(
                header_frame, image=self.logo_image, background=AetheroTheme.DARK_GRAY
            )
            logo_label.pack(side=tk.LEFT, padx=15, pady=5)
        else:
            # Text fallback
            text_logo = tk.Label(
                header_frame,
                text="AETHERO",
                font=("TkDefaultFont", 14, "bold"),
                background=AetheroTheme.DARK_GRAY,
                foreground=AetheroTheme.CYAN_ACCENT,
            )
            text_logo.pack(side=tk.LEFT, padx=15, pady=5)

        # App title in header
        title_label = tk.Label(
            header_frame,
            text="RDFM Artifact Tool",
            font=("TkDefaultFont", 12, "bold"),
            background=AetheroTheme.DARK_GRAY,
            foreground=AetheroTheme.PRIMARY_TEXT,
        )
        title_label.pack(side=tk.LEFT, padx=10)

        info_label = tk.Label(
            header_frame,
            text="Version 0.1",
            font=("TkDefaultFont", 9),
            background=AetheroTheme.DARK_GRAY,
            foreground=AetheroTheme.CYAN_ACCENT,
        )
        info_label.pack(side=tk.RIGHT, padx=15)

        # Create the artifact tab directly in the main window
        self.artifact_tab = ArtifactTab(self.root, self.cli_executor)
        # Grid the artifact tab's frame in row 1
        self.artifact_tab.frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Create status bar frame with cancel button in row 2
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=2, column=0, sticky="ew")

        # Status bar label
        self.status_bar = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Cancel button (hidden by default)
        self.cancel_button = ttk.Button(
            status_frame, text="Cancel", command=self.cancel_current_command, width=8
        )

    def cancel_current_command(self) -> None:
        """Cancel the currently running command"""
        # Check if this is a force cancel (button text changed)
        force = self.cancel_button.cget("text") == "Force Cancel"
        self.cli_executor.cancel_command(force=force)

    def process_output_queue(self) -> None:
        """Process output queue for thread-safe GUI updates"""
        try:
            while True:
                msg_type, msg_data = self.output_queue.get_nowait()

                if msg_type == "status":
                    self.status_bar.config(text=msg_data)
                elif msg_type == "clear":
                    if self.artifact_tab.output:
                        self.artifact_tab.output.delete("1.0", tk.END)
                elif msg_type == "output":
                    if self.artifact_tab.output:
                        self.artifact_tab.output.insert(tk.END, msg_data)
                        self.artifact_tab.output.see(tk.END)
                elif msg_type == "command_started":
                    self.cancel_button.config(text="Cancel")
                    self.cancel_button.pack(side=tk.RIGHT, padx=5, pady=2)
                elif msg_type == "cancel_requested":
                    # Change button to Force Cancel after graceful cancel requested
                    self.cancel_button.config(text="Force Cancel")
                elif msg_type == "command_finished":
                    self.cancel_button.pack_forget()
                    self.cancel_button.config(text="Cancel")
                    self.cli_executor.reset_cancel_state()

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.process_output_queue)


def main() -> None:
    """Main entry point for the RDFM Artifact Tool"""
    # Setup logging
    setup_logging()
    logger.info("Starting RDFM Artifact Tool")

    try:
        root = tk.Tk()
        _ = ArtifactTool(root)
        logger.info("Application initialized successfully")
        root.mainloop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise
    finally:
        logger.info("Application shutting down")


if __name__ == "__main__":
    main()
