# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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
import logging
from pyramid.view import view_config
from stalker import Entity, Studio, Project, Group, User

import stalker_pyramid
from stalker_pyramid.views import PermissionChecker, get_logged_in_user, milliseconds_since_epoch


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='user_dialog',
    renderer='templates/auth/dialog/user_dialog.jinja2',
)
@view_config(
    route_name='list_entity_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_studio_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_project_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_department_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_group_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='list_users',
    renderer='templates/auth/list/list_entity_users.jinja2'
)
@view_config(
    route_name='view_user',
    renderer='templates/auth/view/view_user.jinja2'
)
@view_config(
    route_name='list_user_groups',
    renderer='templates/group/list/list_entity_groups.jinja2'
)
@view_config(
    route_name='list_entity_groups',
    renderer='templates/group/list/list_entity_groups.jinja2'
)
@view_config(
    route_name='department_dialog',
    renderer='templates/department/dialog/department_dialog.jinja2',
)
@view_config(
    route_name='list_entity_departments',
    renderer='templates/department/list/list_entity_departments.jinja2'
)
@view_config(
    route_name='list_user_departments',
    renderer='templates/department/list/list_entity_departments.jinja2'
)
@view_config(
    route_name='list_studio_departments',
    renderer='templates/department/list/list_entity_departments.jinja2'
)
@view_config(
    route_name='project_dialog',
    renderer='templates/project/dialog/project_dialog.jinja2',
)
@view_config(
    route_name='list_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='list_entity_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='list_user_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='list_studio_projects',
    renderer='templates/project/list/list_entity_projects.jinja2'
)
@view_config(
    route_name='view_project',
    renderer='templates/project/view/view_project.jinja2'
)
@view_config(
    route_name='view_studio',
    renderer='templates/studio/view/view_studio.jinja2'
)
@view_config(
    route_name='list_project_assets',
    renderer='templates/asset/list/list_entity_assets.jinja2'
)
@view_config(
    route_name='list_project_shots',
    renderer='templates/shot/list/list_entity_shots.jinja2'
)
@view_config(
    route_name='list_project_sequences',
    renderer='templates/sequence/list/list_entity_sequences.jinja2'
)
@view_config(
    route_name='view_user_tasks',
    renderer='templates/task/list_entity_tasks.jinja2'
)
@view_config(
    route_name='view_entity_nav_bar',
    renderer='templates/content_nav_bar.jinja2',
)
@view_config(
    route_name='dialog_upload_entity_reference',
    renderer='templates/link/dialog_upload_reference.jinja2'
)
@view_config(
    route_name='dialog_upload_entity_thumbnail',
    renderer='templates/link/dialog_upload_thumbnail.jinja2'
)
@view_config(
    route_name='list_task_time_logs',
    renderer='templates/time_log/content_list_time_logs.jinja2'
)
@view_config(
    route_name='list_user_time_logs',
    renderer='templates/time_log/content_list_time_logs.jinja2'
)
@view_config(
    route_name='list_entity_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_user_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_project_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_task_tickets',
    renderer='templates/ticket/list_entity_tickets.jinja2'
)
@view_config(
    route_name='list_studio_vacations',
    renderer='templates/vacation/list/list_entity_vacations.jinja2'
)
@view_config(
    route_name='list_user_vacations',
    renderer='templates/vacation/list/list_entity_vacations.jinja2'
)
@view_config(
    route_name='list_user_tasks',
    renderer='templates/task/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_project_tasks',
    renderer='templates/task/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_task_tasks',
    renderer='templates/task/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_entity_tasks',
    renderer='templates/task/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_studio_tasks',
    renderer='templates/task/list_entity_tasks.jinja2'
)
@view_config(
    route_name='list_entity_references',
    renderer='templates/link/list_entity_references.jinja2'
)
@view_config(
    route_name='list_task_versions',
    renderer='templates/version/content_list_versions.jinja2'
)
@view_config(
    route_name='list_project_references',
    renderer='templates/link/content_list_references.jinja2'
)
@view_config(
    route_name='view_ticket',
    renderer='templates/ticket/view_ticket.jinja2'
)
def get_entity_related_data(request):
    """lists the time logs of the given task
    """
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    entity_id = request.matchdict.get('id')
    if not entity_id:
        entity = studio
    else:
        entity = Entity.query.filter_by(id=entity_id).first()

    projects = Project.query.all()

    mode = request.matchdict.get('mode', None)

    came_from = request.params.get('came_from', request.url)

    return {
        'mode': mode,
        'entity': entity,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'stalker_pyramid': stalker_pyramid,
        'projects': projects,
        'studio': studio,
        'came_from': came_from
    }
