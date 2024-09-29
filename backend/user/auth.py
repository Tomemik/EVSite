from django.conf import settings
from knox.auth import TokenAuthentication
from knox.settings import knox_settings
from rest_framework import HTTP_HEADER_ENCODING, exceptions


class CustomHeaderTokenAuthentication(TokenAuthentication):
    def get_authorization_header(self, request):
        http_header = f"HTTP_{settings.API_HEADER}"
        auth = request.META.get(http_header, b"")
        if isinstance(auth, str):
            auth = auth.encode(HTTP_HEADER_ENCODING)
        return auth

    def authenticate(self, request):
        auth = self.get_authorization_header(request).split()
        prefix = knox_settings.AUTH_HEADER_PREFIX.encode()

        if not auth:
            return None
        if auth[0].lower() != prefix.lower():
            return None
        if len(auth) == 1:
            msg = "Invalid token header. No credentials provided."
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = "Invalid token header. Token string should not contain spaces."
            raise exceptions.AuthenticationFailed(msg)

        user, auth_token = self.authenticate_credentials(auth[1])
        return (user, auth_token)
