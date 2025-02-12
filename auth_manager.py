from auth_methods.password_auth import PasswordAuth
from auth_methods.google_auth import GoogleAuth
from auth_methods.otp_auth import OTPAuth

class AuthManager:
    def __init__(self):
        self.auth_methods = {
            "password": PasswordAuth(),
            "google": GoogleAuth(),
            "otp": OTPAuth(),
        }

    def authenticate(self, method: str, *args, **kwargs):
        auth_method = self.auth_methods.get(method)
        if not auth_method:
            raise ValueError(f"Authentication method {method} not supported")
        return auth_method.authenticate(*args, **kwargs) 