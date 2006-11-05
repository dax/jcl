##
## error.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Sun Nov  5 20:13:48 2006 David Rousselie
## $Id$
## 
## Copyright (C) 2006 David Rousselie
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

"""Jabber exception classes"""

__revision__ = "$Id: error.py,v 1.1 2006/11/05 20:13:48 dax Exp $"

class FieldError(Exception):
    """Error raised when error exists on Jabber Data Form fields"""
    pass

