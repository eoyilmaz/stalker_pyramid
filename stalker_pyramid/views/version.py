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
import logging
import shutil
import os

from pyramid.httpexceptions import HTTPOk, HTTPServerError
from pyramid.view import view_config
from sqlalchemy import distinct

from stalker import Task, TimeLog, Version, Link, Entity, defaults
from stalker.db import DBSession

from stalker_pyramid.views import (get_logged_in_user, get_user_os,
                                   PermissionChecker, get_multi_integer)
from stalker_pyramid.views.link import convert_file_link_to_full_path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@view_config(
    route_name='dialog_create_task_version',
    renderer='templates/version/dialog_create_version.jinja2',
)
def create_version_dialog(request):
    """creates a create_version_dialog by using the given task
    """
    logger.debug('inside create_version_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.task_id==task_id).first()

    takes = map(
        lambda x: x[0],
        DBSession.query(distinct(Version.take_name))
        .filter(Version.task == task)
        .all()
    )

    if defaults.version_take_name not in takes:
        takes.append(defaults.version_take_name)

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'task': task,
        'default_take_name': defaults.version_take_name,
        'take_names': [defaults.version_take_name]
    }

@view_config(
    route_name='dialog_update_version',
    renderer='templates/version/dialog_create_version.jinja2',
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


# @view_config(
#     route_name='create_version'
# )
# def create_version(request):
#     """runs when creating a version
#     """
#     logged_in_user = get_logged_in_user(request)
# 
#     task_id = request.params.get('task_id')
#     task = Task.query.filter(Task.id==task_id).first()
# 
#     if task:
# 
#         version = Version(
#             task=task,
#             created_by=logged_in_user,
#         )
# 
#         DBSession.add(version)
#     else:
#         HTTPServerError()
# 
#     return HTTPOk()

@view_config(
    route_name='assign_version',
)
def assign_version(request):
    """assigns the version to the given entity
    """
    # TODO: this should be renamed to create version
    # collect data
    link_ids = get_multi_integer(request, 'link_ids')
    task_id = request.params.get('task_id', -1)

    link = Link.query.filter(Link.id.in_(link_ids)).first()
    task = Task.query.filter_by(id=task_id).first()
    logged_in_user = get_logged_in_user(request)

    logger.debug('link_ids  : %s' % link_ids)
    logger.debug('link      : %s' % link)
    logger.debug('task_id   : %s' % task_id)
    logger.debug('task      : %s' % task)

    if task and link:
        # delete the link and create a version instead
        full_path = convert_file_link_to_full_path(link.full_path)
        take_name = request.params.get('take_name', defaults.version_take_name)
        publish = bool(request.params.get('publish'))

        logger.debug('publish : %s' % publish)

        path_and_filename, extension = os.path.splitext(full_path)

        version = Version(task=task, take_name=take_name,
                          created_by=logged_in_user)
        version.is_published = publish

        # generate path values
        version.update_paths()
        version.extension = extension

        # specify that this version is created with Stalker Pyramid
        version.created_with = 'StalkerPyramid' # TODO: that should also be a config value

        # now move the link file to the version.absolute_full_path
        try:
            os.makedirs(
                os.path.dirname(version.absolute_full_path)
            )
        except OSError:
            # dir exists
            pass

        logger.debug('full_path : %s' % full_path)
        logger.debug('version.absolute_full_path : %s' % version.absolute_full_path)

        shutil.copyfile(full_path, version.absolute_full_path)
        os.remove(full_path)

        # it is now safe to delete the link
        DBSession.add(task)
        DBSession.delete(link)
        DBSession.add(version)

    return HTTPOk()


@view_config(
    route_name='update_version'
)
def update_version(request):
    """runs when updating a version
    """
    logged_in_user = get_logged_in_user(request)

    version_id = request.params.get('version_id')
    version = TimeLog.query.filter_by(id=version_id).first()

    name = request.params.get('name')

    if version and name:

        version.name = name
        version.updated_by = logged_in_user
    else:
        DBSession.add(version)

    return HTTPOk()


@view_config(
    route_name='get_task_versions',
    renderer='json'
)
def get_task_versions(request):
    """returns all the Shots of the given Project
    """
    logger.debug('get_versions is running')
    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter_by(id=task_id).first()
    version_data = []

    user_os = get_user_os(request)
    logger.debug('entity_id : %s' % task_id)
    logger.debug('user os: %s' % user_os)

    repo = task.project.repository

    # if entity.versions:
    for version in task.versions:
        logger.debug('version.task.id : %s' % version.task.id)
        assert isinstance(version, Version)

        version_absolute_full_path = version.absolute_full_path
        if repo:
            if user_os == 'windows':
                version_absolute_full_path = \
                    repo.to_windows_path(version.absolute_full_path)
            elif user_os == 'linux':
                version_absolute_full_path = \
                    repo.to_linux_path(version.absolute_full_path)
            elif user_os == 'osx':
                version_absolute_full_path = \
                    repo.to_osx_path(version.absolute_full_path)

        version_data.append({
            'id': version.id,
            'name': version.name,
            'task_id': version.task.id,
            'task_name': version.task.name,
            'parent_name': ' | '.join([parent.name for parent in version.task.parents]),
            'absolute_full_path': version_absolute_full_path,
            'created_by_id': version.created_by_id,
            'created_by_name': version.created_by.name,
            'is_published': version.is_published
            # 'hours_to_complete': version.hours_to_complete,
            # 'notes': version.notes
        })

    return version_data


@view_config(
    route_name='view_version',
    renderer='templates/version/page_view_version.jinja2'
)
def view_version(request):
    """lists the versions of the given task
    """

    logger.debug('view_version is running')

    version_id = request.matchdict.get('id', -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug('version_id : %s' % version_id)
    return {
        'version': version,
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='list_version_outputs',
    renderer='templates/version/content_list_version_outputs.jinja2'
)
def list_version_outputs(request):
    """lists the versions of the given task
    """

    logger.debug('list_version_outputs is running')

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

