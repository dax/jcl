##
## runner.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Thu May 17 22:02:08 2007 David Rousselie
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
import os
import sys
from ConfigParser import ConfigParser
from getopt import gnu_getopt

from jcl.lang import Lang
from jcl.jabber.component import JCLComponent
import jcl.model as model
from jcl.model.account import Account, PresenceAccount, User, LegacyJID

class JCLRunner(object):
    def __init__(self, component_name, component_version):
        """
        options: list of tuples:
        - short_opt: same as getopt
        - long_opt: same as getopt
        """
        self.component_name = component_name
        self.component_version = component_version
        self.config_file = "jcl.conf"
        self.server = "localhost"
        self.port = 5347
        self.secret = "secret"
        self.service_jid = "jcl.localhost"
        self.language = "en"
        self.db_url = "sqlite:///var/spool/jabber/jcl.db"
        self.pid_file = "/var/run/jabber/jcl.pid"
        self.options = [("c:", "config-file=", None,
                         " FILE\t\t\t\tConfiguration file to use",
                         lambda arg: self.set_attr("config_file", arg)),
                        ("S:", "server=", "jabber",
                         " SERVER_ADDRESS\t\t\tAddress of the Jabber server",
                         lambda arg: self.set_attr("server", arg)),
                        ("P:", "port=", "jabber",
                         " PORT\t\t\t\t\tPort of the Jabber server to connect the component",
                         lambda arg: self.set_attr("port", int(arg))),
                        ("s:", "secret=", "jabber",
                         " SECRET\t\t\t\tComponent password to connect to the Jabber server",
                         lambda arg: self.set_attr("secret", arg)),
                        ("j:", "service-jid=", "jabber",
                         " JID\t\t\t\tJID of the component",
                         lambda arg: self.set_attr("service_jid", arg)),
                        ("l:", "language=", "jabber",
                         " LANG\t\t\t\tDefault Language of the component",
                         lambda arg: self.set_attr("language", arg)),
                        ("u:", "db-url=", "db",
                         " URL\t\t\t\tDatabase URL",
                         lambda arg: self.set_attr("db_url", arg)),
                        ("p:", "pid-file=", "component",
                         " FILE\t\t\t\tPath of the PID file",
                         lambda arg: self.set_attr("pid_file", arg)),
                        ("d", "debug", None,
                         "\t\t\t\t\tEnable debug traces",
                         lambda arg: self.set_attr("debug", True)),
                        ("h", "help", None,
                         "\t\t\t\t\tThis help",
                         lambda arg: self.print_help())]
        self.logger = logging.getLogger()
        self.logger.addHandler(logging.StreamHandler())
        self.__debug = False

    def set_attr(self, attr, value):
        setattr(self, attr, value)

    def __configure_commandline_args(self, shortopts, longopts, cleanopts):
        (opts, args) = gnu_getopt(sys.argv[1:], shortopts, longopts)
        commandline_args = {}
        for (arg, value) in opts:
            clean_arg = arg.lstrip('-')
            if cleanopts.has_key(clean_arg):
                commandline_args[clean_arg] = value
        return commandline_args

    def __apply_commandline_args(self, commandline_args, cleanopts):
        for arg in commandline_args:
            value = commandline_args[arg]
            self.logger.debug("Applying argument " + arg + " = " +
                              value)
            cleanopts[arg][1](value)

    def __apply_configfile(self, commandline_args, cleanopts):
        if commandline_args.has_key("config_file"):
            self.config_file = commandline_args["config_file"]
        elif commandline_args.has_key("c"):
            self.config_file = commandline_args["c"]
        self.config = ConfigParser()
        self.logger.debug("Loading config file " + self.config_file)
        read_file = self.config.read(self.config_file)
        if read_file == []:
            self.logger.info("Creating empty config file " + self.config_file)
        else:
            for opt in cleanopts:
                if len(opt) > 1:
                    (section, set_func) = cleanopts[opt]
                    if section is not None:
                        attr = opt.replace("-", "_")
                        config_property = self.config.get(section, attr)
                        self.logger.debug("Setting " + attr + " = " +
                                          config_property +
                                          " from configuration file " +
                                          self.config_file)
                        set_func(config_property)

    def configure(self):
        """Apply configuration from command line and configuration file.
        command line arguments override configuration file properties.
        """
        shortopts = ""
        longopts = []
        cleanopts = {}
        for option in self.options:
            shortopts += option[0]
            longopts += [option[1]]
            cleanopts[option[0][0]] = (option[2], option[4])
            if option[1][-1:] == '=':
                cleanopts[option[1][:-1]] = (option[2], option[4])
            else:
                cleanopts[option[1]] = (option[2], option[4])

        commandline_args = self.__configure_commandline_args(shortopts, longopts, cleanopts)
        if commandline_args.has_key("debug") or commandline_args.has_key("d"):
            self.debug = True
            self.logger.debug("Debug activated")
        self.__apply_configfile(commandline_args, cleanopts)
        self.__apply_commandline_args(commandline_args, cleanopts)

    def _get_help(self):
        help = self.component_name + " v" + self.component_version + " help:\n"
        for option in self.options:
            if option[1][-1:] == '=':
                long_option = option[1][:-1]
            else:
                long_option = option[1]
            help += "\t-" + option[0][0] + ", --" + long_option + option[3] + "\n"
        return help

    def print_help(self):
        print self._get_help()
        sys.exit(0)

    def get_debug(self):
        return self.__debug

    def set_debug(self, value):
        self.__debug = value
        if self.__debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.CRITICAL)

    debug = property(get_debug, set_debug)


    def setup_db(self):
        Account.createTable(ifNotExists=True)
        PresenceAccount.createTable(ifNotExists=True)
        User.createTable(ifNotExists=True)
        LegacyJID.createTable(ifNotExists=True)

    def setup_pidfile(self):
        pidfile = open(self.pid_file, "w")
        pidfile.write(str(os.getpid()))
        pidfile.close()

    def _run(self, run_func):
        try:
            self.setup_pidfile()
            model.db_connection_str = self.db_url
            model.db_connect()
            self.setup_db()
            model.db_disconnect()
            self.logger.debug(self.component_name + " v" +
                              self.component_version + " is starting ...")
            restart = True
            while restart:
                restart = run_func()
            self.logger.debug(self.component_name + " is exiting")
        finally:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)

    def run(self):
        def run_func():
            component = JCLComponent(jid=self.service_jid,
                                     secret=self.secret,
                                     server=self.server,
                                     port=self.port,
                                     lang=Lang(self.language),
                                     config=self.config,
                                     config_file=self.config_file)
            return component.run()
        self._run(run_func)


def main():
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    del sys.setdefaultencoding
    import jcl
    from jcl.runner import JCLRunner
    runner = JCLRunner("JCL", jcl.version)
    runner.configure()
    runner.run()

if __name__ == '__main__':
    main()
