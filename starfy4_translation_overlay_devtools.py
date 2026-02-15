import sys
import os
import json
import ctypes
import time
import threading
from ctypes import wintypes

import pyautogui
import imagehash
import vlc
import keyboard
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QWidget, QCheckBox, QPushButton, QPlainTextEdit, QLabel,
    QVBoxLayout, QHBoxLayout, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QFontDatabase, QTextDocument


# CONFIG

# Database and monitoring settings
HASH_DB_FILE = os.path.join("database/", "hash_db.json")
REGIONS_FILE = os.path.join("database/", "regions.json")
UNSEEN_DIR = "untranslated"

CHECK_INTERVAL = 16  # milliseconds
UI_RECT = (1300, 80, 320, 600)

# CG configuration
CG_CFG = {
    "trigger_crop": (752, 241, 413, 111),
    "stop_crop": (1191, 433, 62, 69),
    "overlay_rect": (641, 60, 639, 960),
    "video_path": "cg.mp4",
}

# Region definitions & hash color overrides (loaded from external JSON)
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), REGIONS_FILE)
with open(_cfg_path, "r", encoding="utf-8") as _f:
    _external_cfg = json.load(_f)

REGION_CFG = _external_cfg["regions"]
HASH_COLOR_OVERRIDES = _external_cfg["hash_color_overrides"]

# Global state
ACTIVE_REGION = 0
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
            db = json.load(f)
            return migrate_database(db)
    return {}


def save_database(db):
    """Save the hash database to file."""
    with open(HASH_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def migrate_database(db):
    """Migrate database to use hash type prefixes."""
    migrated = {}
    needs_migration = False

    for key, value in db.items():
        if not key.startswith('phash:') and not key.startswith('sha256:') and not key.startswith('__'):
            # Old format hash - add phash prefix
            migrated[f'phash:{key}'] = value
            needs_migration = True
        else:
            # Already migrated or special key
            migrated[key] = value

    if needs_migration:
        print(f"Migrated {len(db)} database entries to new format")
        save_database(migrated)

    return migrated


def normalize_image(img):
    return img


def get_perceptual_hash(img):
    """Get perceptual hash of an image."""
    return imagehash.phash(normalize_image(img))


def get_sha256_hash(img):
    """Get SHA256 hash of an image."""
    import hashlib
    # Convert PIL image to bytes
    img_bytes = img.tobytes()
    # Get image mode and size for hash
    metadata = f"{img.mode}{img.size}".encode()
    # Hash both image data and metadata
    return hashlib.sha256(metadata + img_bytes).hexdigest()


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


# RULER WINDOW

class RulerWindow(QWidget):
    """Resizable ruler for measuring screen rects."""

    def __init__(self, on_capture=None):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.on_capture = on_capture
        self.setWindowTitle("Screen Ruler")
        self.setWindowOpacity(0.8)
        self.setMinimumSize(120, 80)
        self.setStyleSheet("background-color: red;")

        self.status = QLabel()
        self.status.setStyleSheet("background-color: white; padding: 4px;")
        self.btn_capture = QPushButton("Capture")
        self.btn_capture.setStyleSheet("background-color: white;")
        self.btn_capture.clicked.connect(self.capture)

        bar = QFrame()
        bar.setStyleSheet("background-color: white;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(4, 4, 4, 4)
        bar_layout.addWidget(self.status, 1)
        bar_layout.addWidget(self.btn_capture)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(bar)

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(60)

        self.show()
        hide_from_capture(int(self.winId()))

    def _tick(self):
        geo = self.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        self.status.setText(f"({x}, {y}, {w}, {h})")

    def capture(self):
        geo = self.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        coords = f"({x}, {y}, {w}, {h})"
        clipboard = QApplication.clipboard()
        clipboard.setText(coords)
        if self.on_capture:
            self.on_capture(coords)

    def closeEvent(self, event):
        self._tick_timer.stop()
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

        # Compute both hashes
        phash_key = f"phash:{str(get_perceptual_hash(cropped_image))}"
        sha256_key = f"sha256:{get_sha256_hash(cropped_image)}"

        # Check both hash types simultaneously
        phash_translation = database.get(phash_key, "").strip()
        sha256_translation = database.get(sha256_key, "").strip()

        # Prefer SHA256 if both match, otherwise use whichever exists
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
            # Strip prefix for backward compatibility with HASH_COLOR_OVERRIDES
            bare_hash = active_hash_key.replace('phash:', '').replace('sha256:', '')
            desired_color = HASH_COLOR_OVERRIDES.get(
                bare_hash, self.config.get("overlay_color", (255, 255, 255))
            )

            # Is this a brand-new hash?
            new_hash = (current_hash != self.last_hash)

            # Re-create overlay if it's missing OR hash changed OR color changed
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
                self.app.set_current_hash(active_hash_key, translation_text)
                self.app.log(f"Detected hash {active_hash_key}")

            # Remember what it's showing
            self.last_hash = current_hash

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

        # Preload VLC player and media at initialization
        vlc_instance = vlc.Instance("--no-video-title-show", "--quiet")
        self.player = vlc_instance.media_player_new()
        media = vlc_instance.media_new(os.path.abspath(config["video_path"]))
        self.player.set_media(media)
        self.player.audio_set_mute(True)
        # Parse media to preload it without playing
        self.player.play()
        # Wait until VLC actually starts playing (or timeout after 2 seconds)
        timeout = 2.0
        start = time.time()
        while self.player.get_state() not in (vlc.State.Playing, vlc.State.Paused, vlc.State.Ended):
            time.sleep(0.01)
            if time.time() - start > timeout:
                break
        self.player.pause()
        self.player.stop()

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
        phash = str(get_perceptual_hash(cropped_image))
        hash_key = f"phash:{phash}"
        tag = self.app.db.get(hash_key, "").strip()

        if not self.is_running and tag == "__START_CG__":
            self._start_cg()
        elif self.is_running and tag == "__STOP_CG__":
            self._stop_cg()

    def _start_cg(self):
        """Start playing cutscene video."""
        # Reset player to start position
        self.player.set_position(0.0)
        # Create video window with preloaded player
        self.video_window = VideoOverlay(
            self.config["overlay_rect"],
            self.player
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
        self.current_hash = None
        self.ruler_window = None

        # Initialize UI
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._initialize_controllers()
        
        self.show()
        hide_from_capture(int(self.winId()))
        self.log(f"UI ready – polling every {CHECK_INTERVAL} ms")
        
        # Start hotkey listener
        self._start_hotkey_thread()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Checkboxes
        self.chk_translation = QCheckBox("Enable translation", checked=True)
        self.chk_cg = QCheckBox("Play opening CG", checked=True)
        
        # Region selector
        self.cmb_region = QComboBox()
        for i, region in enumerate(REGION_CFG):
            self.cmb_region.addItem(f"{i}: {region.get('name', region['crop'])}")
        
        # Buttons
        self.btn_hash = QPushButton("Hash textbox (F8)")
        self.btn_hash_sha256 = QPushButton("Hash SHA256 (F9)")
        self.btn_preview = QPushButton("Preview current")
        self.btn_save = QPushButton("Save translation")
        self.btn_rect = QPushButton("Measure RECT")
        
        # Text areas
        self.edit_translation = QPlainTextEdit()
        self.edit_translation.setFixedHeight(80)
        self.log_display = QPlainTextEdit(readOnly=True)
        self.log_display.setMaximumBlockCount(200)

    def _setup_layout(self):
        """Set up the widget layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Checkboxes
        layout.addWidget(self.chk_translation)
        layout.addWidget(self.chk_cg)
        
        # Region selection
        layout.addWidget(QLabel("Active RECT:"))
        layout.addWidget(self.cmb_region)
        
        # Translation editing
        layout.addWidget(QLabel("Current line:"))
        layout.addWidget(self.edit_translation)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_hash)
        button_layout.addWidget(self.btn_preview)
        layout.addLayout(button_layout)

        layout.addWidget(self.btn_hash_sha256)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_rect)
        
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
        self.cmb_region.currentIndexChanged.connect(self._change_active_region)
        self.btn_hash.clicked.connect(self.capture_hash)
        self.btn_hash_sha256.clicked.connect(self.capture_hash_sha256)
        self.btn_preview.clicked.connect(self.preview_current)
        self.btn_save.clicked.connect(self.save_current)
        self.btn_rect.clicked.connect(self.measure_rect)

    def _initialize_controllers(self):
        """Initialize region and CG controllers."""
        self.region_controllers = [RegionController(config, self) for config in REGION_CFG]
        self.cg_controller = CGController(CG_CFG, self)
        
        # Start main update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_tick)
        self.update_timer.start(CHECK_INTERVAL)

    def _start_hotkey_thread(self):
        """Start background thread for hotkey monitoring."""
        def hotkey_loop_f8():
            while True:
                keyboard.wait("f8")
                QTimer.singleShot(0, self.capture_hash)

        def hotkey_loop_f9():
            while True:
                keyboard.wait("f9")
                QTimer.singleShot(0, self.capture_hash_sha256)

        threading.Thread(target=hotkey_loop_f8, daemon=True).start()
        threading.Thread(target=hotkey_loop_f9, daemon=True).start()

    # Event handlers
    def log(self, message):
        """Add message to log display."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_display.appendPlainText(f"[{timestamp}] {message}")
        print(message)

    def set_current_hash(self, hash_key, text):
        """Set current hash and update translation editor."""
        self.current_hash = hash_key
        self.edit_translation.setPlainText(text)

    def _get_active_crop_rect(self):
        """Get the crop rectangle for the currently active region."""
        return REGION_CFG[ACTIVE_REGION]["crop"]

    def _change_active_region(self, index):
        """Change the active region for hash capture."""
        global ACTIVE_REGION
        ACTIVE_REGION = index
        self.log(f"Active region set to {index} → {REGION_CFG[index].get('name', REGION_CFG[index]['crop'])}")

    def _update_tick(self):
        """Main update loop - called by timer."""
        screenshot = pyautogui.screenshot()
        self.cg_controller.update(screenshot)
        for controller in self.region_controllers:
            controller.update(screenshot, self.db)

    def capture_hash(self):
        """Capture and hash the current active region using pHash."""
        x, y, w, h = self._get_active_crop_rect()
        screenshot = pyautogui.screenshot().crop((x, y, x + w, y + h))
        phash = str(get_perceptual_hash(screenshot))
        hash_key = f"phash:{phash}"

        if hash_key not in self.db:
            os.makedirs(UNSEEN_DIR, exist_ok=True)
            screenshot.save(os.path.join(UNSEEN_DIR, f"{phash}.png"))
            self.db[hash_key] = ""
            save_database(self.db)
            self.log(f"NEW hash {hash_key} added")

        self.set_current_hash(hash_key, self.db.get(hash_key, ""))

    def capture_hash_sha256(self):
        """Capture and hash the current active region using SHA256."""
        x, y, w, h = self._get_active_crop_rect()
        screenshot = pyautogui.screenshot().crop((x, y, x + w, y + h))
        sha256_hash = get_sha256_hash(screenshot)
        hash_key = f"sha256:{sha256_hash}"

        if hash_key not in self.db:
            os.makedirs(UNSEEN_DIR, exist_ok=True)
            screenshot.save(os.path.join(UNSEEN_DIR, f"{sha256_hash}.png"))
            self.db[hash_key] = ""
            save_database(self.db)
            self.log(f"NEW SHA256 hash {hash_key} added")
        else:
            self.log(f"SHA256 hash already exists: {hash_key}")

        self.set_current_hash(hash_key, self.db.get(hash_key, ""))

    def preview_current(self):
        """Show preview of current translation."""
        if not self.current_hash:
            return
        
        region_config = REGION_CFG[ACTIVE_REGION]
        preview_overlay = OverlayWindow(
            region_config["overlay"],
            bg_color=region_config.get("overlay_color"),
            font_pt=region_config.get("font_pt", 13)
        )
        preview_overlay.set_text(self.edit_translation.toPlainText())
        self.log("Preview displayed")

    def save_current(self):
        """Save current translation to database."""
        if not self.current_hash:
            return
        
        self.db[self.current_hash] = self.edit_translation.toPlainText()
        save_database(self.db)
        self.log(f"Saved translation for {self.current_hash}")

    def measure_rect(self):
        """Toggle the on-screen ruler window."""
        if self.ruler_window and self.ruler_window.isVisible():
            self.ruler_window.close()
            self.ruler_window = None
            return

        def on_capture(coords):
            self.log(f"RECT -> {coords} (copied)")

        self.ruler_window = RulerWindow(on_capture=on_capture)
        self.ruler_window.setGeometry(100, 100, 300, 200)


# MAIN ENTRY POINT

def app_dir() -> str:
    # If running as a PyInstaller exe
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Normal python run
    return os.path.abspath(os.path.dirname(__file__))

def beside_exe(filename: str) -> str:
    return os.path.join(app_dir(), filename)






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
