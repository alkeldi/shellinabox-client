# Python Client for ShellInABox
This is a python client to access ShellInABox programmatically or using a terminal emulator.

## Getting Started
You can import this package and programmatically interact with the ShellInABox server. Alternatively, you can use the included terminal client to access the remote server from your local terminal.

### Prepare the `python` Environment
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Terminal Client
```
% python terminal.py <url>
```

### Integration with pexpect
```python
import os
import urllib3
import requests
import pexpect.fdpexpect
from shellinabox_client import ShellInABoxClient

# create http session
session = requests.Session()
session.verify = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# create pipes
reader_fd, stdout_fd = os.pipe()
stdin_fd, writer_fd = os.pipe()
stdout = os.fdopen(stdout_fd, "w")
stdin = os.fdopen(stdin_fd, "r")
reader = os.fdopen(reader_fd, "r")
writer = os.fdopen(writer_fd, "w")

# create shellinabox client
client = ShellInABoxClient(url="https://localhost:5555/", session=session)
client.start(stdout=stdout, stdin=stdin)

# use with pexpect
child = pexpect.fdpexpect.fdspawn(reader.fileno())
username = "root"
password = "root"
command = "ls /"
child.expect("login")
writer.write(f"{username}\n")
writer.flush()
child.expect("Password")
writer.write(f"{password}\n")
writer.flush()
child.expect("# ")
writer.write(f"{command}\n")
writer.flush()
child.expect("# ")
output = child.before.decode("utf-8")
print(output[len(command) + 2:])

# cleanup
client.stop()
reader.close()
writer.close()
stdout.close()
stdin.close()
```

### Testing - Using ShellInABox in Docker
The following commands will bringup a docker container and run shellinabox at https://localhost:5555/. The username and password for the container are both `root`.
```
# On the docker host
docker run --rm -it -p 5555:5555 ubuntu bash

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
