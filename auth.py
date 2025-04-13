import os
import json
from datetime import datetime, timedelta
import streamlit as st
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
import extra_streamlit_components as stx
from dotenv import load_dotenv
import httpx
from urllib.parse import quote_plus

load_dotenv()

class Auth0Management:
    def __init__(self):
        """Initialize Auth0 authentication"""
        self.auth0_client_id = st.secrets.get("AUTH0_CLIENT_ID", os.getenv("AUTH0_CLIENT_ID"))
        self.auth0_client_secret = st.secrets.get("AUTH0_CLIENT_SECRET", os.getenv("AUTH0_CLIENT_SECRET"))
        self.auth0_domain = st.secrets.get("AUTH0_DOMAIN", os.getenv("AUTH0_DOMAIN"))
        self.auth0_callback_url = st.secrets.get("AUTH0_CALLBACK_URL", os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8501/"))
        
        self.config_valid = all([self.auth0_client_id, self.auth0_client_secret, self.auth0_domain])
        
        if not self.config_valid:
            print("Auth0 configuration incomplete. Some required credentials are missing.")
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
        except Exception as e:
            print(f"Error initializing Auth0: {str(e)}")
            self.config_valid = False

    def get_login_url(self):
        """Get the Auth0 login URL"""
        if not self.config_valid:
            return None
        encoded_callback = quote_plus(self.auth0_callback_url)
        return f"https://{self.auth0_domain}/authorize?response_type=code&client_id={self.auth0_client_id}&redirect_uri={encoded_callback}&scope=openid%20profile%20email"

    def get_logout_url(self):
        """Get the Auth0 logout URL"""
        if not self.config_valid:
            return None
        encoded_return_to = quote_plus(self.auth0_callback_url)
        return f"https://{self.auth0_domain}/v2/logout?client_id={self.auth0_client_id}&returnTo={encoded_return_to}"
    
    def handle_callback(self, code):
        """Handle the Auth0 callback after login"""
        if not self.config_valid or not code:
            return None
            
        try:
            token_url = f"https://{self.auth0_domain}/oauth/token"
            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.auth0_client_id,
                "client_secret": self.auth0_client_secret,
                "code": code,
                "redirect_uri": self.auth0_callback_url
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(token_url, data=token_data)
                response.raise_for_status()
                
                token_info = response.json()
                
                if "id_token" in token_info:
                    user_info_url = f"https://{self.auth0_domain}/userinfo"
                    headers = {"Authorization": f"Bearer {token_info['access_token']}"}
                    user_response = client.get(user_info_url, headers=headers)
                    user_response.raise_for_status()
                    
                    user_info = user_response.json()
                    return user_info
                else:
                    print("ID token not found in Auth0 response")
                    return None
                
        except OAuthError as e:
            print(f"OAuth Error: {str(e)}")
            return None
        except Exception as e:
            print(f"Error in Auth0 callback: {str(e)}")
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
            except:
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


def clear_auth():
    """Clear authentication data"""
    if "auth_user" in st.session_state:
        del st.session_state.auth_user
    cookie_manager = create_cookie_manager()
    cookie_manager.delete("auth_token")


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