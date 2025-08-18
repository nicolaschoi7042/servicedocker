#!/usr/bin/env python3
"""
LDAP Authentication Service for OpenGrok
Validates HTTP Basic Auth credentials against OpenLDAP server
"""

from flask import Flask, request, jsonify
import ldap
import base64
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# LDAP Configuration
LDAP_SERVER = os.getenv('LDAP_SERVER', 'ldap://openldap:389')
LDAP_BASE_DN = os.getenv('LDAP_BASE_DN', 'dc=roboetech,dc=com')
LDAP_USER_BASE = os.getenv('LDAP_USER_BASE', 'ou=users,dc=roboetech,dc=com')
LDAP_GROUP_BASE = os.getenv('LDAP_GROUP_BASE', 'ou=groups,dc=roboetech,dc=com')
LDAP_BIND_DN = os.getenv('LDAP_BIND_DN', 'cn=admin,dc=roboetech,dc=com')
LDAP_BIND_PASSWORD = os.getenv('LDAP_BIND_PASSWORD', 'admin')

def authenticate_ldap(username, password):
    """Authenticate user against LDAP server"""
    try:
        # Connect to LDAP server
        conn = ldap.initialize(LDAP_SERVER)
        conn.protocol_version = ldap.VERSION3
        conn.set_option(ldap.OPT_REFERRALS, 0)
        
        # Bind with admin credentials to search for user
        conn.simple_bind_s(LDAP_BIND_DN, LDAP_BIND_PASSWORD)
        
        # Search for user
        search_filter = f"(&(objectClass=person)(uid={username}))"
        result = conn.search_s(LDAP_USER_BASE, ldap.SCOPE_SUBTREE, search_filter, ['cn', 'mail'])
        
        if not result:
            app.logger.info(f"User {username} not found in LDAP")
            return False, "User not found"
            
        user_dn = result[0][0]
        user_attributes = result[0][1]
        
        app.logger.info(f"Found user: {user_dn}")
        
        # Try to bind as the user to verify password
        try:
            user_conn = ldap.initialize(LDAP_SERVER)
            user_conn.protocol_version = ldap.VERSION3
            user_conn.simple_bind_s(user_dn, password)
            user_conn.unbind_s()
            
            app.logger.info(f"Authentication successful for {username}")
            return True, {"username": username, "dn": user_dn, "attributes": user_attributes}
            
        except ldap.INVALID_CREDENTIALS:
            app.logger.info(f"Invalid password for {username}")
            return False, "Invalid credentials"
            
    except ldap.LDAPError as e:
        app.logger.error(f"LDAP Error: {e}")
        return False, f"LDAP Error: {e}"
    except Exception as e:
        app.logger.error(f"Authentication Error: {e}")
        return False, f"Error: {e}"
    finally:
        try:
            conn.unbind_s()
        except:
            pass

def parse_basic_auth(auth_header):
    """Parse HTTP Basic Auth header"""
    if not auth_header or not auth_header.startswith('Basic '):
        return None, None
    
    try:
        encoded_credentials = auth_header[6:]  # Remove 'Basic '
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)
        return username, password
    except Exception as e:
        app.logger.error(f"Error parsing auth header: {e}")
        return None, None

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    """
    nginx auth_request endpoint
    Returns 200 for valid auth, 401/403 for invalid
    """
    # Get Authorization header
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        app.logger.info("No Authorization header provided")
        return jsonify({"error": "Authorization required"}), 401
    
    # Parse Basic Auth
    username, password = parse_basic_auth(auth_header)
    
    if not username or not password:
        app.logger.info("Invalid Authorization header format")
        return jsonify({"error": "Invalid authorization format"}), 401
    
    # Authenticate against LDAP
    success, result = authenticate_ldap(username, password)
    
    if success:
        # Return 200 with user info in headers for nginx
        response = jsonify({"status": "authenticated", "user": username})
        response.headers['X-Auth-User'] = username
        response.headers['X-Auth-Status'] = 'OK'
        if isinstance(result, dict) and 'dn' in result:
            # URL encode the DN to handle Korean characters safely
            import urllib.parse
            encoded_dn = urllib.parse.quote(result['dn'], safe='')
            response.headers['X-Auth-DN'] = encoded_dn
        return response, 200
    else:
        app.logger.info(f"Authentication failed for {username}: {result}")
        return jsonify({"error": "Authentication failed", "detail": result}), 401

@app.route('/validate', methods=['POST'])
def validate():
    """
    Alternative validation endpoint for direct credential checking
    """
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password required"}), 400
    
    username = data['username']
    password = data['password']
    
    success, result = authenticate_ldap(username, password)
    
    if success:
        return jsonify({"status": "valid", "user": username, "result": result}), 200
    else:
        return jsonify({"status": "invalid", "error": result}), 401

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test LDAP connection
        conn = ldap.initialize(LDAP_SERVER)
        conn.simple_bind_s(LDAP_BIND_DN, LDAP_BIND_PASSWORD)
        conn.unbind_s()
        return jsonify({"status": "healthy", "ldap": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Service info endpoint"""
    return jsonify({
        "service": "OpenGrok LDAP Authentication Service",
        "version": "1.0",
        "endpoints": {
            "/auth": "nginx auth_request endpoint",
            "/validate": "direct credential validation",
            "/health": "health check"
        },
        "ldap_server": LDAP_SERVER,
        "user_base": LDAP_USER_BASE
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)