import os
import json
import logging
from datetime import datetime, timedelta
import streamlit as st
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
import extra_streamlit_components as stx
from dotenv import load_dotenv
import httpx
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class Auth0Management:
    def __init__(self):
        """Initialize Auth0 authentication"""
        self.auth0_client_id = st.secrets.get("AUTH0_CLIENT_ID", os.getenv("AUTH0_CLIENT_ID"))
        self.auth0_client_secret = st.secrets.get("AUTH0_CLIENT_SECRET", os.getenv("AUTH0_CLIENT_SECRET"))
        self.auth0_domain = st.secrets.get("AUTH0_DOMAIN", os.getenv("AUTH0_DOMAIN"))
        self.auth0_callback_url = st.secrets.get("AUTH0_CALLBACK_URL", os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8501/"))
        
        self.config_valid = all([self.auth0_client_id, self.auth0_client_secret, self.auth0_domain])
        
        if self.config_valid:
            logger.info(f"Auth0 configuration valid. Domain: {self.auth0_domain}, Callback URL: {self.auth0_callback_url}")
        else:
            missing = []
            if not self.auth0_client_id:
                missing.append("AUTH0_CLIENT_ID")
            if not self.auth0_client_secret:
                missing.append("AUTH0_CLIENT_SECRET")
            if not self.auth0_domain:
                missing.append("AUTH0_DOMAIN")
            logger.error(f"Auth0 configuration incomplete. Missing: {', '.join(missing)}")
            return
            
        try:
            self.oauth = OAuth()
            self.oauth.register(
                "auth0",
                client_id=self.auth0_client_id,
                client_secret=self.auth0_client_secret,
                client_kwargs={
                    "scope": "openid profile email"
                },
                server_metadata_url=f"https://{self.auth0_domain}/.well-known/openid-configuration"
            )
            logger.info("Auth0 OAuth client registered successfully")
        except Exception as e:
            logger.error(f"Error initializing Auth0: {str(e)}")
            self.config_valid = False

    def get_login_url(self):
        """Get the Auth0 login URL"""
        if not self.config_valid:
            return None
        encoded_callback = quote_plus(self.auth0_callback_url)
        state = os.urandom(16).hex()
        st.session_state.auth0_state = state
        
        login_url = (f"https://{self.auth0_domain}/authorize?"
                    f"response_type=code&"
                    f"client_id={self.auth0_client_id}&"
                    f"redirect_uri={encoded_callback}&"
                    f"state={state}&"
                    f"scope=openid%20profile%20email")
        
        logger.info(f"Login URL generated: {login_url[:50]}...")
        return login_url

    def get_logout_url(self):
        """Get the Auth0 logout URL"""
        if not self.config_valid:
            return None
        encoded_return_to = quote_plus(self.auth0_callback_url)
        return f"https://{self.auth0_domain}/v2/logout?client_id={self.auth0_client_id}&returnTo={encoded_return_to}"
    
    def handle_callback(self, code):
        """Handle the Auth0 callback after login"""
        if not self.config_valid or not code:
            logger.error("Cannot handle callback: invalid configuration or missing code")
            return None
            
        try:
            logger.info("Handling Auth0 callback...")
            
            token_url = f"https://{self.auth0_domain}/oauth/token"

            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.auth0_client_id,
                "client_secret": self.auth0_client_secret,
                "code": code,
                "redirect_uri": self.auth0_callback_url
            }
            
            logger.info(f"Sending token request to {token_url}")
            logger.info(f"Using callback URL: {self.auth0_callback_url}")
            
            with httpx.Client(timeout=30.0) as client:
                headers = {"Content-Type": "application/json"}
                response = client.post(token_url, json=token_data, headers=headers)
                
                if not response.is_success:
                    logger.error(f"Token request failed: {response.status_code} - {response.text}")
                    return None
                
                token_info = response.json()
                logger.info("Token received successfully")
                
                if "access_token" in token_info:
                    user_info_url = f"https://{self.auth0_domain}/userinfo"
                    headers = {"Authorization": f"Bearer {token_info['access_token']}"}
                    
                    logger.info(f"Requesting user info from {user_info_url}")
                    user_response = client.get(user_info_url, headers=headers)
                    
                    if not user_response.is_success:
                        logger.error(f"User info request failed: {user_response.status_code} - {user_response.text}")
                        return None
                    
                    user_info = user_response.json()
                    logger.info(f"User info received for: {user_info.get('email', 'unknown')}")
                    return user_info
                else:
                    logger.error("No access token found in Auth0 response")
                    if "error" in token_info:
                        logger.error(f"Auth0 error: {token_info.get('error')} - {token_info.get('error_description')}")
                    return None
                
        except Exception as e:
            logger.error(f"Error in Auth0 callback: {str(e)}")
            return None


def create_cookie_manager():
    """Create and return a cookie manager for session handling"""
    return stx.CookieManager()


def get_auth_status():
    """Check if the user is authenticated"""
    if "auth_user" not in st.session_state:
        cookie_manager = create_cookie_manager()
        auth_cookie = cookie_manager.get("auth_token")
        
        if auth_cookie:
            try:
                auth_data = json.loads(auth_cookie)
                expiry_time = datetime.fromisoformat(auth_data.get("expiry", "2000-01-01"))
                
                if datetime.now() < expiry_time:
                    st.session_state.auth_user = auth_data.get("user")
                    return True
            except Exception as e:
                logger.error(f"Error reading auth cookie: {str(e)}")
                pass
        return False
    return True


def set_auth_cookie(user_data):
    """Set authentication cookie"""
    if user_data:
        cookie_manager = create_cookie_manager()
        expiry_time = datetime.now() + timedelta(days=7)
        
        auth_data = {
            "user": user_data,
            "expiry": expiry_time.isoformat()
        }
        
        cookie_manager.set("auth_token", json.dumps(auth_data), expires_at=expiry_time)
        st.session_state.auth_user = user_data
        logger.info(f"Authentication cookie set for user: {user_data.get('email', 'unknown')}")


def clear_auth():
    """Clear authentication data"""
    if "auth_user" in st.session_state:
        logger.info(f"Logging out user: {st.session_state.auth_user.get('email', 'unknown')}")
        del st.session_state.auth_user
    
    cookie_manager = create_cookie_manager()
    cookie_manager.delete("auth_token")
    logger.info("Auth cookie deleted")


def require_auth():
    """Require authentication to access a page"""
    if not get_auth_status():
        st.error("Please log in to access this feature")
        auth = Auth0Management()
        
        if auth.config_valid:
            login_url = auth.get_login_url()
            st.markdown(f"[Login with Auth0]({login_url})")
        else:
            st.error("Auth0 is not properly configured. Please check your settings.")
            
        st.stop()