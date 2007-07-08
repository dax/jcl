"""Jabber related classes"""
__revision__ = ""

import jcl.model.account as account
from jcl.model.account import Account

class Handler(object):
    """handling class"""

    def __init__(self, component):
        """Default Handler constructor"""
        self.component = component

    def filter(self, stanza, lang_class):
        """
        Filter account to be processed by the handler
        return all accounts. DB connection might already be opened.
        """
        accounts = Account.select()
        return accounts

    def handle(self, stanza, lang_class, data):
        """
        Apply actions to do on given accounts
        Do nothing by default.
        """
        return []

def root_filter(self, stanza, lang_class, node=None):
    """Filter stanza sent to root node"""
    to_jid = stanza.get_to()
    if to_jid.resource is None and to_jid.node is None and node is None:
        return True
    else:
        return None

def account_type_filter(self, stanza, lang_class, node=None):
    """Filter stanzas sent to account type node"""
    to_jid = stanza.get_to()
    account_type = to_jid.resource
    if account_type is not None and to_jid.node is None:
        return account_type
    else:
        return None

def account_filter(self, stanza, lang_class, node=None):
    """Filter stanzas sent to account jid"""
    name = stanza.get_to().node
    return name

def get_account_filter(self, stanza, lang_class, node=None):
    """Filter stanzas sent to account jid, only if account exists"""
    name = stanza.get_to().node
    if name is not None:
        return account.get_account(name,
                                   stanza.get_from().bare())
    else:
        return None

def get_accounts_root_filter(self, stanza, lang_class, node=None):
    """Filter stanza sent to root node"""
    to_jid = stanza.get_to()
    if to_jid.resource is None and to_jid.node is None and node is None:
        return account.get_accounts(stanza.get_from().bare())
    else:
        return None
