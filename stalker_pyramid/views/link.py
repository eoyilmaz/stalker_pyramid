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

import Image

from stalker import Entity, Link, defaults
from stalker.db import DBSession
from pyramid.response import Response

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk

import transaction

from stalker_pyramid.views import (get_logged_in_user, get_multi_integer,
                                   get_tags, StdErrToHTMLConverter)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='upload_files',
    renderer='json'
)
def upload_files(request):
    """uploads a list of files to the server, creates Link instances in server
    and returns the created link ids with a response to let the front end
    request a linkage between the entity and the uploaded files
    """
    # decide if it is single or multiple files
    file_params = request.POST.getall('file')
    logger.debug('file_params: %s ' % file_params)

    try:
        new_links = upload_files_to_server(request, file_params)
    except IOError as e:
        c = StdErrToHTMLConverter(e)
        response = Response(c.html())
        response.status_int = 500
        return response
    else:
        # store the link object
        DBSession.add_all(new_links)

        logger.debug('created links for uploaded files: %s' % new_links)

        return {
            'link_ids': [link.id for link in new_links]
        }

@view_config(
    route_name='assign_thumbnail',
)
def assign_thumbnail(request):
    """assigns the thumbnail to the given entity
    """
    link_ids = get_multi_integer(request, 'link_ids')
    entity_id = request.params.get('entity_id', -1)

    link = Link.query.filter(Link.id.in_(link_ids)).first()
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('link_ids  : %s' % link_ids)
    logger.debug('link      : %s' % link)
    logger.debug('entity_id : %s' % entity_id)
    logger.debug('entity    : %s' % entity)

    logged_in_user = get_logged_in_user(request)

    if entity and link:
        entity.thumbnail = link

        # resize the thumbnail
        file_full_path = convert_file_link_to_full_path(link.full_path)
        img = Image.open(file_full_path)
        img.thumbnail((512, 512))
        img.thumbnail((256, 256), Image.ANTIALIAS)
        img.save(file_full_path)

        DBSession.add(entity)
        DBSession.add(link)

    return HTTPOk()

@view_config(
    route_name='assign_reference',
)
def assign_reference(request):
    """assigns the link to the given entity as a new reference
    """
    link_ids = get_multi_integer(request, 'link_ids[]')
    removed_link_ids = get_multi_integer(request, 'removed_link_ids[]')
    entity_id = request.params.get('entity_id', -1)

    entity = Entity.query.filter_by(id=entity_id).first()
    links = Link.query.filter(Link.id.in_(link_ids)).all()
    removed_links = Link.query.filter(Link.id.in_(removed_link_ids)).all()

    # Tags
    logger.debug('request.POST: %s' % request.POST)
    tags = get_tags(request)

    logged_in_user = get_logged_in_user(request)

    logger.debug('link_ids      : %s' % link_ids)
    logger.debug('links         : %s' % links)
    logger.debug('entity_id     : %s' % entity_id)
    logger.debug('entity        : %s' % entity)
    logger.debug('tags          : %s' % tags)
    logger.debug('removed_links : %s' % removed_links)

    # remove all the removed links
    for removed_link in removed_links:
        # no need to search for any linked tasks here
        DBSession.delete(removed_link)

    if entity and links:
        entity.references.extend(links)

        # assign all the tags to the links
        for link in links:
            link.tags.extend(tags)
            # generate thumbnail
            thumbnail = generate_thumbnail(link)
            link.thumbnail = thumbnail
            thumbnail.created_by = logged_in_user
            DBSession.add(thumbnail)

        DBSession.add(entity)
        DBSession.add_all(links)

    return HTTPOk()


def convert_file_link_to_full_path(link_path):
    """converts the given Stalker Pyramid Local file link to a real full path

    :param link_path: A link to a file in SPL starting with SPL
      (ex: SPL/b0/e6/b0e64b16c6bd4857a91be47fb2517b53.jpg)
    :returns: str
    """
    link_full_path = link_path[len('SPL/'):]
    file_full_path = os.path.join(
        defaults.server_side_storage_path,
        link_full_path
    )
    return file_full_path


def generate_thumbnail(link):
    """Generates a thumbnail for the given link

    :param link: Generates a thumbnail for the given link
    :return:
    """
    file_full_path = convert_file_link_to_full_path(link.full_path)

    extension = os.path.splitext(file_full_path)[-1]

    link_original_filename, link_original_extension = \
        os.path.splitext(link.original_filename)

    thumbnail_original_filename = link_original_filename + '_t' + \
                                  link_original_extension

    # generate thumbnails for those references
    img = Image.open(file_full_path)
    img.thumbnail((512, 512)) # TODO: connect this to a config variable
    img.thumbnail((256, 256), Image.ANTIALIAS)

    thumbnail_full_path, thumbnail_link_full_path = generate_local_file_path(extension)

    # create the dirs before saving
    os.makedirs(os.path.dirname(thumbnail_full_path))
    img.save(thumbnail_full_path)

    # create a link to be the thumbnail of the original
    thumbnail = Link(
        full_path=thumbnail_link_full_path,
        original_filename=thumbnail_original_filename
    )
    return thumbnail



@view_config(route_name='get_project_references', renderer='json')
@view_config(route_name='get_task_references', renderer='json')
@view_config(route_name='get_asset_references', renderer='json')
@view_config(route_name='get_shot_references', renderer='json')
@view_config(route_name='get_sequence_references', renderer='json')
@view_config(route_name='get_entity_references', renderer='json')
def get_entity_references(request):
    """called when the references to Project/Task/Asset/Shot/Sequence is
    requested
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id==entity_id).first()
    logger.debug('asking references for entity: %s' % entity)

    # TODO: there should be a 'get all references' for Projects for example
    #       which returns all the references related to this project.

    if entity:
        return [
            {
                'id': link.id,
                'full_path': link.full_path,
                'original_filename': link.original_filename,
                'thumbnail': link.thumbnail.full_path if link.thumbnail else link.full_path,
                'tags': [tag.name for tag in link.tags]
            } for link in entity.references]
    return []


def generate_local_file_path(extension):
    """generates file paths in server side storage

    :param extension: desired file extension
    :return:
    """
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
    return file_full_path, link_full_path


def upload_files_to_server(request, file_params):
    """Uploads files from a request.POST to the given path

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
    :param str file_param_name: The name of the parameter that holds the files.
    :returns [(str, str)]: The original filename and the file path on the server.
    """
    links = []
    # get the file names
    for file_param in file_params:
        # file_param = request.POST.get(file_param_name)
        filename = file_param.filename
        extension = os.path.splitext(filename)[1]
        input_file = file_param.file

        logger.debug('file_param : %s' % file_param)
        logger.debug('filename   : %s' % filename)
        logger.debug('extension  : %s' % extension)
        logger.debug('input_file : %s' % input_file)

        file_full_path, link_full_path = generate_local_file_path(extension)
        file_path = os.path.dirname(file_full_path)

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
        links.append(new_link)

    transaction.commit()
    return links

@view_config(
    route_name='delete_reference',
    permission='Delete_Link'
)
def delete_reference(request):
    """deletes the reference with the given ID
    """
    ref_id = request.matchdict.get('id')
    ref = Link.query.get(ref_id)

    files_to_remove = []
    if ref:
        original_filename = ref.original_filename
        # check if it has a thumbnail
        if ref.thumbnail:
            # remove the file first
            files_to_remove.append(ref.thumbnail.full_path)

            # delete the thumbnail Link from the database
            DBSession.delete(ref.thumbnail)
        # remove the reference itself
        files_to_remove.append(ref.full_path)

        # delete the ref Link from the database
        # IMPORTANT: Because there is no link from Link -> Task deleting a Link
        #            directly will raise an IntegrityError, so remove the Link
        #            from the associated Task before deleting it
        from stalker import Task
        for task in Task.query.filter(Task.references.contains(ref)).all():
            logger.debug('%s is referencing %s, breaking this relation' % (task, ref))
            task.references.remove(ref)
        DBSession.delete(ref)

        # now delete files
        for f in files_to_remove:
            # convert the paths to system path
            f_system = convert_file_link_to_full_path(f)
            try:
                os.remove(f_system)
            except OSError:
                pass

        response = Response('%s removed successfully' % original_filename)
        response.status_int = 200
        return response
    else:
        response = Response('No ref with id : %i' % ref_id)
        response.status_int = 500
        return response
