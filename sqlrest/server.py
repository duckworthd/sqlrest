import gevent.monkey; gevent.monkey.patch_all()
import psycogreen.gevent; psycogreen.gevent.patch_psycopg()
import os
import re

from duxlib.bottle import SuperBottle
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

  app = SuperBottle(app) # additional routes
  app.json_route("/tables")          (db.tables)
  app.json_route("/:table/columns")  (db.columns)
  app.json_route("/:table/aggregate")(db.aggregate)
  app.json_route("/:table/select")   (db.select)
  app.error(500)(error_handler)

  return app


def error_handler(exception):
  # add AJAX headers
  ajax_headers(bottle.request, bottle.response)

  # print exception string
  e = exception.exception
  return e.__class__.__name__ + ": " + str(e)


if __name__ == '__main__':
  spec = os.path.join(
    os.path.split(__file__)[0],
    "config.spec.py"
  )
  if os.path.exists('config.py'):
    config = configurati.configure(config='config.py', spec=spec)
  else:
    config = configurati.configure(spec=spec)

  init_logging()

  main(config)
