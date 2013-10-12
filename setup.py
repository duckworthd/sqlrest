from setuptools import setup, find_packages

import sqlrest


setup(
    name = 'sqlrest',
    version = sqlrest.__version__,
    author = 'Daniel Duckworth',
    author_email = 'duckworthd@gmail.com',
    description = "Instant REST APIs for SQL tables",
    license = 'BSD',
    keywords = 'database sql rest api',
    url = 'http://github.com/duckworthd/sqlrest',
    packages = find_packages(),
    classifiers = [
      'Development Status :: 4 - Beta',
      'License :: OSI Approved :: BSD License',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
    ],
    install_requires = [     # dependencies
      # command line config
      'configurati>=0.2.0',

      # connecting to databases
      'SQLAlchemy>=0.8.2',
      'mysql-connector-python>=1.0.12',
      'psycopg2>=2.5.1',

      # asynchronous requests
      'psycogreen>=1.0',
      'gevent>=0.13.8',

      # webserver
      'bottle>=0.11.6',
      'duxlib>=0.1.0',

      # caching
      'redis>=2.7.1',
    ],
)
