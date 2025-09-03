import os
import sys
import tty
import queue
import termios
import signal
import requests
import threading
from .client import ShellInABoxClient

class ShellInABoxTerminal():
    def __init__(self, client: ShellInABoxClient):
        self.client = client
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.input_reading_thread = threading.Thread(target=self.input_reader, daemon=True)
        self.input_sending_thread = threading.Thread(target=self.input_sender, daemon=True)
        self.output_printing_thread = threading.Thread(target=self.output_receiver, daemon=True)
        self.output_receiving_thread = threading.Thread(target=self.output_printer, daemon=True)
        self.shared_lock = threading.Lock()
        self.terminated = threading.Event()
        self.old_tty_settings = None
        self.exit_error = None

    def update_terminal_size(self) -> None:
        with self.shared_lock:
            terminal_size = os.get_terminal_size()
            self.client.width = terminal_size.columns
            self.client.height = terminal_size.lines

    def terminal_resize_handler(self, signum, frame) -> None:
        try:
            self.update_terminal_size()
            self.input_queue.put("")
        except Exception as e:
            self.stop(e)
            return

    def stop(self, e: Exception = None) -> None:
        sys.stdout.flush()
        if self.old_tty_settings:
            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, self.old_tty_settings)
            self.old_tty_settings = None
        self.terminated.set()
        with self.shared_lock:
            if self.exit_error is None and e is not None:
                self.exit_error = e
                # NOTE: this is to handle special case where the shellinabox session is closed (unset the exit error)
                if isinstance(e, requests.exceptions.HTTPError):
                    if e.response.status_code in [400, 500]:
                        self.exit_error = None

    def input_sender(self) -> None:
        while not self.terminated.is_set():
            try:
                keys = self.input_queue.get()
            except Exception as e:
                self.stop(e)
                return
            while True:
                try:
                    keys += self.input_queue.get_nowait()
                except queue.Empty:
                    break
                except Exception as e:
                    self.stop(e)
                    return
            try:
                self.client.send(keys)
            except Exception as e:
                self.stop(e)
                return

    def input_reader(self) -> None:
        fd = sys.stdin.fileno()
        self.old_tty_settings = termios.tcgetattr(fd)
        tty.setraw(sys.stdin.fileno())
        while not self.terminated.is_set():
            ch = sys.stdin.read(1)
            try:
                self.input_queue.put(ch)
            except Exception as e:
                self.stop(e)
                return

    def output_receiver(self) -> None:
        while not self.terminated.is_set():
            try:
                data = self.client.receive()
                self.output_queue.put(data)
            except Exception as e:
                self.stop(e)
                return

    def output_printer(self) -> None:
        while not self.terminated.is_set():
            try:
                data = self.output_queue.get()
                sys.stdout.write(data)
                sys.stdout.flush()
            except Exception as e:
                self.stop(e)
                return

    def start(self) -> None:
        self.update_terminal_size()
        signal.signal(signal.SIGWINCH, self.terminal_resize_handler)
        self.client.connect()
        self.output_receiving_thread.start()
        self.output_printing_thread.start()
        self.input_reading_thread.start()
        self.input_sending_thread.start()
        while not self.terminated.is_set():
            continue
        if self.exit_error is not None:
            raise self.exit_error
