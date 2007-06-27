##
## command.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 27 08:23:04 2007 David Rousselie
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

import unittest

from jcl.lang import Lang
import jcl.jabber.command as command

class CommandManager_TestCase(unittest.TestCase):
    def test_get_long_command_desc(self):
        command_desc = command.command_manager.get_command_desc("http://jabber.org/protocol/admin#test-command",
                                                                Lang.en)
        self.assertEquals(command_desc, "test-command")

    def test_get_command_desc(self):
        command_desc = command.command_manager.get_command_desc("test-command",
                                                                Lang.en)
        self.assertEquals(command_desc, "test-command")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CommandManager_TestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
