"""Contains data model classes"""
__revision__ = ""

from sqlobject.dbconnection import ConnectionHub
from sqlobject.dbconnection import connectionForURI

import jcl.model

db_connection_str = ""

# create a hub to attach a per thread connection
hub = ConnectionHub()

def db_connect():
    """
    Create a new connection to the DataBase (SQLObject use connection
    pool) associated to the current thread.
    """
    #if not jcl.model.db_connected:
    jcl.model.hub.threadConnection = \
        connectionForURI(db_connection_str)
    #        account.hub.threadConnection.debug = True
    #jcl.model.db_connected = True

def db_disconnect():
    """
    Delete connection associated to the current thread.
    """
    pass
    #if jcl.model.db_connected:
    #del jcl.model.hub.threadConnection
    #jcl.model.db_connected = False
