"""Django project initialization"""

# Use PyMySQL as the MySQL database driver instead of mysqlclient
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from .celery import app as celery_app

__all__ = ('celery_app',)
