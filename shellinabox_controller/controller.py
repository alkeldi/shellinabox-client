"""`ShellInABox` Controller Module"""
import os
import sys
import tty
import signal
import asyncio
import termios
import functools
import threading

import httpx

class ShellInABoxController():
    """
    `ShellInABox` Controller.

    Parameters
    ----------
    * **url** - URL of the remote `ShellInABox` instance.
    * **width** - *(optional)* Default terminal width.
    * **height** - *(optional)* Default terminal height.
    * **verify** - *(optional)* Enable/Disable SSL verification.
    * **client** - *(optional)* Use a custom HTTP client.
    """
    def __init__(
        self,
        url: str,
        width: int = 128,
        height: int = 32,
        verify: bool = True,
        client: httpx.AsyncClient = None,
    ) -> None:
        if not isinstance(verify, bool):
            raise ValueError("Argument `verify` must be of type `bool`.")
        if not isinstance(client, httpx.AsyncClient) and client is not None:
            raise ValueError("Argument `client` must be of type `httpx.AsyncClient`.")
        self._url = url
        self._width = width
        self._height = height
        self._client = client
        if self._client is None:
            self._client = httpx.AsyncClient(verify=verify)
        self._session = None
        self._running = False
        self._shared_lock = threading.Lock()

    def _internal_terminal_resize_signal_handler(self, loop: asyncio.AbstractEventLoop) -> None:
        terminal_size = os.get_terminal_size()
        loop.create_task(self._internal_update_terminal_size(
            width=terminal_size.columns,
            height=terminal_size.lines
        ))

    async def _internal_update_terminal_size(self, width: int, height: int) -> None:
        with self._shared_lock:
            self._width = width
            self._height = height
        if self._session is not None:
            response = await self._client.post(self._url, data={
                "width": self._width,
                "height": self._height,
                "session": self._session,
                "keys": "",
            })
            response.raise_for_status()

    async def _internal_input_handler_task(self, reader: asyncio.StreamReader) -> None:
        while True:
            data = await reader.read(128)
            if data == b"":
                await asyncio.sleep(0)
                continue
            response = await self._client.post(self._url, data={
                "width": self._width,
                "height": self._height,
                "session": self._session,
                "keys": data.hex(),
            })
            response.raise_for_status()

    async def _internal_output_handler_task(self, writer: asyncio.StreamWriter) -> None:
        while True:
            response = await self._client.post(self._url, timeout=None, data={
                "width": self._width,
                "height": self._height,
                "session": self._session,
            })
            response.raise_for_status()
            data: bytes = response.json()["data"].encode()
            writer.write(data)
            await writer.drain()

    async def _internal_run_forever(self, input_fd: int, output_fd: int) -> None:
        response = await self._client.post(self._url, data={
            "width": self._width,
            "height": self._height,
            "rooturl": self._url,
        })
        response.raise_for_status()
        self._session = response.json()["session"]
        output_file = os.fdopen(output_fd, "w")
        if input_fd != output_fd:
            input_file = os.fdopen(input_fd, "r")
        else:
            input_file = output_file
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, input_file)
        w_transport, w_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin,
            output_file
        )
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
        await asyncio.gather(
            self._internal_input_handler_task(reader),
            self._internal_output_handler_task(writer)
        )

    async def _internal_run_forever_interactive(self, input_fd: int, output_fd: int) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(
                signal.SIGWINCH,
                functools.partial(self._internal_terminal_resize_signal_handler, loop)
            )
            terminal_size = os.get_terminal_size()
            await self._internal_update_terminal_size(
                width=terminal_size.columns,
                height=terminal_size.lines
            )
        except RuntimeError:
            # NOTE: ignore errors if we can't register a terminal resize handler
            #       This normaly happens when running outside the main thread
            pass
        old_tty_settings = None
        try:
            old_tty_settings = termios.tcgetattr(input_fd)
            tty.setraw(input_fd)
            await self._internal_run_forever(input_fd=input_fd, output_fd=output_fd)
        finally:
            if old_tty_settings is not None:
                termios.tcsetattr(input_fd, termios.TCSADRAIN, old_tty_settings)

    async def run(self, input_fd: int = None, output_fd: int = None, interactive = False) -> None:
        """
        Run ShellInABox Controller

        Parameters
        ----------
        * **input_fd** - *(optional)* The controller's input file descriptor.
        If this value is `None`, then `sys.stdin.fileno()` is used as default.
        * **output_fd** - *(optional)* The controller's output file descriptor.
        If this value is `None`, then `sys.stdout.fileno()` is used as default.
        * **interactive** - *(optional)* Enable support for interactive terminals.
        This option is only valid when `input_fd` supports raw mode.
        """
        with self._shared_lock:
            if self._running:
                raise RuntimeError("Controller is already running")
            self._running = True
        if input_fd is None:
            input_fd = sys.stdin.fileno()
        if output_fd is None:
            output_fd = sys.stdout.fileno()
        if interactive:
            await self._internal_run_forever_interactive(input_fd=input_fd, output_fd=output_fd)
        else:
            await self._internal_run_forever(input_fd=input_fd, output_fd=output_fd)
