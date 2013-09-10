from setuptools import setup, find_packages

setup(
    name = 'sqlrest',
    version = '0.1.0',
    author = 'Daniel Duckworth',
    author_email = 'duckworthd@gmail.com',
    description = "Instant REST APIs for SQL tables",
    license = 'BSD',
    keywords = 'database sql rest api',
    url = 'github.com/duckworthd/sqlrest',
    packages = find_packages(),
    classifiers = [
      'Development Status :: 4 - Beta',
      'License :: OSI Approved :: BSD License',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
    ],
    install_requires = [     # dependencies
      'configurati>=0.1.3',
      'bottle>=0.11.6',
      'SQLAlchemy>=0.8.2',
      'MySQL-python>=1.2.4',
      'tornado>=3.1.1',
    ],
)
