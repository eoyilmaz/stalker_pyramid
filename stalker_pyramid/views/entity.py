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
from stalker import Entity
from stalker_pyramid.views import PermissionChecker, get_logged_in_user, milliseconds_since_epoch


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



@view_config(
    route_name='view_user_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
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
    route_name='list_user_tickets',
    renderer='templates/ticket/content_list_tickets.jinja2'
)
@view_config(
    route_name='list_entity_tickets',
    renderer='templates/ticket/content_list_tickets.jinja2'
)
@view_config(
    route_name='list_task_tickets',
    renderer='templates/ticket/content_list_tickets.jinja2'
)
@view_config(
    route_name='list_projects',
    renderer='templates/project/content_list_projects.jinja2'
)
@view_config(
    route_name='list_user_projects',
    renderer='templates/project/content_list_projects.jinja2'
)
@view_config(
    route_name='list_studio_vacations',
    renderer='templates/vacation/content_list_vacations.jinja2'
)
@view_config(
    route_name='list_user_vacations',
    renderer='templates/vacation/content_list_vacations.jinja2'
)
@view_config(
    route_name='list_user_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
)
@view_config(
    route_name='list_project_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
)
@view_config(
    route_name='list_task_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
)
@view_config(
    route_name='list_entity_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
)
@view_config(
    route_name='list_studio_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
)
@view_config(
    route_name='list_entity_references',
    renderer='templates/link/content_list_references.jinja2'
)
@view_config(
    route_name='list_task_versions',
    renderer='templates/version/content_list_versions.jinja2'
)
@view_config(
    route_name='list_project_tickets',
    renderer='templates/ticket/content_list_tickets.jinja2'
)
@view_config(
    route_name='list_project_references',
    renderer='templates/link/content_list_references.jinja2'
)
@view_config(
    route_name='view_project',
    renderer='templates/project/page_view_project.jinja2'
)
@view_config(
    route_name='list_project_users',
    renderer='templates/auth/content_list_users.jinja2'
)
@view_config(
    route_name='list_users',
    renderer='templates/auth/content_list_users.jinja2'
)
@view_config(
    route_name='list_project_assets',
    renderer='templates/asset/content_list_assets.jinja2'
)
@view_config(
    route_name='list_project_shots',
    renderer='templates/shot/content_list_shots.jinja2'
)
@view_config(
    route_name='list_project_sequences',
    renderer='templates/sequence/content_list_sequences.jinja2'
)
@view_config(
    route_name='list_department_users',
    renderer='templates/auth/content_list_users.jinja2'
)
@view_config(
    route_name='list_group_users',
    renderer='templates/auth/content_list_users.jinja2'
)
@view_config(
    route_name='summarize_asset',
    renderer='templates/asset/content_summarize_asset.jinja2'
)
@view_config(
    route_name='summarize_department',
    renderer='templates/department/content_summarize_department.jinja2'
)
@view_config(
    route_name='summarize_group',
    renderer='templates/auth/content_summarize_group.jinja2'
)
@view_config(
    route_name='summarize_project',
    renderer='templates/project/content_summarize_project.jinja2'
)
@view_config(
    route_name='summarize_sequence',
    renderer='templates/sequence/content_summarize_sequence.jinja2'
)
@view_config(
    route_name='summarize_shot',
    renderer='templates/shot/content_summarize_shot.jinja2'
)
@view_config(
    route_name='summarize_studio',
    renderer='templates/studio/content_summarize_studio.jinja2'
)
@view_config(
    route_name='summarize_task',
    renderer='templates/task/content_summarize_task.jinja2'
)
@view_config(
    route_name='summarize_ticket',
    renderer='templates/ticket/content_summarize_ticket.jinja2'
)
@view_config(
    route_name='summarize_user',
    renderer='templates/auth/content_summarize_user.jinja2'
)
@view_config(
    route_name='summarize_version',
    renderer='templates/version/content_summarize_version.jinja2'
)
@view_config(
    route_name='view_shot',
    renderer='templates/shot/page_view_shot.jinja2'
)
@view_config(
    route_name='view_task',
    renderer='templates/task/page_view_task.jinja2'
)
def get_entity_related_data(request):
    """lists the time logs of the given task
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return {
        'entity': entity,
        'has_permission': PermissionChecker(request),
        'logged_in_user': get_logged_in_user(request),
        'milliseconds_since_epoch': milliseconds_since_epoch
    }
