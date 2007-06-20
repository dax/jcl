"""Jabber related classes"""
__revision__ = ""

from jcl.model.account import Account

class Handler(object):
    """handling class"""

    def filter(self, stanza, lang_class):
        """Filter account to be processed by the handler
        return all accounts. DB connection might already be opened."""
        accounts = Account.select()
        return accounts

    def handle(self, stanza, lang_class, accounts):
        """Apply actions to do on given accounts
        Do nothing by default"""
        return []

class DiscoHandler(object):
    """Handle disco get items requests"""

    def filter(self, node, info_query):
        """Filter requests to be handled"""
        return False

    def handle(self, disco_items, node, info_query, data, lang_class):
        """Handle disco get items request"""
        return None
