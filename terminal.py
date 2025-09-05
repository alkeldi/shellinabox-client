import sys
import urllib3
import requests
import argparse
from shellinabox_client import ShellInABoxClient

def main():
    # parse arguments
    parser = argparse.ArgumentParser(description="A ShellInABox Terminal Emulator")
    parser.add_argument("url", type=str, help="URL to a ShellInABox instance")
    parser.add_argument("--no-verify", action='store_true', help="disable http security verifications")
    args = parser.parse_args()

    # disable warnnings
    if args.no_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # create http session
    session = requests.Session()
    session.verify = not args.no_verify

    # create shellinabox client
    client = ShellInABoxClient(url=args.url, session=session)

    # interact
    client.interact()


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError as e:
        error: Exception =  e
        while hasattr(error, "args"):
            error_args = getattr(error, "args")
            if len(error_args) == 0:
                break
            error = error_args[0]
            if hasattr(error, "reason"):
                error = getattr(error, "reason")
                break
        message = str(error)
        if isinstance(error, urllib3.exceptions.NewConnectionError):
            actual_error: urllib3.exceptions.NewConnectionError = error
            message = actual_error._message.split(": ", 1)[0]
        sys.stderr.write(f"Error: {message}\n")
        sys.stderr.flush()
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code not in [400]:
            sys.stderr.write(f"Error: HTTP Error {e.response.status_code}\n")
            sys.stderr.flush()
            sys.exit(1)
