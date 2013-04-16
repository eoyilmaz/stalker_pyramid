# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
# 
# This file is part of Stalker.
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
from pyramid.httpexceptions import HTTPOk
from pyramid.view import view_config


@view_config(
    route_name='create_studio_dialog',
    renderer='templates/studio/dialog_create_studio.jinja2'
)
def create_studio_dialog(request):
    """creates the content of the create_studio_dialog
    """
    return {}


@view_config(
    route_name='create_studio'
)
def create_studio(request):
    """creates the studio
    """
    
    name = request.params['name']
    daily_working_hours = request.params['dwh']
    
    
    
    return HTTPOk()
