"""
Utils - Common utility functions for the RDFM GUI application

This module provides shared utility functions to reduce code duplication
across the application.
"""

import re
import shutil
import tarfile
import tempfile
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING

from app.logger import get_logger

if TYPE_CHECKING:
    from app.cli_executor import CLIExecutor

logger = get_logger(__name__)


def resolve_path(path_str: str) -> Path | None:
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
        if path.parts and path.parts[0] == "~":
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

    def clear_selection(event: tk.Event) -> None:
        event.widget.selection_clear()
        event.widget.master.focus_set()

    combo.bind("<<ComboboxSelected>>", clear_selection, add="+")


def update_combobox_values(
    combos: list[ttk.Combobox], values: list[str], preserve_selection: bool = True
) -> None:
    """Update multiple combobox widgets with new values.

    Args:
        combos: List of Combobox widgets to update
        values: New list of values
        preserve_selection: If True, keep current selection if it's still valid
    """
    for combo in combos:
        current = combo.get()
        combo["values"] = values

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


def browse_file(
    title: str = "Select File",
    filetypes: list[tuple[str, str]] | None = None,
    var_set: tk.StringVar | None = None,
    list_insert: tk.Listbox | None = None,
    highlight_list_dupes: bool = True,
) -> str:
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

    filename = filedialog.askopenfilename(title=title, filetypes=filetypes)

    if filename:
        if var_set is not None:
            var_set.set(filename)
        if (
            list_insert is not None
            and highlight_list_dupes
            and not _is_duplicate_filepath(list_insert, filename)
        ):
            list_insert.insert(tk.END, filename)
        return filename
    return ""


def browse_directory(
    title: str = "Select Directory",
    var_set: tk.StringVar | None = None,
    list_insert: tk.Listbox | None = None,
    highlight_list_dupes: bool = True,
) -> str:
    """Open a directory browser dialog and return the selected path.

    Args:
        title: Dialog window title
        initial_dir: Initial directory to open in

    Returns:
        Selected directory path as string, or empty string if cancelled
    """
    dirname = filedialog.askdirectory(title=title)
    if dirname:
        if var_set is not None:
            var_set.set(dirname)
        if (
            list_insert is not None
            and highlight_list_dupes
            and not _is_duplicate_filepath(list_insert, dirname)
        ):
            list_insert.insert(tk.END, dirname)
        return dirname
    return ""


def browse_save_file(
    title: str = "Save File",
    filetypes: list[tuple[str, str]] | None = None,
    default_extension: str = "",
    var_set: tk.StringVar | None = None,
) -> str:
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
        title=title, filetypes=filetypes, defaultextension=default_extension
    )

    if filename:
        if var_set is not None:
            var_set.set(filename)
        return filename
    return ""


def extract_id_from_display(display_text: str) -> str | None:
    """Extract the ID from a display string formatted as "(#id) name".

    Args:
        display_text: Display string in format "(#123) Item Name"

    Returns:
        Extracted ID as string, or None if not found
    """
    if not display_text:
        return None

    id_rgx = r"\(\ *#(\d+)\ *\)"
    id = re.match(id_rgx, display_text)
    if id:
        return id.groups()[0]

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


def center_window(
    window: tk.Tk | tk.Toplevel,
    width: int | None = None,
    height: int | None = None,
) -> None:
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

    window.geometry(f"{width}x{height}+{x}+{y}")


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


def try_copy_file(src: Path, dest: Path, cli_executor: "CLIExecutor") -> bool:
    logger.info(f"Trying to copy file {src} to {dest}")
    try:
        shutil.copy2(src, dest)
        cli_executor.output_queue.put(
            (
                "output",
                f"Copied file: {src.name} to {dest}\n",
            )
        )
        return True
    except (OSError, PermissionError) as e:
        cli_executor.output_queue.put(("output", f"Error copying file: {e}\n"))
        cli_executor.output_queue.put(("status", "Failed to copy file"))
        cli_executor.output_queue.put(("command_finished", None))
        return False


def make_nested_dict() -> defaultdict:
    return defaultdict(make_nested_dict, __files__=[])


def pprint_rdfm_contents(artifact_path: str) -> str | None:
    if not artifact_path:
        return None
    if not artifact_path.endswith(".rdfm"):
        return None
    with tempfile.TemporaryDirectory() as staging_dir:
        staging_path = Path(staging_dir)
        with tarfile.open(artifact_path, "r") as artifact:
            artifact.extract(artifact.getmember("data/0000.tar"), str(staging_path))
        data_tar_path = staging_path / "data" / "0000.tar"
        with tarfile.open(data_tar_path, "r") as data_tar:
            fn_ptr = data_tar.extractfile("filename")
            update_file = fn_ptr.read().decode("utf-8").strip()
            dest_ptr = data_tar.extractfile("dest_dir")
            update_dest = dest_ptr.read().decode("utf-8")
            tgz_rgx = r"(.*\.tar\.gz)|(.*\.tgz)"
            if re.search(tgz_rgx, update_file):
                data_member = data_tar.getmember(update_file)
                data_tar.extract(data_member, str(staging_path))
                return update_dest + pprint_tar_contents(
                    str(staging_path / update_file)
                )
            return update_dest + "└── " + update_file
    return None


def pprint_tar_contents(tar_path: str) -> str:
    struct = make_nested_dict()

    with tarfile.open(tar_path, "r") as tar:
        for member in tar:
            parts = member.name.strip("/").split("/")

            current = struct
            for part in parts[:-1]:
                current = current[part]

            if member.isdir():
                current[parts[-1]]
            elif member.isfile():
                current["__files__"].append(parts[-1])

    return _pprint_struct(struct)


def _pprint_struct(struct: dict, out_str: str = "", depth: int = 0) -> str:
    prefix = "│  " * depth

    files = sorted(struct.get("__files__", []))
    subdirs = sorted(k for k in struct if k != "__files__")

    items = [(f, False) for f in files] + [(d, True) for d in subdirs]

    for i, (name, is_dir) in enumerate(items):
        connector = "└── " if i == len(items) - 1 else "├── "
        suffix = "/" if is_dir else ""
        out_str += f"{prefix}{connector}{name}{suffix}\n"

        if is_dir:
            out_str = _pprint_struct(struct[name], out_str, depth + 1)

    return out_str


# Common file type filters for dialogs
FILETYPES_ALL: list[tuple[str, str]] = [("All files", "*.*")]
FILETYPES_RDFM: list[tuple[str, str]] = [("RDFM artifacts", "*.rdfm")]
FILETYPES_TAR: list[tuple[str, str]] = [("Gzip archives", "*.tar.gz *.tgz")]
FILETYPES_COMPOSE: list[tuple[str, str]] = [("YAML Files", "*.yml *.yaml")]
FILETYPES_ZEPHYR: list[tuple[str, str]] = [("Zephyr Binaries", "*.bin")]
FILETYPES_ROOTFS: list[tuple[str, str]] = [
    ("Rootfs files", "*.ext4 *.squashfs *.tar *.tar.gz *.tgz"),
    ("EXT4 images", "*.ext4"),
    ("SquashFS images", "*.squashfs"),
    ("TAR archives", "*.tar *.tar.gz *.tgz"),
    ("All files", "*.*"),
]
