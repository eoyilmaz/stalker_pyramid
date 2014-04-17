# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
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
import time
import logging
import uuid
import base64
import transaction
from HTMLParser import HTMLParser
from PIL import Image

from pyramid.response import Response, FileResponse
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk

from stalker.db import DBSession
from stalker import Entity, Link, defaults

from stalker_pyramid.views import (get_logged_in_user, get_multi_integer,
                                   get_tags, StdErrToHTMLConverter)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ImageData(object):
    """class for handling image data coming from html
    """

    def __init__(self, data):
        self.raw_data = data
        self.type = ''
        self.extension = ''
        self.base64_data = ''
        self.parse()

    def parse(self):
        """parses the data
        """
        temp_data = self.raw_data.split(';')
        self.type = temp_data[0].split(':')[1]
        self.extension = '.%s' % self.type.split('/')[1]
        self.base64_data = temp_data[1].split(',')[1]


class ImgToLinkConverter(HTMLParser):
    """An HTMLParser derivative that parses HTML data and replaces the ``src``
    attributes in <img> tags with Link paths
    """

    def __init__(self):
        HTMLParser.__init__(self)
        self.raw_img_to_url = []
        self.links = []
        self.raw_data = ''

    def feed(self, data):
        """the overridden feed method which stores the original data
        """
        HTMLParser.feed(self, data)
        self.raw_data = data

    def handle_starttag(self, tag, attrs):
        # print tag, attrs
        attrs_dict = {}
        if tag == 'img':
            # convert attributes to a dict
            for attr in attrs:
                attrs_dict[attr[0]] = attr[1]
            src = attrs_dict['src']

            # check if it contains data
            if not src.startswith('data'):
                return

            # get the file type and use it as extension
            image_data = ImageData(src)
            # generate a path for this file
            file_full_path, link_full_path = \
                generate_local_file_path(image_data.extension)
            original_name = os.path.basename(link_full_path)

            # create folders
            try:
                os.makedirs(os.path.dirname(file_full_path))
            except OSError:
                # path exists
                pass

            with open(file_full_path, 'wb') as f:
                f.write(
                    base64.decodestring(image_data.base64_data)
                )

            # create Link instances
            # create a Link instance and return it
            new_link = Link(
                full_path=link_full_path,
                original_filename=original_name,
            )
            DBSession.add(new_link)
            self.links.append(new_link)

            # save data to be replaced in the raw content
            self.raw_img_to_url.append(
                (src, link_full_path)
            )

    def replace_urls(self):
        """replaces the raw image data with the url in the given data
        """
        for img_to_url in self.raw_img_to_url:
            self.raw_data = self.raw_data.replace(
                img_to_url[0],
                '/%s' % img_to_url[1]
            )
        return self.raw_data


def replace_img_data_with_links(raw_data):
    """replaces the image data coming in base64 form with Links

    :param raw_data: The raw html data that may contain <img> elements
    :returns str, list: string containing html data with the ``src`` parameters
      of <img> tags are replaced with Link addresses and the generated links
    """
    parser = ImgToLinkConverter()
    parser.feed(raw_data)
    parser.replace_urls()
    return parser.raw_data, parser.links


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
        transaction.abort()
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
    link_ids = get_multi_integer(request, 'link_ids[]')
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
        if img.format != 'GIF':
            img.thumbnail((1024, 1024))
            img.thumbnail((512, 512), Image.ANTIALIAS)
            img.save(file_full_path)

        DBSession.add(entity)
        DBSession.add(link)

    return HTTPOk()


@view_config(
    route_name='assign_reference',
    renderer='json'
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
            # add the ones not in the tags already
            for tag in tags:
                if tag not in link.tags:
                    link.tags.append(tag)
            #link.tags.extend(tags)
            # generate thumbnail
            thumbnail = generate_thumbnail(link)
            link.thumbnail = thumbnail
            thumbnail.created_by = logged_in_user
            DBSession.add(thumbnail)

        DBSession.add(entity)
        DBSession.add_all(links)

    # return new links as json data
    # in response text
    return [
        {
            'id': link.id,
            'full_path': link.full_path,
            'original_filename': link.original_filename,
            'thumbnail_full_path': link.thumbnail.full_path
            if link.thumbnail else link.full_path,
            'tags': [tag.name for tag in link.tags]
        } for link in links
    ]


def convert_file_link_to_full_path(link_path):
    """converts the given Stalker Pyramid Local file link to a real full path

    :param link_path: A link to a file in SPL starting with SPL
      (ex: SPL/b0/e6/b0e64b16c6bd4857a91be47fb2517b53.jpg)
    :returns: str
    """
    if 'SPL/' in link_path:
        link_full_path = link_path[len('SPL/'):]
    else:
        link_full_path = link_path

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
    # TODO: support video files (somehow, gif thumbs may be???)
    file_full_path = convert_file_link_to_full_path(link.full_path)

    extension = os.path.splitext(file_full_path)[-1]

    link_original_filename, link_original_extension = \
        os.path.splitext(link.original_filename)

    thumbnail_original_filename = \
        link_original_filename + '_t' + link_original_extension

    # generate thumbnails for those references
    img = Image.open(file_full_path)
    img.thumbnail((1024, 1024))  # TODO: connect this to a config variable
    img.thumbnail((512, 512), Image.ANTIALIAS)

    thumbnail_full_path, thumbnail_link_full_path = \
        generate_local_file_path(extension)

    # create the dirs before saving
    try:
        os.makedirs(os.path.dirname(thumbnail_full_path))
    except OSError:  # path exists
        pass
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
    entity = Entity.query.filter(Entity.id == entity_id).first()
    logger.debug('asking references for entity: %s' % entity)

    offset = request.params.get('offset', 0)
    limit = request.params.get('limit', 1e10)

    search_string = request.params.get('search', '')
    logger.debug('search_string: %s' % search_string)

    search_query = ''
    if search_string != "":
        search_string_buffer = ['and (']
        for i, s in enumerate(search_string.split(' ')):
            if i != 0:
                search_string_buffer.append('or')
            tmp_search_query = """
            '%(search_str)s' = any (entity_tags.tags)
            or tasks.entity_type = '%(search_str)s'
            or tasks.full_path ilike '%(search_wide)s'
            or "Links".original_filename ilike '%(search_wide)s'
            """ % {
                'search_str': s,
                'search_wide': '%{s}%'.format(s=s)
            }
            search_string_buffer.append(tmp_search_query)
        search_string_buffer.append(')')
        search_query = '\n'.join(search_string_buffer)
    logger.debug('search_query: %s' % search_query)

    # we need to do that import here
    from stalker_pyramid.views.task import \
        query_of_tasks_hierarchical_name_table

    # using Raw SQL queries here to fasten things up quite a bit and also do
    # some fancy queries like getting all the references of tasks of a project
    # also with their tags
    sql_query = """
    -- select all links assigned to a project tasks or assigned to a task and its children
select
    "Links".id,
    "Links".full_path,
    "Links".original_filename,
    "Thumbnails".full_path as "thumbnail_full_path",
    entity_tags.tags,
    array_agg(tasks.id) as entity_id,
    array_agg(tasks.full_path) as full_path,
    array_agg(tasks.entity_type) as entity_type
from (
    %(tasks_hierarchical_name_table)s
) as tasks
join "Task_References" on tasks.id = "Task_References".task_id
join "Links" on "Task_References".link_id = "Links".id
join "SimpleEntities" as "Link_SimpleEntities" on "Links".id = "Link_SimpleEntities".id
join "Links" as "Thumbnails" on "Link_SimpleEntities".thumbnail_id = "Thumbnails".id
left outer join (
    select
        "Links".id,
        array_agg("Tag_SimpleEntities".name) as tags
    from "Links"
    join "Entity_Tags" on "Links".id = "Entity_Tags".entity_id
    join "SimpleEntities" as "Tag_SimpleEntities" on "Entity_Tags".tag_id = "Tag_SimpleEntities".id
    group by "Links".id
) as entity_tags on "Links".id = entity_tags.id

where %(id)s = any (tasks.path) %(search_string)s

group by "Links".id,
    "Links".full_path,
    "Links".original_filename,
    "Thumbnails".id,
    entity_tags.tags

offset %(offset)s
limit %(limit)s
    """ % {
        'id': entity_id,
        'tasks_hierarchical_name_table':
        query_of_tasks_hierarchical_name_table(),
        'search_string': search_query,
        'offset': offset,
        'limit': limit
    }

    # if offset and limit:
    #     sql_query += "offset %s limit %s" % (offset, limit)

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return_val = [
        {
            'id': r[0],
            'full_path': r[1],
            'original_filename': r[2],
            'thumbnail_full_path': r[3],
            'tags': r[4],
            'entity_ids': r[5],
            'entity_names': r[6],
            'entity_types': r[7]
        } for r in result.fetchall()
    ]

    return return_val


@view_config(route_name='get_project_references_count', renderer='json')
@view_config(route_name='get_task_references_count', renderer='json')
@view_config(route_name='get_asset_references_count', renderer='json')
@view_config(route_name='get_shot_references_count', renderer='json')
@view_config(route_name='get_sequence_references_count', renderer='json')
@view_config(route_name='get_entity_references_count', renderer='json')
def get_entity_references_count(request):
    """called when the count of references to Project/Task/Asset/Shot/Sequence
    is requested
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()
    logger.debug('asking references for entity: %s' % entity)

    offset = request.params.get('offset', 0)
    limit = request.params.get('limit', 1e10)

    search_string = request.params.get('search', '')
    logger.debug('search_string: %s' % search_string)

    search_query = ''
    if search_string != "":
        search_string_buffer = ['and (']
        for i, s in enumerate(search_string.split(' ')):
            if i != 0:
                search_string_buffer.append('or')
            tmp_search_query = """
            '%(search_str)s' = any (entity_tags.tags)
            or tasks.entity_type = '%(search_str)s'
            or tasks.full_path ilike '%(search_wide)s'
            or "Links".original_filename ilike '%(search_wide)s'
            """ % {
                'search_str': s,
                'search_wide': '%{s}%'.format(s=s)
            }
            search_string_buffer.append(tmp_search_query)
        search_string_buffer.append(')')
        search_query = '\n'.join(search_string_buffer)
    logger.debug('search_query: %s' % search_query)

    # we need to do that import here
    from stalker_pyramid.views.task import \
        query_of_tasks_hierarchical_name_table

    # using Raw SQL queries here to fasten things up quite a bit and also do
    # some fancy queries like getting all the references of tasks of a project
    # also with their tags
    sql_query = """
    -- select all links assigned to a project tasks or assigned to a task and its children
select count(1) from (
    select
        "Links".id,
        "Links".full_path,
        "Links".original_filename,
        "Thumbnails".full_path as "thumbnail_full_path",
        entity_tags.tags,
        array_agg(tasks.id) as entity_id,
        array_agg(tasks.full_path) as full_path,
        array_agg(tasks.entity_type) as entity_type
    from (
        %(tasks_hierarchical_name_table)s
    ) as tasks
    join "Task_References" on tasks.id = "Task_References".task_id
    join "Links" on "Task_References".link_id = "Links".id
    join "SimpleEntities" as "Link_SimpleEntities" on "Links".id = "Link_SimpleEntities".id
    join "Links" as "Thumbnails" on "Link_SimpleEntities".thumbnail_id = "Thumbnails".id
    left outer join (
        select
            "Links".id,
            array_agg("Tag_SimpleEntities".name) as tags
        from "Links"
        join "Entity_Tags" on "Links".id = "Entity_Tags".entity_id
        join "SimpleEntities" as "Tag_SimpleEntities" on "Entity_Tags".tag_id = "Tag_SimpleEntities".id
        group by "Links".id
    ) as entity_tags on "Links".id = entity_tags.id

    where %(id)s = any (tasks.path) %(search_string)s

    group by "Links".id,
        "Links".full_path,
        "Links".original_filename,
        "Thumbnails".id,
        entity_tags.tags
    ) as data
    """ % {
        'id': entity_id,
        'tasks_hierarchical_name_table':
        query_of_tasks_hierarchical_name_table(),
        'search_string': search_query
    }

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]


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

    SPL/{{uuid4[:2]}}/{{uuid4[2:4]}}//{{uuid4}}.extension

    :param request: The request object.
    :param str file_params: The name of the parameter that holds the files.
    :returns [(str, str)]: The original filename and the file path on the
    server.
    """
    links = []
    # get the file names
    for file_param in file_params:
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
        try:
            os.makedirs(file_path)
        except OSError:  # Path exist
            pass

        output_file = open(temp_file_path, 'wb')  # TODO: guess ascii or binary mode

        input_file.seek(0)
        while True:  # TODO: use 'with'
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
            logger.debug('%s is referencing %s, '
                         'breaking this relation' % (task, ref))
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
        transaction.abort()
        return response


@view_config(
    route_name='serve_files'
)
def serve_files(request):
    """serves files in the stalker server side storage
    """
    partial_file_path = request.matchdict['partial_file_path']
    file_full_path = convert_file_link_to_full_path(partial_file_path)
    return FileResponse(file_full_path)


@view_config(
    route_name='forced_download_files'
)
def force_download_files(request):
    """serves files but forces to download
    """
    partial_file_path = request.matchdict['partial_file_path']
    file_full_path = convert_file_link_to_full_path(partial_file_path)
    # get the link to get the original file name
    link = Link.query.filter(
        Link.full_path == 'SPL/' + partial_file_path).first()
    if link:
        original_filename = link.original_filename
    else:
        original_filename = os.path.basename(file_full_path)

    response = FileResponse(
        file_full_path,
        request=request,
        content_type='application/force-download',
    )
    # update the content-disposition header
    response.headers['content-disposition'] = \
        str('attachment; filename=' + original_filename)
    return response
