class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status, self.code = status, code
        self.message, self.details = message, details or {}
