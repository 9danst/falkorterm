from falkorterm.app import run_app
from falkorterm.config import load_config


def main() -> None:
    run_app(load_config())


if __name__ == "__main__":
    main()
