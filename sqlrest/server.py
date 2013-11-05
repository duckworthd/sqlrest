import gevent.monkey; gevent.monkey.patch_all()
import psycogreen.gevent; psycogreen.gevent.patch_psycopg()
import os
import re

from duxlib.bottle import JsonBottle
import bottle
import configurati

from .caching import RedisCache, CachingBottle
from .database import Database
from .log import initialize as init_logging


def main(config):
  # setup routes
  app = attach_routes(
    config.db,
    prefix=config.frontend.prefix,
    caching=config.caching,
    editing=config.editing,
  )

  # start server
  app.run(
    port=config.frontend.port,
    host=config.frontend.host,
    server='gevent',
  )


def attach_routes(db, app=None, prefix=None, caching=None, editing=False):
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

  # add json routes
  app = JsonBottle(app)
  app.error(500)(error_handler)
  if caching is None:
    app.json_route(prefix + "/tables"           )(db.tables    )
    app.json_route(prefix + "/:table/columns"   )(db.columns   )
    app.json_route(prefix + "/:table/aggregate" )(db.aggregate )
    app.json_route(prefix + "/:table/select"    )(db.select    )
  else:
    # caching routes, too
    app = CachingBottle(app, RedisCache(**caching.config))
    app.json_route(prefix + "/tables"           )(app.memoize(caching.timeouts.tables    )(db.tables    ))
    app.json_route(prefix + "/:table/columns"   )(app.memoize(caching.timeouts.columns   )(db.columns   ))
    app.json_route(prefix + "/:table/aggregate" )(app.memoize(caching.timeouts.aggregate )(db.aggregate ))
    app.json_route(prefix + "/:table/select"    )(app.memoize(caching.timeouts.select    )(db.select    ))
    app.json_route(prefix + "/:table", method=["POST", "GET"])(app.memoize(caching.timeouts.select    )(db.select    ))
    if editing:
      app.json_route(prefix + "/:table", method=["PUT"])(db.insert)
      app.json_route(prefix + "/:table", method=["DELETE"])(db.delete)
      app.json_route(prefix + "/:table", method=["PATCH"])(db.update)
    else:
      def not_enabled(*args, **kwargs):
        return {
            "status": "failure",
            "reason": "destructive operations not enabled"
        }
      app.json_route(prefix + "/:table", method=["PUT"])(not_enabled)
      app.json_route(prefix + "/:table", method=["DELETE"])(not_enabled)
      app.json_route(prefix + "/:table", method=["PATCH"])(not_enabled)

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
  config = configurati.configure(spec=spec)

  init_logging()

  main(config)
