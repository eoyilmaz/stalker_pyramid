# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
#
# This file is part of Stalker Pyramid.
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
from pyramid.view import view_config
from stalker import Tag


@view_config(
    route_name='get_tags',
    renderer='json'
)
def get_tags(request):
    """returns all the tags in database
    """
    as_list = request.params.get('as_list')
    if as_list:
        return [
            tag.name
            for tag in Tag.query.all()
        ]
    else:
        return [
            {'name': tag.name,
             'id': tag.id
            }
            for tag in Tag.query.all()
        ]
