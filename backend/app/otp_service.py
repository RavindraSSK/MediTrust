from datetime import datetime, timedelta
import random


class OTPStore:
    def __init__(self):
        self._codes = {}

    def generate_code(self, email: str, ttl_minutes: int = 10) -> str:
        code = f"{random.randint(100000, 999999)}"
        self._codes[email.lower().strip()] = {
            "code": code,
            "expires_at": datetime.utcnow() + timedelta(minutes=ttl_minutes),
            "verified": False,
        }
        return code

    def verify_code(self, email: str, code: str) -> bool:
        key = email.lower().strip()
        item = self._codes.get(key)

        if not item:
            return False

        if datetime.utcnow() > item["expires_at"]:
            self._codes.pop(key, None)
            return False

        if item["code"] != code.strip():
            return False

        item["verified"] = True
        return True

    def is_verified(self, email: str) -> bool:
        key = email.lower().strip()
        item = self._codes.get(key)

        if not item:
            return False

        if datetime.utcnow() > item["expires_at"]:
            self._codes.pop(key, None)
            return False

        return bool(item.get("verified"))

    def clear(self, email: str):
        self._codes.pop(email.lower().strip(), None)


otp_store = OTPStore()