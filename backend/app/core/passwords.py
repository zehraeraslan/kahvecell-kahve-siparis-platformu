import base64
import hashlib
import hmac
import secrets

PASSWORD_HASH_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return (
        f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$"
        f"{encode(salt)}${encode(digest)}"
    )


def verify_password(password: str, stored_hash: str | None) -> bool:
    if stored_hash is None:
        return False
    try:
        algorithm, iterations, encoded_salt, encoded_digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt)
        expected_digest = base64.urlsafe_b64decode(encoded_digest)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual_digest, expected_digest)
