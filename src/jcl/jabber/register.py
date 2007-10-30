##
## register.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jul 18 21:32:51 2007 David Rousselie
## $Id$
## 
## Copyright (C) 2007 David Rousselie
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##

import logging
import sys
import traceback

import pyxmpp.error as error

from jcl.error import FieldError
import jcl.model as model
import jcl.jabber as jabber

class SetRegisterHandler(object):
    """Handle disco get items requests"""

    def __init__(self, component):
        self.component = component
        self.account_manager = component.account_manager
        self.__logger = logging.getLogger("jcl.jabber.SetRegisterHandler")

    def filter(self, info_query, lang_class, x_data):
        """Filter requests to be handled"""
        return False

    def handle(self, info_query, lang_class, data, x_data):
        """Handle disco get items request"""
        return None

    def handle_error(self, field_error, info_query, lang_class):
        type, value, stack = sys.exc_info()
        self.__logger.error("Error while populating account: %s\n%s" %
                            (field_error, "".join(traceback.format_exception
                                                (type, value, stack, 5))))
        iq_error = info_query.make_error_response("not-acceptable")
        text = iq_error.get_error().xmlnode.newTextChild(\
            None,
            "text",
            lang_class.mandatory_field % (field_error.field))
        text.setNs(text.newNs(error.STANZA_ERROR_NS, None))
        return [iq_error]

class RootSetRegisterHandler(SetRegisterHandler):

    def __init__(self, component):
        SetRegisterHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.RootSetRegisterHandler")

    def filter(self, stanza, lang_class, x_data):
        """
        """
        return jabber.root_filter(self, stanza, lang_class)

    def handle(self, info_query, lang_class, data, x_data):
        """
        """
        self.__logger.debug("root_set_register")
        _account = None
        if not "name" in x_data or x_data["name"].value == "":
            # TODO : use handle_error
            iq_error = info_query.make_error_response("not-acceptable")
            text = iq_error.get_error().xmlnode.newTextChild(\
                None,
                "text",
                lang_class.mandatory_field % ("name"))
            text.setNs(text.newNs(error.STANZA_ERROR_NS, None))
            return [iq_error]
        try:
            info_queries = self.account_manager.create_default_account(\
                    x_data["name"].value,
                    info_query.get_from(),
                    lang_class,
                    x_data)
            info_queries.insert(0, info_query.make_result_response())
        except FieldError, field_error:
            return self.handle_error(field_error,
                                     info_query, lang_class)
        return info_queries

class AccountSetRegisterHandler(SetRegisterHandler):

    def __init__(self, component):
        SetRegisterHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.AccountSetRegisterHandler")

    def filter(self, stanza, lang_class, x_data):
        """
        """
        return jabber.account_filter(self, stanza, lang_class)

    def handle(self, info_query, lang_class, data, x_data):
        """
        """
        self.__logger.debug("account_set_register")
        _account = None
        resource = info_query.get_to().resource
        if resource is not None:
            account_type = resource.split("/")[0]
        else:
            account_type = ""
        try:
            info_queries = self.account_manager.update_account(\
                x_data["name"].value,
                info_query.get_from(),
                account_type,
                lang_class,
                x_data)
            info_queries.insert(0, info_query.make_result_response())
        except FieldError, field_error:
            return self.handle_error(field_error,
                                     info_query, lang_class)
        return info_queries

class AccountTypeSetRegisterHandler(SetRegisterHandler):

    def __init__(self, component):
        SetRegisterHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.AccountTypeSetRegisterHandler")

    def filter(self, stanza, lang_class, x_data):
        """
        """
        return jabber.account_type_filter(self, stanza, lang_class)

    def handle(self, info_query, lang_class, data, x_data):
        """
        """
        self.__logger.debug("account_type_set_register")
        account_type = data
        _account = None
        try:
            info_queries = self.account_manager.create_account_from_type(\
                x_data["name"].value,
                info_query.get_from(),
                account_type,
                lang_class,
                x_data)
            info_queries.insert(0, info_query.make_result_response())
        except FieldError, field_error:
            return self.handle_error(field_error,
                                     info_query, lang_class)
        return info_queries
