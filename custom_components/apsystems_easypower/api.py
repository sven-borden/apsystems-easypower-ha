"""AP Systems EasyPower Cloud API client."""
from __future__ import annotations

import base64
import logging
import os
import random
import re

import aiohttp

from .const import API_APP_ID, API_APP_SECRET, API_BASE_URL, RSA_PUBLIC_KEY_B64

_LOGGER = logging.getLogger(__name__)


def _rsa_encrypt(data: str) -> str:
    """Encrypt data with RSA public key (PKCS1v15 padding), return base64."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

    key_b64 = re.sub(r"\s+", "", RSA_PUBLIC_KEY_B64)
    key_der = base64.b64decode(key_b64)
    public_key = serialization.load_der_public_key(key_der)
    encrypted = public_key.encrypt(data.encode("utf-8"), asym_padding.PKCS1v15())
    return base64.b64encode(encrypted).decode("utf-8")


def _aes_encrypt_hex(data: str, key: str, iv: str) -> str:
    """Encrypt data with AES-256-CBC, zero-padded, return HEX (matches APK z4.a.a encoding)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    # Key: use raw bytes of the key string (32-char hex string → 32 bytes = AES-256)
    key_bytes = key.encode("utf-8")
    if len(key_bytes) < 16:
        key_bytes = key_bytes + b"0" * (16 - len(key_bytes))

    iv_bytes = iv.encode("utf-8")[:16]

    data_bytes = data.encode("utf-8")
    # Always pad to next block boundary (Java: len + blockSize - len%blockSize)
    padding_len = 16 - (len(data_bytes) % 16)
    data_bytes = data_bytes + b"\x00" * padding_len

    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(data_bytes) + encryptor.finalize()
    # Return HEX-encoded (matches APK y4.e.a(z4.a.a(...)))
    return encrypted.hex()


def _prepare_login_params(username: str, password: str) -> dict:
    """Prepare encrypted login parameters exactly as the APK does (S0.c.b())."""
    # Generate 16 random bytes, hex-encode → 32-char hex string
    aes_key = os.urandom(16).hex()
    # Generate random 16-digit version string
    version = f"{int(random.random() * 10**16):016d}"

    return {
        "app_id": API_APP_ID,
        "app_secret": API_APP_SECRET,
        "key": _rsa_encrypt(aes_key),
        "version": _rsa_encrypt(version),
        "username": _aes_encrypt_hex(username, aes_key, version),
        "password": _aes_encrypt_hex(password, aes_key, version),
    }


class APSystemsAuthError(Exception):
    """Authentication error."""


class APSystemsAPIError(Exception):
    """General API error."""


class APSystemsInverterOfflineError(Exception):
    """Inverter is offline or unreachable (API code 1001)."""


class APSystemsAPI:
    """Client for the AP Systems cloud API."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._user_id: str | None = None
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def authenticate(self) -> None:
        """Login with encrypted credentials — returns user access token."""
        params = _prepare_login_params(self._username, self._password)
        url = f"{API_BASE_URL}/api/token/generateToken/user/loginEncrypt"

        async with self._get_session().post(
            url,
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            body = await resp.json(content_type=None)

        if body.get("code") != 0:
            _LOGGER.error("AP Systems login failed (code=%s): %s", body.get("code"), body)
            raise APSystemsAuthError(f"Login failed: {body}")

        self._access_token = body["data"]["access_token"]
        self._user_id = body["data"]["user_id"]
        _LOGGER.debug("AP Systems authentication successful, user_id=%s", self._user_id)

    def _get_bearer_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept-Language": "en",
        }

    async def _api_request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        retry_auth: bool = True,
    ) -> dict:
        """Make an authenticated API call, re-authenticating if token is expired."""
        if not self._access_token:
            await self.authenticate()

        url = f"{API_BASE_URL}/aps-api-web/{path}"
        headers = self._get_bearer_headers()

        async with self._get_session().request(
            method,
            url,
            headers=headers,
            data=params if method == "POST" else None,
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            body = await resp.json(content_type=None)

        # Handle token expiry codes
        code = body.get("code", -1)
        if retry_auth and code in (2006, 3000, 3001, 3002, 3003, 3004, 5000):
            _LOGGER.debug("Token may be expired (code=%s), re-authenticating", code)
            await self.authenticate()
            # Retry once
            url = f"{API_BASE_URL}/aps-api-web/{path}"
            headers = self._get_bearer_headers()
            async with self._get_session().request(
                method,
                url,
                headers=headers,
                data=params if method == "POST" else None,
                ssl=False,
            ) as resp2:
                resp2.raise_for_status()
                body = await resp2.json(content_type=None)

        code = body.get("code")
        if code == 1001:
            raise APSystemsInverterOfflineError(f"Inverter offline on {path}")
        if code != 0:
            raise APSystemsAPIError(f"API error on {path}: code={code} {body.get('message', '')}")

        return body.get("data") or {}

    async def get_user_info(self) -> dict:
        """Get user information including system list."""
        if not self._user_id:
            await self.authenticate()
        return await self._api_request("GET", f"api/v2/user/ezUser/{self._user_id}")

    async def get_inverter_list(self, system_id: str) -> list[dict]:
        """Get list of EZ inverters for a system."""
        data = await self._api_request("GET", f"api/v2/device/ezInverter/inverterList/{system_id}")
        return data.get("inverter", [])

    async def get_inverter_statistic(self, dev_id: str) -> dict:
        """Get inverter statistics: today/month/lifetime energy, last power, status."""
        return await self._api_request("GET", f"api/v2/data/device/ezInverter/statistic/{dev_id}")

    async def get_inverter_realtime(self, dev_id: str) -> dict:
        """Get inverter real-time data: current power, today energy per channel."""
        return await self._api_request("GET", f"api/v2/data/device/ezInverter/realTime/{dev_id}")

    async def get_inverter_status(self, dev_id: str) -> dict:
        """Get inverter communication and running status."""
        return await self._api_request("GET", f"api/v2/data/device/ezInverter/status/{dev_id}")
