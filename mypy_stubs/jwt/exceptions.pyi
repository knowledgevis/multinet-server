from typing import Any

class PyJWTError(Exception): ...
class InvalidTokenError(PyJWTError): ...
class DecodeError(InvalidTokenError): ...
class InvalidSignatureError(DecodeError): ...
class ExpiredSignatureError(InvalidTokenError): ...
class InvalidAudienceError(InvalidTokenError): ...
class InvalidIssuerError(InvalidTokenError): ...
class InvalidIssuedAtError(InvalidTokenError): ...
class ImmatureSignatureError(InvalidTokenError): ...
class InvalidKeyError(PyJWTError): ...
class InvalidAlgorithmError(InvalidTokenError): ...

class MissingRequiredClaimError(InvalidTokenError):
    claim: Any = ...
    def __init__(self, claim: Any) -> None: ...

ExpiredSignature = ExpiredSignatureError
InvalidAudience = InvalidAudienceError
InvalidIssuer = InvalidIssuerError
