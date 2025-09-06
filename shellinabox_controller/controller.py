"""ShellInABox Controller Module"""
import os
import io
import sys
import tty
import signal
import asyncio
import termios
import functools
from typing import Tuple

import httpx

class ShellInABoxController():
    """ShellInABox Controller Class"""
    def __init__(self, url: str, client: httpx.AsyncClient = None, width: int = 128, height: int = 32):
        self.url = url
        if client:
            self.client = client
        else:
            self.client = httpx.AsyncClient()
        self.width = width
        self.height = height
        self.session = None

    async def update_terminal_size(self, width: int, height: int) -> None:
        """
        Update the terminal size. If a shellinabox session is active,
        then immediately send the update to the remote terminal.
        """
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
        """
        Continuously watch for input from the `reader` stream in an infinite loop.
        When some input is received, then send it to the remote terminal.
        Unless an error occurs, this funcion will run forever.
        """
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
        """
        Continuously listen for output from the remote terminal in an infinite loop.
        When some output is received, then write it to the `writer` stream.
        Unless an error occurs, this funcion will run forever.
        """
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
        """
        Start a new shellinabox session and trigger `input_handler_task` and `output_handler_task`.
        Both tasks run in an infinite loop (asynchronously). So this function will `gather` both tasks.
        Unless an error occurs, this funcion will run forever.
        """
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
        """
        Take control over the remote shellinabox terminal.
        Returns two file descriptors `reader_fd`, `writer_fd`.
        Use `reader_fd` for receiving output from the remote terminal's stdout,
        and `writer_fd` for sending input to the remote terminal's stdin.
        """
        reader_fd, stdout_fd = os.pipe()
        stdin_fd, writer_fd = os.pipe()
        stdout = os.fdopen(stdout_fd, "w")
        stdin = os.fdopen(stdin_fd, "r")
        asyncio.create_task(self.run_forever(stdin=stdin, stdout=stdout))
        return reader_fd, writer_fd

    async def interact(self) -> None:
        """Start an interactive terminal shell"""
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
