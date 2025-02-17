import os
from flask import Flask, redirect, url_for, render_template, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import jwt
import datetime
from functools import wraps
from dotenv import load_dotenv

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



def generate_jwt(role):
    """Generate a JWT for a given user role."""
    header = {
        'alg': 'HS256',  # Algorithm used to sign the token
        'typ': 'JWT'     # Type of the token
    }

    payload = {
        'user': {
            'role': role
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
            
            token = generate_jwt(user_object.role)

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
