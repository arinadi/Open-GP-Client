import logging
import sys

def main():
    # Setup basic logging to see everything
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("open-gp-client.main")
    logger.debug("Starting main entry point")
    
    try:
        from .app import OpenGPApp
        app = OpenGPApp()
        logger.debug("Running app")
        app.run(sys.argv)
    except Exception as e:
        logger.exception("Failed to run app")

if __name__ == "__main__":
    main()
