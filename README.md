# Starfy 4 Translation Overlay Tool

## What Is This?

This project is a translation overlay tool for Starfy 4 that works by:

- Taking live screenshots of the game at an adjustable millisecond rate
- Hashing very specific regions of those screenshots
- Matching them against a database of known text images
- Overlaying translated text on top of the game
- Pretending this is a normal and sustainable approach

Think of it more like a puppet show performed in front of an emulator.

**What this does NOT do:**
- Modify the ROM
- Inject code

---

## Translation Progress

World 1: Fully translated
- All main gameplay text
- Almost all static UI elements
- Pause Menu 
- Stuff Menu 
- Hints Screen 

Other Worlds: Not yet translated

I will update this project as I continue my playthrough of Starfy 4, hoping for a near-complete translation in the coming months

---

## How It Works

1. You run Starfy 4 in an emulator
2. The tool takes screenshots of your screen at an adjustable millisecond rate
3. When certain UI/text regions appear:
   - A screenshot is captured
   - A perceptual hash is generated
   - The hash is compared against a known database
4. If everything aligns:
   - Translated text displays in an overlay
5. If anything is even slightly off:
   - It doesn't work (see "System Requirements" below)

---

## System Requirements

⚠️ **READ THIS CAREFULLY** ⚠️

This project will not work unless your setup matches the following **exactly**.

### Operating System
- **Windows 11 ONLY** (not Windows 10)

### Display Settings
- **Resolution:** 1920×1080 (1080p)
- **Windows Scaling:** 125%
- **Refresh Rate:** 60Hz

### Emulator
- **melonDS**
- **Windowed Fullscreen mode**

### Game
- **Starfy 4 ROM** (you must supply this yourself)

### Media Player
- **VLC Media Player** (yes, really, the opening CG is an overlayed translated video)

### Antivirus
- **Windows Defender may flag this as evasive malware** due to the way the program is coded to hide windows from screenshots. This is a false positive. You may need to whitelist the tool or disable the check to run it.

### Performance
- On my machine with an i7-9700, I could comfortably run the tool at 1ms with it only using 10-15% CPU, on a laptop with an i5-1135G7, it could handle 10ms with the same CPU overhead of 10-15%. The tool is configured out the gate to run at 10ms. You can adjust this to match performance.

---

## Why Are the Requirements So Strict?

This tool relies on:

- Absolute pixel positions
- Predictable scaling behavior
- Stable frame timing
- The emulator rendering identical pixels every time

Change anything and:
- Hashes won't match
- Screenshots won't align
- Translations won't trigger

---

## Known Issues

**Not Implemented/Bugs:**
-Title screen is not translated
-Sometimes the opening CG starts late, so try again by re-opening the ROM or just deal with audio not being perfectly synced

**Breaks if:**
- You move the emulator window
- Don't run it in windowed maximized 
- You change scaling
- You run any rendering setting besides Software in MelonDS

**Does not like:**
- Multi-monitor setups
- Your optimism

---

## Getting Started

1. Set up your system according to the requirements above (yes, all of them)
2. Obtain your Starfy 4 ROM
3. Run the tool first before opening the ROM in MelonDS
4. Configure the tool's screenshot capture rate
5. Load the ROM
6. Either enjoy translations or debugging

---

## Credits & Acknowledgments

This project would not exist without **SomeUselessTranslations** on YouTube. Their full translation of Starfy 4 was used extensively during development. The opening CG fully belongs to them.

---

*If this works on your machine: Congratulations. If it doesn't: Good luck. :)*
