# -*- coding: utf-8 -*-

import pytz
import datetime
from pyramid.httpexceptions import HTTPOk

from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import Structure, FilenameTemplate

import logging
from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   get_multi_integer)

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.WARNING)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='dialog_create_structure',
    renderer='templates/structure/dialog_create_structure.jinja2'
)
def dialog_create_structure(request):
    """fills the create structure dialog
    """
    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='dialog_update_structure',
    renderer='templates/structure/dialog_create_structure.jinja2'
)
def dialog_update_structure(request):
    """fills the update structure dialog
    """
    structure_id = request.matchdict.get('id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'structure': structure
    }


@view_config(
    route_name='create_structure'
)
def create_structure(request):
    """creates a structure
    """
    logged_in_user = get_logged_in_user(request)

    # get parameters
    name = request.params.get('name')
    custom_template = request.params.get('custom_template')
    ft_ids = get_multi_integer(request, 'filename_templates')
    fts = FilenameTemplate.query.filter(FilenameTemplate.id.in_(ft_ids)).all()

    if name and custom_template:
        # create a new structure
        new_structure = Structure(
            name=name,
            custom_template=custom_template,
            templates=fts,
            created_by=logged_in_user,
        )
        DBSession.add(new_structure)

    return HTTPOk()


@view_config(
    route_name='update_structure'
)
def update_structure(request):
    """updates a structure
    """
    logged_in_user = get_logged_in_user(request)

    # get params
    structure_id = request.params.get('structure_id')
    structure = Structure.query.filter_by(id=structure_id).first()

    name = request.params.get('name')
    custom_template = request.params.get('custom_template')

    # get all FilenameTemplates
    ft_ids = get_multi_integer(request, 'filename_templates')
    fts = FilenameTemplate.query.filter(FilenameTemplate.id.in_(ft_ids)).all()

    if name:
        # update structure
        structure.name = name
        structure.custom_template = custom_template
        structure.templates = fts
        structure.updated_by = logged_in_user
        utc_now = datetime.datetime.now(pytz.utc)
        structure.date_updated = utc_now

        DBSession.add(structure)

    return HTTPOk()


@view_config(
    route_name='get_structures',
    renderer='json'
)
def get_structures(request):
    """returns all the structures in the database
    """
    return [
        {
            'id': structure.id,
            'name': structure.name
        }
        for structure in Structure.query.all()
    ]
