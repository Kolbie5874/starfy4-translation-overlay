"""
systemcheck.py

Checks the system requirements.
"""

# Checking if on Windows

OS = None

try:
    import winreg
    OS = "Windows"
except ImportError:
    OS = None
    
# Things to make the CLI pretty

class Color:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

def print_module_status(modules: dict):
    print(f"{Color.GREEN}Module Name{Color.RESET:>20}{Color.GREEN} | Status{Color.RESET:>10}")
    print("=" * 35)
    
    for module, status in modules.items():
        status_text = "Installed" if status else "Missing"
        color = Color.GREEN if status else Color.RED
        print(f"{color}{module:<20}{Color.RESET} | {color}{status_text:>10}{Color.RESET}")

# Function

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


def vlc_installed() -> bool:
    try:
        import vlc
        # Try to create an instance to confirm installation
        vlc_instance = vlc.Instance("--no-video-title-show", "--quiet")
        player = vlc_instance.media_player_new()
        player.stop()  # Ensure we can stop the player without issues
        return True  # VLC is installed
    except ImportError:
        return False  # VLC is not installed
    except Exception as e:
        print(f"{Color.RED}Error: {e}{Color.RESET}")  # print any other errors
        return False  # VLC is not installed or encountered an error


def run() -> list:
    # Running Tests

    print("Running Tests\n")

    modules = check_modules()
    vlc_status = f"{Color.YELLOW}Unknown{Color.RESET}"

    vlc_okay = False
    if OS == "Windows" and modules["vlc"]:
        vlc_okay = vlc_installed()
        vlc_status = f"{Color.RED}Installed{Color.RESET}" if vlc_okay else f"{Color.RED}Not Installed{Color.RESET}"

    # Printing Output

    OS_okay = OS == "Windows"
    OS_Check = f'{Color.GREEN}Valid{Color.RESET}' if OS_okay else f'{Color.RED}Invalid{Color.RESET}'
    print(f"Operating System Check: {OS_Check}")

    print("\n"+"="*35)
    print_module_status(modules)
    print("="*35+"\n")

    print(f"VLC Status: {vlc_status}")

    # Consolidating Output

    errors = []

    if not OS_okay:
        errors.append("[FATAL] Operating System invalid")

    for module, status in modules.items():
        if not status:
            errors.append(f"[FATAL] Vital module \'{module}\' not found")

    if not vlc_okay:
        errors.append("[CRITICAL] VLC (64-bit) not installed")

    return errors
    

if __name__ == "__main__":
    run()

    