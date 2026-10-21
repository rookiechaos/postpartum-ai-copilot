"""Container API readiness probe; does not import or initialize the application."""

from urllib.request import urlopen


def main():
    try:
        with urlopen("http://localhost:8000/health", timeout=3) as response:
            return 0 if response.status == 200 else 1
    except Exception:
        # Do not echo environment, credentials, URLs or exception messages.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
