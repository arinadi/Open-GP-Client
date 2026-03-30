"""Entry point: python3 -m gp_connect"""

from .app import OpenGPApp


def main():
    app = OpenGPApp()
    app.run()


if __name__ == "__main__":
    main()
