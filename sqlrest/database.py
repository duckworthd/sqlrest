import re

import sqlalchemy as s
from sqlalchemy import orm, func
from sqlalchemy.sql.expression import label


class Database(object):
  def __init__(self, config):
    # you'll get 'MySQL server has gone away' errors if you don't set pool_recycle
    engine            = s.create_engine(config.uri, pool_recycle=300)
    self.config       = config
    self.meta         = s.MetaData(bind=engine)
    self.sessionmaker = orm.sessionmaker(bind=engine)

    # discover what tables are available
    self.meta.reflect(engine)

  def aggregate(self, table, groupby, filters={}, aggregate='count(*)', page=0, page_size=100, orderby=None):
    table_  = self._table(table)
    columnd = { col.name:col for col in table_.columns }

    if isinstance(groupby, basestring):
      groupby = [ groupby ]
    if isinstance(aggregate, basestring):
      aggregate = [ aggregate ]

    session = self.sessionmaker()
    try:
      filters_    = querify(filters, table_)
      groupby_    = [ label(c, str2col(c, table_)) for c in groupby ]
      aggregate_  = [ label(a, str2col(a, table_)) for a in aggregate ]
      query       = (
          session
          .query(*(aggregate_ + groupby_))
          .filter(filters_)
          .group_by(*groupby_)
      )
      if orderby is not None:
        query = query.order_by(str2col(orderby, table_))

      query = query.slice(page * page_size, (page + 1) * page_size)

      return result2dict(query.all())
    finally:
      session.close()

  def select(self, table, columns=None, filters={}, page=0, page_size=100, orderby=None):
    table_  = self._table(table)
    columnd = { c.name:c for c in table_.columns }

    # get column objects corresponding to names
    if isinstance(columns, basestring):
      columns = [ columns ]

    if columns is None:
      columns_ = list(table_.columns)
    else:
      columns_ = [label(c, str2col(c, table_)) for c in columns]

    session = self.sessionmaker()
    try:
      filters_ = querify(filters, table_)
      query   = (
          session
          .query(*columns_)
          .filter(filters_)
      )

      if orderby is not None:
        query = query.order_by(str2col(orderby, table_))

      query = query.slice(page * page_size, (page + 1) * page_size)

      return result2dict(query.all())
    finally:
      session.close()

  def tables(self):
    return self.meta.tables.keys()

  def columns(self, table):
    self.has_table(table)
    return [c.name for c in self._table(table).columns]

  def __str__(self):
    return "Database(%s)" % (self.config.uri,)

  def _table(self, table):
    self.has_table(table)
    return s.Table(table, self.meta, autoload=True)

  def has_columns(self, table, columns):
    """Check if table has necessary columns"""
    available_columns = set(self.columns(table))
    rogue = [c for c in columns if not c in available_columns]
    if len(rogue) > 0:
      raise SqlRestException("No column(s) named '%s' in table '%s'" % (", ".join(rogue), table))

  def has_table(self, table):
    if not table in self.tables():
      raise SqlRestException("No table named '%s' (available: '%s')" % (table, ", ".join(self.tables())))


def querify(q, table):
  """Transform a JSON blob into a proper SQLAlchemy query"""
  def iscontinuous(c):
    types     = [s.DateTime, s.Date, s.Time, s.SmallInteger, s.Integer, s.BigInteger, s.Float]
    functypes = {'date'}  # some functions have incorrect return types
    return any(isinstance(c.type, type_) for type_ in types) \
        or (isinstance(c, s.sql.expression.Function) \
            and c.name.lower() in functypes)

  clauses = []
  # for each query attribute
  for k, v in q.iteritems():
    c = str2col(k, table)
    if isinstance(v, list):
      if iscontinuous(c) and len(v) == 2:
        # if it's a continuous field and there are 2 values, it's a range query
        clauses.append(c >= v[0])
        clauses.append(c <= v[1])
      else:
        # if the field isn't continuous or the number of values != 2, it's an "or" query
        clauses.append( s.or_(*[str2col(k, table) == v_ for v_ in v]) )
    else:
      # otherwise, make an equality restriction
      clauses.append( getcolumn(k) == v )

  return s.and_(*clauses)


def str2col(field, table):
  """Convert count(distinct(column)) into an actual query-able object"""
  # TODO this should be evaluated with a lexical parser
  # TODO functions of columns don't necessarily preserve type. e.g. DATE(...)
  # TODO don't recompute column name -> column mapping every time this function
  #      is called.

  # get column by name
  td = { col.name:col for col in table.columns }
  def getcolumn(k):
    if k == '*':
      # TODO this should be smarter. How do you resolve "*" in sqlalchemy?
      return td.values()[0]
    else:
      return td[k]

  # is this string a function call on a column?
  pattern = re.compile("^\s*(\w+)\((.+?)\)\s*$")
  def is_function(s):
    return pattern.search(s) is not None

  # get (function name, insides)
  def function_split(s):
    return pattern.search(s).groups()

  queue = []
  while is_function(field):
    funcname, field = function_split(field)
    queue.append(getattr(s.func, funcname))

  # all that's left is a single column
  column = getcolumn(field)

  # apply functions to column
  for f in reversed(queue):
    column = f(column)

  return column


def result2dict(r):
  """Convert SQLAlchemy's result set into an iterable of dicts"""
  result = []
  for e in r:
    result.append( { key:getattr(e, key) for key in e.keys() } )
  return result


class SqlRestException(Exception):
  pass
