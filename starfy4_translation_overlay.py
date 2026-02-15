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
    QVBoxLayout, QHBoxLayout, QSpinBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QFontDatabase, QTextDocument

# CONFIG

# Database and monitoring settings
HASH_DB_FILE = os.path.join("database/", "hash_db.json")
REGIONS_FILE = os.path.join("database/", "regions.json")
FONT_FILE = os.path.join("assets/", "NDS.ttf")

CHECK_INTERVAL_DEFAULT = 16  # milliseconds
UI_RECT = (1300, 80, 300, 400)

# CG configuration
CG_CFG = {
    "trigger_crop": (752, 241, 413, 111),
    "stop_crop": (1191, 433, 62, 69),
    "overlay_rect": (641, 60, 639, 960),
    "video_path": "cg.mp4",
}

# Region definitions & hash color overrides (loaded from external JSON)
# We expect regions.json to exist in the same directory
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), REGIONS_FILE)
if os.path.exists(_cfg_path):
    with open(_cfg_path, "r", encoding="utf-8") as _f:
        _external_cfg = json.load(_f)
    REGION_CFG = _external_cfg.get("regions", [])
    HASH_COLOR_OVERRIDES = _external_cfg.get("hash_color_overrides", {})
else:
    print("[WARN] regions.json not found. Overlays may not work.")
    REGION_CFG = []
    HASH_COLOR_OVERRIDES = {}

# Global state
NDS_FAMILY = "Courier New"  # Default font, replaced if NDS.ttf is found


# UTILITY

def hide_from_capture(hwnd):
    """Hide windows from screenshots (Windows only)."""
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


def normalize_image(img):
    return img


def get_perceptual_hash(img):
    """Get perceptual hash of an image."""
    return imagehash.phash(normalize_image(img))


def get_sha256_hash(img):
    """Get SHA256 hash of an image."""
    import hashlib
    img_bytes = img.tobytes()
    metadata = f"{img.mode}{img.size}".encode()
    return hashlib.sha256(metadata + img_bytes).hexdigest()


def create_qcolor(color, default=(255, 255, 255)):
    """Create QColor from various input formats."""
    if color is None:
        return QColor(*default)
    return QColor(color) if isinstance(color, str) else QColor(*color)


# OVERLAY CLASSES

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

        if isinstance(spec, (tuple, list)):
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

    def __init__(self, rect, player):
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

        # Use pre-initialized player
        self.player = player

        # Set video output window
        if sys.platform.startswith("win"):
            self.player.set_hwnd(int(self.winId()))
        else:
            self.player.set_xwindow(int(self.winId()))

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

        # Compute hashes
        phash_key = f"phash:{str(get_perceptual_hash(cropped_image))}"
        sha256_key = f"sha256:{get_sha256_hash(cropped_image)}"

        # Check database
        phash_translation = database.get(phash_key, "").strip()
        sha256_translation = database.get(sha256_key, "").strip()

        # Prefer SHA256
        if sha256_translation:
            translation_text = sha256_translation
            active_hash_key = sha256_key
        elif phash_translation:
            translation_text = phash_translation
            active_hash_key = phash_key
        else:
            translation_text = ""
            active_hash_key = None

        # Use combined hash for change detection
        current_hash = f"{phash_key}|{sha256_key}"

        if translation_text:
            # Decide the overlay background color
            bare_hash = active_hash_key.replace('phash:', '').replace('sha256:', '')
            desired_color = HASH_COLOR_OVERRIDES.get(
                bare_hash, self.config.get("overlay_color", (255, 255, 255))
            )

            # Is this a brand-new hash?
            new_hash = (current_hash != self.last_hash)

            # Re-create overlay if it's missing OR color changed
            if (
                not self.overlay
                or desired_color != getattr(self.overlay, "bg_color", None)
            ):
                self.destroy()
                self._create_overlay(desired_color)

            # Update text
            if new_hash or self.overlay.text != translation_text:
                self.overlay.set_text(translation_text)

            # Log if it's a new encounter in this session
            if new_hash:
                self.app.log(f"Matched: {active_hash_key[:15]}...")

            self.last_hash = current_hash
        else:
            self.destroy()

    def _create_overlay(self, bg_color):
        """Create the overlay window and patches."""
        holes = []
        block_patches = []
        
        for spec in self.config.get("patches", []):
            if isinstance(spec, dict) and ("cut" in spec or "hole" in spec):
                holes.append(spec.get("cut") or spec.get("hole"))
            else:
                block_patches.append(spec)
        
        self.overlay = OverlayWindow(
            self.config["overlay"],
            holes=holes,
            bg_color=bg_color,
            font_pt=self.config.get("font_pt", 13),
        )
       
        self.patches = [PatchWindow(spec) for spec in block_patches]


class CGController:
    """Controller for managing cutscene video overlays."""

    def __init__(self, config, app):
        self.config = config
        self.app = app
        self.video_window = None
        self.is_running = False

        # Preload VLC
        try:
            vlc_instance = vlc.Instance("--no-video-title-show", "--quiet")
            self.player = vlc_instance.media_player_new()
            media_path = os.path.abspath(config["video_path"])
            if os.path.exists(media_path):
                media = vlc_instance.media_new(media_path)
                self.player.set_media(media)
                self.player.audio_set_mute(True)
                # Prime the player
                self.player.play()
                time.sleep(0.1)
                self.player.pause()
                self.player.stop()
            else:
                self.app.log(f"[WARN] CG file not found: {media_path}")
        except Exception as e:
            self.app.log(f"[ERR] VLC Init failed: {e}")

    def update(self, screenshot):
        """Update CG state based on screenshot."""
        if not self.app.cg_enabled:
            if self.is_running and self.video_window:
                self.video_window.close()
            self.video_window = None
            self.is_running = False
            return

        if self.is_running:
            crop_rect = self.config["stop_crop"]
        else:
            crop_rect = self.config["trigger_crop"]
        
        x, y, w, h = crop_rect
        cropped_image = screenshot.crop((x, y, x + w, y + h))
        phash = str(get_perceptual_hash(cropped_image))
        hash_key = f"phash:{phash}"
        tag = self.app.db.get(hash_key, "").strip()

        if not self.is_running and tag == "__START_CG__":
            self._start_cg()
        elif self.is_running and tag == "__STOP_CG__":
            self._stop_cg()

    def _start_cg(self):
        self.player.set_position(0.0)
        self.video_window = VideoOverlay(
            self.config["overlay_rect"],
            self.player
        )
        self.is_running = True
        self.app.log("CG started")

    def _stop_cg(self):
        if self.video_window:
            self.video_window.close()
        self.is_running = False
        self.app.log("CG stopped")


# MAIN VIEWER PANEL

class ViewerPanel(QWidget):
    """Simplified Viewer UI for the translation overlay."""
    
    def __init__(self):
        super().__init__(None, Qt.WindowStaysOnTopHint)
        self.setGeometry(*UI_RECT)
        self.setWindowTitle("Starfy TL Viewer")

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
        self.log(f"Viewer Ready. Database entries: {len(self.db)}")

    def _create_widgets(self):
        # Checkboxes
        self.chk_translation = QCheckBox("Enable translation", checked=True)
        self.chk_cg = QCheckBox("Play opening CG", checked=True)
        
        # Interval Control
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(10, 2000)
        self.spin_interval.setSingleStep(10)
        self.spin_interval.setValue(CHECK_INTERVAL_DEFAULT)
        self.spin_interval.setSuffix(" ms")

        # Log
        self.log_display = QPlainTextEdit(readOnly=True)
        self.log_display.setMaximumBlockCount(100)

    def _setup_layout(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        
        # Settings Block
        settings_group = QFrame()
        settings_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        g_layout = QVBoxLayout(settings_group)
        g_layout.addWidget(self.chk_translation)
        g_layout.addWidget(self.chk_cg)
        
        # Interval Row
        row_interval = QHBoxLayout()
        row_interval.addWidget(QLabel("Scan Speed:"))
        row_interval.addWidget(self.spin_interval)
        g_layout.addLayout(row_interval)
        
        layout.addWidget(settings_group)
        
        # Log
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_display)

    def _connect_signals(self):
        self.chk_translation.stateChanged.connect(
            lambda state: setattr(self, "translation_enabled", bool(state))
        )
        self.chk_cg.stateChanged.connect(
            lambda state: setattr(self, "cg_enabled", bool(state))
        )
        self.spin_interval.valueChanged.connect(self._update_interval)

    def _initialize_controllers(self):
        self.region_controllers = [RegionController(config, self) for config in REGION_CFG]
        self.cg_controller = CGController(CG_CFG, self)
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_tick)
        self.update_timer.start(CHECK_INTERVAL_DEFAULT)

    def log(self, message):
        """Add message to log display."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_display.appendPlainText(f"[{timestamp}] {message}")

    def _update_interval(self, value):
        """Update timer interval."""
        self.update_timer.setInterval(value)

    def _update_tick(self):
        """Main update loop."""
        screenshot = pyautogui.screenshot()
        self.cg_controller.update(screenshot)
        for controller in self.region_controllers:
            controller.update(screenshot, self.db)


# ENTRY POINT

def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

def beside_exe(filename: str) -> str:
    return os.path.join(app_dir(), filename)

def main():
    global NDS_FAMILY

    font_path = beside_exe(FONT_FILE)
    app = QApplication(sys.argv)

    if not os.path.exists(font_path):
        print(f"[WARN] NDS.ttf not found at: {font_path}")
    else:
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            fams = QFontDatabase.applicationFontFamilies(font_id)
            if fams:
                NDS_FAMILY = fams[0]

    viewer = ViewerPanel()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()