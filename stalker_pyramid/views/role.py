# -*- coding: utf-8 -*-

from pyramid.view import view_config

from stalker import db
from stalker.db.session import DBSession
from stalker import Role

import logging
#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


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

    result = DBSession.connection().execute(sql_query)

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
        DBSession.add(role)

    return role
