# import os
# import pygetwindow as gw
#
# SEARCH_PATHS = [
#     "D:/",
# ]
#
#
# def scan_files():
#
#     file_list = []
#
#     for directory in SEARCH_PATHS:
#
#         for root, dirs, files in os.walk(directory):
#
#             for file in files:
#
#                 full_path = os.path.join(root, file)
#
#                 file_list.append(full_path)
#
#     return file_list
#
#
# def search_file(keyword, files):
#
#     keyword = keyword.lower()
#
#     matches = []
#
#     for file in files:
#
#         filename = os.path.basename(file).lower()
#
#         if keyword in filename:
#
#             matches.append(file)
#
#     return matches
#
#
# def open_file(file_path):
#
#     try:
#
#         os.startfile(file_path)
#
#         print(f"✅ Opened: {file_path}")
#
#     except Exception as e:
#
#         print(f"❌ Error opening file: {e}")
#
#
#
#
#         ##### chnage of close
# def close_file(window_keyword):
#
#     try:
#
#         windows = gw.getAllWindows()
#
#         found = False
#
#         for window in windows:
#
#             title = window.title.lower()
#
#             if window_keyword.lower() in title:
#
#                 print(f"✅ Closing window: {window.title}")
#
#                 window.close()
#
#                 found = True
#
#         if not found:
#
#             print("❌ Window not found")
#
#     except Exception as e:
#
#         print(f"❌ Error closing window: {e}")
#
import os
import time
import subprocess
import pygetwindow as gw


SEARCH_PATHS = [
    "D:/",
]

# Map of common voice keywords to their process names for force-kill
KNOWN_APPS = {
    "chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "explorer": "explorer.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "vlc": "vlc.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "vscode": "Code.exe",
    "code": "Code.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",
}


def scan_files():

    file_list = []

    for directory in SEARCH_PATHS:

        for root, dirs, files in os.walk(directory):

            for file in files:

                full_path = os.path.join(root, file)

                file_list.append(full_path)

    return file_list


def search_file(keyword, files):

    keyword = keyword.lower()

    matches = []

    for file in files:

        filename = os.path.basename(file).lower()

        if keyword in filename:

            matches.append(file)

    return matches


def open_file(file_path):

    try:

        os.startfile(file_path)

        print(f"✅ Opened: {file_path}")

    except Exception as e:

        print(f"❌ Error opening file: {e}")


def close_file(window_keyword):
    """
    Close a window/application by keyword.
    Strategy:
      1. Try to match a known app name and force-kill via taskkill.
      2. Otherwise, find matching windows and close them gracefully,
         then force-kill if they don't close within a timeout.
    """
    keyword_lower = window_keyword.lower().strip()

    # --- Strategy 1: Known app → taskkill ---
    for app_key, process_name in KNOWN_APPS.items():
        if app_key in keyword_lower:
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", process_name],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    print(f"✅ Force-closed {process_name}")
                    return True
                else:
                    print(f"⚠️ taskkill said: {result.stderr.strip()}")
                    # Fall through to window-based close
            except Exception as e:
                print(f"⚠️ taskkill failed: {e}")
            break  # only try one known-app match

    # --- Strategy 2: Window title match → graceful close + force fallback ---
    try:
        windows = gw.getAllWindows()
        matched = []

        for window in windows:
            title = window.title.strip()
            if not title:
                continue
            if keyword_lower in title.lower():
                matched.append(window)

        if not matched:
            print(f"❌ No window found matching '{window_keyword}'")
            return False

        for window in matched:
            try:
                print(f"✅ Closing window: {window.title}")
                window.close()
            except Exception as e:
                print(f"⚠️ Graceful close failed for '{window.title}': {e}")

        # Give windows a moment to close
        time.sleep(1.0)

        # Check if any are still open and force-kill
        still_open = gw.getAllWindows()
        for window in matched:
            for w in still_open:
                if w.title == window.title and w._hWnd == window._hWnd:
                    try:
                        print(f"⚠️ Window still open, force-killing: {window.title}")
                        # Use taskkill with the window's PID if available
                        import ctypes
                        pid = ctypes.c_ulong()
                        ctypes.windll.user32.GetWindowThreadProcessId(
                            window._hWnd, ctypes.byref(pid)
                        )
                        if pid.value:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(pid.value)],
                                capture_output=True, timeout=5
                            )
                            print(f"✅ Force-killed PID {pid.value}")
                    except Exception as e:
                        print(f"❌ Force-kill failed: {e}")
                    break

        return True

    except Exception as e:
        print(f"❌ Error closing window: {e}")
        return False