import requests

class ShellInABoxClientError(Exception):
    pass

class ShellInABoxClient():
    def __init__(self, url: str, width: int = 128, height: int = 32, session: requests.Session = None):
        self.url = url
        self.width = width
        self.height = height
        if session:
            self.session = session
        else:
            self.session = requests.Session()
        self.shellinabox_session_id = None

    def connect(self) -> None:
        if self.shellinabox_session_id is not None:
            return
        payload = {
            "width": self.width,
            "height": self.height,
            "rooturl": self.url,
        }
        response = self.session.post(self.url, verify=False, data=payload)
        response.raise_for_status()
        self.shellinabox_session_id = response.json()["session"]

    def must_be_connected(self):
        if self.shellinabox_session_id is None:
            raise ShellInABoxClientError("Client has not been connected to a shellinabox server")

    def receive(self) -> str:
        self.must_be_connected()
        payload = {
            "width": self.width,
            "height": self.height,
            "session": self.shellinabox_session_id,
        }
        response = self.session.post(self.url, verify=False, data=payload)
        response.raise_for_status()
        return response.json()["data"]

    def send_bytes(self, b: bytes) -> None:
        self.must_be_connected()
        payload = {
            "width": self.width,
            "height": self.height,
            "session": self.shellinabox_session_id,
            "keys": b.hex()
        }
        response = self.session.post(self.url, verify=False, data=payload)
        response.raise_for_status()
        if "<title>OK</title>" not in response.content.decode("utf-8"):
            raise ShellInABoxClientError("Client received an invalid response")

    def send(self, s: str) -> None:
        self.send_bytes(s.encode())

    def sendline(self, s: str = "") -> None:
        self.send(f"{s}\r")
