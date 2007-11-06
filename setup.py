##
## setup.py
## Login : <dax@happycoders.org>
## Started on  Tue Apr 17 21:12:33 2007 David Rousselie
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

from setuptools import setup, find_packages

setup(name='jcl',
      version='0.1',
      description='Jabber Component Library',
      author='David Rousselie',
      author_email='dax@happycoders.org',
      license="GPL",
      keywords="jabber component",
      url='http://people.happycoders.org/dax/projects/jcl',
      package_dir={'': 'src'},
      packages=find_packages('src', exclude=["*.tests",
                                             "*.tests.*",
                                             "tests.*",
                                             "tests"]),
      test_suite='jcl.tests.suite',
      install_requires=['SQLObject>=0.8', 'pyxmpp>=1.0', 'pysqlite>=2.0'])
