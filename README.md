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
% python main.py <url>
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
python main.py https://localhost:5555 --no-warnings
```
