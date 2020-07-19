from flix.kodi import set_logger
from lib.provider import MagnetoProvider

set_logger()
MagnetoProvider().register()
