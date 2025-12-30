import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)

logging.getLogger("http_audit").setLevel(logging.WARNING)
