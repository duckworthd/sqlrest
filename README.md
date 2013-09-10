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
  --db.uri "mysql://root:@localhost:3306/kittendb"
```


Querying
========

Using the wonderful [httpie](https://github.com/jkbr/httpie) project,

```bash
$ http get localhost:8000/tables          # get a list of tables
$ http get localhost:8000/kittens/column  # get a list of columns in table "kittens"
$ http get localhost:8000/kittens/aggregate <<< '{
    "groupby": ["breed", "location"],
    "filters": {"birthday": ["2009-08-01", "2009-09-01"]},
    "aggfunc": "count",
    "aggcol": "name"
  }'  # count the number of cats per (breed, location) pair born between 08/01 and 09/01
$ http get localhost:8000/kittens/select <<< '{
    "filters": {
      "name": "Mittens",
      "breed": ["Calico", "Persian"],
      "birthday": ["2009-08-01", "2009-09-01"]
    },
    "columns": ["name", "location"],
    "page": 0,
    "page_size": 1000
  }'  # get (name, location) of first 1000 cats named Mittens of breed Calico or Persian and born between 08/01 and 09/01
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
     "birthday": ["2009-08-01", "2009-09-01"]
  },
  ...
}
```

In this scenario, only rows where `name == "Mittens"`, `breed` is one of
`"Calico"` or `"Persian"`, and `birthday` is after `"2009-08-01"` but 
before `"2009-09-01"` are included. To select one of a finite set of 
`birthdays`s, you must simply use a value with more than 2 values, e.g.

```json
{
  ...
  'filters': {
    ...
    "birthday": ["2009-08-01", "2009-09-01", "2009-10-01"]
    ...
  },
  ...
}
```
