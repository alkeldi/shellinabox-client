# Python Controller for ShellInABox
This is a python controller to access ShellInABox programmatically or using a terminal emulator.

## Getting Started
You can import this package and programmatically interact with the ShellInABox server. Alternatively, you can use this project to access the remote ShellInABox server from your local terminal.

### Prepare the `python` Environment
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interactive Terminal
```
% python terminal.py <url>
```

### Integration with pexpect
```python
import os
import httpx
import asyncio
import pexpect.fdpexpect
from shellinabox_controller import ShellInABoxController

async def main():
    # create http client
    client = httpx.AsyncClient(verify=False)

    # create shellinabox controller
    controller = ShellInABoxController(url="https://localhost:5555/", client=client)
    reader_fd, writer_fd = await controller.control()

    # connect the shellinabox controller to pexpect
    writer = os.fdopen(writer_fd, "bw", buffering=0)
    child = pexpect.fdpexpect.fdspawn(reader_fd)

    # use pexpect
    username = "root"
    password = "root"
    command = "ls /"
    await child.expect("login", async_=True)
    writer.write(f"{username}\n".encode())
    await child.expect("Password", async_=True)
    writer.write(f"{password}\n".encode())
    await child.expect("# ", async_=True)
    writer.write(f"{command}\n".encode())
    await child.expect("# ", async_=True)
    output = child.before.decode("utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
```

### Testing - Using ShellInABox in Docker
The following commands will bringup a docker container and run shellinabox at https://localhost:5555/. The username and password for the container are both `root`.
```
make container
```
Or you can run the container manually
```
# On the docker host
docker run --name shellinabox --rm -it -p 5555:5555 ubuntu bash

# Inside the docker container
echo "root:root" | chpasswd
apt update
apt install -y openssl shellinabox
/usr/bin/shellinaboxd \
    --debug \
    --no-beep \
    --disable-peer-check \
    -u shellinabox \
    -g shellinabox \
    -c /var/lib/shellinabox \
    -p 5555
```

Then, we can try this project by running
```
python terminal.py https://localhost:5555 --no-verify
```
