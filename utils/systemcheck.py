"""
systemcheck.py

Checks the system requirements.
"""

try:
    import winreg
except ImportError:
    print("Fatal! Module: winreg not found! (are you on windows?)")
    print("Exiting Safely!")
    exit()

def check_modules() -> dict:
    modules = {}
    module_list = ["pyautogui", "imagehash", "vlc", "keyboard", "PIL", "PyQt5"]

    for module in module_list:
        try:
            __import__(module)
            modules[module] = True
        except ImportError:
            modules[module] = False

    return modules

def check_vlc_installed():
    try:
        # Open the VLC registry key
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC") as key:
            vlc_path = winreg.QueryValueEx(key, "InstallLocation")[0]
            return f"VLC is installed at: {vlc_path}"

    except FileNotFoundError:
        return "VLC is not installed."

if __name__ == "__main__":
    # Testing Modules

    modules = check_modules()
    print("Module(Found)")
    print("---")
    for mod in modules:
        print(f"{mod}({modules[mod]})") 

    print(check_vlc_installed())

    