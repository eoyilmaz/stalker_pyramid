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
from pyramid.view import view_config
from stalker import Type


@view_config(
    route_name='get_types',
    renderer='json'
)
def get_types(request):
    """returns the types in the database use the 'target_entity_type' parameter
    of for the desired type with the given target_entity_type
    """
    target_entity_type = request.params.get('target_entity_type')
    if target_entity_type:
        return [
            type_.name
            for type_ in Type.query.filter(
                Type._target_entity_type == target_entity_type
            ).all()
        ]
    else:
        return [type_.name for type_ in Type.query.all()]
