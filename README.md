# Starfy 4 Translation Overlay Tool  

## What Is This?

This project is a translation overlay tool for Starfy 4 that works by:

- Taking live screenshots of the game at an adjustable millisecond rate 
- Hashing very specific regions of those screenshots  
- Matching them against a database of known text images  
- Overlaying translated text on top of the game  
- Pretending this is a normal and sustainable approach  

Think of it more like a puppet show performed in front of an emulator.

This does **not** modify the ROM.  
This does **not** inject code.  

---

## How Does It Work?

1. You run Starfy 4 in an emulator.
2. The tool takes screenshots of your screen at an adjustable millisecond rate.
3. When certain UI/text regions appear:
   - A screenshot is taken
   - A perceptual hash is generated
   - The hash is compared against a known set
4. If it all aligns:
   - Translated text is displayed in an overlay
5. If anything is even slightly off:
   - It doesn’t work (see “System Requirements”)

---

## System Requirements (READ THIS!!!)

This project **will not work** unless your setup matches the following *exactly*.  

### Operating System
- **Windows 11 ONLY**
  - Not Windows 10

### Display
- **1920×1080 (1080p)**
- **125% Windows scaling**
- **60Hz refresh rate**

---

### Emulator
- **melonDS**
- **Windowed Fullscreen mode**

### Game
- **Starfy 4 ROM**
  - You must supply this yourself

---

### Media Player
- **VLC Media Player**
  - Yes, really

---

## Why Are the Requirements So Specific?

Because this tool relies on:

- Absolute pixel positions  
- Predictable scaling behavior  
- Stable frame timing  
- The emulator drawing the exact same pixels every time  

Change anything and:
- Hashes won’t match
- Screenshots won’t align
- Translations won’t trigger

---

## Known Issues

- Breaks if:
  - You move the emulator window
  - You change scaling
- Does not like:
  - Multi-monitor setups
  - Your optimism

---

## Final Notes

If this works on your machine:
- Congratulations

If it doesn’t:
- Good luck.

:)
