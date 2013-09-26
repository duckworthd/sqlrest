import gevent.monkey; gevent.monkey.patch_all()
import psycogreen.gevent; psycogreen.gevent.patch_psycopg()
import datetime
import json
import os
import re

import bottle
import configurati

from .database import Database
from .log import initialize as init_logging


def main(config):
  # setup routes
  app = attach_routes(config.db, prefix=config.frontend.prefix)

  # start server
  app.run(
    port=config.frontend.port,
    host=config.frontend.host,
    server='gevent',
  )


def attach_routes(db, app=None, prefix=None):
  """Attach sqlrest routes to app"""

  # if connector isn't specified, choose one that's asynchronous
  if db.uri.startswith("mysql://"):
    db.uri = re.sub("^mysql://", "mysql+mysqlconnector://", db.uri)
  elif config.uri.startswith("postgresql://"):
    db.uri = re.sub("^postgresql://", "postgresql+psycopg2://", db.uri)

  if prefix is None:
    prefix = ''

  # create app, if necessary
  if app is None:
    app = bottle.Bottle()

  # connect to db
  db = Database(db)

  # attach routes
  def register(route, f):
    json_route(app, prefix + route)(json_response(f))

  register("/tables",            db.tables)
  register("/:table/columns",    db.columns)
  register("/:table/aggregate",  db.aggregate)
  register("/:table/select",     db.select)

  return app


def json_route(app=None, *args, **kwargs):
  """Decorator for routes with JSON parameters as input"""

  # merge dictionaries together, preferring earliest first
  def merge(*dicts):
    result = {}
    for d in reversed(dicts):
      result.update(d)
    return result

  if app is None:
    app = bottle

  def decorate(f):
    def decorated(*args_, **kwargs_):
      # This is necessary for frontend libraries like AngularJS and jQuery to
      # make AJAX requests.
      r = bottle.response
      r.headers['Access-Control-Allow-Origin']  = '*'
      r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
      r.headers['Access-Control-Allow-Headers'] = \
          'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

      if bottle.request.method == 'OPTIONS':
        # an OPTIONS request is a "preflight" request sent before a cross-site
        # AJAX request is made. It's done by most modern browsers to make sure
        # that the next GET/POST/whatever request is allowed by the server.
        return {}
      else:
        new_kwargs = json_args(bottle.request)
        return f(*args_, **merge(new_kwargs, kwargs_))

    decorated = app.route(*args, **merge({"method": ["OPTIONS", "GET", "POST"]}, kwargs))(decorated)
    return decorated

  return decorate


def json_response(f):
  """Return output a function as a JSON response"""

  def decorated(*args, **kwargs):
    return asjson(f(*args, **kwargs))

  return decorated


def json_args(r):
  """Get JSON arguments to this request"""
  if r.json is not None:
    return r.json
  else:
    try:
      r.body.seek(0)
      return json.loads(r.body.read())
    except ValueError as e:
      return dict(r.params)


def asjson(o):
  """return a response as json"""
  r = bottle.response
  r.content_type = 'application/json'
  r.body = json.dumps(json_escape(o))
  return r


def json_escape(o):
  if isinstance(o, list):
    return [json_escape(e) for e in o]
  if isinstance(o, dict):
    result = {}
    for k, v in o.items():
      result[k] = json_escape(v)
    return result
  if isinstance(o, datetime.datetime) or isinstance(o, datetime.date):
    return o.isoformat()
  if isinstance(o, basestring):
    # handle unicode encoding errors
    try:
      json.dumps(o)
      return o
    except UnicodeDecodeError:
      return o.decode("utf8", errors="replace")

  return o


if __name__ == '__main__':
  spec_path = os.path.join(
    os.path.split(__file__)[0],
    "config.spec.py"
  )
  if os.path.exists('config.py'):
    config = configurati.configure(
      config_path='config.py',
      spec_path=spec_path
    )
  else:
    config = configurati.configure(spec_path=spec_path)

  init_logging()

  main(config)
