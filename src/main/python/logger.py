import logging

logging.basicConfig(
    filename="configuraTed.log",
    format="%(module)s::%(levelname)s => %(message)s")
log = logging.getLogger("")
log.setLevel(logging.DEBUG)
