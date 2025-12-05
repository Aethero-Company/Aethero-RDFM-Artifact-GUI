"""
Base Tab - Abstract base class for all tabs
"""

import tkinter as tk
from functools import partial
from pathlib import Path
from tkinter import messagebox, ttk

from artifact_gui.cli_executor import CLIExecutor
from artifact_gui.theme import AetheroTheme
from artifact_gui.ui_constants import (
    OUTPUT_AREA_HEIGHT,
    OUTPUT_AREA_WIDTH,
    STANDARD_PAD,
)
from artifact_gui.utils import (
    FILETYPES_ALL,
    bind_combobox_selection_clear,
    browse_directory,
    browse_file,
    browse_save_file,
    extract_id_from_display,
    resolve_path,
    update_combobox_values,
)


class BaseTab:
    """Abstract base class for all application tabs.

    Provides common initialization, output area creation, and helper methods
    for dropdown management and file dialogs.
    """

    def __init__(
        self,
        parent: ttk.Frame,
        cli_executor: CLIExecutor,
        data_manager: object | None = None,
    ) -> None:
        """Initialize the base tab

        Args:
            parent: Parent widget
            cli_executor: CLI command executor
            data_manager: Optional data manager
        """
        self.parent = parent
        self.cli_executor = cli_executor
        self.frame = ttk.Frame(parent)
        self.output: tk.Text | None = None
        self.data_manager = data_manager or None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Override this method in subclasses to setup the tab UI"""
        raise NotImplementedError

    def create_output_area(self, parent: ttk.Frame, title: str = "Output") -> tk.Text:
        """Create a scrolled text output area.

        Args:
            parent: Parent widget
            title: Title for the output frame

        Returns:
            The created Text widget
        """
        output_frame = ttk.LabelFrame(parent, text=title)
        output_frame.pack(
            fill="both",
            expand=True,
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
            side=tk.RIGHT,
        )

        output = tk.Text(
            output_frame,
            height=OUTPUT_AREA_HEIGHT,
            width=OUTPUT_AREA_WIDTH,
            wrap=tk.WORD,
        )
        output.pack(
            fill="both", expand=True, padx=STANDARD_PAD, pady=STANDARD_PAD, side=tk.LEFT
        )

        # Add themed scrollbar
        scrollbar = ttk.Scrollbar(
            output_frame, orient=tk.VERTICAL, command=output.yview
        )
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        output.config(yscrollcommand=scrollbar.set)

        # Apply theme styling to text widget
        AetheroTheme.configure_text_widget(output)

        return output

    def update_combobox_values(
        self,
        combos: list[ttk.Combobox],
        values: list[str],
        preserve_selection: bool = True,
    ) -> None:
        """Update multiple combobox widgets with new values.

        Args:
            combos: List of Combobox widgets to update
            values: New list of values
            preserve_selection: If True, keep current selection if still valid
        """
        update_combobox_values(combos, values, preserve_selection)

    def get_selected_id(self, combo: ttk.Combobox) -> str | None:
        """Extract the ID from a combobox selection.

        Assumes the combobox displays items in format "(#id) name".

        Args:
            combo: Combobox widget to get selection from

        Returns:
            Extracted ID as string, or None if not found
        """
        return extract_id_from_display(combo.get())

    def browse_and_set(  # noqa: PLR0913
        self,
        var: tk.StringVar,
        title: str = "Select File",
        filetypes: list[tuple] | None = None,
        is_directory: bool = False,
        is_save: bool = False,
        default_extension: str = "",
    ) -> None:
        """Open a file dialog and set the result to a StringVar.

        Args:
            var: StringVar to update with selected path
            title: Dialog title
            filetypes: File type filters (for file dialogs)
            is_directory: If True, open directory dialog
            is_save: If True, open save dialog
            default_extension: Default extension for save dialogs
        """
        if is_directory:
            path = browse_directory(title=title)
        elif is_save:
            path = browse_save_file(
                title=title,
                filetypes=filetypes or FILETYPES_ALL,
                default_extension=default_extension,
            )
        else:
            path = browse_file(title=title, filetypes=filetypes or FILETYPES_ALL)

        if path:
            var.set(path)

    def confirm_action(self, title: str, message: str) -> bool:
        """Show a confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message

        Returns:
            True if user confirmed, False otherwise
        """
        return messagebox.askyesno(title, message)

    def show_warning(self, title: str, message: str) -> None:
        """Show a warning message dialog.

        Args:
            title: Dialog title
            message: Warning message
        """
        messagebox.showwarning(title, message)

    def show_error(self, title: str, message: str) -> None:
        """Show an error message dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show an info message dialog.

        Args:
            title: Dialog title
            message: Info message
        """
        messagebox.showinfo(title, message)

    def create_labeled_entry(
        self,
        parent: ttk.Frame,
        label_text: str,
        row: int,
        entry_var: tk.StringVar | None = None,
        width: int = 30,
    ) -> tuple[tk.StringVar, ttk.Entry]:
        """Create a label and entry field pair.

        Args:
            parent: Parent widget
            label_text: Text for the label
            row: Grid row number
            entry_var: StringVar for the entry (created if None)
            width: Entry field width

        Returns:
            Tuple of (StringVar, Entry widget)
        """
        if entry_var is None:
            entry_var = tk.StringVar()

        ttk.Label(parent, text=label_text).grid(
            row=row, column=0, sticky="w", padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        entry = ttk.Entry(parent, textvariable=entry_var, width=width)
        entry.grid(row=row, column=1, sticky="ew", padx=STANDARD_PAD, pady=STANDARD_PAD)

        return entry_var, entry

    def create_labeled_combo(  # noqa: PLR0913
        self,
        parent: ttk.Frame,
        label_text: str,
        row: int,
        values: list[str] | None = None,
        width: int = 27,
        readonly: bool = True,
        start_col: int = 0,
    ) -> tuple[tk.StringVar, ttk.Combobox]:
        """Create a label and combobox pair.

        Args:
            parent: Parent widget
            label_text: Text for the label
            row: Grid row number
            values: Initial values for the combobox
            width: Combobox width
            readonly: If True, set combobox to readonly state (default True)
            start_col: Starting column for the widgets (default 0)

        Returns:
            Tuple of (StringVar, Combobox widget)
        """
        var = tk.StringVar()

        ttk.Label(parent, text=label_text).grid(
            row=row, column=start_col, sticky="w", padx=STANDARD_PAD, pady=STANDARD_PAD
        )
        state = "readonly" if readonly else "normal"
        combo = ttk.Combobox(parent, textvariable=var, width=width, state=state)
        if values:
            combo["values"] = values
            combo.set(combo["values"][0])
        combo.grid(
            row=row,
            column=start_col + 1,
            sticky="ew",
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
        )

        # Bind selection clear for readonly comboboxes
        if readonly:
            bind_combobox_selection_clear(combo)

        return var, combo

    def bind_selection_clear(self, *combos: ttk.Combobox) -> None:
        """Bind selection clear event to readonly comboboxes.

        Clears the text selection highlight when user selects an option.

        Args:
            *combos: Combobox widgets to bind
        """
        for combo in combos:
            bind_combobox_selection_clear(combo)

    def create_button_frame(self, parent: ttk.Frame) -> ttk.Frame:
        """Create a horizontal frame for buttons.

        Args:
            parent: Parent widget

        Returns:
            The created frame
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=STANDARD_PAD, pady=STANDARD_PAD)
        return frame

    def create_labeled_entry_with_browse(  # noqa: PLR0913
        self,
        parent: ttk.Frame,
        label_text: str,
        row: int,
        entry_var: tk.StringVar | None = None,
        browse_title: str = "Select File",
        browse_type: str = "file",
        filetypes: list[tuple] | None = None,
        start_col: int = 0,
    ) -> tuple[tk.StringVar, ttk.Entry, ttk.Button]:
        """Create a label, entry field, and browse button in one row.

        Args:
            parent: Parent widget
            label_text: Text for the label
            row: Grid row number
            entry_var: StringVar for the entry (created if None)
            browse_title: Title for the browse dialog
            browse_type: Type of browse dialog ('file', 'directory', 'save')
            filetypes: File type filters (for file/save dialogs)
            start_col: Starting column for the widgets (default 0)

        Returns:
            Tuple of (StringVar, Entry widget, Button widget)
        """
        if entry_var is None:
            entry_var = tk.StringVar()

        ttk.Label(parent, text=label_text).grid(
            row=row, column=start_col, sticky="w", padx=STANDARD_PAD, pady=STANDARD_PAD
        )

        entry = ttk.Entry(parent, textvariable=entry_var)
        entry.grid(
            row=row,
            column=start_col + 1,
            sticky="ew",
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
        )

        # Create browse button with appropriate command
        if browse_type == "directory":
            browse_cmd = partial(
                browse_directory,
                title=browse_title,
                var_set=entry_var,
            )
        elif browse_type == "save":
            browse_cmd = partial(
                browse_save_file,
                title=browse_title,
                filetypes=filetypes or FILETYPES_ALL,
                var_set=entry_var,
            )
        else:  # "file"
            browse_cmd = partial(
                browse_file,
                title=browse_title,
                filetypes=filetypes or FILETYPES_ALL,
                var_set=entry_var,
            )

        button = ttk.Button(parent, text="Browse...", command=browse_cmd)
        button.grid(
            row=row,
            column=start_col + 2,
            sticky="w",
            padx=STANDARD_PAD,
            pady=STANDARD_PAD,
        )

        return entry_var, entry, button

    def validate_required_fields(
        self, fields: dict[str, str], title: str = "Input Error"
    ) -> bool:
        """Validate that required fields are filled in.

        Args:
            fields: Dictionary mapping field names to their values
            title: Dialog title for warning

        Returns:
            True if all fields are valid, False otherwise
        """
        missing = [name for name, value in fields.items() if not value]

        if missing:
            self.show_warning(
                title, f"Please fill in the required fields:\n{', '.join(missing)}"
            )
            return False

        return True

    def resolve_output_path(
        self, path_str: str, default_filename: str = "output.rdfm"
    ) -> Path:
        """Resolve and validate an output path with consistent logic.

        Args:
            path_str: User-provided path string
            default_filename: Default filename if path is empty or directory

        Returns:
            Resolved Path object ready for use
        """

        if not path_str or path_str.strip() == "":
            return Path.cwd() / default_filename

        resolved = resolve_path(path_str)
        if not resolved:
            return Path.cwd() / default_filename

        # If path is an existing directory, append default filename
        if resolved.exists() and resolved.is_dir():
            return resolved / default_filename

        return resolved
