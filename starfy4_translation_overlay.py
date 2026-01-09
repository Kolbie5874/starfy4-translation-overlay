import sys
import os
import json
import ctypes
import time
from ctypes import wintypes

import pyautogui
import imagehash
import vlc
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QWidget, QCheckBox, QPlainTextEdit, QLabel,
    QVBoxLayout, QHBoxLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QFontDatabase, QTextDocument, QIntValidator


def app_dir() -> str:
    # If running as a PyInstaller exe
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Normal python run
    return os.path.abspath(os.path.dirname(__file__))


def beside_exe(filename: str) -> str:
    return os.path.join(app_dir(), filename)

# Database and monitoring settings
HASH_DB_FILE = "hash_db.json"
UNSEEN_DIR = "untranslated"
CHECK_INTERVAL = 10  # milliseconds
UI_RECT = (1300, 80, 320, 600)
OVERLAY_CONFIG_FILE = "overlay_regions.json"

# CG configuration
CG_CFG = {
    "trigger_crop": (752, 241, 413, 111),
    "stop_crop": (1191, 433, 62, 69),
    "overlay_rect": (641, 60, 639, 960),
    "video_path": "cg.mp4",
}

# Region definitions are loaded from overlay_regions.json.
DEFAULT_REGION_CFG = []

# Hash color overrides are loaded from overlay_regions.json.
DEFAULT_HASH_COLOR_OVERRIDES = {}

def load_overlay_config():
    config_path = beside_exe(OVERLAY_CONFIG_FILE)
    if not os.path.exists(config_path):
        return DEFAULT_REGION_CFG, DEFAULT_HASH_COLOR_OVERRIDES

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Failed to load {config_path}: {exc}")
        return DEFAULT_REGION_CFG, DEFAULT_HASH_COLOR_OVERRIDES

    regions = data.get("regions", DEFAULT_REGION_CFG)
    overrides = data.get("hash_color_overrides", DEFAULT_HASH_COLOR_OVERRIDES)
    return regions, overrides


REGION_CFG, HASH_COLOR_OVERRIDES = load_overlay_config()

NDS_FAMILY = "Courier New"  # Default font, replaced if NDS.ttf is found


# UTILITY

def hide_from_capture(hwnd):
    """Hide windows from screenshots."""
    if sys.platform.startswith("win"):
        WDA_EXCLUDEFROMCAPTURE = 0x11
        user32 = ctypes.windll.user32
        user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
        user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)


def load_database():
    """Load the hash database from file."""
    if os.path.exists(HASH_DB_FILE):
        with open(HASH_DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_database(db):
    """Save the hash database to file."""
    with open(HASH_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def normalize_image(img):
    return img


def get_perceptual_hash(img):
    """Get perceptual hash of an image."""
    return imagehash.phash(normalize_image(img))


def create_qcolor(color, default=(255, 255, 255)):
    """Create QColor from various input formats."""
    if color is None:
        return QColor(*default)
    return QColor(color) if isinstance(color, str) else QColor(*color)


# OVERLAY

class OverlayWindow(QWidget):
    """Overlay window for displaying translations."""
    
    def __init__(self, rect, text="", font_pt=13, holes=None, bg_color=(255, 255, 255), font_family=None):
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setGeometry(*rect)

        self.text = text
        self.font_pt = font_pt
        self.font_family = font_family or NDS_FAMILY
        self.holes = holes or []
        self.bg_color = bg_color

        self.show()
        hide_from_capture(int(self.winId()))

    def set_text(self, text):
        """Update the displayed text."""
        self.text = text
        self.update()

    def paintEvent(self, event):
        """Custom paint event to render text with holes."""
        painter = QPainter(self)
        
        # Fill background
        painter.fillRect(self.rect(), create_qcolor(self.bg_color))
        
        # Create holes (transparent areas)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        overlay_x, overlay_y = self.x(), self.y()
        for hole_x, hole_y, hole_w, hole_h in self.holes:
            painter.fillRect(QRect(hole_x - overlay_x, hole_y - overlay_y, hole_w, hole_h), 
                           QColor(0, 0, 0, 0))
        
        # Draw text
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if self.text:
            self._draw_text(painter)

    def _draw_text(self, painter):
        """Draw formatted text on the overlay."""
        doc = QTextDocument()
        font = QFont(self.font_family)
        font.setPixelSize(self.font_pt)
        font.setWeight(QFont.Normal)
        doc.setDefaultFont(font)
        doc.setDefaultStyleSheet("body { margin:0; padding:0; line-height:1; }")
        doc.setTextWidth(self.rect().width() - 16)
        doc.setPlainText(self.text)
        
        painter.save()
        doc.drawContents(painter)
        painter.restore()


class PatchWindow(QWidget):
    """Small overlay patch for covering UI elements."""
    
    def __init__(self, spec):
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        if isinstance(spec, (list, tuple)):
            rect = spec
            self.text = ""
            self.font_pt = 12
            self.color = (255, 255, 255)
        else:
            rect = spec["rect"]
            self.text = spec.get("text", "")
            self.font_pt = spec.get("font_pt", 12)
            self.color = spec.get("color", (255, 255, 255))

        self.setGeometry(*rect)
        self.show()
        hide_from_capture(int(self.winId()))

    def paintEvent(self, event):
        """Paint the patch with optional text."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), create_qcolor(self.color))
        
        if self.text:
            painter.setPen(QColor(0, 0, 0))
            font = QFont(NDS_FAMILY)
            font.setPixelSize(self.font_pt)
            font.setWeight(QFont.Normal)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self.text)


class VideoOverlay(QWidget):
    """Video overlay for playing cutscenes."""
    
    def __init__(self, rect, video_path):
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setGeometry(*rect)
        self.show()
        hide_from_capture(int(self.winId()))
        
        # Initialize VLC player
        vlc_instance = vlc.Instance("--no-video-title-show", "--quiet")
        self.player = vlc_instance.media_player_new()
        media = vlc_instance.media_new(os.path.abspath(video_path))
        self.player.set_media(media)
        
        # Set video output window
        if sys.platform.startswith("win"):
            self.player.set_hwnd(int(self.winId()))
        else:
            self.player.set_xwindow(int(self.winId()))
        
        self.player.audio_set_mute(True)
        self.player.play()

    def closeEvent(self, event):
        """Clean up video player on close."""
        self.player.stop()
        super().closeEvent(event)


# CONTROLLERS

class RegionController:
    """Controller for managing translation overlays for specific screen regions."""
    
    def __init__(self, config, app):
        self.config = config
        self.app = app
        self.overlay = None
        self.patches = []
        self.last_hash = None
        self._sanitize_config()

    def _sanitize_config(self):
        """Sanitize region configuration format."""
        for key in ("crop", "overlay"):
            value = self.config[key]
            if (isinstance(value, (list, tuple)) and len(value) == 1 and 
                isinstance(value[0], (list, tuple))):
                self.config[key] = tuple(value[0])

    def destroy(self):
        """Clean up all overlay windows."""
        if self.overlay:
            self.overlay.close()
        for patch in self.patches:
            patch.close()
        self.overlay = None
        self.patches = []
        self.last_hash = None

    def update(self, screenshot, database):
        """Update overlay based on current screenshot."""
        if not self.app.translation_enabled:
            self.destroy()
            return

        # Crop screenshot to region
        x, y, w, h = self.config["crop"]
        cropped_image = screenshot.crop((x, y, x + w, y + h))
        
        # Exact hash look-up
        hash_key = str(get_perceptual_hash(cropped_image))
        translation_text = database.get(hash_key, "").strip()

        if translation_text:
            # Decide the overlay background color
            desired_color = HASH_COLOR_OVERRIDES.get(
                hash_key, self.config.get("overlay_color", (255, 255, 255))
            )

            # Is this a brand-new hash?
            new_hash = (hash_key != self.last_hash)

            # Re-create overlay if it’s missing OR hash changed OR color changed
            if (
                not self.overlay
                or desired_color != getattr(self.overlay, "bg_color", None)
            ):
                self.destroy()
                self._create_overlay(desired_color)

            # Make sure the text is up to date
            if new_hash or self.overlay.text != translation_text:
                self.overlay.set_text(translation_text)

            # Only log the first time you see a new hash
            if new_hash:
                self.app.log(f"Detected hash {hash_key}")

            # Remember what it's showing
            self.last_hash = hash_key

        else:
            # No translation, nuke the overlay
            self.destroy()



    def _create_overlay(self, bg_color):
        """Create the overlay window and patches."""
        holes = []
        block_patches = []
        
        # Separate holes from block patches
        for spec in self.config.get("patches", []):
            if isinstance(spec, dict) and ("cut" in spec or "hole" in spec):
                holes.append(spec.get("cut") or spec.get("hole"))
            else:
                block_patches.append(spec)
        
        # Create main overlay
        self.overlay = OverlayWindow(
            self.config["overlay"],
            holes=holes,
            bg_color=bg_color,
            font_pt=self.config.get("font_pt", 13),
        )
       
        # Create patch windows
        self.patches = [PatchWindow(spec) for spec in block_patches]


class CGController:
    """Controller for managing cutscene video overlays."""
    
    def __init__(self, config, app):
        self.config = config
        self.app = app
        self.video_window = None
        self.is_running = False

    def update(self, screenshot):
        """Update CG state based on screenshot."""
        if not self.app.cg_enabled:
            if self.is_running and self.video_window:
                self.video_window.close()
            self.video_window = None
            self.is_running = False
            return

        # Choose crop region based on current state
        if self.is_running:
            crop_rect = self.config["stop_crop"]
        else:
            crop_rect = self.config["trigger_crop"]
        
        # Check for trigger/stop markers
        x, y, w, h = crop_rect
        cropped_image = screenshot.crop((x, y, x + w, y + h))
        hash_key = str(get_perceptual_hash(cropped_image))
        tag = self.app.db.get(hash_key, "").strip()

        if not self.is_running and tag == "__START_CG__":
            self._start_cg()
        elif self.is_running and tag == "__STOP_CG__":
            self._stop_cg()

    def _start_cg(self):
        """Start playing cutscene video."""
        self.video_window = VideoOverlay(
            self.config["overlay_rect"], 
            self.config["video_path"]
        )
        self.is_running = True
        self.app.log("CG started")

    def _stop_cg(self):
        """Stop playing cutscene video."""
        if self.video_window:
            self.video_window.close()
        self.is_running = False
        self.app.log("CG stopped")


# MAIN CONTROL PANEL

class ControlPanel(QWidget):
    """Main control panel for the translation overlay system."""
    
    def __init__(self):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.setGeometry(*UI_RECT)
        self.setWindowTitle("Starfy TL Console")

        # Application state
        self.translation_enabled = True
        self.cg_enabled = True
        self.db = load_database()

        # Initialize UI
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._initialize_controllers()
        
        self.show()
        hide_from_capture(int(self.winId()))
        self.log(f"UI ready - polling every {self.update_timer.interval()} ms")

    def _create_widgets(self):
        """Create all UI widgets."""
        # Checkboxes
        self.chk_translation = QCheckBox("Enable translation", checked=True)
        self.chk_cg = QCheckBox("Play opening CG", checked=True)
        
        # Polling interval input
        self.edit_interval = QLineEdit(str(CHECK_INTERVAL))
        self.edit_interval.setValidator(QIntValidator(1, 60000, self))
        self.edit_interval.setMaximumWidth(120)

        # Log area
        self.log_display = QPlainTextEdit(readOnly=True)
        self.log_display.setMaximumBlockCount(200)

    def _setup_layout(self):
        """Set up the widget layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Checkboxes
        layout.addWidget(self.chk_translation)
        layout.addWidget(self.chk_cg)
        
        # Polling interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Screenshot interval (ms):"))
        interval_layout.addWidget(self.edit_interval)
        interval_layout.addStretch(1)
        layout.addLayout(interval_layout)
        
        # Log display
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_display)

    def _connect_signals(self):
        """Connect widget signals to handlers."""
        self.chk_translation.stateChanged.connect(
            lambda state: setattr(self, "translation_enabled", bool(state))
        )
        self.chk_cg.stateChanged.connect(
            lambda state: setattr(self, "cg_enabled", bool(state))
        )
        self.edit_interval.editingFinished.connect(self._apply_interval)

    def _initialize_controllers(self):
        """Initialize region and CG controllers."""
        self.region_controllers = [RegionController(config, self) for config in REGION_CFG]
        self.cg_controller = CGController(CG_CFG, self)
        
        # Start main update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_tick)
        self.update_timer.start(CHECK_INTERVAL)

    # Event handlers
    def log(self, message):
        """Add message to log display."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_display.appendPlainText(f"[{timestamp}] {message}")
        print(message)

    def _apply_interval(self):
        """Apply the polling interval from the UI."""
        if not hasattr(self, "update_timer"):
            return
        text = self.edit_interval.text().strip()
        if not text:
            return
        try:
            interval = int(text)
        except ValueError:
            return
        if interval < 1:
            interval = 1
            self.edit_interval.setText(str(interval))
        self.update_timer.setInterval(interval)
        self.log(f"Polling interval set to {interval} ms")

    def _update_tick(self):
        """Main update loop - called by timer."""
        screenshot = pyautogui.screenshot()
        self.cg_controller.update(screenshot)
        for controller in self.region_controllers:
            controller.update(screenshot, self.db)

# MAIN ENTRY POINT


def main():
    """Main entry point for the application."""
    global NDS_FAMILY

    font_path = beside_exe("NDS.ttf")
    app = QApplication(sys.argv)

    if not os.path.exists(font_path):
        print(f"[WARN] NDS.ttf not found at: {font_path}")
    else:
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            print(f"[WARN] Failed to load font file: {font_path}")
        else:
            fams = QFontDatabase.applicationFontFamilies(font_id)
            if fams:
                NDS_FAMILY = fams[0]

    print(f"[INFO] DS font family → {NDS_FAMILY}")

    # Create and run control panel
    control_panel = ControlPanel()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
