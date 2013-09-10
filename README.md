sqlrest
=======

Automatically generate a REST API for a SQL database. Uses `sqlalchemy` to talk
to databases, `bottle` to talk to web clients.


Usage
=====

```bash
# start server on port 8000 mapped to a MySQL instance
$ python -m sqlrest.server \
  --frontend.port 8000 \
  --frontend.host '0.0.0.0' \
  --db.uri "mysql://root:@localhost:3306/erinys"
```


Querying
========

Using the wonderful [httpie](https://github.com/jkbr/httpie) project,

```bash
$ http get localhost:8000/tables        # get a list of tables
$ http get localhost:8000/asimi/column  # get a list of columns in table "asimi"
$ http get localhost:8000/asimi/aggregate <<< '{
    "groupby": ["domain", "status"],
    "filters": {"timestamp": ["2009-08-01", "2009-09-01"]},
    "aggfunc": "count",
    "aggcol": "id"
  }'  # count the number of unique ids per (domain, status) pair between 08/01 and 09/01
$ http get localhost:8000/asimi/select <<< '{
    "filters": {
      "domain": "com.amazon",
      "status": ["incorrect", "no_erinys_extractions"],
      "timestamp": ["2009-08-01", "2009-09-01"]
    },
    "columns": ["id", "domain", "field_name"],
    "page": 0,
    "page_size": 1000
  }'  # get "id", "domain", and "field_name" columns from first 1000 rows where domain == com.amazon and status is either "incorrect" or "no_erinys_extractions"
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
    "domain": "com.amazon",
    "status": ["incorrect", "no_erinys_extractions"],
    "timestamp": ["2009-08-01", "2009-09-01"]
  },
  ...
}
```

In this scenario, only rows where `domain == "com.amazon"`, `status` is one of
`"incorrect"` or `"no_erinys_extractions"`, and `timestamp` is after
`"2009-08-01"` but before `"2009-09-01"` are included. To select one of a
finite set of `timestamp`s, you must simply use a value with more than 2
values, e.g.

```json
{
  ...
  'filters': {
    ...
    "timestamp": ["2009-08-01", "2009-09-01", "2009-10-01"]
    ...
  },
  ...
}
```
