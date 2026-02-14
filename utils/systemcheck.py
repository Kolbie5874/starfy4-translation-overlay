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

def vlc_installed():
    try:
        # Open the VLC registry key
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VideoLAN\VLC") as key:
            vlc_path = winreg.QueryValueEx(key, "InstallLocation")[0]
            return True

    except FileNotFoundError:
        return False

def main():
    # Running Tests

    print("Running Tests")

    modules = check_modules()
    vlc_status = f"{Color.YELLOW}Unknown{Color.RESET}"

    if OS == "Windows":
        vlc_status = f"{Color.RED}Installed{Color.RESET}" if vlc_installed() else f"{Color.RED}Not Installed{Color.RESET}"

    # Printing Output

    OS_Check = f'{Color.GREEN}Valid{Color.RESET}' if OS == "Windows" else f'{Color.RED}Invalid{Color.RESET}'
    print(f"Operating System Check: {OS_Check}")

    print("\n"+"="*30+"\n")

    print_module_status(modules)

    print("\n"+"="*30+"\n")

    print(f"VLC Status: {vlc_status}")




        



if __name__ == "__main__":
    main()

    