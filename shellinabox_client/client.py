import io
import sys
import tty
import queue
import termios
import requests
import threading

class ShellInABoxClient():
    def __init__(self, url: str, session: requests.Session = None):
        self.url = url
        self.width = 128
        self.height = 32
        if session:
            self.session = session
        else:
            self.session = requests.Session()
        self.stopper = threading.Event()
        self.exit_error = None

    def input_reader_thread(self, stdin: io.TextIOWrapper, dst: queue.Queue[str]) -> None:
        while not self.stopper.is_set():
            try:
                data = stdin.read(1)
                dst.put(data)
            except Exception as e:
                self.stop(e)

    def input_sender_thread(self, src: queue.Queue[str], session_id: str) -> None:
        while not self.stopper.is_set():
            try:
                data = src.get()
                while True:
                    try:
                        data += src.get_nowait()
                    except queue.Empty:
                        break
                response = self.session.post(self.url, data={
                    "width": self.width,
                    "height": self.height,
                    "session": session_id,
                    "keys": data.encode().hex()
                })
                response.raise_for_status()
            except Exception as e:
                self.stop(e)

    def output_receiver_thread(self, dst: queue.Queue[str], session_id: str) -> None:
        while not self.stopper.is_set():
            try:
                payload = {
                    "width": self.width,
                    "height": self.height,
                    "session": session_id,
                }
                response = self.session.post(self.url, data=payload)
                response.raise_for_status()
                data: str = response.json()["data"]
                dst.put(data)
            except Exception as e:
                self.stop(e)

    def output_writer_thread(self, src: queue.Queue[str], stdout: io.TextIOWrapper) -> None:
        while not self.stopper.is_set():
            try:
                data = src.get()
                stdout.write(data)
                stdout.flush()
            except Exception as e:
                self.stop(e)

    def stop(self, e: Exception = None):
        self.stopper.set()
        self.exit_error = e

    def start(self, stdout: io.TextIOWrapper, stdin: io.TextIOWrapper) -> None:
        response = self.session.post(self.url, data={
            "width": self.width,
            "height": self.height,
            "rooturl": self.url,
        })
        response.raise_for_status()
        session_id = response.json()["session"]
        input_queue = queue.Queue()
        output_queue = queue.Queue()
        input_reader = threading.Thread(target=self.input_reader_thread, args=(stdin, input_queue), daemon=True)
        input_sender = threading.Thread(target=self.input_sender_thread, args=(input_queue, session_id), daemon=True)
        output_reciever = threading.Thread(target=self.output_receiver_thread, args=(output_queue, session_id), daemon=True)
        output_writer = threading.Thread(target=self.output_writer_thread, args=(output_queue, stdout), daemon=True)
        all_threads = [output_reciever, output_writer, input_reader, input_sender]
        for thread in all_threads:
            thread.start()

    def wait(self):
        while not self.stopper.is_set():
            pass
        if self.exit_error is not None:
            raise self.exit_error

    def interact(self) -> None:
        try:
            fd = sys.stdin.fileno()
            old_tty_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            self.start(sys.stdout, sys.stdin)
            self.wait()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_tty_settings)
            pass
