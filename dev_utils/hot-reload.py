import os
import time
import subprocess

APP_COMMAND = ["python", "src/main.py"]  # change if needed
DEBOUNCE_MS = 200  # avoid restart-spam


def get_files_mtime():
    mtimes = {}
    for root, dirs, files in os.walk("./src"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                mtimes[path] = os.path.getmtime(path)
    return mtimes


def watch_and_reload(proc):
    last = get_files_mtime()
    while True:
        time.sleep(0.3)
        current = get_files_mtime()
        if current != last:
            print("🔄 Code changed, restarting...")
            proc.terminate()
            proc.wait()
            return  # exit watcher → main loop restarts app
        last = current


def main():
    while True:
        print("🚀 Starting app...")
        proc = subprocess.Popen(APP_COMMAND)

        watch_and_reload(proc)

        # brief debounce to avoid loops
        time.sleep(DEBOUNCE_MS / 1000)


if __name__ == "__main__":
    main()
