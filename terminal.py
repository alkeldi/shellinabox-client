import sys
import httpx
import asyncio
import argparse
from shellinabox_controller import ShellInABoxController

async def main():
    # parse arguments
    parser = argparse.ArgumentParser(description="A ShellInABox Terminal Controller")
    parser.add_argument("url", type=str, help="URL to a ShellInABox instance")
    parser.add_argument("--no-verify", action='store_true', help="disable http security verifications")
    args = parser.parse_args()

    # create http client
    client = httpx.AsyncClient(verify=not args.no_verify)

    # create shellinabox controller
    controller = ShellInABoxController(url=args.url, client=client)

    # interact
    await controller.interact()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.HTTPStatusError as e:
        if e.response.status_code not in [400, 500]:
            sys.stderr.write(f"Error: HTTP Error {e.response.status_code}\n")
            sys.stderr.flush()
            sys.exit(1)
    except httpx.ConnectError as e:
        msg = str(e)
        if len(msg) > 0:
            print(f"Error: {msg}")
        else:
            print(f"Error: Connection error")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
