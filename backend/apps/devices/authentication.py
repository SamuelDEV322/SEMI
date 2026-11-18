import hashlib
import hmac
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Device


class DevicePrincipal:
    is_authenticated = True

    def __init__(self, device):
        self.device = device


class DeviceAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Device"

    def authenticate(self, request):
        identity = request.headers.get("X-SEMI-Device-ID", "")
        supplied = request.headers.get("X-SEMI-Device-Token", "")
        expected = settings.SEMI_DEVICE_TOKENS.get(identity)
        device = (
            Device.objects.filter(device_id=identity, enabled=True).first()
            if len(identity) <= 64
            else None
        )
        valid = (
            hmac.compare_digest(
                hashlib.sha256(supplied.encode()).digest(),
                hashlib.sha256((expected or "").encode()).digest(),
            )
            if len(supplied) <= 512
            else False
        )
        if not device or not expected or not supplied or not valid:
            raise AuthenticationFailed(
                "Credenciales de dispositivo inválidas.", code="device_auth_failed"
            )
        return DevicePrincipal(device), device
