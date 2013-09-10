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

  def aggregate(self, table, groupby, filters={}, aggfunc='count', aggcol=None):
    self.has_table(table)

    table_  = self._table(table)
    columns = { col.name:col for col in table_.columns }

    if isinstance(groupby, basestring):
      groupby = [ groupby ]

    self.has_columns(table, groupby + list(filters.keys()))

    session = self.sessionmaker()
    try:
      filters = querify(filters, table_)
      fields  = tuple(columns[name] for name in groupby)
      aggfunc = getattr(func, aggfunc)
      aggcol  = columns[aggcol] if aggcol is not None else fields[0]
      query   = (
          session
          .query(label('aggregate', aggfunc(aggcol)), *fields)
          .filter(filters)
          .group_by(*fields)
      )
      return result2dict(query.all())
    finally:
      session.close()

  def select(self, table, columns=None, filters={}, page=0, page_size=100):
    self.has_table(table)

    table_  = self._table(table)
    columnd = { c.name:c for c in table_.columns }

    # get column objects corresponding to names
    if columns is None:
      columns = list(table_.columns)
    else:
      self.has_columns(table, columns)
      columns = [columnd[c] for c in columns]

    session = self.sessionmaker()
    try:
      filters = querify(filters, table_)
      query   = (
          session
          .query(*columns)
          .filter(filters)
          .slice(page * page_size, (page + 1) * page_size)
      )
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
      import ipdb; ipdb.set_trace()
      raise SqlRestException("No table named '%s' (available: '%s')" % (table, ", ".join(self.tables())))


def querify(q, table):
  """Transform a JSON blob into a proper SQLAlchemy query"""
  td = { col.name:col for col in table.columns }
  def getcolumn(k):
    return td[k]

  def iscontinuous(c):
    types = [s.DateTime, s.Integer, s.BigInteger, s.Date, s.Float, s.SmallInteger, s.Time]
    return any(isinstance(c.type, type_) for type_ in types)

  clauses = []
  # for each query attribute
  for k, v in q.iteritems():
    c = getcolumn(k)
    if isinstance(v, list):
      if iscontinuous(c) and len(v) == 2:
        # if it's a continuous field and there are 2 values, it's a range query
        clauses.append(c >= v[0])
        clauses.append(c <= v[1])
      else:
        # if the field isn't continuous or the number of values != 2, it's an "or" query
        clauses.append( s.or_(*[getcolumn(k) == v_ for v_ in v]) )
    else:
      # otherwise, make an equality restriction
      clauses.append( getcolumn(k) == v )

  return s.and_(*clauses)


def result2dict(r):
  """Convert SQLAlchemy's result set into an iterable of dicts"""
  result = []
  for e in r:
    result.append( { key:getattr(e, key) for key in e.keys() } )
  return result


class SqlRestException(Exception):
  pass
