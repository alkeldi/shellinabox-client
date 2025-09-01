import argparse
import urllib3
from shellinabox_client import ShellInABoxTerminalClient

def main():
    # parse arguments
    parser = argparse.ArgumentParser(description="A ShellInABox Terminal Client")
    parser.add_argument("url", type=str, help="URL to a ShellInABox instance")
    parser.add_argument("--no-warnings", action='store_true', help="disable http security warnings")
    args = parser.parse_args()

    # disable warnnings
    if args.no_warnings:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # start terminal client
    terminal = ShellInABoxTerminalClient(url=args.url)
    terminal.start()

if __name__ == "__main__":
    main()
