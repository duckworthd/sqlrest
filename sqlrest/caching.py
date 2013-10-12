import cPickle as pickle
import datetime
import hashlib

from bottle import request
from redis import StrictRedis, ConnectionError

from .log import Loggable


class AbstractCache(object):
  def __init__(self, timeout):
    self.timeout = timeout

  def key(self, func, *args, **kwargs):
    """Construct a unique key for this function call"""
    name      = func.__module__ + '.' + func.__name__
    argskey   = pickle.dumps(args)
    kwargskey = pickle.dumps(kwargs)
    return hashlib.sha1(name + argskey + kwargskey).hexdigest()

  def memoize(self, decorated):
    """Memoize a function with a timeout

    >>> cache = RedisCache(host='localhost', port=6379, timeout=30) # default to 30 second timeout
    >>> @cache.memoize
    ... def hello(name):
    ...   print 'recalculating call to hello()'
    ...   return "Hello, " + name
    >>> hello("Dave")   # cache miss
    >>> hello("Dave")   # cache hit
    >>> hello("John")   # cache miss
    >>> hello("Dave")   # cache hit
    >>> hello("John")   # cache hit

    """
    def decorator(*args, **kwargs):
      # construct key
      k = self.key(decorated, *args, **kwargs)

      # get cache value
      try:
        result = self[k]
        self.log.info("Successfully found key: {}".format(k))
        return result
      except KeyError:
        # key not in cache (result is None), so calculate it it now and put it in
        self.log.info("Missed key: {}; reconstructing...".format(k))
        result = decorated(*args, **kwargs)
        self.set(k, result, timeout or self.timeout)
      except ConnectionError:
        self.log.warning("Unable to connect to Redis; reconstructing...".format(k))
        return decorated(*args, **kwargs)

      return result

    return decorator

  def __setitem__(self, key, value):
    self.set(key, value)

  def __getitem__(self, key):
    return self.get(key)

  def __contains__(self, key):
    try:
      self[k]
      return True
    except KeyError:
      return False

  def get(self, key):
    abstract

  def set(self, key, value, timeout=None):
    abstract


class RedisCache(AbstractCache, Loggable):
  """A cache backed by Redis

  Use as a dictionary,

  >>> cache = RedisCache(host="localhost", port=6379)
  >>> cache['hello'] = 'world'
  >>> cache['hello']            # 'world'
  >>> 'hello' in cache          # True
  >>> 'goodbye' in cache        # False

  or as a function memoizer,

  >>> @cache.memoize
  >>> def hello(name):
  ...   return "Hello, " + name

  Parameters
  ----------
  same as `redis.StrictRedis`
  """
  def __init__(self, *args, **kwargs):
    AbstractCache.__init__(self, kwargs.get('timeout', datetime.timedelta(days=1)))
    Loggable.__init__(self)

    if 'timeout' in kwargs:
      del kwargs['timeout']
    self.redis = StrictRedis(*args, **kwargs)

  def get(self, key):
    # value will be None if key is missing, but this is ambiguous
    value = self.redis.get(key)
    if not self.redis.exists(key):
      raise KeyError()
    else:
      return pickle.loads(value)

  def set(self, key, value, timeout=None):
    self.redis.set(key, pickle.dumps(value))
    self.redis.expire(key, datetime.timedelta(seconds=timeout) or self.timeout)


class CachingBottle(Loggable):

  def __init__(self, app, cache=None):
    super(CachingBottle, self).__init__()

    self.app   = app
    self.cache = cache

  def __getattr__(self, key):
    return getattr(self.app, key)

  def __hasattr__(self, key):
    return hasattr(self.app, key)

  def memoize(self, timeout):
    def decorator_(decorated):
      def decorator(*args, **kwargs):
        cache_control = request.headers.get("Cache-Control", "").lower()
        use_cache     = self.cache is not None and (cache_control != "no-cache")
        if not use_cache:
          self.log.info("Skipping cache; reconstructing...")
          return decorated(*args, **kwargs)
        else:
          k = self.cache.key(decorated, *args, **kwargs)
          try:
            v = self.cache[k]
            self.log.info("Found key: {}".format(k))
            return v
          except KeyError:
            self.log.info("Missed key: {}; reconstructing...".format(k))
            v = decorated(*args, **kwargs)
            self.cache.set(k, v, timeout)
            return v
          except ConnectionError:
            self.log.info("Failure connecting to Redis: {}; reconstructing...".format(k))
            return decorated(*args, **kwargs)

      return decorator
    return decorator_
