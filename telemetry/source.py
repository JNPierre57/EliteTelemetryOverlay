"""Source boundary. Never infer an unverified EDEB database schema."""


class UnverifiedSourceError(RuntimeError):
    pass


def read_current_trip():
    raise UnverifiedSourceError(
        'EDEB schema not verified. Run tools/inspect-edeb.ps1 on Shadow and '
        'follow docs/EDEB-DATA-SOURCE.md. No value has been sent. '
        'Use --demo only to test the transport and overlay.')
