# Python Controller for `ShellInABox`
This is a python controller to access `ShellInABox` programmatically or using a terminal emulator.

## Getting Started
You can import this package and programmatically interact with the `ShellInABox` instance. Alternatively, you can use this project to access the remote `ShellInABox` instance from your local terminal.

### Prepare the `python` Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interactive Terminal
```bash
python terminal.py --no-verify <url>
```
Replace `<url>` with your actual `ShellInABox` URL. Note that `--no-verify` is used to disable http security verifications.
You can run `make container` to bringup a `ShellInABox` docker container at https://localhost:5555

### Example 1: Using in synchronous code (Separate Thread)
```python
import asyncio
import threading
from shellinabox_controller import ShellInABoxController

def main():
    controller = ShellInABoxController("https://localhost:5555/", verify=False)
    controller_thread = threading.Thread(
        target=asyncio.run,
        args=(controller.run(interactive=True),)
    )
    controller_thread.start()
    print("You can do other stuff here, like printing this message")
    controller_thread.join()

if __name__ == "__main__":
    main()

```

### Example 2: Using in synchronous code (Same Thread)
```python
import asyncio
from shellinabox_controller import ShellInABoxController

def main():
    controller = ShellInABoxController("https://localhost:5555/", verify=False)
    asyncio.run(controller.run(interactive=True))
    print("This will not be printed")

if __name__ == "__main__":
    main()

```

### Example 3: Using in asynchronous code
```python
import asyncio
from shellinabox_controller import ShellInABoxController

async def main():
    controller = ShellInABoxController("https://localhost:5555/", verify=False)
    await controller.run(interactive=True)

if __name__ == "__main__":
    asyncio.run(main())

```

### Example 4: Integration with `pexpect`
```python
import os
import asyncio
import pexpect.fdpexpect
from shellinabox_controller import ShellInABoxController

async def main():
    # create pipes
    reader_fd, output_fd = os.pipe()
    input_fd, writer_fd = os.pipe()

    # create shellinabox controller
    controller = ShellInABoxController("https://localhost:5555/", verify=False)
    asyncio.create_task(controller.run(input_fd=input_fd, output_fd=output_fd))

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

### Testing - Starting up `ShellInABox` in Docker
The following commands will bringup a docker container and run `ShellInABox` at https://localhost:5555/. The username and password for the container are both `root`.
```bash
# On the docker host (keep it running)
make container
```
**Alternatively, you can run the container manually as following:**
```bash
# On the docker host (keep it running)
docker run --name shellinabox --rm -it -p 5555:5555 ubuntu bash
```

```bash
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
```bash
python terminal.py https://localhost:5555 --no-verify
```
