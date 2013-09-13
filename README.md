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
