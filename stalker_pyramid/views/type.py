# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
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

from stalker import db
from stalker import Type

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='get_types',
    renderer='json'
)
def get_types(request):
    """returns the types in the database use the 'target_entity_type' parameter
    of for the desired type with the given target_entity_type
    """
    target_entity_type = request.params.get('target_entity_type')

    sql_query = """select
    "SimpleEntities".id,
    "SimpleEntities".name
from "Types"
join "SimpleEntities" on "Types".id = "SimpleEntities".id
"""

    if target_entity_type:
        sql_query += \
            """where "Types".target_entity_type = '%s'
            """ % target_entity_type

    sql_query += """order by "SimpleEntities".name"""



    result = db.DBSession.connection().execute(sql_query)

    return [
        {
            'id': r[0],
            'name': r[1]
        }
        for r in result.fetchall()
    ]


def query_type(entity_type, type_name):
    """returns a Type instance either it creates a new one or gets it from DB
    """
    if not type_name:
        return None

    type_query = Type.query.filter_by(target_entity_type=entity_type)
    type_ = type_query.filter_by(name=type_name).first()
    if type_name and type_ is None:
        # create a new Type
        logger.debug('creating new %s type: %s' % (
            entity_type.lower(), type_name)
        )
        type_ = Type(
            name=type_name,
            code=type_name,
            target_entity_type=entity_type
        )
        db.DBSession.add(type_)

    return type_
