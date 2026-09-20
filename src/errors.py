"""A required backing service is unreachable or not set up. There is deliberately no fallback:
the API answers 503 and says which service, instead of quietly degrading to something else."""


class DependencyUnavailable(RuntimeError):
    def __init__(self, service: str, detail: str = "") -> None:
        super().__init__(f"{service} is unavailable" + (f": {detail}" if detail else ""))
        self.service = service
        self.detail = detail
