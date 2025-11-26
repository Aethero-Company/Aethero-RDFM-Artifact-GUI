"""
Utils - Common utility functions for the RDFM GUI application

This module provides shared utility functions to reduce code duplication
across the application.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import tkinter as tk
from tkinter import ttk, filedialog


def resolve_path(path_str: str) -> Optional[Path]:
    """Resolve a user-provided path string to an absolute Path object.

    Handles:
    - Empty strings (returns None)
    - Tilde expansion (~/)
    - Relative paths (resolved against CWD)
    - Already absolute paths

    Args:
        path_str: User-provided path string

    Returns:
        Resolved Path object, or None if input is empty
    """
    if not path_str:
        return None

    path_str = path_str.strip()
    if not path_str:
        return None

    path = Path(path_str)

    if not path.is_absolute():
        if path.parts and path.parts[0] == '~':
            path = path.expanduser()
        else:
            path = (Path.cwd() / path).resolve()

    return path


def resolve_path_str(path_str: str) -> str:
    """Resolve a user-provided path string to an absolute path string.

    Convenience wrapper around resolve_path that returns a string.

    Args:
        path_str: User-provided path string

    Returns:
        Resolved path as string, or empty string if input is empty
    """
    resolved = resolve_path(path_str)
    return str(resolved) if resolved else ""


def bind_combobox_selection_clear(combo: ttk.Combobox) -> None:
    """Bind event handler to clear selection highlight when user selects an option.

    This prevents the blue text highlight from appearing on readonly comboboxes
    after selection by clearing selection and redirecting focus to the parent.

    Args:
        combo: Combobox widget to bind
    """
    def clear_selection(event):
        event.widget.selection_clear()
        event.widget.master.focus_set()

    combo.bind("<<ComboboxSelected>>", clear_selection, add="+")


def update_combobox_values(combos: List[ttk.Combobox], values: List[str],
                          preserve_selection: bool = True) -> None:
    """Update multiple combobox widgets with new values.

    Args:
        combos: List of Combobox widgets to update
        values: New list of values
        preserve_selection: If True, keep current selection if it's still valid
    """
    for combo in combos:
        current = combo.get()
        combo['values'] = values

        if preserve_selection and current in values:
            # Keep current selection
            pass
        elif values:
            # Select first item if current is invalid or empty
            combo.set(values[0])
        else:
            # Clear if no values
            combo.set("")

        # Clear selection highlight on readonly comboboxes after event processing
        combo.after_idle(combo.selection_clear)

def _is_duplicate_filepath(listbox: tk.Listbox, filepath: str) -> bool:
    """Check if a filepath is already in the listbox.

    Args:
        listbox: Listbox widget to check
        filepath: File path to search for

    Returns:
        True if the filepath is found, False otherwise
    """
    for i in range(listbox.size()):
        path = listbox.get(i)
        if filepath == path:
            listbox.select_clear(0, tk.END)
            listbox.selection_set(i)
            return True
    return False

def browse_file(title: str = "Select File",
                filetypes: Optional[List[Tuple[str, str]]] = None,
                var_set: Optional[tk.StringVar] = None,
                list_insert: Optional[tk.Listbox] = None,
                highlight_list_dupes: bool = True) -> str:
    """Open a file browser dialog and return the selected path.

    Args:
        title: Dialog window title
        filetypes: List of (description, pattern) tuples for file type filter
        initial_dir: Initial directory to open in

    Returns:
        Selected file path as string, or empty string if cancelled
    """
    if filetypes is None:
        filetypes = FILETYPES_ALL

    filename = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes
    )

    if var_set is not None and filename:
        var_set.set(filename)
    if list_insert is not None and filename:
        if highlight_list_dupes and not _is_duplicate_filepath(list_insert, filename):
            list_insert.insert(tk.END, filename)

def browse_directory(title: str = "Select Directory",
                     var_set: Optional[tk.StringVar] = None,
                     list_insert: Optional[tk.Listbox] = None,
                     highlight_list_dupes: bool = True) -> str:
    """Open a directory browser dialog and return the selected path.

    Args:
        title: Dialog window title
        initial_dir: Initial directory to open in

    Returns:
        Selected directory path as string, or empty string if cancelled
    """
    dirname = filedialog.askdirectory(
        title=title
    )
    if var_set is not None and dirname:
        var_set.set(dirname)
    if list_insert is not None and dirname:
        if highlight_list_dupes and not _is_duplicate_filepath(list_insert, dirname):
            list_insert.insert(tk.END, dirname)


def browse_save_file(title: str = "Save File",
                     filetypes: Optional[List[Tuple[str, str]]] = None,
                     default_extension: str = "",
                     var_set: Optional[tk.StringVar] = None) -> str:
    """Open a save file dialog and return the selected path.

    Args:
        title: Dialog window title
        filetypes: List of (description, pattern) tuples for file type filter
        default_extension: Default extension to append if none specified
        initial_dir: Initial directory to open in

    Returns:
        Selected file path as string, or empty string if cancelled
    """
    if filetypes is None:
        filetypes = FILETYPES_ALL

    filename = filedialog.asksaveasfilename(
        title=title,
        filetypes=filetypes,
        defaultextension=default_extension
    )

    if var_set is not None and filename:
        var_set.set(filename)


def extract_id_from_display(display_text: str) -> Optional[str]:
    """Extract the ID from a display string formatted as "(#id) name".

    Args:
        display_text: Display string in format "(#123) Item Name"

    Returns:
        Extracted ID as string, or None if not found
    """
    if not display_text:
        return None

    # Format is "(#id) name"
    if display_text.startswith("(#") and ")" in display_text:
        end = display_text.index(")")
        return display_text[2:end]

    return None


def format_display_name(item_id: str, name: str) -> str:
    """Format an ID and name into the standard display format.

    Args:
        item_id: The item's ID
        name: The item's display name

    Returns:
        Formatted string as "(#id) name"
    """
    return f"(#{item_id}) {name}"


def center_window(window: tk.Tk | tk.Toplevel, width: Optional[int] = None, height: Optional[int] = None) -> None:
    """Center a window on the screen.

    Args:
        window: The window to center
        width: Window width (if None, use current width)
        height: Window height (if None, use current height)
    """
    window.update_idletasks()

    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    window.geometry(f'{width}x{height}+{x}+{y}')


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length with a suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: String to append when truncating

    Returns:
        Truncated text or original if under max_length
    """
    if len(text) <= max_length:
        return text

    truncate_at = max_length - len(suffix)
    return text[:truncate_at] + suffix


# Common file type filters for dialogs
FILETYPES_ALL: List[Tuple[str, str]] = [("All files", "*.*")]
FILETYPES_RDFM: List[Tuple[str, str]] = [("RDFM artifacts", "*.rdfm")]
FILETYPES_PEM: List[Tuple[str, str]] = [("PEM certificates", "*.pem"), ("All files", "*.*")]
FILETYPES_TAR: List[Tuple[str, str]] = [("TAR archives", "*.tar"), ("Gzip archives", "*.tar.gz *.tgz")]
FILETYPES_COMPOSE: List[Tuple[str, str]] = [("YAML Files", "*.yml *.yaml")]
FILETYPES_ZEPHYR: List[Tuple[str, str]] = [("Zephyr Binaries", "*.bin")]
FILETYPES_ROOTFS: List[Tuple[str, str]] = [
    ("Rootfs files", "*.ext4 *.squashfs *.tar *.tar.gz *.tgz"),
    ("EXT4 images", "*.ext4"),
    ("SquashFS images", "*.squashfs"),
    ("TAR archives", "*.tar *.tar.gz *.tgz"),
    ("All files", "*.*")
]
