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

import os
import logging
import uuid

from stalker import Entity, Link, defaults
from stalker.db import DBSession

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPServerError, HTTPOk
import transaction

from stalker_pyramid.views import PermissionChecker, get_logged_in_user


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='dialog_upload_reference',
    renderer='templates/link/dialog_upload_reference.jinja2'
)
@view_config(
    route_name='dialog_upload_thumbnail',
    renderer='templates/link/dialog_upload_thumbnail.jinja2'
)
def dialog_upload_file(request):
    """fills the upload file dialog, used both in uploading thumbnails and
    references
    """
    entity_id = request.matchdict.get('entity_id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('entity_id : %s' % entity_id)
    logger.debug('entity    : %s' % entity)

    return {
        'entity': entity,
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='upload_file',
    renderer='json'
)
def upload_file(request):
    """uploads a file to the server, creates a Link instance in server and
    returns the created link id to the UI to let the front end request a
    linkage between the entity and the uploaded file
    """
    try:
        new_link = upload_file_to_server(request, 'uploadedfile')
    except IOError:
        HTTPServerError()
    else:
        # store the link object
        DBSession.add(new_link)

        return {
            'file': new_link.full_path,
            'name': new_link.original_filename,
            'width': 320,
            'height': 240,
            'type': os.path.splitext(new_link.original_filename)[1],
            'link_id': new_link.id
        }


@view_config(
    route_name='assign_thumbnail',
)
def assign_thumbnail(request):
    """assigns the thumbnail to the given entity
    """
    link_id = request.params.get('link_id', -1)
    entity_id = request.params.get('entity_id', -1)

    link = Link.query.filter_by(id=link_id).first()
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('link_id   : %s' % link_id)
    logger.debug('link      : %s' % link)
    logger.debug('entity_id : %s' % entity_id)
    logger.debug('entity    : %s' % entity)

    if entity and link:
        entity.thumbnail = link
        DBSession.add(entity)
        DBSession.add(link)

    return HTTPOk()

@view_config(
    route_name='assign_reference',
)
def assign_reference(request):
    """assigns the link to the given entity as a new reference
    """
    link_id = request.params.get('link_id', -1)
    entity_id = request.params.get('entity_id', -1)

    link = Link.query.filter_by(id=link_id).first()
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('link_id   : %s' % link_id)
    logger.debug('link      : %s' % link)
    logger.debug('entity_id : %s' % entity_id)
    logger.debug('entity    : %s' % entity)

    if entity and link:
        entity.references.append(link)
        DBSession.add(entity)
        DBSession.add(link)

    return HTTPOk()





@view_config(route_name='get_project_references', renderer='json')
@view_config(route_name='get_task_references', renderer='json')
@view_config(route_name='get_asset_references', renderer='json')
@view_config(route_name='get_shot_references', renderer='json')
@view_config(route_name='get_sequence_references', renderer='json')
def get_entity_references(request):
    """called when the references to Project/Task/Asset/Shot/Sequence is
    requested
    """
    logger.debug('asking references for task')
    entity_id = request.matchdict.get('entity_id', -1)
    entity = Entity.query.filter(Entity.id==entity_id).first()
    if entity:
        return [
            {
                'full_path': link.full_path,
                'original_filename': link.original_filename,
            } for link in entity.references]
    return []

# view_config(
#     route_name='upload_reference'
# )
# def upload_reference(request):
#     """called when uploading a reference
#     """
# 
#     entity_id = request.matchdict.get('entity_id')
#     entity = Entity.query.filter_by(id=entity_id).first()
# 
#     # check if entity accepts references
#     try:
#         if not entity.accepts_references:
#             raise HTTPServerError()
#     except AttributeError as e:
#         raise HTTPServerError(msg=e.message)
# 
#     filename, file_path = upload_file_to_server(request, 'link')
# 
#     # create a Link and assign it to the given Referencable Entity
#     new_link = Link(
#         full_path= file_path,
#         original_filename=filename
#     )
# 
#     # assign it as a reference
#     entity.references.append(new_link)
# 
#     DBSession.add(new_link)
# 
#     return HTTPOk()


def upload_file_to_server(request, file_param_name):
    """Uploads a file from a request.POST to the given path

    Uses the hex representation of a uuid4 sequence as the filename.

    The first two digits of the uuid4 is used for the first folder name,
    there are 256 possible variations, then the third and fourth characters
    are used for the second folder name (again 256 other possibilities) and
    then the uuid4 sequence with the original file extension generates the
    filename.

    The extension is used on purpose where OSes like windows can infer the file
    type from the extension.

    SPL/{{uuid4[:2]}}/{{uuid4[2:4]}}//{{uuuid4}}.extension

    :param request: The request object.
    :param str file_param_name: The name of the parameter that holds the file.
    :returns (str, str): The original filename and the file path on the server.
    """
    # get the filename
    file_param = request.POST.get(file_param_name)
    filename = file_param.filename
    extension = os.path.splitext(filename)[1]
    input_file = file_param.file

    logger.debug('file_param : %s' % file_param)
    logger.debug('filename   : %s' % filename)
    logger.debug('extension  : %s' % extension)
    logger.debug('input_file : %s' % input_file)

    # upload it to the stalker server side storage path
    new_filename = uuid.uuid4().hex + extension

    first_folder = new_filename[:2]
    second_folder = new_filename[2:4]

    file_path = os.path.join(
        defaults.server_side_storage_path,
        first_folder,
        second_folder
    )

    link_path = os.path.join(
        'SPL',
        first_folder,
        second_folder
    )

    file_full_path = os.path.join(
        file_path,
        new_filename
    )

    link_full_path = os.path.join(
        link_path,
        new_filename
    )

    # write down to a temp file first
    temp_file_path = file_full_path + '~'

    # create folders
    os.makedirs(file_path)

    output_file = open(temp_file_path, 'wb')  # TODO: guess ascii or binary mode

    input_file.seek(0)
    while True: # TODO: use 'with'
        data = input_file.read(2 << 16)
        if not data:
            break
        output_file.write(data)
    output_file.close()

    # data is written completely, rename temp file to original file
    os.rename(temp_file_path, file_full_path)

    # create a Link instance and return it
    new_link = Link(
        full_path=link_full_path,
        original_filename=filename,
        created_by=get_logged_in_user(request)
    )
    DBSession.add(new_link)
    transaction.commit()

    return new_link
