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
import shutil
import subprocess
import tempfile
import datetime
import copy
import os
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
from stalker import Entity, Link, defaults, Repository, Version, Daily

from stalker_pyramid.views import (get_logged_in_user, get_tags,
                                   StdErrToHTMLConverter, local_to_utc)


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
            file_full_path = \
                MediaManager.generate_local_file_path(image_data.extension)
            link_full_path = \
                MediaManager.convert_full_path_to_file_link(file_full_path)
            original_name = os.path.basename(file_full_path)

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
    """Uploads a list of files to the server.

    It will store the files in a temp folder and return the placement of the
    files in the server to let the front end request a linkage between the
    entity and the uploaded files, like using them as a reference for some
    entities or as a thumbnail for others etc.
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    # decide if it is single or multiple files
    file_params = request.POST.getall('file')
    logger.debug('file_params: %s ' % file_params)

    mm = MediaManager()
    try:
        new_files_info = mm.upload_with_request_params(file_params)
    except IOError as e:
        c = StdErrToHTMLConverter(e)
        response = Response(c.html())
        response.status_int = 500
        transaction.abort()
        return response
    else:
        logger.debug('created links for uploaded files: %s' % new_files_info)

        return {
            'files': new_files_info
        }


@view_config(
    route_name='assign_thumbnail',
)
def assign_thumbnail(request):
    """assigns the thumbnail to the given entity
    """
    # just to make it safe
    logged_in_user = get_logged_in_user(request)

    full_path = request.params.get('full_path')
    entity_id = request.params.get('entity_id', -1)

    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('full_path : %s' % full_path)
    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity     : %s' % entity)

    if entity and full_path:
        mm = MediaManager()
        thumbnail_path = mm.generate_thumbnail(full_path)
        thumbnail_extension = os.path.splitext(thumbnail_path)[-1]

        # move the thumbnail to SPL
        thumbnail_spl_path = mm.generate_local_file_path(
            extension=thumbnail_extension
        )
        thumbnail_spl_relative_path = thumbnail_spl_path.replace(
            defaults.server_side_storage_path, 'SPL'
        )
        try:
            os.makedirs(os.path.dirname(thumbnail_spl_path))
        except OSError:  # dir exists
            pass

        # move the file there
        shutil.move(thumbnail_path, thumbnail_spl_path)

        logger.debug('thumbnail_path              : %s' % thumbnail_path)
        logger.debug('thumbnail_extension         : %s' % thumbnail_extension)
        logger.debug('thumbnail_spl_path          : %s' % thumbnail_spl_path)
        logger.debug('thumbnail_spl_relative_path : %s' %
                     thumbnail_spl_relative_path)

        # now create a link for the thumbnail
        utc_now = local_to_utc(datetime.datetime.now())
        link = Link(
            full_path=thumbnail_spl_relative_path,
            created_by=logged_in_user,
            date_created=utc_now
        )
        entity.thumbnail = link

        DBSession.add(entity)
        DBSession.add(link)

    return HTTPOk()


@view_config(
    route_name='assign_reference',
    renderer='json'
)
def assign_reference(request):
    """assigns the given files as references for the given entity
    """
    logged_in_user = get_logged_in_user(request)

    full_paths = request.POST.getall('full_paths[]')
    original_filenames = request.POST.getall('original_filenames[]')

    entity_id = request.params.get('entity_id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    # Tags
    tags = get_tags(request)

    logger.debug('full_paths         : %s' % full_paths)
    logger.debug('original_filenames : %s' % original_filenames)
    logger.debug('entity_id          : %s' % entity_id)
    logger.debug('entity             : %s' % entity)
    logger.debug('tags               : %s' % tags)

    links = []
    if entity and full_paths:
        mm = MediaManager()
        for full_path, original_filename in zip(full_paths, original_filenames):
            l = mm.upload_reference(entity, open(full_path), original_filename)
            l.created_by = logged_in_user
            l.date_created = local_to_utc(datetime.datetime.now())
            l.date_updated = l.date_created

            for tag in tags:
                if tag not in l.tags:
                    l.tags.extend(tags)

            DBSession.add(l)
            links.append(l)

    # to generate ids for links
    transaction.commit()
    DBSession.add_all(links)

    # return new links as json data
    # in response text
    return [
        {
            'id': link.id,

            'original_filename': link.original_filename,

            'hires_full_path': link.full_path,
            'webres_full_path': link.thumbnail.full_path,
            'thumbnail_full_path': link.thumbnail.thumbnail.full_path
                     if link.thumbnail.thumbnail else link.thumbnail.full_path,

            'tags': [tag.name for tag in link.tags]
        } for link in links
    ]


@view_config(
    route_name='update_reference_dialog',
    renderer='templates/link/dialogs/update_reference_dialog.jinja2'
)
def update_reference_dialog(request):
    """update reference dialog
    """
    reference_id = request.matchdict.get('id')
    ref = Link.query.get(reference_id)

    # try to get the repository that this reference resides
    from stalker import Task
    t = Task.query.filter(Task.references.contains(ref)).first()

    repo_id = -1
    if t:
        repo_id = t.project.repository.id

    return {
        'reference': ref,
        'repo_id': repo_id
    }


@view_config(
    route_name='update_reference'
)
def update_reference(request):
    """update reference
    """
    ref_id = request.matchdict.get('id')
    ref = Link.query.get(ref_id)

    # Tags
    tags = get_tags(request)

    if ref:
        ref.tags = tags
    else:
        return Response('No reference with id: %s' % ref_id)

    return Response('Successfully updated reference %s' % ref_id)


@view_config(
    route_name='assign_output',
    renderer='json'
)
def assign_output(request):
    """assigns the given files as version outputs for the given entity
    """

    logger.debug('assign_output')
    logged_in_user = get_logged_in_user(request)

    full_paths = request.POST.getall('full_paths[]')
    original_filenames = request.POST.getall('original_filenames[]')

    entity_id = request.params.get('entity_id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    daily_id = request.params.get('daily_id', -1)
    daily = Daily.query.filter_by(id=daily_id).first()

    # Tags
    tags = get_tags(request)

    logger.debug('daily_id         : %s' % daily_id)

    logger.debug('full_paths         : %s' % full_paths)
    logger.debug('original_filenames : %s' % original_filenames)
    logger.debug('entity_id          : %s' % entity_id)
    logger.debug('entity             : %s' % entity)
    logger.debug('tags               : %s' % tags)

    version_id = entity.id
    version_number = entity.version_number
    version_take_name = entity.take_name
    version_published = entity.is_published

    links = []
    if entity and full_paths:
        mm = MediaManager()
        for full_path, original_filename in zip(full_paths, original_filenames):
            l = mm.upload_version_output(entity, open(full_path), original_filename)
            l.created_by = logged_in_user
            l.date_created = local_to_utc(datetime.datetime.now())
            l.date_updated = l.date_created

            for tag in tags:
                if tag not in l.tags:
                    l.tags.extend(tags)

            DBSession.add(l)
            links.append(l)
            if daily:
                if l not in daily.links:
                    daily.links.append(l)


    # to generate ids for links
    transaction.commit()
    DBSession.add_all(links)

    # return new links as json data
    # in response text
    return [
        {
            'id': link.id,

            'original_filename': link.original_filename,

            'hires_full_path': link.full_path,
            'webres_full_path': link.thumbnail.full_path,
            'thumbnail_full_path': link.thumbnail.thumbnail.full_path
                     if link.thumbnail.thumbnail else link.thumbnail.full_path,

            'tags': [tag.name for tag in link.tags],
            'version_id': version_id,
            'version_number': version_number,
            'version_take_name': version_take_name,
            'version_published':version_published
        } for link in links
    ]


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
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

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
                search_string_buffer.append('and')
            tmp_search_query = """(
            '%(search_wide)s' = any (tags.name)
            or tasks.entity_type = '%(search_str)s'
            or tasks.full_path ilike '%(search_wide)s'
            or "Links".original_filename ilike '%(search_wide)s'
            )
            """ % {
                'search_str': s,
                'search_wide': '%{s}%'.format(s=s)
            }
            search_string_buffer.append(tmp_search_query)
        search_string_buffer.append(')')
        search_query = '\n'.join(search_string_buffer)
    logger.debug('search_query: %s' % search_query)

    path_id = '%|{id}|%' if entity.entity_type != 'Project' else '%{id}|%'
    path_id = path_id.format(id=entity_id)

    # we need to do that import here
    from stalker_pyramid.views.task import \
        generate_recursive_task_query

    # using Raw SQL queries here to fasten things up quite a bit and also do
    # some fancy queries like getting all the references of tasks of a project
    # also with their tags
    sql_query = """
    -- select all links assigned to a project tasks or assigned to a task and its children
select * from (
select
    "Links".id,
    "Links".original_filename,

    'repositories/' || task_repositories.repo_id || '/' || "Links".full_path as hires_full_path,
    'repositories/' || task_repositories.repo_id || '/' || "Links_ForWeb".full_path as webres_full_path,
    'repositories/' || task_repositories.repo_id || '/' || "Thumbnails".full_path as thumbnail_full_path,

    tags.name as tags,

    array_agg(tasks.id) as entity_id,
    array_agg(tasks.full_path) as entity_full_path,
    array_agg(tasks.entity_type) as entity_type

-- start with tasks (with full names)
from (
    {recursive_task_query}
) as tasks


-- find Links (References)
join "Task_References" on tasks.id = "Task_References".task_id
join "Links" on "Task_References".link_id = "Links".id


-- tags
left join (
    select
        entity_id,
        array_agg(name) as name
    from "Entity_Tags"
    join "SimpleEntities" on "Entity_Tags".tag_id = "SimpleEntities".id
    group by "Entity_Tags".entity_id
) as tags on "Links".id = tags.entity_id


-- find repository id
join (
    select
        "Tasks".id as task_id,
        "Repositories".id as repo_id
    from "Tasks"
    join "Projects" on "Tasks".project_id = "Projects".id
    join "Repositories" on "Projects".repository_id = "Repositories".id
) as task_repositories on tasks.id = task_repositories.task_id


-- continue on links
join "SimpleEntities" as "Link_SimpleEntities" on "Links".id = "Link_SimpleEntities".id
join "Links" as "Links_ForWeb" on "Link_SimpleEntities".thumbnail_id = "Links_ForWeb".id
join "SimpleEntities" as "Links_ForWeb_SimpleEntities" on "Links_ForWeb".id = "Links_ForWeb_SimpleEntities".id
join "Links" as "Thumbnails" on "Links_ForWeb_SimpleEntities".thumbnail_id = "Thumbnails".id

where (tasks.path ilike '{path_id}' or tasks.id = {id}) {search_string}

group by "Links".id,
    "Links_ForWeb".full_path,
    "Links".original_filename,
    task_repositories.repo_id,
    "Thumbnails".id,
    tags.name
) as data

order by data.id

offset {offset}
limit {limit}
    """.format(
        id=entity_id,
        path_id=path_id,
        recursive_task_query=generate_recursive_task_query(ordered=False),
        search_string=search_query,
        offset=offset,
        limit=limit
    )

    # if offset and limit:
    #     sql_query += "offset %s limit %s" % (offset, limit)

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return_val = [
        {
            'id': r[0],
            'original_filename': r[1],
            'hires_full_path': r[2],
            'webres_full_path': r[3],
            'thumbnail_full_path': r[4],
            'tags': r[5],
            'entity_ids': r[6],
            'entity_names': r[7],
            'entity_types': r[8]
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

    search_string = request.params.get('search', '')
    logger.debug('search_string: %s' % search_string)

    search_query = ''
    if search_string != "":
        search_string_buffer = ['and (']
        for i, s in enumerate(search_string.split(' ')):
            if i != 0:
                search_string_buffer.append('and')
            tmp_search_query = """
            (
            '%(search_wide)s' = any (tags.name)
            or tasks.entity_type = '%(search_str)s'
            or tasks.full_path ilike '%(search_wide)s'
            or "Links".original_filename ilike '%(search_wide)s'
            )
            """ % {
                'search_str': s,
                'search_wide': '%{s}%'.format(s=s)
            }
            search_string_buffer.append(tmp_search_query)
        search_string_buffer.append(')')
        search_query = '\n'.join(search_string_buffer)
    logger.debug('search_query: %s' % search_query)

    path_id = '%|{id}|%' if entity.entity_type != 'Project' else '%{id}|%'
    path_id = path_id.format(id=entity_id)

    # we need to do that import here
    from stalker_pyramid.views.task import generate_recursive_task_query

    # using Raw SQL queries here to fasten things up quite a bit and also do
    # some fancy queries like getting all the references of tasks of a project
    # also with their tags
    sql_query = """
    -- select all links assigned to a project tasks or assigned to a task and its children
select count(1) from (
select
    "Links".id

-- start with tasks (with fullnames)
from (
    {recursive_task_query}
) as tasks


-- find Links (References)
join "Task_References" on tasks.id = "Task_References".task_id
join "Links" on "Task_References".link_id = "Links".id


-- tags
left join (
    select
        entity_id,
        array_agg(name) as name
    from "Entity_Tags"
    join "SimpleEntities" on "Entity_Tags".tag_id = "SimpleEntities".id
    group by "Entity_Tags".entity_id
) as tags on "Links".id = tags.entity_id


-- continue on links
join "SimpleEntities" as "Link_SimpleEntities" on "Links".id = "Link_SimpleEntities".id

where (tasks.path ilike '{path_id}' or tasks.id = {id}) {search_string}

group by
    "Links".id,
    "Links".original_filename,
    tags.name
) as data
    """.format(
        id=entity_id,
        path_id=path_id,
        recursive_task_query=generate_recursive_task_query(ordered=False),
        search_string=search_query
    )

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]


@view_config(
    route_name='delete_reference',
    permission='Delete_Link'
)
def delete_reference(request):
    """deletes the reference with the given ID
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    ref_id = request.matchdict.get('id')
    ref = Link.query.get(ref_id)

    files_to_remove = []
    references_to_delete = []

    if ref:
        logger.debug('ref.id         : %s' % ref.id)
        original_filename = ref.original_filename
        # check if it has a web version
        web_version = ref.thumbnail
        if web_version:
            logger.debug('web_version.id : %s' % web_version.id)
            # remove the file first
            files_to_remove.append(web_version.full_path)

            # also check the thumbnail
            thumbnail = web_version.thumbnail

            if thumbnail:
                logger.debug('thumbnail      : %s' % thumbnail)
                # remove the file first
                files_to_remove.append(thumbnail.full_path)

                # delete the thumbnail Link from the database
                references_to_delete.append(thumbnail)

            # delete the thumbnail Link from the database
            references_to_delete.append(web_version)

        # remove the reference itself
        files_to_remove.append(ref.full_path)

        # delete the ref Link from the database
        # IMPORTANT: Because there is no link from Link -> Task deleting a Link
        #            directly will raise an IntegrityError, so remove the Link
        #            from the associated Task before deleting it
        prefix = ''
        from stalker import Task
        for task in Task.query.filter(Task.references.contains(ref)).all():
            logger.debug('%s is referencing %s, '
                         'breaking this relation' % (task, ref))
            task.references.remove(ref)
            if prefix == '':
                # get the repository
                repo = task.project.repository
                prefix = repo.path

        references_to_delete.append(ref)

        # delete Links from database
        for r in references_to_delete:
            DBSession.delete(r)

        # now delete files
        for f in files_to_remove:
            # convert the paths to system path
            f_system = os.path.join(prefix, f)
            logger.debug('deleting : %s' % f_system)
            try:
                os.remove(f_system)
            except OSError:
                pass

        response = Response('%s removed successfully' % original_filename)
        return response
    else:
        response = Response('No ref with id : %i' % ref_id, 500)
        transaction.abort()
        return response


@view_config(route_name='get_version_outputs', renderer='json')
@view_config(route_name='get_task_outputs', renderer='json')
@view_config(route_name='get_entity_outputs', renderer='json')
def get_entity_outputs(request):
    """called when the outputs to Project/Task/Version is
    requested
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()
    logger.debug('asking references for entity: %s' % entity)

    offset = request.params.get('offset', 0)
    limit = request.params.get('limit', 1e10)

    search_string = request.params.get('search', '')
    is_published_str = request.params.get('is_published', '')

    logger.debug('is_published_str: %s' % is_published_str)
    logger.debug('search_string: %s' % search_string)

    where_condition = ''
    search_query = ''
    is_published =''

    if search_string != "":
        search_string_buffer = ['and (']
        for i, s in enumerate(search_string.split(' ')):
            if i != 0:
                search_string_buffer.append('and')
            tmp_search_query = """(
            '%(search_str)s' = any (tags.name)
            or "Versions".take_name ilike '%(search_wide)s'
            or "Version_Links".original_filename ilike '%(search_wide)s'
            )
            """ % {
                'search_str': s,
                'search_wide': '%{s}%'.format(s=s)
            }
            search_string_buffer.append(tmp_search_query)
        search_string_buffer.append(')')
        search_query = '\n'.join(search_string_buffer)
    logger.debug('search_query: %s' % search_query)

    if is_published_str != '':
        is_published = """ and "Versions".is_published = 't' """

    logger.debug('is_published: %s' % is_published)

    if entity.entity_type == 'Version':
        where_condition= """where "Versions".id = %(id)s %(search_query)s %(is_published)s""""" % {'id':entity.id, 'search_query':search_query, 'is_published':is_published }
    elif entity.entity_type == 'Task':
        where_condition= """where "Task_SimpleEntities".id = %(id)s %(search_query)s %(is_published)s""""" % {'id':entity.id, 'search_query':search_query, 'is_published':is_published }

    logger.debug('where_condition: %s' % where_condition)

    sql_query = """
    -- select all links assigned to a project tasks or assigned to a task and its children
select
    "Version_Links".id,
    "Version_Links".original_filename,

    'repositories/' || task_repositories.repo_id || '/' || "Version_Links".full_path as hires_full_path,
    'repositories/' || task_repositories.repo_id || '/' || "Links_ForWeb".full_path as webres_full_path,
    'repositories/' || task_repositories.repo_id || '/' || "Thumbnails".full_path as thumbnail_full_path,

    tags.name as tags,

    "Versions".id as version_id,
    "Versions".version_number as version_number,
    "Versions".take_name as take_name,
    "Versions".is_published as version_published,
    "Daily_SimpleEntities".name as daily_name,
    "Daily_SimpleEntities".id as daily_id,
    (extract(epoch from "Link_SimpleEntities".date_created::timestamp at time zone 'UTC') * 1000)::bigint as date_created




from "Version_Outputs"
join "Versions" on "Versions".id = "Version_Outputs".version_id
join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Versions".task_id
join "Links" as "Version_Links" on "Version_Links".id = "Version_Outputs".link_id
join "SimpleEntities" as "Link_SimpleEntities" on "Version_Links".id = "Link_SimpleEntities".id
join "Links" as "Links_ForWeb" on "Link_SimpleEntities".thumbnail_id = "Links_ForWeb".id
join "SimpleEntities" as "Links_ForWeb_SimpleEntities" on "Links_ForWeb".id = "Links_ForWeb_SimpleEntities".id
join "Links" as "Thumbnails" on "Links_ForWeb_SimpleEntities".thumbnail_id = "Thumbnails".id
left outer join "Daily_Links" on "Daily_Links".link_id = "Version_Outputs".link_id
left outer join "SimpleEntities" as "Daily_SimpleEntities" on "Daily_SimpleEntities".id = "Daily_Links".daily_id

join (
    select
        "Tasks".id as task_id,
        "Repositories".id as repo_id
    from "Tasks"
    join "Projects" on "Tasks".project_id = "Projects".id
    join "Repositories" on "Projects".repository_id = "Repositories".id
) as task_repositories on "Versions".task_id = task_repositories.task_id

left outer join (
    select
        entity_id,
        array_agg(name) as name
    from "Entity_Tags"
    join "SimpleEntities" on "Entity_Tags".tag_id = "SimpleEntities".id
    group by "Entity_Tags".entity_id
) as tags on "Version_Links".id = tags.entity_id


%(where_condition)s

order by "Versions".id desc, date_created desc
offset %(offset)s
limit %(limit)s

    """ % {
        'where_condition': where_condition,
        'offset': offset,
        'limit': limit
    }

    logger.debug('sql_query: %s' % sql_query)

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return_val = [
        {
            'id': r[0],
            'original_filename': r[1],
            'hires_full_path': r[2],
            'webres_full_path': r[3],
            'thumbnail_full_path': r[4],
            'tags': r[5],
            'version_id': r[6],
            'version_number': r[7],
            'version_take_name': r[8],
            'version_published':r[9],
            'daily_name':r[10],
            'daily_id':r[11],
            'date_created':r[12]
        } for r in result.fetchall()
    ]

    return return_val


@view_config(route_name='get_version_outputs_count', renderer='json')
@view_config(route_name='get_task_outputs_count', renderer='json')
@view_config(route_name='get_entity_outputs_count', renderer='json')
def get_entity_outputs_count(request):
    """called when the count of references to Project/Task/Asset/Shot/Sequence
    is requested
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()
    logger.debug('asking outputs for entity: %s' % entity)

    search_string = request.params.get('search', '')
    is_published_str = request.params.get('is_published', '')

    logger.debug('is_published_str: %s' % is_published_str)
    logger.debug('search_string: %s' % search_string)

    where_condition = ''
    search_query = ''
    is_published =''

    if search_string != "":
        search_string_buffer = ['and (']
        for i, s in enumerate(search_string.split(' ')):
            if i != 0:
                search_string_buffer.append('and')
            tmp_search_query = """
            (
            '%(search_str)s' = any (tags.name)
            or "Versions".take_name ilike '%(search_wide)s'
            or "Version_Links".original_filename ilike '%(search_wide)s'
            )
            """ % {
                'search_str': s,
                'search_wide': '%{s}%'.format(s=s)
            }
            search_string_buffer.append(tmp_search_query)
        search_string_buffer.append(')')
        search_query = '\n'.join(search_string_buffer)
    logger.debug('search_query: %s' % search_query)


    if is_published_str != '':
        is_published = """ and "Versions".is_published = 't' """


    if entity.entity_type == 'Version':
        where_condition= """where "Versions".id = %(id)s %(search_query)s %(is_published)s""""" % {'id':entity.id, 'search_query':search_query, 'is_published':is_published }
    elif entity.entity_type == 'Task':
        where_condition= """where "Task_SimpleEntities".id = %(id)s %(search_query)s %(is_published)s""""" % {'id':entity.id, 'search_query':search_query, 'is_published':is_published }

    logger.debug('where_condition: %s' % where_condition)
    # we need to do that import here
    from stalker_pyramid.views.task import \
        generate_recursive_task_query

    # using Raw SQL queries here to fasten things up quite a bit and also do
    # some fancy queries like getting all the references of tasks of a project
    # also with their tags
    sql_query = """
    -- select all links assigned to a project tasks or assigned to a task and its children
select

    count(1)

from "Version_Outputs"
join "Versions" on "Versions".id = "Version_Outputs".version_id
join "SimpleEntities" as "Task_SimpleEntities" on "Task_SimpleEntities".id = "Versions".task_id
join "Links" as "Version_Links" on "Version_Links".id = "Version_Outputs".link_id

left outer join (
    select
        entity_id,
        array_agg(name) as name
    from "Entity_Tags"
    join "SimpleEntities" on "Entity_Tags".tag_id = "SimpleEntities".id
    group by "Entity_Tags".entity_id
) as tags on "Version_Links".id = tags.entity_id

%(where_condition)s
    """ % {
        'where_condition': where_condition
    }

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]


@view_config(
    route_name='delete_output',
    permission='Delete_Link'
)
def delete_output(request):
    """deletes the reference with the given ID
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    output_id = request.matchdict.get('id')
    output = Link.query.get(output_id)

    files_to_remove = []
    outputs_to_delete = []

    if output:
        logger.debug('output.id         : %s' % output.id)
        original_filename = output.original_filename
        # check if it has a web version
        web_version = output.thumbnail
        if web_version:
            logger.debug('web_version.id : %s' % web_version.id)
            # remove the file first
            files_to_remove.append(web_version.full_path)

            # also check the thumbnail
            thumbnail = web_version.thumbnail

            if thumbnail:
                logger.debug('thumbnail      : %s' % thumbnail)
                # remove the file first
                files_to_remove.append(thumbnail.full_path)

                # delete the thumbnail Link from the database
                outputs_to_delete.append(thumbnail)

            # delete the thumbnail Link from the database
            outputs_to_delete.append(web_version)

        # remove the reference itself
        files_to_remove.append(output.full_path)

        # delete the ref Link from the database
        # IMPORTANT: Because there is no link from Link -> Task deleting a Link
        #            directly will raise an IntegrityError, so remove the Link
        #            from the associated Task before deleting it
        prefix = ''
        from stalker import Version
        for version in Version.query.filter(Version.outputs.contains(output)).all():
            logger.debug('%s output is %s, '
                         'breaking this relation' % (version, output))
            version.outputs.remove(output)
            if prefix == '':
                # get the repository
                repo = version.task.project.repository
                prefix = repo.path

        outputs_to_delete.append(output)

        # delete the Link to daily relation
        for daily in Daily.query.filter(Daily.links.contains(output)).all():
            logger.debug(
                '%s is connected to %s, breaking this connection' %
                (output, daily)
            )
            daily.links.remove(output)

        # delete Links from database
        for o in outputs_to_delete:
            DBSession.delete(o)

        # now delete files
        for f in files_to_remove:
            # convert the paths to system path
            f_system = os.path.join(prefix, f)
            logger.debug('deleting : %s' % f_system)
            try:
                os.remove(f_system)
            except OSError:
                pass

        response = Response('%s removed successfully' % original_filename)
        return response
    else:
        response = Response('No ref with id : %i' % output_id, 500)
        transaction.abort()
        return response


@view_config(
    route_name='serve_files'
)
def serve_files(request):
    """serves files in the stalker server side storage
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    partial_file_path = request.matchdict['partial_file_path']
    file_full_path = MediaManager.convert_file_link_to_full_path(partial_file_path)
    return FileResponse(file_full_path)


@view_config(
    route_name='forced_download_files'
)
def force_download_files(request):
    """serves files but forces to download
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    partial_file_path = request.matchdict['partial_file_path']
    file_full_path = MediaManager.convert_file_link_to_full_path(partial_file_path)
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


@view_config(
    route_name='serve_repository_files'
)
def serve_repository_files(request):
    """serves files in the stalker repositories
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    # TODO: check file access
    repo_id = request.matchdict['id']
    partial_file_path = request.matchdict['partial_file_path']

    repo = Repository.query.filter_by(id=repo_id).first()
    # assert isinstance(repo, Repository)

    file_full_path = os.path.join(
        repo.path,
        partial_file_path
    )

    logger.debug('serve_repository_files is running')
    logger.debug('file_full_path : %s' % file_full_path)

    return FileResponse(file_full_path)


@view_config(
    route_name='forced_download_repository_files'
)
def force_download_repository_files(request):
    """serves files but forces to download
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    # TODO: check file access
    partial_file_path = request.matchdict['partial_file_path']
    repo_id = request.matchdict['id']

    repo = Repository.query.filter_by(id=repo_id).first()

    file_full_path = os.path.join(
        repo.path,
        partial_file_path
    )

    logger.debug('partial_file_path: %s' % partial_file_path)

    # get the link to get the original file name
    link = Link.query.filter(Link.full_path == partial_file_path).first()
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


@view_config(
    route_name='video_player',
    renderer='templates/link/video_player.jinja2'
)
def video_player(request):
    """generates an iframe for video player
    """
    # just to make it safe
    logger.debug("logged_in_user: %s" % get_logged_in_user(request))

    return {
        'video_full_path': request.params.get('video_full_path')
    }


@view_config(
    route_name='convert_to_webm'
)
def convert_to_webm(request):
    """converts the given file with at the given Link output to WebM format
    """
    link_id = request.matchdict['id']
    link = Link.query.filter(Link.id == link_id).first()

    if not link:
        return

    # get a version that has this Link
    v = Version.query.filter(Version.outputs.contains(link)).first()

    if not v:
        return

    repo = v.task.project.repository

    # for now we need to write code that supports both Stalker pre v0.2.13 and
    # post v0.2.13 which introduces a difference in Repository path
    pre_upgrade = False
    if '$' in link.full_path:  # this is the new style starting with Stalker v0.2.13
        link_full_path = os.path.expandvars(link.full_path)
    else:  # this is the pre Stalker v0.2.13
        pre_upgrade = True
        link_full_path = '%s/%s' % (repo.path, link.full_path)

    m = MediaManager()
    web_version_temp_full_path = m.generate_video_for_web(link_full_path)

    # generate a path with ".webm" extension
    web_version_full_path = \
        '%s%s' % (os.path.splitext(link_full_path)[0], m.web_video_format)

    # move the file there
    try:
        shutil.move(web_version_temp_full_path, web_version_full_path)
    except IOError:
        logger.debug('there was an error moving the web version to its new '
                     'path!')
        return

    # and update the link
    old_path = '%s/%s' % (repo.path, link.full_path)

    if pre_upgrade:
        link.full_path = repo.make_relative(web_version_full_path)
    else:
        # we need to use the new style of links with env variables
        link.full_path = '%s/%s' % (
            defaults.repo_env_var_template % {'id': repo.id},
            link.full_path
        )

    try:
        # remove the old one
        os.remove(old_path)
    except OSError:
        pass

    return


class MediaManager(object):
    """Manages media files.

    MediaManager is the media hub of Stalker Pyramid. It is responsible of the
    uploads/downloads of media files and all kind of conversions.

    It can convert image, video and audio files. The default format for image
    files is PNG and the default format for video os WebM (VP8), and mp3
    (stereo, 96 kBit/s) is the default format for audio files.

    It can filter files from request parameters and upload them to the server,
    also for image files it will generate thumbnails and versions to be viewed
    from web.

    It can handle image sequences, and will create only one Link object per
    image sequence. The thumbnail of an image sequence will be a gif image.

    It will generate a zip file to serve all the images in an image sequence.
    """

    def __init__(self):
        self.reference_path = 'References/Stalker_Pyramid/'
        self.version_output_path = 'Outputs/Stalker_Pyramid/'

        # accepted image formats
        self.image_formats = [
            '.gif', '.ico', '.iff',
            '.jpg', '.jpeg', '.png', '.tga', '.tif',
            '.tiff', '.bmp', '.exr',
        ]

        # accepted video formats
        self.video_formats = [
            '.3gp', '.a64', '.asf', '.avi', '.dnxhd', '.f4v', '.filmstrip',
            '.flv', '.h261', '.h263', '.h264', '.ipod', '.m4v', '.matroska',
            '.mjpeg', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.mpeg1video',
            '.mpeg2video', '.mv', '.mxf', '.ogg', '.rm', '.swf', '.vc1',
            '.vcd', '.vob', '.webm'
        ]

        # thumbnail format
        self.thumbnail_format = '.jpg'
        self.thumbnail_width = 512
        self.thumbnail_height = 512
        self.thumbnail_options = {  # default options for thumbnails
            'quality': 80
        }

        # images and videos for web
        self.web_image_format = '.jpg'
        self.web_image_width = 1920
        self.web_image_height = 1080

        self.web_video_format = '.webm'
        self.web_video_width = 960
        self.web_video_height = 540
        self.web_video_bitrate = 4096  # in kBits/sec

        # commands
        self.ffmpeg_command_path = '/usr/bin/ffmpeg'
        self.ffprobe_command_path = '/usr/local/bin/ffprobe'

    @classmethod
    def reorient_image(cls, img):
        """re-orients rotated images by looking at EXIF data
        """
        # get the image rotation from EXIF information
        import exifread

        file_full_path = img.filename

        with open(file_full_path) as f:
            tags = exifread.process_file(f)

        orientation_string = tags.get('Image Orientation')

        if orientation_string:
            orientation = orientation_string.values[0]
            if orientation == 1:
                # do nothing
                pass
            elif orientation == 2:  # flipped in X
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:  # rotated 180 degree
                img = img.transpose(Image.ROTATE_180)
            elif orientation == 4:  # flipped in Y
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:  #
                img = img.transpose(Image.ROTATE_270)
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 6:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 7:
                img = img.transpose(Image.ROTATE_90)
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 8:
                img = img.transpose(Image.ROTATE_90)

        return img

    def generate_image_thumbnail(self, file_full_path):
        """Generates a thumbnail for the given image file

        :param file_full_path: Generates a thumbnail for the given file in the
          given path
        :return str: returns the thumbnail path
        """
        # generate thumbnail for the image and save it to a tmp folder
        suffix = self.thumbnail_format

        img = Image.open(file_full_path)
        # do a double scale
        img.thumbnail((2 * self.thumbnail_width, 2 * self.thumbnail_height))
        img.thumbnail((self.thumbnail_width, self.thumbnail_height),
                      Image.ANTIALIAS)

        # re-orient images
        img = self.reorient_image(img)

        if img.format == 'GIF':
            suffix = '.gif'  # force save in gif format
        else:
            # check if the image is in RGB mode
            if img.mode != "RGB":
                img = img.convert("RGB")

        thumbnail_path = tempfile.mktemp(suffix=suffix)

        img.save(thumbnail_path, **self.thumbnail_options)
        return thumbnail_path

    def generate_image_for_web(self, file_full_path):
        """Generates a version suitable to be viewed from a web browser.

        :param file_full_path: Generates a thumbnail for the given file in the
          given path.
        :return str: returns the thumbnail path
        """
        # generate thumbnail for the image and save it to a tmp folder
        suffix = self.thumbnail_format

        img = Image.open(file_full_path)
        if img.size[0] > self.web_image_width \
           or img.size[1] > self.web_image_height:
            # do a double scale
            img.thumbnail(
                (2 * self.web_image_width, 2 * self.web_image_height)
            )
            img.thumbnail(
                (self.web_image_width, self.web_image_height),
                Image.ANTIALIAS
            )

        # re-orient images
        img = self.reorient_image(img)

        if img.format == 'GIF':
            suffix = '.gif'  # force save in gif format
        else:
            # check if the image is in RGB mode
            if img.mode != "RGB":
                img = img.convert("RGB")

        thumbnail_path = tempfile.mktemp(suffix=suffix)

        img.save(thumbnail_path)
        return thumbnail_path

    def generate_video_thumbnail(self, file_full_path):
        """Generates a thumbnail for the given video link

        :param str file_full_path: A string showing the full path of the video
          file.
        """
        # TODO: split this in to two different methods, one generating
        #       thumbnails from the video and another one accepting three
        #       images
        media_info = self.get_video_info(file_full_path)
        video_info = media_info['video_info']

        # get the correct stream
        video_stream = None
        for stream in media_info['stream_info']:
            if stream['codec_type'] == 'video':
                video_stream = stream

        nb_frames = video_stream.get('nb_frames')
        if nb_frames is None or nb_frames == 'N/A':
            # no nb_frames
            # first try to use "r_frame_rate" and "duration"
            frame_rate = video_stream.get('r_frame_rate')

            if frame_rate is None:  # still no frame rate
                # try to use the video_info and duration
                # and try to get frame rate
                frame_rate = float(video_info.get('TAG:framerate', 23.976))
            else:
                # check if it is in Number/Number format
                if '/' in frame_rate:
                    nominator, denominator = frame_rate.split('/')
                    frame_rate = float(nominator)/float(denominator)

            # get duration
            duration = video_stream.get('duration')
            if duration == 'N/A':  # no duration
                duration = float(video_info.get('duration', 1))
            else:
                duration = float(duration)

            # at this stage we should have enough info, may not be correct but
            # we should have something
            # calculate nb_frames
            logger.debug('duration  : %s' % duration)
            logger.debug('frame_rate: %s' % frame_rate)
            nb_frames = int(duration * frame_rate)
        nb_frames = int(nb_frames)

        start_thumb_path = tempfile.mktemp(suffix=self.thumbnail_format)
        mid_thumb_path = tempfile.mktemp(suffix=self.thumbnail_format)
        end_thumb_path = tempfile.mktemp(suffix=self.thumbnail_format)

        thumbnail_path = tempfile.mktemp(suffix=self.thumbnail_format)

        # generate three thumbnails from the start, middle and end of the file
        start_frame = int(nb_frames * 0.10)
        mid_frame = int(nb_frames * 0.5)
        end_frame = int(nb_frames * 0.90)

        #start_frame
        self.ffmpeg(**{
            'i': file_full_path,
            'vf': "select='eq(n, 0)'",
            'vframes': start_frame,
            'o': start_thumb_path
        })
        #mid_frame
        self.ffmpeg(**{
            'i': file_full_path,
            'vf': "select='eq(n, %s)'" % mid_frame,
            'vframes': 1,
            'o': mid_thumb_path
        })
        #end_frame
        self.ffmpeg(**{
            'i': file_full_path,
            'vf': "select='eq(n, %s)'" % end_frame,
            'vframes': 1,
            'o': end_thumb_path
        })

        # now merge them
        self.ffmpeg(**{
            'i': [start_thumb_path, mid_thumb_path, end_thumb_path],
            'filter_complex':
                "[0:0] scale=3*%(tw)s/4:-1, pad=%(tw)s:%(th)s [s]; "
                "[1:0] scale=3*%(tw)s/4:-1, fade=out:300:30:alpha=1 [m]; "
                "[2:0] scale=3*%(tw)s/4:-1, fade=out:300:30:alpha=1 [e]; "
                "[s][e] overlay=%(tw)s/4:%(th)s-h [x]; "
                "[x][m] overlay=%(tw)s/8:%(th)s/2-h/2" %
                {
                    'tw': self.thumbnail_width,
                    'th': self.thumbnail_height
                },
            'o': thumbnail_path
        })

        # remove the intermediate data
        os.remove(start_thumb_path)
        os.remove(mid_thumb_path)
        os.remove(end_thumb_path)
        return thumbnail_path

    def generate_video_for_web(self, file_full_path):
        """Generates a web friendly version for the given video.

        :param str file_full_path: A string showing the full path of the video
          file.
        """
        web_version_full_path = tempfile.mktemp(suffix=self.web_video_format)
        self.convert_to_webm(file_full_path, web_version_full_path)
        return web_version_full_path

    def generate_thumbnail(self, file_full_path):
        """Generates a thumbnail for the given link

        :param file_full_path: Generates a thumbnail for the given file in the
          given path
        :return str: returns the thumbnail path
        """
        extension = os.path.splitext(file_full_path)[-1].lower()
        # check if it is an image or video or non of them
        if extension in self.image_formats:
            # generate a thumbnail from image
            return self.generate_image_thumbnail(file_full_path)
        elif extension in self.video_formats:
            return self.generate_video_thumbnail(file_full_path)

        # not an image nor a video so no thumbnail, raise RuntimeError
        raise RuntimeError('%s is not an image nor a video file, can not '
                           'generate a thumbnail for it!' %
                           file_full_path)

    def generate_media_for_web(self, file_full_path):
        """Generates a media suitable for web browsers.

        It will generate PNG for images, and a WebM for video files.

        :param file_full_path: Generates a web suitable version for the given
          file in the given path.
        :return str: returns the media file path.
        """
        extension = os.path.splitext(file_full_path)[-1].lower()
        # check if it is an image or video or non of them
        if extension in self.image_formats:
            # generate a thumbnail from image
            return self.generate_image_for_web(file_full_path)
        elif extension in self.video_formats:
            return self.generate_video_for_web(file_full_path)

        # not an image nor a video so no thumbnail, raise RuntimeError
        raise RuntimeError('%s is not an image nor a video file!' %
                           file_full_path)

    @classmethod
    def generate_local_file_path(cls, extension=''):
        """Generates file paths in server side storage.

        :param extension: Desired file extension
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

        file_full_path = os.path.join(
            file_path,
            new_filename
        )

        return file_full_path

    @classmethod
    def convert_file_link_to_full_path(cls, link_path):
        """OBSOLETE: converts the given Stalker Pyramid Local file link to a
        real full path.

        :param link_path: A link to a file in SPL starting with SPL
          (ex: SPL/b0/e6/b0e64b16c6bd4857a91be47fb2517b53.jpg)
        :returns: str
        """
        logger.debug('link_path: %s' % link_path)
        if not isinstance(link_path, (str, unicode)):
            raise TypeError(
                '"link_path" argument in '
                '%(class)s.convert_file_link_to_full_path() method should be '
                'a str, not %(link_path_class)s' % {
                    'class': cls.__name__,
                    'link_path_class': link_path.__class__.__name__
                }
            )

        # if not link_path.startswith('SPL'):
        #     raise ValueError(
        #         '"link_path" argument in '
        #         '%(class)s.convert_file_link_to_full_path() method should be '
        #         'a str starting with "SPL/"' % {
        #             'class': cls.__name__
        #         }
        #     )

        spl_prefix = 'SPL/'
        if spl_prefix in link_path:
            link_full_path = link_path[len(spl_prefix):]
        else:
            link_full_path = link_path

        file_full_path = os.path.join(
            defaults.server_side_storage_path,
            link_full_path
        )
        return file_full_path

    @classmethod
    def convert_full_path_to_file_link(cls, full_path):
        """OBSOLETE: Converts the given full path to Stalker Pyramid Local
        Storage relative path.

        :param full_path: The full path of the file in SPL.
          (ex: /home/stalker/Stalker_Storage/b0/e6/b0e64b16c6bd4857a91be47fb2517b53.jpg)
        :returns: str
        """
        if not isinstance(full_path, (str, unicode)):
            raise TypeError(
                '"full_path" argument in '
                '%(class)s.convert_full_path_to_file_link() method should be '
                'a str, not %(full_path_class)s' % {
                    'class': cls.__name__,
                    'full_path_class': full_path.__class__.__name__
                }
            )

        if not full_path.startswith(defaults.server_side_storage_path):
            raise ValueError(
                '"full_path" argument in '
                '%(class)s.convert_full_path_to_file_link() method should be '
                'a str starting with "%(spl)s"' % {
                    'class': cls.__name__,
                    'spl': defaults.server_side_storage_path,
                }
            )

        spl_prefix = 'SPL/'
        return os.path.normpath(
            full_path.replace(defaults.server_side_storage_path, spl_prefix)
        )

    def get_video_info(self, full_path):
        """Returns the video info like the duration  in seconds and fps.

        Uses ffmpeg to extract information about the video file.

        :param str full_path: The full path of the video file
        :return: int
        """
        output_buffer = self.ffprobe(**{
            'show_streams': full_path,
        })

        media_info = {
            'video_info': None,
            'stream_info': []
        }
        video_info = {}
        stream_info = {}

        # get STREAM info
        line = output_buffer.pop(0).strip()
        while line is not None:
            if line == '[STREAM]':
                # pop until you find [/STREAM]
                while line != '[/STREAM]':
                    if '=' in line:
                        flag, value = line.split('=')
                        stream_info[flag] = value
                    line = output_buffer.pop(0).strip()

                copy_stream = copy.deepcopy(stream_info)
                media_info['stream_info'].append(copy_stream)
                stream_info = {}
            try:
                line = output_buffer.pop(0).strip()
            except IndexError:
                line = None

        # also get FORMAT info
        output_buffer = self.ffprobe(**{
            'show_format': full_path,
        })

        line = output_buffer.pop(0).strip()
        while line is not None:
            if line == '[FORMAT]':
                # pop until you find [/FORMAT]
                while line != '[/FORMAT]':
                    if '=' in line:
                        flag, value = line.split('=')
                        video_info[flag] = value
                    line = output_buffer.pop(0).strip()

                media_info['video_info'] = video_info
            try:
                line = output_buffer.pop(0).strip()
            except IndexError:
                line = None

        return media_info

    def ffmpeg(self, **kwargs):
        """A simple python wrapper for ``ffmpeg`` command.
        """
        # there is only one special keyword called 'o'

        # this will raise KeyError if there is no 'o' key which is good to
        # prevent the rest to execute
        output = kwargs.get('o')
        try:
            kwargs.pop('o')
        except KeyError:  # no output
            pass

        # generate args
        args = [self.ffmpeg_command_path]
        for key in kwargs:
            flag = '-' + key
            value = kwargs[key]
            if not isinstance(value, list):
                # append the flag
                args.append(flag)
                # append the value
                args.append(str(value))
            else:
                # it is a multi flag
                # so append the flag every time you append the key
                for v in value:
                    args.append(flag)
                    args.append(str(v))

            # overwrite output

        # use all cpus
        import multiprocessing
        num_of_threads = multiprocessing.cpu_count()
        args.append('-threads')
        args.append('%s' % num_of_threads)

        # overwrite any file
        args.append('-y')

        # append the output
        if output != '' and output is not None:  # for info only
            args.append(output)

        logger.debug('calling ffmpeg with args: %s' % args)

        process = subprocess.Popen(args, stderr=subprocess.PIPE)

        # loop until process finishes and capture stderr output
        stderr_buffer = []
        while True:
            stderr = process.stderr.readline()

            if stderr == '' and process.poll() is not None:
                break

            if stderr != '':
                stderr_buffer.append(stderr)

        # if process.returncode:
        #     # there is an error
        #     raise RuntimeError(stderr_buffer)

        logger.debug(stderr_buffer)
        logger.debug('process completed!')
        return stderr_buffer

    def ffprobe(self, **kwargs):
        """A simple python wrapper for ``ffprobe`` command.
        """
        # generate args
        args = [self.ffprobe_command_path]
        for key in kwargs:
            flag = '-' + key
            value = kwargs[key]
            if not isinstance(value, list):
                # append the flag
                args.append(flag)
                # append the value
                args.append(str(value))
            else:
                # it is a multi flag
                # so append the flag every time you append the key
                for v in value:
                    args.append(flag)
                    args.append(str(v))

        logger.debug('calling ffprobe with args: %s' % args)

        process = subprocess.Popen(args, stdout=subprocess.PIPE)

        # loop until process finishes and capture stderr output
        stdout_buffer = []
        while True:
            stdout = process.stdout.readline()

            if stdout == '' and process.poll() is not None:
                break

            if stdout != '':
                stdout_buffer.append(stdout)

        # if process.returncode:
        #     # there is an error
        #     raise RuntimeError(stderr_buffer)

        logger.debug(stdout_buffer)
        logger.debug('process completed!')
        return stdout_buffer

    @classmethod
    def convert_to_h264(cls, input_path, output_path, options=None):
        """converts the given input to h264
        """
        if options is None:
            options = {}

        # change the extension to mp4
        output_path = '%s%s' % (os.path.splitext(output_path)[0], '.mp4')

        conversion_options = {
            'i': input_path,
            'vcodec': 'libx264',
            'profile:v': 'main',
            'g': 1,  # key frame every 1 frame
            'b:v': '4096k',
            'o': output_path
        }
        conversion_options.update(options)

        cls.ffmpeg(**conversion_options)

        return output_path

    def convert_to_webm(self, input_path, output_path, options=None):
        """Converts the given input to webm format

        :param input_path: A string of path, can have wild card characters
        :param output_path: The output path
        :param options: Extra options to pass to the ffmpeg command
        :return:
        """
        if options is None:
            options = {}

        # change the extension to webm
        output_path = '%s%s' % (os.path.splitext(output_path)[0], '.webm')

        conversion_options = {
            'i': input_path,
            'vcodec': 'libvpx',
            'b:v': '%sk' % self.web_video_bitrate,
            'o': output_path
        }
        conversion_options.update(options)

        self.ffmpeg(**conversion_options)

        return output_path

    def convert_to_prores(self, input_path, output_path, options=None):
        """Converts the given input to Apple Prores 422 format.

        :param input_path: A string of path, can have wild card characters
        :param output_path: The output path
        :param options: Extra options to pass to the ffmpeg command
        :return:
        """
        if options is None:
            options = {}

        # change the extension to webm
        output_path = '%s%s' % (os.path.splitext(output_path)[0], '.mov')

        conversion_options = {
            'i': input_path,
            'probesize': 5000000,
            'f': 'image2',
            'profile:v': 3,
            'qscale:v': 13,  # use between 9 - 13
            'vcodec': 'prores_ks',
            'vendor': 'ap10',
            'pix_fmt': 'yuv422p10le',
            'o': output_path
        }
        conversion_options.update(options)

        self.ffmpeg(**conversion_options)

        return output_path

    def convert_to_mjpeg(self, input_path, output_path, options=None):
        """Converts the given input to Apple Motion Jpeg format.

        :param input_path: A string of path, can have wild card characters
        :param output_path: The output path
        :param options: Extra options to pass to the ffmpeg command
        :return:
        """
        if options is None:
            options = {}

        # change the extension to webm
        output_path = '%s%s' % (os.path.splitext(output_path)[0], '.mov')

        # ffmpeg -y
        # -probesize 5000000
        # -f image2
        # -r 48
        # -force_fps
        # -i ${DPX_HERO}
        # -c:v mjpeg
        # -qscale:v 1
        # -vendor ap10
        # -pix_fmt yuvj422p
        # -s 2048x1152
        # -r 48 output.mov
        conversion_options = {
            'i': input_path,
            'probesize': 5000000,
            'f': 'image2',
            'qscale:v': 1,
            'vcodec': 'mjpeg',
            'vendor': 'ap10',
            'pix_fmt': 'yuv422p',
            'o': output_path
        }
        conversion_options.update(options)

        self.ffmpeg(**conversion_options)

        return output_path

    @classmethod
    def convert_to_animated_gif(cls, input_path, output_path, options=None):
        """converts the given input to animated gif

        :param input_path: A string of path, can have wild card characters
        :param output_path: The output path
        :param options: Extra options to pass to the ffmpeg command
        :return:
        """
        if options is None:
            options = {}

        # change the extension to gif
        output_path = '%s%s' % (os.path.splitext(output_path)[0], '.gif')

        conversion_options = {
            'i': input_path,
            'o': output_path
        }
        conversion_options.update(options)

        cls.ffmpeg(**conversion_options)

        return output_path

    def upload_with_request_params(self, file_params):
        """upload objects with request params

        :param file_params: An object with two attributes, first a
          ``filename`` attribute and a ``file`` which is a file like object.
        """
        uploaded_file_info = []
        # get the file names
        for file_param in file_params:
            filename = file_param.filename
            file_object = file_param.file

            # upload to a temp path
            uploaded_file_full_path = self.upload_file(
                file_object,
                tempfile.mkdtemp(),
                filename
            )

            # return the file information
            file_info = {
                'full_path': uploaded_file_full_path,
                'original_filename': filename
            }

            uploaded_file_info.append(file_info)

        return uploaded_file_info

    def randomize_file_name(self, full_path):
        """randomizes the file name by adding a the first 4 characters of a
        UUID4 sequence to it.

        :param str full_path: The filename to be randomized
        :return: str
        """
        # get the filename
        path = os.path.dirname(full_path)
        filename = os.path.basename(full_path)

        # get the base name
        basename, extension = os.path.splitext(filename)

        # generate uuid4 sequence until there is no file with that name
        def generate():
            random_part = '_%s' % uuid.uuid4().hex[:4]
            return os.path.join(
                path, '%s%s%s' % (basename, random_part, extension)
            )

        random_file_full_path = generate()
        # generate until we have something unique
        # it will be the first one 99.9% of time
        while os.path.exists(random_file_full_path):
            random_file_full_path = generate()

        return random_file_full_path

    def format_filename(self, filename):
        """formats the filename to comply with file naming rules of Stalker
        Pyramid
        """
        if isinstance(filename, str):
            filename = filename.decode('utf-8')

        # replace Turkish characters
        bad_character_map = {
            '\xc3\xa7': 'c',
            '\xc4\x9f': 'g',
            '\xc4\xb1': 'i',
            '\xc3\xb6': 'o',
            '\xc5\x9f': 's',
            '\xc3\xbc': 'u',
            '\xc3\x87': 'C',
            '\xc4\x9e': 'G',
            '\xc4\xb0': 'I',
            '\xc5\x9e': 'S',
            '\xc3\x96': 'O',
            '\xc3\x9c': 'U',

            u'\xe7': 'c',
            u'\u011f': 'g',
            u'\u0131': 'i',
            u'\xf6': 'o',
            u'\u015f': 's',
            u'\xfc': 'u',
            u'\xc7': 'C',
            u'\u011e': 'G',
            u'\u0130': 'I',
            u'\u015e': 'S',
            u'\xd6': 'O',
            u'\xdc': 'U',
        }
        filename_buffer = []
        for char in filename:
            if char in bad_character_map:
                filename_buffer.append(bad_character_map[char])
            else:
                filename_buffer.append(char)
        filename = ''.join(filename_buffer)

        # replace ' ' with '_'
        import re
        basename, extension = os.path.splitext(filename)
        filename = '%s%s' % (
            re.sub(r'[\s\.\\/:\*\?"<>|=,+]+', '_', basename),
            extension
        )

        return filename

    def upload_file(self, file_object, file_path=None, filename=None):
        """Uploads files to the given path.

        The data of the files uploaded from a Web application is hold in a file
        like object. This method dumps the content of this file like object to
        the given path.

        :param file_object: File like object holding the data.
        :param str file_path: The path of the file to output the data to. If it
          is skipped the data will be written to a temp folder.
        :param str filename: The desired file name for the uploaded file. If it
          is skipped a unique temp filename will be generated.
        """
        if file_path is None:
            file_path = tempfile.gettempdir()

        if filename is None:
            filename = tempfile.mktemp(dir=file_path)
        else:
            filename = self.format_filename(filename)

        file_full_path = os.path.join(file_path, filename)
        if os.path.exists(file_full_path):
            file_full_path = self.randomize_file_name(file_full_path)

        # write down to a temp file first
        temp_file_full_path = '%s~' % file_full_path

        # create folders
        try:
            os.makedirs(file_path)
        except OSError:  # Path exist
            pass

        with open(temp_file_full_path, 'wb') as output_file:
            file_object.seek(0)
            while True:
                data = file_object.read(2 << 16)
                if not data:
                    break
                output_file.write(data)

        # data is written completely, rename temp file to original file
        os.rename(temp_file_full_path, file_full_path)

        return file_full_path

    def upload_reference(self, task, file_object, filename):
        """Uploads a reference for the given task to
        Task.path/References/Stalker_Pyramid/ folder and create a Link object
        to there. Again the Link object will have a Repository root relative
        path.

        It will also create a thumbnail under
        {{Task.absolute_path}}/References/Stalker_Pyramid/Thumbs folder and a
        web friendly version (PNG for images, WebM for video files) under
        {{Task.absolute_path}}/References/Stalker_Pyramid/ForWeb folder.

        :param task: The task that a reference is uploaded to. Should be an
          instance of :class:`.Task` class.
        :type task: :class:`.Task`
        :param file_object: The file like object holding the content of the
          uploaded file.
        :param str filename: The original filename.
        :returns: :class:`.Link` instance.
        """
        ############################################################
        # ORIGINAL
        ############################################################
        file_path = os.path.join(
            os.path.join(task.absolute_path),
            self.reference_path
        )

        # upload it
        reference_file_full_path = \
            self.upload_file(file_object, file_path, filename)

        reference_file_file_name = os.path.basename(reference_file_full_path)
        reference_file_base_name = \
            os.path.splitext(reference_file_file_name)[0]

        # create a Link instance and return it.
        # use a Repository relative path
        repo = task.project.repository
        assert isinstance(repo, Repository)
        relative_full_path = repo.make_relative(reference_file_full_path)

        link = Link(full_path=relative_full_path, original_filename=filename)

        # create a thumbnail for the given reference
        # don't forget that the first thumbnail is the Web viewable version
        # and the second thumbnail is the thumbnail

        ############################################################
        # WEB VERSION
        ############################################################
        web_version_temp_full_path = \
            self.generate_media_for_web(reference_file_full_path)
        web_version_extension = \
            os.path.splitext(web_version_temp_full_path)[-1]

        web_version_file_name = '%s%s' % (reference_file_base_name,
                                          web_version_extension)
        web_version_full_path = \
            os.path.join(
                os.path.dirname(reference_file_full_path),
                'ForWeb',
                web_version_file_name
            )
        web_version_repo_relative_full_path = \
            repo.make_relative(web_version_full_path)
        web_version_link = Link(
            full_path=web_version_repo_relative_full_path,
            original_filename=web_version_file_name
        )

        # move it to repository
        try:
            os.makedirs(os.path.dirname(web_version_full_path))
        except OSError:  # path exists
            pass
        shutil.move(web_version_temp_full_path, web_version_full_path)

        ############################################################
        # THUMBNAIL
        ############################################################
        # finally generate a Thumbnail
        thumbnail_temp_full_path = \
            self.generate_thumbnail(reference_file_full_path)
        thumbnail_extension = os.path.splitext(thumbnail_temp_full_path)[-1]
        thumbnail_file_name = '%s%s' % (reference_file_base_name,
                                        thumbnail_extension)

        thumbnail_full_path = \
            os.path.join(
                os.path.dirname(reference_file_full_path),
                'Thumbnail',
                thumbnail_file_name
            )
        thumbnail_repo_relative_full_path = \
            repo.make_relative(thumbnail_full_path)
        thumbnail_link = Link(
            full_path=thumbnail_repo_relative_full_path,
            original_filename=thumbnail_file_name
        )

        # move it to repository
        try:
            os.makedirs(os.path.dirname(thumbnail_full_path))
        except OSError:  # path exists
            pass
        shutil.move(thumbnail_temp_full_path, thumbnail_full_path)

        ############################################################
        # LINK Objects
        ############################################################
        # link them
        # assign it as a reference to the given task
        task.references.append(link)
        link.thumbnail = web_version_link
        web_version_link.thumbnail = thumbnail_link

        return link

    def upload_version(self, task, file_object, take_name=None, extension=''):
        """Uploads versions to the Task.path/ folder and creates a Version
        object to there. Again the Version object will have a Repository root
        relative path.

        The filename of the version will be automatically generated by Stalker.

        :param task: The task that a version is uploaded to. Should be an
          instance of :class:`.Task` class.
        :param file_object: A file like object holding the content of the
          version.
        :param str take_name: A string showing the the take name of the
          Version. If skipped defaults.version_take_name will be used.
        :param str extension: The file extension of the version.
        :returns: :class:`.Version` instance.
        """
        if take_name is None:
            take_name = defaults.version_take_name

        v = Version(task=task,
                    take_name=take_name,
                    created_with='Stalker Pyramid')
        v.update_paths()
        v.extension = extension

        # upload it
        self.upload_file(file_object, v.absolute_path, v.filename)

        return v

    def upload_version_output(self, version, file_object, filename):
        """Uploads a file as an output for the given :class:`.Version`
        instance. Will store the file in
        {{Version.absolute_path}}/Outputs/Stalker_Pyramid/ folder.

        It will also generate a thumbnail in
        {{Version.absolute_path}}/Outputs/Stalker_Pyramid/Thumbs folder and a
        web friendly version (PNG for images, WebM for video files) under
        {{Version.absolute_path}}/Outputs/Stalker_Pyramid/ForWeb folder.

        :param version: A :class:`.Version` instance that the output is
          uploaded for.
        :type version: :class:`.Version`
        :param file_object: The file like object holding the content of the
          uploaded file.
        :param str filename: The original filename.
        :returns: :class:`.Link` instance.
        """
        ############################################################
        # ORIGINAL
        ############################################################
        file_path = os.path.join(
            os.path.join(version.absolute_path),
            self.version_output_path
        )

        # upload it
        version_output_file_full_path = \
            self.upload_file(file_object, file_path, filename)

        version_output_file_name = \
            os.path.basename(version_output_file_full_path)
        version_output_base_name = \
            os.path.splitext(version_output_file_name)[0]

        # create a Link instance and return it.
        # use a Repository relative path
        repo = version.task.project.repository
        assert isinstance(repo, Repository)
        relative_full_path = str(repo.make_relative(
            str(version_output_file_full_path)
        ))

        link = Link(
            full_path=relative_full_path,
            original_filename=str(filename)
        )

        # create a thumbnail for the given version output
        # don't forget that the first thumbnail is the Web viewable version
        # and the second thumbnail is the thumbnail

        ############################################################
        # WEB VERSION
        ############################################################
        web_version_temp_full_path = \
            self.generate_media_for_web(version_output_file_full_path)
        web_version_extension = \
            os.path.splitext(web_version_temp_full_path)[-1]
        web_version_full_path = \
            os.path.join(
                os.path.dirname(version_output_file_full_path),
                'ForWeb',
                version_output_base_name + web_version_extension
            )
        web_version_repo_relative_full_path = \
            repo.make_relative(str(web_version_full_path))
        web_version_link = Link(
            full_path=web_version_repo_relative_full_path,
            original_filename=filename
        )

        # move it to repository
        try:
            os.makedirs(os.path.dirname(web_version_full_path))
        except OSError:  # path exists
            pass
        shutil.move(web_version_temp_full_path, web_version_full_path)

        ############################################################
        # THUMBNAIL
        ############################################################
        # finally generate a Thumbnail
        thumbnail_temp_full_path = \
            self.generate_thumbnail(version_output_file_full_path)
        thumbnail_extension = os.path.splitext(thumbnail_temp_full_path)[-1]

        thumbnail_full_path = \
            os.path.join(
                os.path.dirname(version_output_file_full_path),
                'Thumbnail',
                version_output_base_name + thumbnail_extension
            )
        thumbnail_repo_relative_full_path = \
            repo.make_relative(thumbnail_full_path)
        thumbnail_link = Link(
            full_path=thumbnail_repo_relative_full_path,
            original_filename=filename
        )

        # move it to repository
        try:
            os.makedirs(os.path.dirname(thumbnail_full_path))
        except OSError:  # path exists
            pass
        shutil.move(thumbnail_temp_full_path, thumbnail_full_path)

        ############################################################
        # LINK Objects
        ############################################################
        # link them
        # assign it as an output to the given version
        version.outputs.append(link)
        link.thumbnail = web_version_link
        web_version_link.thumbnail = thumbnail_link

        return link
