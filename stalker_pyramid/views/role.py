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
from stalker import Role

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='get_roles',
    renderer='json'
)
def get_roles(request):
    """returns the roles in the database use the
    """
    sql_query = """select
    "SimpleEntities".id,
    "SimpleEntities".name
from "Roles"
join "SimpleEntities" on "Roles".id = "SimpleEntities".id
order by "SimpleEntities".name
"""

    result = db.DBSession.connection().execute(sql_query)

    return [
        {
            'id': r[0],
            'name': r[1]
        }
        for r in result.fetchall()
    ]


def query_role(role_name):
    """returns a Role instance either it creates a new one or gets it from DB
    """
    if not role_name:
        return None

    role = Role.query.filter_by(name=role_name).first()
    if role_name and role is None:
        # create a new Type
        logger.debug('creating new role: %s' % role_name)
        role = Role(name=role_name)
        db.DBSession.add(role)

    return role
