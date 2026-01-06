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
    QVBoxLayout, QHBoxLayout, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QFontDatabase, QTextDocument


# CONFIG

# Database and monitoring settings
HASH_DB_FILE = "hash_db_v3.json"
UNSEEN_DIR = "untranslated"
CHECK_INTERVAL = 10  # milliseconds

# UI positioning, first textbox is hardcoded, leftover from testing
TEXTBOX_RECT = (661, 367, 539, 153)
UI_RECT = (1300, 80, 320, 600)

# CG configuration
CG_CFG = {
    "trigger_crop": (752, 241, 413, 111),
    "stop_crop": (1191, 433, 62, 69),
    "overlay_rect": (641, 60, 639, 960),
    "video_path": "cg.mp4",
}

# Region definitions
REGION_CFG = [
    {  # 0 – standard dialogue
        "crop": TEXTBOX_RECT,
        "overlay": TEXTBOX_RECT,
        "patches": [(1200, 368, 66, 115)],
        "font_pt": 25,
    },
    {  # 1 – YES/NO prompt
        "crop": (793, 365, 465, 156),
        "overlay": (661, 367, 539, 153),
        "patches": [{"cut": (722, 438, 69, 83)}],
        "font_pt": 24,
    },
    {  # 2 – menu bottom
        "crop": (654, 401, 604, 118),
        "overlay": (654, 401, 604, 118),
        "overlay_color": "#FBDBA2",
        "font_pt": 25,
    },
    {  # 3 – menu top
        "crop": (654, 361, 610, 32),
        "overlay": (654, 361, 610, 32),
        "overlay_color": "#FB8A00",
        "font_pt": 22,
    },
    {  # 4 - bottom-screen goal
        "crop": (1098, 619, 132, 23),
        "overlay": (1098, 619, 102, 23),
        "font_pt": 14,
    },
    {  # 5 - bottom-screen city
        "crop": (1100, 701, 163, 19),
        "overlay": (1100, 700, 163, 20),
        "font_pt": 12,
    },
    {  # 6 - bottom-screen warp
        "crop": (1098, 778, 160, 24),
        "overlay": (1098, 778, 160, 24),
        "font_pt": 14,
    },
    {  # 7 - bottom-screen warp king
        "crop": (1099, 858, 162, 23),
        "overlay": (1099, 858, 162, 23),
        "font_pt": 14,
    },
    {  # 8 - bottom-screen warp door
        "crop": (1099, 937, 157, 24),
        "overlay": (1099, 937, 157, 24),
        "font_pt": 14,
    },
    {  # 9 - bottom-screen pause
        "crop": (887, 978, 89, 21),
        "overlay": (887, 978, 89, 21),
        "font_pt": 15,
    },
    {  # 10 - abilities dialogue
        "crop": (656, 374, 600, 156),
        "overlay": (656, 374, 600, 156),
        "font_pt": 25,
        "patches": [
            {"cut": (694, 490, 90, 37)},
            {"cut": (1046, 495, 44, 35)},
        ],
    },
    {  # 11 - bottom-screen dialogue
        "crop": (656, 580, 535, 155),
        "overlay": (656, 580, 535, 155),
        "patches": [(1170, 577, 89, 120)],
        "font_pt": 27,
    },
    {  # 12 - 1-1 warp
        "crop": (919, 148, 281, 109),
        "overlay": (919, 148, 281, 109),
        "font_pt": 27,
    },
    {  # 13 - stuff
        "crop": (661, 561, 549, 158),
        "overlay": (661, 561, 549, 158),
        "font_pt": 31,
        "patches": [
            {"cut": (977, 686, 75, 31)},
        ],
    },
    {  # 14 - world sign
        "crop": (689, 76, 547, 48),
        "overlay": (689, 75, 547, 48),
        "overlay_color": "#FBCB71",
        "font_pt": 32,
    },
    {  # 15 – stuff menu logo
        "crop":       (739, 560, 280, 76),
        "overlay":    (683, 560, 339, 78),
        "font_pt":    47,
        "overlay_color": "#8269FB",
    },
    {  # 16 - stuff items 1
        "crop": (680,640,325,37),
        "overlay": (680,640,325,37),
        "font_pt": 27,
    },
    {  # 17 - stuff items description
        "crop": (1044,677,196,65),
        "overlay": (1044,677,199,65),
        "font_pt": 14,
    },
    {  # 18 - stuff buttons
        "crop": (1046,770,194,157),
        "overlay": (1046,769,194,159),
        "font_pt": 18,
        "patches": [
            {"cut": (1027, 794, 233, 18)},
            {"cut": (1027, 840, 233, 18)},
            {"cut": (1027, 886, 233, 18)},
        ],
    },
    {  # 19 - stuff buttons bottom
        "crop": (773, 959, 377, 36),
        "overlay": (773, 959, 377, 36),
        "font_pt": 23,
        "patches": [
            {"cut": (868, 959, 35, 39)},
            {"cut": (1010, 959, 35, 39)},
        ],
    },
    {  # 20 - stuff change starfy/starly
        "crop": (1100, 640, 180, 25),
        "overlay": (1160, 640, 100, 25),
        "font_pt": 16,
        "overlay_color": "#8269FB",
    },
    {  # 21 - stuff top text
        "crop": (665, 479, 590, 51),
        "overlay": (665, 480, 590, 50),
        "font_pt": 28,
        "overlay_color": "#C5B915",
    },
    {  # 22 - moe payphone
        "crop": (662, 583, 550, 142),
        "overlay": (662, 583, 550, 152),
        "patches": [(1209, 578, 54, 128)],
        "font_pt": 25,
    },
    {  # 23 - 1-2 warp
        "crop": (699, 228, 279, 109),
        "overlay": (699, 228, 279, 109),
        "font_pt": 27,
    },
    {  # 24 - 1-1 warp text
        "crop": (986, 196,148,30),
        "overlay": (986, 196,148,37),
        "font_pt": 18,
    },
    {  # 25 - 1-2 warp text
        "crop": (766, 275, 148, 35),
        "overlay": (766, 275, 148, 35),
        "font_pt": 18,
    },
    {  # 26 - pause menu stuff small
        "crop": (640, 540, 640, 480),
        "overlay": (766, 275, 148, 35),
        "font_pt": 18,
    },
    {   #27 warp 1-3
        "crop": (905, 228, 274, 108),
        "overlay": (905, 228, 274, 108),
        "font_pt": 27,
    },
    {   #28 warp 1-3 text
        "crop": (968, 272, 148, 40),
        "overlay": (968, 272, 148, 40),
        "font_pt": 18,
    },
]

# Put hash: color pairs here.
HASH_COLOR_OVERRIDES = {
     "a4ecdcdbd120d319": "#D3FBF3", #Outfit Menu Box 1 Selected
     "ac85d3dfd5609432": "#D3FBF3", #Gear Menu Box 1 Selected
     "ad02bd2556c7d171": "#FB498A", #Gear Menu
     "ab22d542d7819cee": "#FB9A18", #Special Menu
     "ad7c8763cc079607": "#FB498A", #Starly Switch
     "a53dc723dc079607": "#FB9A18", #Starly Switch
     "a4927939c82ddacd": "#7D7D7D",
     "e6d2d2b4b542f151": "#7D7D7D",
     "ebe9c0f6970b8415": "#7D7D7D",
     "eae9c1d69f08ad24": "#7D7D7D",
     "aea79d9ad007c60b": "#7D7D7D",
     "df51c1a6a689896e": "#7D7D7D",
}

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

        if isinstance(spec, tuple):
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
                self.app.set_current_hash(hash_key, translation_text)
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
        self.current_hash = None

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
            self.cmb_region.addItem(f"{i}: {region['crop']}")
        
        # Buttons
        self.btn_hash = QPushButton("Hash textbox (F8)")
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
        def hotkey_loop():
            while True:
                keyboard.wait("f8")
                QTimer.singleShot(0, self.capture_hash)
        
        threading.Thread(target=hotkey_loop, daemon=True).start()

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
        self.log(f"Active region set to {index} → {REGION_CFG[index]['crop']}")

    def _update_tick(self):
        """Main update loop - called by timer."""
        screenshot = pyautogui.screenshot()
        self.cg_controller.update(screenshot)
        for controller in self.region_controllers:
            controller.update(screenshot, self.db)

    def capture_hash(self):
        """Capture and hash the current active region."""
        x, y, w, h = self._get_active_crop_rect()
        screenshot = pyautogui.screenshot().crop((x, y, x + w, y + h))
        hash_key = str(get_perceptual_hash(screenshot))
        
        if hash_key not in self.db:
            os.makedirs(UNSEEN_DIR, exist_ok=True)
            screenshot.save(os.path.join(UNSEEN_DIR, f"{hash_key}.png"))
            self.db[hash_key] = ""
            save_database(self.db)
            self.log(f"NEW hash {hash_key} added")
        
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
        """Start rectangle measurement tool."""
        threading.Thread(target=self._measure_rect_worker, daemon=True).start()

    def _measure_rect_worker(self):
        """Background worker for rectangle measurement."""
        self._thread_safe_log("🖱  Move mouse to TOP-LEFT and press Enter")
        keyboard.wait("enter")
        x1, y1 = pyautogui.position()
        time.sleep(0.35)
        
        self._thread_safe_log("🖱  Move mouse to BOTTOM-RIGHT and press Enter")
        keyboard.wait("enter")
        x2, y2 = pyautogui.position()
        
        width, height = x2 - x1, y2 - y1
        coordinates = f"({x1}, {y1}, {width}, {height})"
        self._thread_safe_log(f"🎯  RECT → {coordinates}")

    def _thread_safe_log(self, message):
        """Thread-safe logging method."""
        QTimer.singleShot(0, lambda: self.log(message))


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