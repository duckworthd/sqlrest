sqlrest
=======

Automatically generate a REST API for a SQL database. Uses `sqlalchemy` to talk
to databases, `bottle` to talk to web clients.


Usage
=====

You can initialize sqlrest independently...

```bash
# start server on port 8000 mapped to a MySQL instance
$ python -m sqlrest.server \
  --frontend.port 8000 \
  --frontend.host '0.0.0.0' \
  --db.uri "mysql://root:@localhost:3306/kittendb"
```

...or by attaching it to another app,

```python
import bottle
from configurati import attrs
from sqlrest.server import attach_routes

app = bottle.Bottle()

# attach other routes here
@app.get("/")
def hello_world():
  return "Hello, World!"

# attach sqlrest routes, with URLS prefixed by "/sqlrest". e.g.
# /sqlrest/kittens/columns, /sqlrest/kittens/select, and
# /sqlrest/kittens/aggregate to access table `kittens`
app = attach_routes(attrs({'uri': "mysql://root:@localhost:3306/kittendb"}), app=app, prefix="/sqlrest")

# start serving content
app.run(...)
```

Querying
========

Using the wonderful [httpie](https://github.com/jkbr/httpie) project,

```bash
# Get all tables available
$ http get localhost:8000/tables

# Get column names in table `kittens`
$ http get localhost:8000/kittens/columns

# SELECT breed, location, count(*), min(birthday) FROM KITTENS
#   WHERE date(birthday) <= "2009-08-01" AND date(birthday) >= "2009-09-01"
#   GROUP BY breed, location
#   ORDER BY count(*) DESC
#   LIMIT 0, 10;
$ http get localhost:8000/kittens/aggregate <<< '{
    "groupby": ["breed", "location"],
    "filters": {
      "date(birthday)": ["2009-08-01", "2009-09-01"]
    },
    "aggregate": ["count(*)", "min(birthday)"],
    "orderby": ["count(*)", "descending"],
    "page": 0,
    "page_size": 10
  }'

# SELECT name, location FROM kittens
#   WHERE (name = "Mittens") AND
#     (breed = "Calico" OR breed = "Persian") AND
#     (birthday >= "2009-08-01" AND birthday <= "2009-09-01");
#   ORDER BY name
#   LIMIT 50, 60;
$ http get localhost:8000/kittens/select <<< '{
    "filters": {
      "name": "Mittens",
      "breed": ["Calico", "Persian"],
      "birthday": ["2009-08-01", "2009-09-01"]
    },
    "columns": ["name", "location"],
    "orderby": "name"
    "page": 5,
    "page_size": 10
  }'
```

Filters
=======

Both `aggregate` and `select` endpoints can take an argument `filters`, an
object where keys are column names and values are either arrays or single
elements.

Let's take the following example,

```json
{
  ...
  'filters': {
     "name": "Mittens",
     "breed": ["Calico", "Persian"],
     "date(birthday)": ["2009-08-01", "2009-09-01"]
  },
  ...
}
```

In this scenario, only rows where `name == "Mittens"`, `breed` is one of
`"Calico"` or `"Persian"`, and `date(birthday)` is after `"2009-08-01"` but
before `"2009-09-01"` are included. To select one of a finite set of
`date(birthday)s`s, you must simply use a value with more than 2 values, e.g.
```json
{
  ...
  'filters': {
    ...
    "date(birthday)": ["2009-08-01", "2009-09-01", "2009-10-01"]
    ...
  },
  ...
}
```


Caching
=======

`sqlrest` supports caching via Redis. By default, caching is disabled, but it
can be enabled by adding settings `caching.enabled = True` in your config. For
example,

```bash
$ redis-server &
$ python -m sqlrest.server                         \
  --db.uri "mysql://root:@localhost:3306/kittendb" \
  --caching.enabled true                           \
  --caching.config.port 6379                       \
  --caching.config.host localhost                  \
  --caching.timeouts '{"select": 300, "aggregate": 900}'
```

In the event that caching is enabled and `sqlrest` is unable to reach Redis, it
will issue a log warning but will continue serving as if caching were disabled.


Configuration
=============

Configuration in `sqlrest` is handled by
[`configurati`](https://github.com/duckworthd/configurati) with the following
specification,

`config.py`

```Python
frontend = {  # webapp configuration
  'port'   : optional(type=int, default=8000),      # port of server
  'host'   : optional(type=str, default='0.0.0.0'), # IP address of server
  'prefix' : optional(type=str, default='')         # prefix for all sqlrest endpoints
}

db = {
  'uri': required(type=str)   # SQLAlchemy database configuration string
}

caching = {
  'enabled' : optional(type=bool, default=False),   # enable caching
  'config'  : optional(type=dict, default={}),      # cache configuration; see `redis.StrictRedis`
  'timeouts' : {                                    # ttl for sqlrest endpoints
    'tables'    : optional(type=int, default=99999),        # for /tables
    'columns'   : optional(type=int, default=99999),        # for /<table>/columns
    'select'    : optional(type=int, default=60 * 5),       # for /<table>/select
    'aggregate' : optional(type=int, default=60 * 60 * 24), # for /<table>/aggregate
  }
}
```

A configuration file can be used via the `--config` command line parameter,

```Python
$ python -m sqlrest.server --config config.py
```
