import os
import sys
import tty
import queue
import termios
import threading
import requests

class ShellInABoxClient():
    def __init__(self, url: str, width: int = 210, height: int = 60):
        self.url = url
        self.root_url = url
        self.width = width
        self.height = height
        self.session = requests.Session()
        self.session_id = self.new_shellinabox_session()

    def new_shellinabox_session(self) -> str:
        payload = {
            "width": self.width,
            "height": self.height,
            "rooturl": self.root_url
        }
        response = self.session.post(self.url, verify=False, data=payload)
        response.raise_for_status()
        session_id = response.json()["session"]
        return session_id

    def receive(self) -> str:
        payload = {
            "width": self.width,
            "height": self.height,
            "session": self.session_id,
        }
        response = self.session.post(self.url, verify=False, data=payload)
        response.raise_for_status()
        return response.json()["data"]

    def send_bytes(self, b: bytes) -> None:
        payload = {
            "width": self.width,
            "height": self.height,
            "session": self.session_id,
            "keys": b.hex()
        }
        response = self.session.post(self.url, verify=False, data=payload)
        response.raise_for_status()
        if "<title>OK</title>" not in response.content.decode("utf-8"):
            raise ValueError("Invalid Response")        

    def send(self, s: str) -> None:
        self.send_bytes(s.encode())

    def sendline(self, s: str = "") -> None:
        self.send(f"{s}\r")

class ShellInABoxTerminalClient():
    def __init__(self, url: str):
        self.client = ShellInABoxClient(url=url)
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.input_reading_thread = threading.Thread(target=self.input_reader, daemon=True)
        self.input_sending_thread = threading.Thread(target=self.input_sender, daemon=True)
        self.output_printing_thread = threading.Thread(target=self.output_receiver, daemon=True)
        self.output_receiving_thread = threading.Thread(target=self.output_printer, daemon=True)
        self.shared_lock = threading.Lock()
        self.terminated = threading.Event()
        self.old_tty_settings = None

    def update_terminal_size(self):
        with self.shared_lock:
            terminal_size = os.get_terminal_size()
            self.client.width = terminal_size.columns
            self.client.height = terminal_size.lines

    def stop(self) -> None:
        sys.stdout.flush()
        if self.old_tty_settings:
            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, self.old_tty_settings)
            self.old_tty_settings = None
        self.terminated.set()

    def input_sender(self) -> None:
        while not self.terminated.is_set():
            keys = self.input_queue.get()
            while True:
                try:
                    keys += self.input_queue.get_nowait()
                except queue.Empty:
                    break
            try:
                self.update_terminal_size()
                self.client.send(keys)
            except requests.exceptions.HTTPError:
                self.stop()

    def input_reader(self) -> None:
        fd = sys.stdin.fileno()
        self.old_tty_settings = termios.tcgetattr(fd)
        tty.setraw(sys.stdin.fileno())
        while not self.terminated.is_set():
            ch = sys.stdin.read(1)
            self.input_queue.put(ch)

    def output_receiver(self) -> None:
        while not self.terminated.is_set():
            try:
                self.update_terminal_size()
                data = self.client.receive()
                self.output_queue.put(data)
            except requests.exceptions.HTTPError:
                self.stop()

    def output_printer(self) -> None:
        while not self.terminated.is_set():
            data = self.output_queue.get()
            sys.stdout.write(data)
            sys.stdout.flush()

    def start(self) -> None:
        self.output_receiving_thread.start()
        self.output_printing_thread.start()
        self.input_reading_thread.start()
        self.input_sending_thread.start()
        while not self.terminated.is_set():
            continue
