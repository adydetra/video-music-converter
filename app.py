# Video Music Converter — MP4/MKV -> MP3 (GUI, offline)
# Enhanced Modern UI with improved UX

import os
import sys
import subprocess
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

import imageio_ffmpeg

# ---- Optional Drag & Drop ----
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except Exception:
    BaseTk = tk.Tk
    DND_AVAILABLE = False

APP_TITLE = "Video Music Converter"
BITRATES = ["96", "128", "160", "192", "256", "320"]

# Valid video file extensions
VALID_VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv', 
    '.flv', '.webm', '.mpg', '.mpeg', '.3gp', '.ogv',
    '.ts', '.mts', '.m2ts', '.vob', '.f4v'
}

# Palet warna modern dengan kontras lebih baik
PALETTE = {
    "bg": "#FFFFFF",
    "card": "#FFFFFF",
    "card_hover": "#F1F5F9",
    "text": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",
    "border": "#E2E8F0",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_text": "#FFFFFF",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "danger_text": "#FFFFFF",
    "disabled": "#94A3B8",
    "disabled_bg": "#E2E8F0",
    "list_bg": "#FFFFFF",
    "list_hover": "#F1F5F9",
    "list_select": "#DBEAFE",
    "input_bg": "#FFFFFF",
    "shadow": "#CBD5E1",
}

def resource_path(p: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, p)

class ModernButton(tk.Canvas):
    """Custom button dengan animasi hover"""
    def __init__(self, parent, text, command, style="primary", **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.style = style
        self.is_hovered = False
        
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
    def _on_enter(self, e):
        self.is_hovered = True
        self.render()
        
    def _on_leave(self, e):
        self.is_hovered = False
        self.render()
        
    def render(self):
        # Override di child class
        pass

class ConverterGUI(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(1000, 650)

        # Icon
        try:
            for rel in ("icon.ico", os.path.join("assets", "icon.ico")):
                p = resource_path(rel)
                if os.path.exists(p):
                    self.iconbitmap(p)
                    break
        except Exception:
            pass

        # State
        self.selected_files = []
        self.output_dir = self._get_default_output_dir()
        self.is_converting = False
        self.stop_flag = False
        self.converted_count = 0
        self.failed_count = 0

        # Init
        self._init_fonts()
        self._init_style()
        self._build_ui()
        self._apply_theme()
        self._update_stats()
        self._update_output_label()
        
        # Enable open folder button if default output dir exists
        if self.output_dir and os.path.isdir(self.output_dir):
            self.btn_open.configure(state="normal")

        # Shortcuts
        self.bind("<Control-o>", lambda e: self.on_add_files())
        self.bind("<Delete>", lambda e: self.on_remove_selected())
        self.bind("<Control-l>", lambda e: self.on_clear_list())
        self.bind("<Control-Return>", self.on_convert_clicked)
        self.bind("<Escape>", lambda e: self.on_stop_clicked() if self.is_converting else None)

        # Global DnD
        if DND_AVAILABLE:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop_files)
            except Exception:
                pass

    def _init_fonts(self):
        """Initialize custom fonts"""
        base = "Segoe UI" if sys.platform == "win32" else "SF Pro Display" if sys.platform == "darwin" else "Ubuntu"
        
        self.fonts = {
            "title": tkfont.Font(family=base, size=24, weight="bold"),
            "subtitle": tkfont.Font(family=base, size=11),
            "heading": tkfont.Font(family=base, size=13, weight="bold"),
            "body": tkfont.Font(family=base, size=10),
            "small": tkfont.Font(family=base, size=9),
            "mono": tkfont.Font(family="Consolas" if sys.platform == "win32" else "Monaco", size=9),
        }

    def _get_default_output_dir(self):
        """Get default output directory (Downloads folder)"""
        try:
            if sys.platform == "win32":
                import winreg
                sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
                downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                    location = winreg.QueryValueEx(key, downloads_guid)[0]
                return location
            else:
                # For macOS and Linux
                downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                if os.path.exists(downloads):
                    return downloads
        except Exception:
            pass
        
        # Fallback to user home directory
        return os.path.expanduser("~")

    def _init_style(self):
        """Initialize ttk styles"""
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

    def _apply_theme(self):
        """Apply color theme"""
        P = PALETTE

        # Window
        self.configure(bg=P["bg"])

        # Update all UI elements
        if hasattr(self, "main_container"):
            self.main_container.configure(bg=P["bg"])
        
        if hasattr(self, "header_frame"):
            self.header_frame.configure(bg=P["bg"])
            self.title_label.configure(bg=P["bg"], fg=P["text"])
            self.subtitle_label.configure(bg=P["bg"], fg=P["text_secondary"])

        # Cards
        for card in [self.files_card, self.control_card, self.log_card]:
            card.configure(bg=P["card"])

        # Labels in cards
        self.files_label.configure(bg=P["card"], fg=P["text"])
        self.settings_label.configure(bg=P["card"], fg=P["text"])
        self.log_label.configure(bg=P["card"], fg=P["text"])

        # Stats
        self.stats_frame.configure(bg=P["card"])
        self.total_label.configure(bg=P["card"], fg=P["text_secondary"])
        self.total_value.configure(bg=P["card"], fg=P["text"])
        self.success_label.configure(bg=P["card"], fg=P["text_secondary"])
        self.success_value.configure(bg=P["card"], fg=P["success"])
        self.failed_label.configure(bg=P["card"], fg=P["text_secondary"])
        self.failed_value.configure(bg=P["card"], fg=P["danger"])

        # Listbox
        self.files_list.configure(
            bg=P["list_bg"],
            fg=P["text"],
            selectbackground=P["list_select"],
            selectforeground=P["text"],
            highlightthickness=1,
            highlightbackground=P["border"],
            highlightcolor=P["accent"]
        )

        # Text (log)
        self.log_text.configure(
            bg=P["list_bg"],
            fg=P["text"],
            insertbackground=P["text"],
            highlightthickness=1,
            highlightbackground=P["border"],
            highlightcolor=P["accent"]
        )

        # Combobox
        self.style.configure("Custom.TCombobox",
            fieldbackground=P["input_bg"],
            background=P["card"],
            foreground=P["text"],
            bordercolor=P["border"],
            arrowcolor=P["text"]
        )

        # Progressbar
        self.style.configure("Custom.Horizontal.TProgressbar",
            background=P["accent"],
            troughcolor=P["border"],
            borderwidth=0,
            thickness=8
        )

        # Status
        self.status_label.configure(bg=P["card"], fg=P["text_secondary"])
        self.progress_label.configure(bg=P["card"], fg=P["text_muted"])

        # Buttons
        self._style_button(self.btn_add, "primary")
        self._style_button(self.btn_remove, "secondary")
        self._style_button(self.btn_clear, "secondary")
        self._style_button(self.btn_folder, "secondary")
        self._style_button(self.btn_convert, "accent")
        self._update_stop_button()
        self._style_button(self.btn_open, "secondary")

        # Output dir label
        self.output_label.configure(bg=P["card"], fg=P["text_secondary"])

    def _style_button(self, btn, variant="primary"):
        """Apply button styling"""
        P = PALETTE
        
        if variant == "primary":
            bg, fg = P["accent"], P["accent_text"]
            border = 0
        elif variant == "accent":
            bg, fg = P["accent"], P["accent_text"]
            border = 0
        elif variant == "danger":
            bg, fg = P["danger"], P["danger_text"]
            border = 1
        else:  # secondary
            bg, fg = P["card"], P["text"]
            border = 1
            
        btn.configure(
            bg=bg,
            fg=fg,
            activebackground=P["accent_hover"] if variant in ["primary", "accent"] else P["card_hover"],
            activeforeground=fg,
            relief="solid" if border else "flat",
            bd=border,
            cursor="hand2",
            highlightthickness=0
        )

    def _update_stop_button(self):
        """Update stop button appearance based on state"""
        P = PALETTE
        
        if self.is_converting:
            # Active state: red with white text
            self.btn_stop.configure(
                bg=P["danger"],
                fg=P["danger_text"],
                activebackground=P["danger"],
                activeforeground=P["danger_text"],
                state="normal",
                cursor="hand2",
                relief="solid",
                bd=1
            )
        else:
            # Disabled state: gray with reduced opacity look
            self.btn_stop.configure(
                bg=P["disabled_bg"],
                fg=P["disabled"],
                activebackground=P["disabled_bg"],
                activeforeground=P["disabled"],
                state="disabled",
                cursor="arrow",
                relief="solid",
                bd=1
            )

    def _build_ui(self):
        """Build main UI"""
        # Main container
        self.main_container = tk.Frame(self, bg=PALETTE["bg"])
        self.main_container.pack(fill="both", expand=True)

        # Header
        self._build_header()

        # Content area
        content = tk.Frame(self.main_container, bg=PALETTE["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Left column
        left = tk.Frame(content, bg=PALETTE["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._build_files_section(left)

        # Right column
        right = tk.Frame(content, bg=PALETTE["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self._build_control_section(right)
        self._build_log_section(right)

    def _build_header(self):
        """Build header section"""
        self.header_frame = tk.Frame(self.main_container, height=100)
        self.header_frame.pack(fill="x", padx=20, pady=(20, 16))
        self.header_frame.pack_propagate(False)

        # Title
        self.title_label = tk.Label(self.header_frame, text=APP_TITLE, font=self.fonts["title"])
        self.title_label.pack(anchor="w")

        # Subtitle
        self.subtitle_label = tk.Label(
            self.header_frame,
            text="Ekstrak audio MP3 dari video dengan cepat. Drag & drop, batch convert, 100% offline.",
            font=self.fonts["subtitle"],
            wraplength=700,
            justify="left"
        )
        self.subtitle_label.pack(anchor="w", pady=(8, 0))

    def _build_files_section(self, parent):
        """Build files list section"""
        self.files_card = tk.Frame(parent, relief="solid", bd=1, bg=PALETTE["card"])
        self.files_card.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self.files_card, bg=PALETTE["card"])
        header.pack(fill="x", padx=16, pady=(16, 12))

        self.files_label = tk.Label(header, text="📁 File Video", font=self.fonts["heading"], bg=PALETTE["card"])
        self.files_label.pack(side="left")

        # Stats
        self.stats_frame = tk.Frame(header, bg=PALETTE["card"])
        self.stats_frame.pack(side="right")

        self.total_label = tk.Label(self.stats_frame, text="Total:", font=self.fonts["small"], bg=PALETTE["card"])
        self.total_label.pack(side="left")
        self.total_value = tk.Label(self.stats_frame, text="0", font=self.fonts["body"], bg=PALETTE["card"])
        self.total_value.pack(side="left", padx=(4, 12))

        self.success_label = tk.Label(self.stats_frame, text="✓", font=self.fonts["small"], bg=PALETTE["card"])
        self.success_label.pack(side="left")
        self.success_value = tk.Label(self.stats_frame, text="0", font=self.fonts["body"], bg=PALETTE["card"])
        self.success_value.pack(side="left", padx=(4, 12))

        self.failed_label = tk.Label(self.stats_frame, text="✗", font=self.fonts["small"], bg=PALETTE["card"])
        self.failed_label.pack(side="left")
        self.failed_value = tk.Label(self.stats_frame, text="0", font=self.fonts["body"], bg=PALETTE["card"])
        self.failed_value.pack(side="left", padx=(4, 0))

        # Buttons
        btn_frame = tk.Frame(self.files_card, bg=PALETTE["card"])
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_add = tk.Button(btn_frame, text="➕ Tambah File (Ctrl+O)", font=self.fonts["body"],
                                command=self.on_add_files, cursor="hand2", padx=12, pady=8)
        self.btn_add.pack(side="left", padx=(0, 8))

        self.btn_remove = tk.Button(btn_frame, text="🗑️ Hapus (Del)", font=self.fonts["body"],
                                    command=self.on_remove_selected, cursor="hand2", padx=12, pady=8)
        self.btn_remove.pack(side="left", padx=(0, 8))

        self.btn_clear = tk.Button(btn_frame, text="Clear All (Ctrl+L)", font=self.fonts["body"],
                                   command=self.on_clear_list, cursor="hand2", padx=12, pady=8)
        self.btn_clear.pack(side="left")

        # Listbox
        list_frame = tk.Frame(self.files_card, bg=PALETTE["card"])
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.files_list = tk.Listbox(list_frame, selectmode="extended", font=self.fonts["body"],
                                     yscrollcommand=scrollbar.set, activestyle="none")
        self.files_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.files_list.yview)

        # Placeholder canvas
        self.placeholder_canvas = tk.Canvas(list_frame, highlightthickness=0, bg=PALETTE["list_bg"])
        self.placeholder_canvas.place(x=10, y=10, anchor="nw")
        
        # Draw placeholder
        self._draw_placeholder()

        if DND_AVAILABLE:
            try:
                self.files_list.drop_target_register(DND_FILES)
                self.files_list.dnd_bind("<<Drop>>", self._on_drop_files)
            except Exception:
                pass

    def _draw_placeholder(self):
        """Draw placeholder text in the listbox"""
        self.placeholder_canvas.delete("all")
        
        # Icon and text aligned to top left
        icon_text = "📁"
        self.placeholder_canvas.create_text(5, 5, text=icon_text, font=("Segoe UI", 20),
                                           fill=PALETTE["text_muted"], anchor="nw")
        
        # Main text
        main_text = "Drag & Drop file video di sini" if DND_AVAILABLE else "Klik 'Tambah File' untuk memulai"
        self.placeholder_canvas.create_text(45, 8, text=main_text, font=self.fonts["body"],
                                           fill=PALETTE["text_secondary"], anchor="nw")
        
        # Sub text
        sub_text = "atau klik tombol 'Tambah File' di atas" if DND_AVAILABLE else "Mendukung MP4, MKV, AVI, MOV, dll"
        self.placeholder_canvas.create_text(45, 28, text=sub_text, font=self.fonts["small"],
                                           fill=PALETTE["text_muted"], anchor="nw")
        
        # Update canvas size to fit content
        self.placeholder_canvas.config(width=400, height=50)

    def _update_placeholder(self):
        """Show or hide placeholder based on file list"""
        if len(self.selected_files) > 0:
            self.placeholder_canvas.place_forget()
        else:
            self.placeholder_canvas.place(x=10, y=10, anchor="nw")
            self._draw_placeholder()

    def _build_control_section(self, parent):
        """Build control section"""
        self.control_card = tk.Frame(parent, relief="solid", bd=1, bg=PALETTE["card"])
        self.control_card.pack(fill="x", pady=(0, 16))

        # Header
        header = tk.Frame(self.control_card, bg=PALETTE["card"])
        header.pack(fill="x", padx=16, pady=(16, 12))

        self.settings_label = tk.Label(header, text="⚙️ Pengaturan", font=self.fonts["heading"], bg=PALETTE["card"])
        self.settings_label.pack(side="left")

        # Settings grid
        grid = tk.Frame(self.control_card, bg=PALETTE["card"])
        grid.pack(fill="x", padx=16, pady=(0, 12))

        # Bitrate
        tk.Label(grid, text="Bitrate Audio:", font=self.fonts["body"], bg=PALETTE["card"]).grid(row=0, column=0, sticky="w", pady=6)
        self.bitrate_var = tk.StringVar(value=BITRATES[5])  # 320 kbps
        bitrate_combo = ttk.Combobox(grid, textvariable=self.bitrate_var, values=BITRATES,
                                     width=12, state="readonly", style="Custom.TCombobox", font=self.fonts["body"])
        bitrate_combo.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=6)
        tk.Label(grid, text="kbps", font=self.fonts["small"], bg=PALETTE["card"]).grid(row=0, column=2, sticky="w", padx=(4, 0), pady=6)

        # Output folder
        tk.Label(grid, text="Folder Output:", font=self.fonts["body"], bg=PALETTE["card"]).grid(row=1, column=0, sticky="w", pady=6)
        self.output_dir_var = tk.StringVar(value=self.output_dir if self.output_dir else "Sama dengan file asli")
        self.output_label = tk.Label(grid, textvariable=self.output_dir_var, font=self.fonts["small"],
                                     anchor="w", width=30, bg=PALETTE["card"])
        self.output_label.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=6)

        self.btn_folder = tk.Button(grid, text="📁 Pilih Folder", font=self.fonts["body"],
                                    command=self.on_choose_output_dir, cursor="hand2", padx=10, pady=6)
        self.btn_folder.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=6)

        # Progress
        progress_frame = tk.Frame(self.control_card, bg=PALETTE["card"])
        progress_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.progress = ttk.Progressbar(progress_frame, mode="determinate", style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 4))

        status_row = tk.Frame(progress_frame, bg=PALETTE["card"])
        status_row.pack(fill="x")

        self.status_label = tk.Label(status_row, text="Siap untuk konversi", font=self.fonts["body"], anchor="w", bg=PALETTE["card"])
        self.status_label.pack(side="left")

        self.progress_label = tk.Label(status_row, text="0/0", font=self.fonts["small"], anchor="e", bg=PALETTE["card"])
        self.progress_label.pack(side="right")

        # Action buttons
        action_frame = tk.Frame(self.control_card, bg=PALETTE["card"])
        action_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.btn_convert = tk.Button(action_frame, text="🚀 Convert ke MP3 (Ctrl+Enter)",
                                     font=self.fonts["heading"], command=self.on_convert_clicked,
                                     cursor="hand2", padx=16, pady=10)
        self.btn_convert.pack(side="left", padx=(0, 8))

        self.btn_stop = tk.Button(action_frame, text="⏹️ Stop (Esc)", font=self.fonts["body"],
                                  command=self.on_stop_clicked, cursor="hand2", padx=12, pady=10, state="disabled",
                                  disabledforeground=PALETTE["disabled"])
        self.btn_stop.pack(side="left", padx=(0, 8))

        self.btn_open = tk.Button(action_frame, text="📂 Buka Folder", font=self.fonts["body"],
                                  command=self.on_open_output, cursor="hand2", padx=12, pady=10, state="disabled",
                                  disabledforeground=PALETTE["disabled"])
        self.btn_open.pack(side="right")

    def _build_log_section(self, parent):
        """Build log section"""
        self.log_card = tk.Frame(parent, relief="solid", bd=1, bg=PALETTE["card"])
        self.log_card.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self.log_card, bg=PALETTE["card"])
        header.pack(fill="x", padx=16, pady=(16, 12))

        self.log_label = tk.Label(header, text="📋 Log Aktivitas", font=self.fonts["heading"], bg=PALETTE["card"])
        self.log_label.pack(side="left")

        # Log text
        log_frame = tk.Frame(self.log_card, bg=PALETTE["card"])
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(log_frame, wrap="word", font=self.fonts["mono"], height=12,
                               yscrollcommand=scrollbar.set, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        self._log("✨ Aplikasi siap digunakan. Silakan tambahkan file video untuk mulai konversi.")

    def toggle_theme(self):
        """Toggle between light and dark mode"""
        # Removed - no longer needed
        pass

    def _log(self, msg: str):
        """Add message to log"""
        self.log_text.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _update_stats(self):
        """Update statistics display"""
        self.total_value.configure(text=str(len(self.selected_files)))
        self.success_value.configure(text=str(self.converted_count))
        self.failed_value.configure(text=str(self.failed_count))

    def _update_output_label(self):
        """Update output folder label"""
        if self.output_dir:
            short_path = self.output_dir if len(self.output_dir) < 40 else "..." + self.output_dir[-37:]
            self.output_dir_var.set(short_path)
        else:
            self.output_dir_var.set("Sama dengan file asli")

    def _add_files(self, paths):
        """Add files to list"""
        if not paths:
            return
        
        added = 0
        skipped = 0
        invalid_files = []
        
        for p in paths:
            if not p or not os.path.isfile(p):
                continue
                
            # Check if file has valid video extension
            ext = os.path.splitext(p)[1].lower()
            if ext not in VALID_VIDEO_EXTENSIONS:
                skipped += 1
                invalid_files.append(os.path.basename(p))
                continue
            
            # Check if file already in list
            if p in self.selected_files:
                continue
                
            self.selected_files.append(p)
            filename = os.path.basename(p)
            self.files_list.insert("end", f"  {filename}")
            added += 1
        
        if added:
            self._log(f"➕ Ditambahkan {added} file baru")
        
        if skipped:
            self._log(f"⚠️ Diabaikan {skipped} file (bukan format video yang valid)")
            if len(invalid_files) <= 3:
                for f in invalid_files:
                    self._log(f"   • {f}")
            
        if not added and not skipped:
            self._log("ℹ️ Tidak ada file baru (mungkin sudah ada dalam daftar)")
        
        self._update_stats()
        self._update_placeholder()

    def _on_drop_files(self, event):
        """Handle drag and drop"""
        files = self._parse_dnd_files(event.data)
        self._add_files(files)

    @staticmethod
    def _parse_dnd_files(data: str) -> list:
        """Parse DnD file data"""
        out, token, in_brace = [], "", False
        for ch in data:
            if ch == "{":
                in_brace, token = True, ""
            elif ch == "}":
                in_brace = False
                out.append(token)
                token = ""
            elif ch == " " and not in_brace:
                if token:
                    out.append(token)
                    token = ""
            else:
                token += ch
        if token:
            out.append(token)
        return out

    def on_add_files(self):
        """Open file dialog to add files"""
        paths = filedialog.askopenfilenames(
            title="Pilih File Video",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov *.m4v *.wmv *.flv *.webm *.mpg *.mpeg"),
                ("All files", "*.*")
            ],
        )
        self._add_files(paths)

    def on_remove_selected(self):
        """Remove selected files from list"""
        sel = list(self.files_list.curselection())
        if not sel:
            self._log("⚠️ Tidak ada file yang dipilih")
            return
        
        sel.sort(reverse=True)
        removed = 0
        for idx in sel:
            if idx < len(self.selected_files):
                self.selected_files.pop(idx)
                removed += 1
            self.files_list.delete(idx)
        
        self._log(f"🗑️ Dihapus {removed} file dari daftar")
        self._update_stats()
        self._update_placeholder()

    def on_clear_list(self):
        """Clear all files"""
        if not self.selected_files:
            return
        
        count = len(self.selected_files)
        self.selected_files.clear()
        self.files_list.delete(0, "end")
        self.converted_count = 0
        self.failed_count = 0
        
        self._log(f"🧹 Daftar dikosongkan ({count} file dihapus)")
        self._update_stats()
        self._update_placeholder()

    def on_choose_output_dir(self):
        """Choose output directory"""
        d = filedialog.askdirectory(title="Pilih Folder Output", initialdir=self.output_dir)
        if d:
            self.output_dir = d
            self._update_output_label()
            self.btn_open.configure(state="normal")
            self._log(f"📁 Folder output: {d}")

    def on_open_output(self):
        """Open output folder"""
        if self.output_dir and os.path.isdir(self.output_dir):
            try:
                if sys.platform == "win32":
                    os.startfile(self.output_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.output_dir])
                else:
                    subprocess.run(["xdg-open", self.output_dir])
            except Exception as e:
                self._log(f"❌ Tidak dapat membuka folder: {e}")
        else:
            messagebox.showinfo("Info", "Belum memilih folder output khusus")

    def on_stop_clicked(self):
        """Stop conversion"""
        if self.is_converting:
            self.stop_flag = True
            self._log("⏸️ Menghentikan konversi...")
            self.status_label.configure(text="Menghentikan...")

    def on_convert_clicked(self, *args):
        """Start conversion"""
        if self.is_converting:
            return
        
        if not self.selected_files:
            messagebox.showwarning("Peringatan", "Tambahkan minimal 1 file video terlebih dahulu")
            return
        
        bitrate = self.bitrate_var.get().strip()
        if bitrate not in BITRATES:
            messagebox.showwarning("Peringatan", "Pilih bitrate yang valid")
            return

        self.is_converting = True
        self.stop_flag = False
        self.converted_count = 0
        self.failed_count = 0
        
        # Disable button but keep white text
        self.btn_convert.configure(state="disabled", disabledforeground=PALETTE["accent_text"])
        self._update_stop_button()
        self.progress.configure(value=0, maximum=len(self.selected_files))
        
        self._log(f"🚀 Memulai konversi {len(self.selected_files)} file dengan bitrate {bitrate} kbps")
        
        threading.Thread(target=self._convert_worker, args=(bitrate,), daemon=True).start()

    def _convert_worker(self, bitrate: str):
        """Worker thread for conversion"""
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        
        if not os.path.exists(ffmpeg_path):
            self._log("❌ FFmpeg tidak ditemukan!")
            self._done(False)
            return

        total = len(self.selected_files)

        for idx, in_path in enumerate(self.selected_files, start=1):
            if self.stop_flag:
                self._log("⏹️ Konversi dihentikan oleh pengguna")
                break

            try:
                # Determine output directory
                out_dir = self.output_dir or os.path.dirname(in_path)
                os.makedirs(out_dir, exist_ok=True)

                # Generate output filename
                base = os.path.splitext(os.path.basename(in_path))[0]
                out_path = os.path.join(out_dir, f"{base}.mp3")

                # Handle duplicate filenames
                counter = 1
                while os.path.exists(out_path):
                    out_path = os.path.join(out_dir, f"{base}_{counter}.mp3")
                    counter += 1

                # Update UI
                filename = os.path.basename(in_path)
                self.status_label.configure(text=f"Mengkonversi: {filename}")
                self.progress_label.configure(text=f"{idx}/{total}")
                self._log(f"🔄 [{idx}/{total}] {filename}")

                # FFmpeg command
                cmd = [
                    ffmpeg_path,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-i", in_path,
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-b:a", f"{bitrate}k",
                    "-map_metadata", "0",
                    out_path
                ]

                # Run conversion
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )

                if proc.returncode != 0:
                    self.failed_count += 1
                    self._log(f"❌ GAGAL: {filename}")
                    if proc.stdout.strip():
                        self._log(f"   Error: {proc.stdout.strip()[:200]}")
                else:
                    self.converted_count += 1
                    out_filename = os.path.basename(out_path)
                    self._log(f"✅ SUKSES: {filename} → {out_filename}")

            except Exception as e:
                self.failed_count += 1
                self._log(f"❌ Exception: {os.path.basename(in_path)} - {str(e)[:100]}")

            # Update progress
            self.progress.configure(value=idx)
            self._update_stats()
            self.update_idletasks()

        self._done(not self.stop_flag and self.failed_count == 0)

    def _done(self, success: bool):
        """Finish conversion"""
        self.is_converting = False
        self.btn_convert.configure(state="normal")
        self._update_stop_button()

        total = self.converted_count + self.failed_count
        
        if self.stop_flag:
            self.status_label.configure(text=f"Dihentikan: {self.converted_count}/{total} berhasil")
            self._log(f"⏹️ Proses dihentikan. Berhasil: {self.converted_count}, Gagal: {self.failed_count}")
        elif success:
            self.status_label.configure(text=f"Selesai! {self.converted_count} file berhasil dikonversi")
            self._log(f"🎉 Konversi selesai! Semua {self.converted_count} file berhasil dikonversi")
            if self.output_dir:
                self.btn_open.configure(state="normal")
        else:
            self.status_label.configure(text=f"Selesai: {self.converted_count} sukses, {self.failed_count} gagal")
            self._log(f"⚠️ Konversi selesai dengan error. Berhasil: {self.converted_count}, Gagal: {self.failed_count}")

        # Show notification
        if total > 0:
            if success:
                messagebox.showinfo("Selesai", f"Konversi selesai!\n\n✅ {self.converted_count} file berhasil dikonversi")
            else:
                messagebox.showwarning("Selesai", 
                    f"Konversi selesai dengan hasil:\n\n✅ Berhasil: {self.converted_count}\n❌ Gagal: {self.failed_count}")


def main():
    app = ConverterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()