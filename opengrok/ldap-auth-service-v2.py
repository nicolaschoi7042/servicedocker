#!/usr/bin/env python3
"""
Enhanced LDAP Authentication Service for OpenGrok
- Web-based login page instead of Basic Auth popup
- Session management with 12-hour timeout
- Cookie-based authentication
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, make_response
import ldap
import base64
import logging
import os
import jwt
import datetime
from functools import wraps
import secrets

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
LDAP_SERVER = os.getenv('LDAP_SERVER', 'ldap://openldap:389')
LDAP_BASE_DN = os.getenv('LDAP_BASE_DN', 'dc=roboetech,dc=com')
LDAP_USER_BASE = os.getenv('LDAP_USER_BASE', 'ou=users,dc=roboetech,dc=com')
LDAP_GROUP_BASE = os.getenv('LDAP_GROUP_BASE', 'ou=groups,dc=roboetech,dc=com')
LDAP_BIND_DN = os.getenv('LDAP_BIND_DN', 'cn=admin,dc=roboetech,dc=com')
LDAP_BIND_PASSWORD = os.getenv('LDAP_BIND_PASSWORD', 'admin')

# Session configuration - 2 hours
SESSION_TIMEOUT_HOURS = 2
JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_urlsafe(32))
COOKIE_NAME = 'opengrok_session'

# HTML Templates
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenGrok 로그인 - Roboetech</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            width: 400px;
            max-width: 90%;
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .logo p {
            color: #666;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .login-button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        
        .login-button:hover {
            transform: translateY(-2px);
        }
        
        .login-button:active {
            transform: translateY(0);
        }
        
        .error-message {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #c33;
        }
        
        .info-message {
            background: #e8f4f8;
            color: #0066cc;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #0066cc;
            font-size: 13px;
            line-height: 1.5;
        }
        
        .info-message strong {
            font-size: 14px;
            display: block;
            margin-bottom: 8px;
        }
        
        .info-message ul {
            margin: 0;
            padding-left: 18px;
        }
        
        .info-message li {
            margin-bottom: 4px;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #888;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>OpenGrok</h1>
            <p>Roboetech Code Search Platform</p>
        </div>
        
        <div class="info-message">
            <strong>로그인 안내</strong>
            <ul>
                <li>사용자 ID: 본인의 이메일 ID</li>
                <li>초기 비밀번호: (Gerrit 로그인 암호)</li>
            </ul>
        </div>
        
        {% if error %}
        <div class="error-message">
            {{ error }}
        </div>
        {% endif %}
        
        {% if info %}
        <div class="info-message">
            {{ info }}
        </div>
        {% endif %}
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="username">사용자명</label>
                <input type="text" id="username" name="username" required 
                       placeholder="LDAP 사용자명을 입력하세요" value="{{ username or '' }}">
            </div>
            
            <div class="form-group">
                <label for="password">비밀번호</label>
                <input type="password" id="password" name="password" required 
                       placeholder="비밀번호를 입력하세요">
            </div>
            
            <button type="submit" class="login-button">로그인</button>
        </form>
        
        <div class="footer">
            <p>세션은 2시간 후 자동으로 만료됩니다.</p>
        </div>
    </div>
</body>
</html>
'''

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
            return True, {
                "username": username, 
                "dn": user_dn, 
                "attributes": user_attributes,
                "cn": user_attributes.get('cn', [b''])[0].decode('utf-8') if user_attributes.get('cn') else username
            }
            
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

def create_session_token(user_info):
    """Create JWT token for session"""
    payload = {
        'username': user_info['username'],
        'cn': user_info.get('cn', user_info['username']),
        'dn': user_info['dn'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=SESSION_TIMEOUT_HOURS),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_session_token(token):
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Session expired"
    except jwt.InvalidTokenError:
        return False, "Invalid session"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Web-based login page"""
    if request.method == 'GET':
        # Check if user is already logged in
        session_token = request.cookies.get(COOKIE_NAME)
        if session_token:
            valid, payload = verify_session_token(session_token)
            if valid:
                # Already logged in, redirect to original URL or OpenGrok
                redirect_url = request.args.get('redirect', 'https://opengrok.roboetech.com')
                return redirect(redirect_url)
        
        # Show login form
        return render_template_string(LOGIN_TEMPLATE)
    
    # POST request - process login
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        return render_template_string(LOGIN_TEMPLATE, 
                                    error="사용자명과 비밀번호를 모두 입력해주세요.", 
                                    username=username)
    
    # Authenticate against LDAP
    success, result = authenticate_ldap(username, password)
    
    if success:
        # Create session token
        session_token = create_session_token(result)
        
        # Create response with redirect
        redirect_url = request.args.get('redirect', 'https://opengrok.roboetech.com')
        response = make_response(redirect(redirect_url))
        
        # Set secure cookie with session token
        response.set_cookie(
            COOKIE_NAME,
            session_token,
            max_age=SESSION_TIMEOUT_HOURS * 3600,  # 12 hours in seconds
            httponly=True,
            secure=True,  # HTTPS only
            samesite='Lax'
        )
        
        app.logger.info(f"Login successful for {username}, redirecting to {redirect_url}")
        return response
    else:
        app.logger.info(f"Login failed for {username}: {result}")
        return render_template_string(LOGIN_TEMPLATE, 
                                    error="로그인에 실패했습니다. 사용자명과 비밀번호를 확인해주세요.", 
                                    username=username)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logout and clear session"""
    response = make_response(render_template_string(LOGIN_TEMPLATE, 
                                                  info="로그아웃되었습니다. 다시 로그인해주세요."))
    response.set_cookie(COOKIE_NAME, '', expires=0)
    return response

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    """
    nginx auth_request endpoint - now uses session cookies instead of Basic Auth
    """
    # Check for session cookie
    session_token = request.cookies.get(COOKIE_NAME)
    
    if not session_token:
        app.logger.info("No session cookie found")
        return jsonify({"error": "Authentication required"}), 401
    
    # Verify session token
    valid, result = verify_session_token(session_token)
    
    if not valid:
        app.logger.info(f"Invalid session: {result}")
        return jsonify({"error": "Session invalid", "detail": result}), 401
    
    # Valid session - return user info in headers for nginx
    response = make_response(jsonify({"status": "authenticated", "user": result['username']}))
    response.headers['X-Auth-User'] = result['username']
    response.headers['X-Auth-Status'] = 'OK'
    
    if 'dn' in result:
        # URL encode the DN to handle Korean characters safely
        import urllib.parse
        encoded_dn = urllib.parse.quote(result['dn'], safe='')
        response.headers['X-Auth-DN'] = encoded_dn
    
    app.logger.info(f"Authentication successful for {result['username']} via session")
    return response, 200

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
        return jsonify({
            "status": "healthy", 
            "ldap": "connected",
            "session_timeout": f"{SESSION_TIMEOUT_HOURS} hours"
        }), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Service info endpoint"""
    return jsonify({
        "service": "OpenGrok Enhanced LDAP Authentication Service",
        "version": "2.0",
        "features": [
            "Web-based login page",
            "Session-based authentication",
            f"{SESSION_TIMEOUT_HOURS}-hour session timeout",
            "Korean character support"
        ],
        "endpoints": {
            "/login": "Web login page",
            "/logout": "Logout and clear session", 
            "/auth": "nginx auth_request endpoint",
            "/validate": "direct credential validation",
            "/health": "health check"
        },
        "ldap_server": LDAP_SERVER,
        "user_base": LDAP_USER_BASE,
        "session_timeout_hours": SESSION_TIMEOUT_HOURS
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)