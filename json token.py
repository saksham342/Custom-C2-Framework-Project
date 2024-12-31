import jwt
import datetime
import os

# Secret key should be kept private and ideally stored in an environment variable
SECRET_KEY = os.urandom(32)  # Generates a random 32-byte secret key

# JWT Header
header = {
    'alg': 'HS256',  # Algorithm used to sign the token
    'typ': 'JWT'     # Type of the token
}

# Payload with the user role as 'superadmin'
payload = {
    'user': {
        'role': 'superadmin'
    },
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # Token expires in 1 hour
    'iat': datetime.datetime.utcnow()  # Issued at time
}

# Generate the JWT token using HS256 algorithm and including the header
encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm='HS256', headers=header)

print("JWT Token:", encoded_jwt)
