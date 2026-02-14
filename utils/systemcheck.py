"""
systemcheck.py

Checks the system requirements.
"""



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

if __name__ == "__main__":
    # Testing Modules

    modules = check_modules()
    print("Module(Found)")
    print("---")
    for mod in modules:
        print(f"{mod}({modules[mod]})") 