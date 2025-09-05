import os
import io
import sys
import tty
import httpx
import signal
import asyncio
import termios
import functools
from typing import Tuple

class ShellInABoxController():
    def __init__(self, url: str, client: httpx.AsyncClient = None, width: int = 128, height: int = 32):
        self.url = url
        self.width = width
        self.height = height
        if client:
            self.client = client
        else:
            self.client = httpx.AsyncClient()
        self.session = None

    async def update_terminal_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        if self.session is not None:
            response = await self.client.post(self.url, data={
                "width": self.width,
                "height": self.height,
                "session": self.session,
                "keys": "",
            })
            response.raise_for_status()

    async def input_handler_task(self, reader: asyncio.StreamReader) -> None:
        while True:
            data = await reader.read(128)
            response = await self.client.post(self.url, data={
                "width": self.width,
                "height": self.height,
                "session": self.session,
                "keys": data.hex(),
            })
            response.raise_for_status()

    async def output_handler_task(self, writer: asyncio.StreamWriter) -> None:
        while True:
            response = await self.client.post(self.url, timeout=None, data={
                "width": self.width,
                "height": self.height,
                "session": self.session,
            })
            response.raise_for_status()
            data: bytes = response.json()["data"].encode()
            writer.write(data)
            await writer.drain()

    async def run_forever(self, stdin: io.TextIOWrapper, stdout: io.TextIOWrapper) -> None:
        response = await self.client.post(self.url, data={
            "width": self.width,
            "height": self.height,
            "rooturl": self.url,
        })
        response.raise_for_status()
        self.session = response.json()["session"]
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, stdin)
        w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, stdout)
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
        await asyncio.gather(
            self.input_handler_task(reader),
            self.output_handler_task(writer)
        )

    async def control(self) -> Tuple[int, int]:
        reader_fd, stdout_fd = os.pipe()
        stdin_fd, writer_fd = os.pipe()
        stdout = os.fdopen(stdout_fd, "w")
        stdin = os.fdopen(stdin_fd, "r")
        asyncio.create_task(self.run_forever(stdin=stdin, stdout=stdout))
        return reader_fd, writer_fd

    async def interact(self) -> None:
        def terminal_resize_signal_handler(loop: asyncio.AbstractEventLoop) -> None:
            terminal_size = os.get_terminal_size()
            loop.create_task(self.update_terminal_size(width=terminal_size.columns, height=terminal_size.lines))
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGWINCH, functools.partial(terminal_resize_signal_handler, loop))
        fd = sys.stdin.fileno()
        old_tty_settings = termios.tcgetattr(fd)
        terminal_size = os.get_terminal_size()
        try:
            tty.setraw(fd)
            await self.update_terminal_size(width=terminal_size.columns, height=terminal_size.lines)
            await self.run_forever(stdin=sys.stdin, stdout=sys.stdout)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_tty_settings)
            pass
