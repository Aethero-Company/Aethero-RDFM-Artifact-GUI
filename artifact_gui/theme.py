"""
Aethero Theme - Dark color scheme and styling for RDFM GUI

Based on Aethero brand colors from https://aethero.com
"""

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageTk


class AetheroTheme:
    """Aethero-inspired dark color theme for the RDFM GUI"""

    # Primary Brand Colors
    PRIMARY_BLUE = "#115cfa"  # Main accent blue from website
    CYAN_ACCENT = "#7ED4E6"  # Light cyan from logo accents
    TEAL = "#4A6D7C"  # Dark teal from logo circle

    # Background Colors (Dark Theme)
    DARK_BG = "#000000"  # Pure black - main background
    DARK_GRAY = "#0a0a0a"  # Header/tabs/label frames background
    MID_GRAY = "#1f1f1f"  # Medium gray - panels/cards
    LIGHT_GRAY = "#2e2e2e"  # Lighter gray - borders/dividers

    # Text Colors
    PRIMARY_TEXT = "#ededed"  # Light gray for main text
    SECONDARY_TEXT = "#a1a1a1"  # Gray for secondary text
    MUTED_TEXT = "#6c6c6c"  # Muted text for disabled states

    # Status Colors
    SUCCESS = "#28a745"  # Green for success states
    WARNING = "#ffc107"  # Amber for warnings
    ERROR = "#dc3545"  # Red for errors
    INFO = "#17a2b8"  # Cyan for info

    # Button Colors - Add/Create/Auth (Blue)
    BTN_ADD_BG = "#0e2146"
    BTN_ADD_BORDER = "#153471"
    BTN_ADD_TEXT = "#67a5f4"

    # Button Colors - Delete/Cancel/Deauth (Red)
    BTN_DELETE_BG = "#440d13"
    BTN_DELETE_BORDER = "#6f101b"
    BTN_DELETE_TEXT = "#ff4d3d"

    # Button Colors - Default/Other (Gray)
    BTN_DEFAULT_BG = "#1f1f1f"
    BTN_DEFAULT_BORDER = "#2e2e2e"
    BTN_DEFAULT_TEXT = "#ededed"

    # Frame and Section Colors
    FRAME_BG = "#0a0a0a"  # Label frame background
    FRAME_BORDER = "#2e2e2e"  # Label frame border
    TAB_BG = "#0a0a0a"  # Tab background
    TAB_BORDER = "#a1a1a1"  # Tab bottom border

    TK_VERSION_CONSOLAS = 8.6

    @classmethod
    def get_logo_path(cls) -> str | None:
        """Get the path to the Aethero logo

        Returns:
            Path to logo file as string, or None if not found
        """
        assets_dir = Path(__file__).parent / "assets"
        logo_path = assets_dir / "aethero_logo.png"
        if logo_path.exists():
            return str(logo_path)
        return None

    @classmethod
    def get_icon_path(cls) -> str | None:
        """Get the path to the application icon

        Returns:
            Path to icon file as string, or None if not found
        """
        assets_dir = Path(__file__).parent / "assets"
        icon_path = assets_dir / "app_icon.png"
        if icon_path.exists():
            return str(icon_path)
        return None

    @classmethod
    def set_app_icon(cls, root: tk.Tk) -> ImageTk.PhotoImage | None:
        """Set the application icon for the taskbar

        Args:
            root: The main Tkinter window

        Returns:
            PhotoImage object to prevent garbage collection, or None if icon not found
        """
        icon_path = cls.get_icon_path()
        if icon_path:
            icon_image = Image.open(icon_path)
            icon_photo = ImageTk.PhotoImage(icon_image)
            root.iconphoto(True, icon_photo)
            # Return the photo to prevent garbage collection
            return icon_photo
        return None

    @classmethod
    def apply_theme(cls, root: tk.Tk) -> ttk.Style:
        """Apply the Aethero dark theme to the application

        Args:
            root: The main Tkinter window

        Returns:
            The configured ttk.Style object
        """
        style = ttk.Style(root)

        # Use clam as base theme for better customization
        style.theme_use("clam")

        # Configure general styles
        style.configure(
            ".",
            background=cls.DARK_BG,
            foreground=cls.PRIMARY_TEXT,
            font=("TkDefaultFont", 10),
        )

        # TFrame styles - use FRAME_BG to blend with label frames
        style.configure("TFrame", background=cls.FRAME_BG)

        style.configure("Dark.TFrame", background=cls.DARK_BG)

        style.configure("Card.TFrame", background=cls.DARK_GRAY)

        # TLabel styles - use FRAME_BG to blend with label frames
        style.configure("TLabel", background=cls.FRAME_BG, foreground=cls.PRIMARY_TEXT)

        style.configure(
            "Header.TLabel",
            background=cls.DARK_GRAY,
            foreground=cls.PRIMARY_TEXT,
            font=("TkDefaultFont", 12, "bold"),
        )

        style.configure(
            "Title.TLabel",
            foreground=cls.CYAN_ACCENT,
            font=("TkDefaultFont", 16, "bold"),
        )

        style.configure(
            "Subtitle.TLabel", foreground=cls.SECONDARY_TEXT, font=("TkDefaultFont", 10)
        )

        style.configure("Status.TLabel", foreground=cls.SECONDARY_TEXT)

        # Default TButton styles (gray)
        style.configure(
            "TButton",
            background=cls.BTN_DEFAULT_BG,
            foreground=cls.BTN_DEFAULT_TEXT,
            bordercolor=cls.BTN_DEFAULT_BORDER,
            darkcolor=cls.BTN_DEFAULT_BG,
            lightcolor=cls.BTN_DEFAULT_BG,
            padding=(10, 5),
            font=("TkDefaultFont", 9),
        )

        style.map(
            "TButton",
            background=[
                ("active", cls.MID_GRAY),
                ("pressed", cls.LIGHT_GRAY),
                ("disabled", cls.DARK_GRAY),
            ],
            foreground=[("disabled", cls.MUTED_TEXT)],
        )

        # Add/Create/Auth button style (blue)
        style.configure(
            "Add.TButton",
            background=cls.BTN_ADD_BG,
            foreground=cls.BTN_ADD_TEXT,
            bordercolor=cls.BTN_ADD_BORDER,
            darkcolor=cls.BTN_ADD_BG,
            lightcolor=cls.BTN_ADD_BG,
        )

        style.map(
            "Add.TButton",
            background=[("active", "#122d5a"), ("pressed", cls.BTN_ADD_BORDER)],
        )

        # Delete/Cancel/Deauth button style (red)
        style.configure(
            "Delete.TButton",
            background=cls.BTN_DELETE_BG,
            foreground=cls.BTN_DELETE_TEXT,
            bordercolor=cls.BTN_DELETE_BORDER,
            darkcolor=cls.BTN_DELETE_BG,
            lightcolor=cls.BTN_DELETE_BG,
        )

        style.map(
            "Delete.TButton",
            background=[("active", "#5a1018"), ("pressed", cls.BTN_DELETE_BORDER)],
        )

        # TEntry styles
        style.configure(
            "TEntry",
            fieldbackground=cls.MID_GRAY,
            foreground=cls.PRIMARY_TEXT,
            insertcolor=cls.PRIMARY_TEXT,
            bordercolor=cls.LIGHT_GRAY,
        )

        # TCombobox styles
        style.configure(
            "TCombobox",
            fieldbackground=cls.MID_GRAY,
            background=cls.MID_GRAY,
            foreground=cls.PRIMARY_TEXT,
            arrowcolor=cls.SECONDARY_TEXT,
            bordercolor=cls.LIGHT_GRAY,
        )

        style.map(
            "TCombobox",
            fieldbackground=[("readonly", cls.MID_GRAY)],
            selectbackground=[("readonly", cls.BTN_ADD_BG)],
            selectforeground=[("readonly", cls.PRIMARY_TEXT)],
        )

        # TSpinbox styles
        style.configure(
            "TSpinbox",
            fieldbackground=cls.MID_GRAY,
            background=cls.MID_GRAY,
            foreground=cls.PRIMARY_TEXT,
            insertcolor=cls.PRIMARY_TEXT,
            arrowcolor=cls.SECONDARY_TEXT,
            bordercolor=cls.LIGHT_GRAY,
        )

        # TNotebook styles (tabs)
        style.configure(
            "TNotebook", background=cls.TAB_BG, tabmargins=[0, 0, 0, 0], borderwidth=0
        )

        # Custom tab layout - only bottom border
        style.layout(
            "TNotebook.Tab",
            [
                (
                    "Notebook.tab",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Notebook.padding",
                                {
                                    "side": "top",
                                    "sticky": "nswe",
                                    "children": [
                                        (
                                            "Notebook.label",
                                            {"side": "top", "sticky": ""},
                                        )
                                    ],
                                },
                            )
                        ],
                    },
                )
            ],
        )

        style.configure(
            "TNotebook.Tab",
            background=cls.TAB_BG,
            foreground=cls.SECONDARY_TEXT,
            padding=[15, 8, 15, 8],
            font=("TkDefaultFont", 10),
            borderwidth=0,
            bordercolor=cls.TAB_BG,
        )

        # Tab styling - bottom border only when selected
        style.map(
            "TNotebook.Tab",
            background=[("selected", cls.TAB_BG), ("active", cls.TAB_BG)],
            foreground=[("selected", cls.PRIMARY_TEXT), ("active", cls.PRIMARY_TEXT)],
            lightcolor=[("selected", cls.TAB_BG), ("!selected", cls.TAB_BG)],
            darkcolor=[("selected", cls.TAB_BG), ("!selected", cls.TAB_BG)],
            bordercolor=[("selected", cls.TAB_BG), ("!selected", cls.TAB_BG)],
        )

        # TLabelframe styles
        style.configure(
            "TLabelframe",
            background=cls.FRAME_BG,
            foreground=cls.PRIMARY_TEXT,
            bordercolor=cls.FRAME_BORDER,
            darkcolor=cls.FRAME_BORDER,
            lightcolor=cls.FRAME_BORDER,
        )

        style.configure(
            "TLabelframe.Label",
            background=cls.FRAME_BG,
            foreground=cls.CYAN_ACCENT,
            font=("TkDefaultFont", 10, "bold"),
        )

        # TProgressbar styles
        style.configure(
            "TProgressbar",
            background=cls.BTN_ADD_TEXT,
            troughcolor=cls.MID_GRAY,
            bordercolor=cls.LIGHT_GRAY,
            lightcolor=cls.CYAN_ACCENT,
            darkcolor=cls.BTN_ADD_TEXT,
        )

        style.configure(
            "Horizontal.TProgressbar",
            background=cls.BTN_ADD_TEXT,
            troughcolor=cls.MID_GRAY,
        )

        # TScrollbar styles
        style.configure(
            "TScrollbar",
            background=cls.MID_GRAY,
            troughcolor=cls.DARK_BG,
            arrowcolor=cls.SECONDARY_TEXT,
            bordercolor=cls.LIGHT_GRAY,
        )

        style.map(
            "TScrollbar",
            background=[("active", cls.LIGHT_GRAY), ("pressed", cls.BTN_ADD_BG)],
        )

        # TCheckbutton styles
        style.configure(
            "TCheckbutton", background=cls.FRAME_BG, foreground=cls.PRIMARY_TEXT
        )

        style.map("TCheckbutton", background=[("active", cls.FRAME_BG)])

        # TRadiobutton styles
        style.configure(
            "TRadiobutton", background=cls.FRAME_BG, foreground=cls.PRIMARY_TEXT
        )

        style.map("TRadiobutton", background=[("active", cls.LIGHT_GRAY)])

        # Configure root window
        root.configure(background=cls.DARK_BG)

        return style

    @classmethod
    def configure_text_widget(cls, widget: tk.Text) -> None:
        """Configure a Text or ScrolledText widget with dark theme colors

        Args:
            widget: Text widget to configure
        """
        widget.configure(
            background=cls.MID_GRAY,
            foreground=cls.PRIMARY_TEXT,
            insertbackground=cls.CYAN_ACCENT,
            selectbackground=cls.PRIMARY_BLUE,
            selectforeground=cls.PRIMARY_TEXT,
            font=("Consolas", 10)
            if tk.TkVersion >= cls.TK_VERSION_CONSOLAS
            else ("Courier", 10),
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=cls.LIGHT_GRAY,
            highlightcolor=cls.CYAN_ACCENT,
        )

    @classmethod
    def configure_listbox(cls, widget: tk.Listbox) -> None:
        """Configure a Listbox widget with dark theme colors

        Args:
            widget: Listbox widget to configure
        """
        widget.configure(
            background=cls.MID_GRAY,
            foreground=cls.PRIMARY_TEXT,
            selectbackground=cls.PRIMARY_BLUE,
            selectforeground=cls.PRIMARY_TEXT,
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=cls.LIGHT_GRAY,
            highlightcolor=cls.CYAN_ACCENT,
        )

    @classmethod
    def configure_treeview(cls, widget: ttk.Treeview, style: ttk.Style) -> None:
        """Configure a Treeview widget with dark theme colors

        Args:
            widget: Treeview widget to configure
            style: ttk.Style object for configuring the treeview
        """
        # Configure treeview style
        style.configure(
            "Dark.Treeview",
            background=cls.MID_GRAY,
            foreground=cls.PRIMARY_TEXT,
            fieldbackground=cls.MID_GRAY,
            borderwidth=1,
            relief="flat",
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=cls.DARK_GRAY,
            foreground=cls.PRIMARY_TEXT,
            borderwidth=1,
            relief="flat",
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", cls.PRIMARY_BLUE)],
            foreground=[("selected", cls.PRIMARY_TEXT)],
        )

        # Apply the style to the widget
        widget.configure(style="Dark.Treeview")
