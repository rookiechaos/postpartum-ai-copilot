"""Explicit deployment entry point; importing this module performs no migration."""


def main():
    from models.database import init_db

    init_db()


if __name__ == "__main__":
    import sys

    try:
        main()
    except Exception as error:
        # A failed deployment must not print SQL, credentials or local paths.
        print(f"Database migration failed ({type(error).__name__})", file=sys.stderr)
        raise SystemExit(1) from None
