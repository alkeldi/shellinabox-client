"""A ShellInABox Remote Terminal"""
import sys
import asyncio
import argparse

import httpx
from shellinabox_controller import ShellInABoxController

async def main():
    """Proram Entrypoint"""
    # parse arguments
    parser = argparse.ArgumentParser(description="A ShellInABox Remote Terminal")
    parser.add_argument(
        "url",
        type=str,
        help="URL to a ShellInABox instance"
    )
    parser.add_argument(
        "--no-verify",
        action='store_true',
        help="disable http security verifications"
    )
    args = parser.parse_args()

    # create http client
    client = httpx.AsyncClient(verify=not args.no_verify)

    # create shellinabox controller
    controller = ShellInABoxController(url=args.url, client=client)

    # interact
    await controller.run(interactive=True)


if __name__ == "__main__":
    try:
        ERROR = None
        asyncio.run(main())
    except httpx.HTTPStatusError as e:
        if e.response.status_code not in [400, 500]:
            ERROR = f"HTTP Error {e.response.status_code}"
    except httpx.ConnectError as e:
        ERROR = str(e)
        if len(ERROR) == 0:
            ERROR = "Connection Error"
    finally:
        if ERROR is not None:
            sys.stderr.write(f"Error: {ERROR}\n")
            sys.stderr.flush()
            sys.exit(1)
