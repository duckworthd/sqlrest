import logging


class Loggable(object):

  def __init__(self):
    name     = self.__class__.__module__ + "." + self.__class__.__name__
    self.log = logging.getLogger(name)

# default logging config
LOGCONF = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'default': {
      'format': "[%(asctime)s][%(levelname)s][%(name)s.%(funcName)s:%(lineno)d][Thread(%(thread)d)] %(message)s",
      'datefmt': "%Y/%m/%d %H:%M:%S",
    },
  },
  'handlers': {
    'console': {
      'level':'INFO',
      'class':'logging.StreamHandler',
      'stream': 'ext://sys.stdout',
      'formatter': 'default',
    },
  },
  'loggers': {
    '': {
      'handlers': ['console'],
      'level': 'DEBUG',
      'propagate': True
    },
  }
}

def initialize():
  import logging.config
  logging.config.dictConfig(LOGCONF)
