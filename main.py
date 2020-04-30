import logging

from flix.kodi import set_logger
from lib.provider import MagnetoProvider

set_logger(level=logging.INFO)
MagnetoProvider().register()
