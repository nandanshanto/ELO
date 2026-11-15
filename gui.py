import json
import os
import shutil
import socket
import subprocess
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from main import load_memory, save_memory
from src.commands import respond, CHAT_HISTORY, save_history
from src.sentinel import sentinel, LOG_FILE, WATCH_DIR
from src.voice import elo_voice

try:
    import psutil
except ImportError:
    psutil = None

BASE_DIR = Path(__file__).parent
UI_FILE = BASE_DIR / "ui" / "index.html"
PORT = 8765

memory_lock = threading.RLock()
memory = load_memory()
voice_enabled = True


def check_ollama():
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.6):
            return True
    except OSError:
        return False


def sentinel_is_running():
    observer = getattr(sentinel, "observer", None)
    return bool(observer and observer.is_alive())


def read_last_lines(path, count=5, chunk_size=4096):
    """Read only the end of a log file instead of loading the whole file."""
    try:
        with path.open("rb") as file:
            file.seek(0, 2)
            position = file.tell()
            buffer = b""
            while position > 0 and buffer.count(b"\n") <= count:
                amount = min(chunk_size, position)
                position -= amount
                file.seek(position)
                buffer = file.read(amount) + buffer
            return buffer.decode("utf-8", errors="replace").splitlines()[-count:]
    except OSError:
        return []


def get_sentinel_info():
    sentinel_file = "document.txt"
    sentinel_time = "10:33 AM"
    events = []

    # Check WATCH_DIR for most recently modified file
    try:
        watch_path = Path(WATCH_DIR)
        if watch_path.exists() and watch_path.is_dir():
            files = [p for p in watch_path.iterdir() if p.is_file()]
            if files:
                latest = max(files, key=lambda p: p.stat().st_mtime)
                sentinel_file = latest.name
                dt = datetime.fromtimestamp(latest.stat().st_mtime)
                sentinel_time = dt.strftime("%I:%M %p").lstrip("0") or dt.strftime("%I:%M %p")
    except Exception:
        pass

    # Also read recent events from LOG_FILE
    try:
        if Path(LOG_FILE).exists():
            recent_lines = read_last_lines(Path(LOG_FILE), 5)
            for line in recent_lines:
                try:
                    item = json.loads(line)
                    path_value = item.get("path", "Unknown file")
                    filename = Path(path_value).name or str(path_value)
                    event_name = str(item.get("event", "event")).upper()
                    event_time = str(item.get("time", ""))
                    if "T" in event_time:
                        raw_t = event_time.split("T", 1)[1][:8]
                        event_time = raw_t
                    destination = item.get("destination")
                    entry = f"{event_time}  {event_name}\n{filename}"
                    if destination:
                        entry += f"\nTO: {Path(destination).name}"
                    events.append(entry)
                    sentinel_file = filename
                except Exception:
                    continue
    except Exception:
        pass

    return sentinel_file, sentinel_time, events


def get_system_metrics():
    cpu_val = 28
    ram_val = 23
    drives_info = []

    if psutil is not None:
        try:
            cpu_val = int(round(psutil.cpu_percent(interval=None)))
            ram_val = int(round(psutil.virtual_memory().percent))
        except Exception:
            pass

    for drive in ("C:\\", "D:\\"):
        try:
            usage = shutil.disk_usage(drive)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            drives_info.append(f"{drive[0]}: Drive  {free_gb:.1f} GB free of {total_gb:.1f} GB")
        except OSError:
            pass

    return cpu_val, ram_val, drives_info


def get_recent_chat_titles():
    user_msgs = [
        item.get("content", "").strip()
        for item in reversed(CHAT_HISTORY)
        if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
    ]
    seen = []
    for msg in user_msgs:
        short = msg if len(msg) <= 18 else msg[:18] + "..."
        if short not in seen:
            seen.append(short)
        if len(seen) >= 5:
            break
    if not seen:
        return ["Hi there, Sir an ...", "Recent help yo..."]
    return seen


def speak_async(text):
    if not voice_enabled or not text:
        return

    def _run():
        try:
            elo_voice.speak(text)
        except Exception as err:
            print(f"ELO Voice Error: {err}")

    threading.Thread(target=_run, daemon=True, name="ELO-Voice").start()


class EloRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP polling logs in terminal
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        global memory
        if self.path in ("/", "/index.html"):
            if UI_FILE.exists():
                content = UI_FILE.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "ui/index.html not found.")
            return

        if self.path.startswith("/api/state"):
            cpu_val, ram_val, drives_info = get_system_metrics()
            s_file, s_time, s_logs = get_sentinel_info()
            with memory_lock:
                memory = load_memory()
                mem_copy = dict(memory)

            self._send_json({
                "cpu": cpu_val,
                "ram": ram_val,
                "drives": drives_info,
                "ollama_online": check_ollama(),
                "voice_enabled": voice_enabled,
                "sentinel_running": sentinel_is_running(),
                "sentinel_file": s_file,
                "sentinel_time": s_time,
                "sentinel_logs": s_logs,
                "memory": mem_copy,
                "recent_chats": get_recent_chat_titles(),
            })
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        global memory, voice_enabled
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            data = {}

        if self.path == "/api/chat":
            user_text = str(data.get("message", "")).strip()
            if not user_text:
                self._send_json({"reply": "Please enter a message."})
                return

            try:
                with memory_lock:
                    memory = load_memory()
                    reply = respond(user_text, memory, save_memory)
                if reply is None:
                    reply = "I couldn't generate a response. Please try again."
                reply = str(reply)
            except Exception as err:
                import traceback
                traceback.print_exc()
                reply = f"I encountered an error while processing your request: {err}"

            speak_async(reply)
            self._send_json({"reply": reply})
            return

        if self.path == "/api/sentinel/start":
            try:
                msg = sentinel.start()
            except Exception as err:
                msg = f"Could not start Sentinel: {err}"
            self._send_json({"message": str(msg), "running": sentinel_is_running()})
            return

        if self.path == "/api/sentinel/stop":
            try:
                msg = sentinel.stop()
            except Exception as err:
                msg = f"Could not stop Sentinel: {err}"
            self._send_json({"message": str(msg), "running": sentinel_is_running()})
            return

        if self.path == "/api/voice/toggle":
            voice_enabled = not voice_enabled
            self._send_json({"voice_enabled": voice_enabled})
            return

        if self.path == "/api/voice/speak":
            text = str(data.get("text", "")).strip()
            if text:
                threading.Thread(
                    target=lambda: elo_voice.speak(text),
                    daemon=True
                ).start()
            self._send_json({"ok": True})
            return

        if self.path == "/api/history/clear":
            CHAT_HISTORY.clear()
            save_history()
            self._send_json({"ok": True})
            return

        self.send_error(404, "Endpoint not found")


def launch_desktop_window(url):
    """Open the UI in an app-mode window (Edge/Chrome) or default browser."""
    browser_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for exe in browser_candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, f"--app={url}", "--window-size=1280,800"])
                return
            except OSError:
                pass
    webbrowser.open(url)


def main():
    if psutil is not None:
        psutil.cpu_percent(interval=None)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), EloRequestHandler)
    url = f"http://127.0.0.1:{PORT}"
    print("====================================================")
    print(f" ELO Personal AI System UI Online: {url}")
    print(f" Sentinel Workspace: {WATCH_DIR}")
    print(" Press Ctrl+C in this terminal to stop ELO.")
    print("====================================================")

    threading.Timer(0.6, lambda: launch_desktop_window(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ELO GUI server...")
    finally:
        try:
            sentinel.stop()
        except Exception:
            pass
        server.server_close()


if __name__ == "__main__":
    main()
