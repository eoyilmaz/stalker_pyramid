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
import logging
import os

from pyramid.view import view_config
from pyramid.response import Response

from sqlalchemy import distinct

from stalker import db, Task, Version, Entity, defaults

from stalker_pyramid.views import (get_logged_in_user, get_user_os,
                                   PermissionChecker, milliseconds_since_epoch)
from stalker_pyramid.views.link import MediaManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='create_version_dialog',
    renderer='templates/version/dialog/create_version_dialog.jinja2',
)
def create_version_dialog(request):
    """creates a create_version_dialog by using the given task
    """
    logger.debug('inside create_version_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('tid', -1)
    task = Task.query.filter(Task.task_id == task_id).first()

    takes = map(
        lambda x: x[0],
        db.DBSession.query(distinct(Version.take_name))
        .filter(Version.task == task)
        .all()
    )

    if defaults.version_take_name not in takes:
        takes.append(defaults.version_take_name)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'task': task,
        'default_take_name': defaults.version_take_name,
        'take_names': [defaults.version_take_name]
    }


@view_config(
    route_name='update_version_dialog',
    renderer='templates/version/dialog/update_version_dialog.jinja2',
)
def update_version_dialog(request):
    """updates a create_version_dialog by using the given task
    """
    # get logged in user
    logged_in_user = get_logged_in_user(request)

    version_id = request.matchdict.get('id', -1)
    version = Version.query.filter_by(id=version_id).first()

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'task': version.task,
        'version': version
    }


@view_config(
    route_name='create_version'
)
def create_version(request):
    """runs when creating a version
    """
    logged_in_user = get_logged_in_user(request)

    task_id = request.params.get('task_id')
    task = Task.query.filter(Task.id == task_id).first()

    take_name = request.params.get('take_name', 'Main')
    is_published = \
        True if request.params.get('is_published') == 'on' else False
    description = request.params.get('description')
    bind_to_originals = \
        True if request.params.get('bind_to_originals') == 'on' else False

    file_object = request.POST.getall('file_object')[0]

    logger.debug('file_object: %s' % file_object)
    logger.debug('take_name: %s' % take_name)
    logger.debug('is_published: %s' % is_published)
    logger.debug('description: %s' % description)
    logger.debug('bind_to_originals: %s' % bind_to_originals)

    if task:
        extension = os.path.splitext(file_object.filename)[-1]
        mm = MediaManager()
        v = mm.upload_version(
            task=task,
            file_object=file_object.file,
            take_name=take_name,
            extension=extension
        )

        v.created_by = logged_in_user
        v.is_published = is_published

        # check if bind_to_originals is true
        if bind_to_originals and extension == '.ma':
            from stalker_pyramid.views import archive
            arch = archive.Archiver()
            arch.bind_to_original(v.absolute_full_path)

        db.DBSession.add(v)
        logger.debug('version added to: %s' % v.absolute_full_path)
    else:
        return Response('No task with id: %s' % task_id, 500)

    return Response('Version is uploaded successfully')


@view_config(
    route_name='get_entity_versions',
    renderer='json'
)
@view_config(
    route_name='get_task_versions',
    renderer='json'
)
def get_entity_versions(request):
    """returns all the Shots of the given Project
    """
    logger.debug('get_versions is running')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    user_os = get_user_os(request)

    logger.debug('entity_id : %s' % entity_id)
    logger.debug('user os: %s' % user_os)

    repo = entity.project.repository

    path_converter = lambda x: x
    if repo:
        if user_os == 'windows':
            path_converter = repo.to_windows_path
        elif user_os == 'linux':
            path_converter = repo.to_linux_path
        elif user_os == 'osx':
            path_converter = repo.to_osx_path


    return [{
        'id': version.id,
        'task': {'id': version.task.id,
                 'name': version.task.name},
        'take_name': version.take_name,
        'parent': {
            'id': version.parent.id,
            'version_number': version.parent.version_number,
            'take_name': version.parent.take_name
            } if version.parent else None,
        'absolute_full_path': path_converter(version.absolute_full_path),
        'created_by': {
            'id': version.created_by.id if version.created_by else None,
            'name': version.created_by.name if version.created_by else None
        },
        'is_published': version.is_published,
        'version_number': version.version_number,
        'date_created': milliseconds_since_epoch(version.date_updated),
        'created_with': version.created_with,
        'description':version.description
    } for version in entity.versions]


@view_config(
    route_name='list_version_outputs',
    renderer='templates/version/content_list_version_outputs.jinja2'
)
def list_version_outputs(request):
    """lists the versions of the given task
    """
    version_id = request.matchdict.get('id', -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug('entity_id : %s' % version_id)
    return {
        'version': version,
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='list_version_inputs',
    renderer='templates/version/content_list_version_inputs.jinja2'
)
def list_version_inputs(request):
    """lists the versions of the given task
    """
    logger.debug('list_version_inputs is running')

    version_id = request.matchdict.get('id', -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug('entity_id : %s' % version_id)
    return {
        'version': version,
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='list_version_children',
    renderer='templates/version/content_list_versions_children.jinja2'
)
def list_version_children(request):
    """lists the versions of the given task
    """
    logger.debug('list_version_children is running')

    version_id = request.matchdict.get('id', -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug('entity_id : %s' % version_id)
    return {
        'version': version,
        'has_permission': PermissionChecker(request)
    }


# @view_config(
#     route_name='get_version_outputs_count',
#     renderer='json'
# )
# def get_version_outputs_count(request):
#     """returns the count of the given version
#     """
#     version_id = request.params.get('id')
#
#     sql_query = """select
# count("Links".id)
# from "Versions"
# join "Version_Outputs" on "Versions".id = "Version_Outputs".version_id
# join "Links" on "Version_Outputs".link_id = "Links".id
# where "Versions".id = %(id)s
#     """ % {'id': version_id}
#
#     return db.DBSession.connection().execute(sql_query).fetchone()[0]

#
# @view_config(
#     route_name='get_task_version_outputs_count',
#     renderer='json'
# )
# def get_task_version_outputs_count(request):
#     """returns the count of the given version
#     """
#     task_id = request.params.get('id')
#
#     sql_query = """select
#     count("Links".id)
# from "Tasks"
# join "Versions" on "Tasks".id = "Versions".task_id
# join "Version_Outputs" on "Versions".id = "Version_Outputs".version_id
# join "Links" on "Version_Outputs".link_id = "Links".id
# where "Tasks".id = %(id)s
#     """ % {'id': task_id}
#
#     return db.DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='pack_version'
)
def pack_version(request):
    """packs the requested version and returns a download link for it
    """
    version_id = request.matchdict.get('id')
    version = Version.query.get(version_id)

    if version:
        # before doing anything check if the file exists
        import os
        archive_path = os.path.join(
            version.absolute_path,
            version.nice_name + '.zip'
        )
        if os.path.exists(archive_path):
            # just serve the same file
            logger.debug('ZIP exists, not creating it again!')
            new_zip_path = archive_path
        else:
            # create the zip file
            logger.debug('ZIP does not exists, creating it!')
            import shutil
            from stalker_pyramid.views.archive import Archiver

            path = version.absolute_full_path
            arch = Archiver()
            task = version.task
            if False:
                assert(isinstance(version, Version))
                assert(isinstance(task, Task))
            project_name = version.nice_name
            project_path = arch.flatten(path, project_name=project_name)

            # append link file
            stalker_link_file_path = os.path.join(project_path,
                                                  'scenes/stalker_links.txt')

            import stalker_pyramid
            version_upload_link = '%s/tasks/%s/versions/list' % (
                stalker_pyramid.stalker_server_external_url,
                task.id
            )
            request_review_link = '%s/tasks/%s/view' % (
                stalker_pyramid.stalker_server_external_url,
                task.id
            )
            with open(stalker_link_file_path, 'w+') as f:
                f.write("Version Upload Link: %s\n"
                        "Request Review Link: %s\n" % (version_upload_link,
                                                       request_review_link))
            zip_path = arch.archive(project_path)

            new_zip_path = os.path.join(
                version.absolute_path,
                os.path.basename(zip_path)
            )

            # move the zip right beside the original version file
            shutil.move(zip_path, new_zip_path)

            # now remove the temp files
            shutil.rmtree(project_path, ignore_errors=True)

        # open the zip file in browser
        # serve the file new_zip_path
        from pyramid.response import FileResponse

        logger.debug('serving packed version file: %s' % new_zip_path)

        response = FileResponse(
            new_zip_path,
            request=request,
            content_type='application/force-download',
        )

        # update the content-disposition header
        response.headers['content-disposition'] = \
            str('attachment; filename=' + os.path.basename(new_zip_path))

        return response
