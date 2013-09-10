import datetime
import json
import os

import bottle
import configurati

from .database import Database


def main(config):
  # connect to db
  db = Database(config.db)

  # setup routes
  app = bottle.Bottle()

  def register(route, f):
    json_route(app, route)(json_response(f))

  register("/tables",            db.tables)
  register("/:table/columns",    db.columns)
  register("/:table/aggregate",  db.aggregate)
  register("/:table/select",     db.select)

  # start server
  app.run(
    port=config.frontend.port,
    host=config.frontend.host,
    server='tornado',
  )


def json_route(app=None, *args, **kwargs):
  """Decorator for routes with JSON parameters as input"""

  if app is None:
    app = bottle

  def decorate(f):
    def decorated(*args_, **kwargs_):
      new_kwargs = json_args(bottle.request)
      new_kwargs.update(kwargs_)
      return f(*args_, **new_kwargs)

    decorated = app.get(*args, **kwargs)(decorated)
    decorated = app.post(*args, **kwargs)(decorated)
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
  r.headers['Access-Control-Allow-Origin'] = '*'
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
  if isinstance(o, datetime.datetime):
    return o.isoformat()
  return o


if __name__ == '__main__':
  if os.path.exists('config.py'):
    config = configurati.configure(config_path='config.py')
  else:
    config = configurati.configure()
  main(config)
