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
"""
Stalker Pyramid is a Production Asset Management System (ProdAM) designed for
Animation and VFX Studios. See docs for more information.
"""
from zope.sqlalchemy import ZopeTransactionExtension

__version__ = '0.1.0.b3'


# before anything about stalker create the defaults
from stalker.config import defaults
from stalker.models.auth import group_finder

import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    from pyramid.config import Configurator
    from pyramid.authentication import AuthTktAuthenticationPolicy
    from pyramid.authorization import ACLAuthorizationPolicy

    # setup the database to the given settings
    from stalker import db
    from stalker.db import DBSession

    # use the ZopeTransactionExtension for session
    db.setup(settings)
    DBSession.remove()
    DBSession.configure(extension=ZopeTransactionExtension())

    # setup authorization and authentication
    authn_policy = AuthTktAuthenticationPolicy(
        'sosecret',
        hashalg='sha512',
        callback=group_finder
    )
    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(
        settings=settings,
        root_factory='stalker.models.auth.RootFactory'
    )
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    config.include('pyramid_jinja2')
    config.include('pyramid_mailer')
    config.add_static_view('static', 'static', cache_max_age=3600)

    # *************************************************************************
    # Basics
    config.add_route('home', '/')
    config.add_route('me_menu', '/me_menu')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_route('busy_dialog', 'dialog/busy')

    # addresses like http:/localhost:6543/SPL/{some_path} will let SP to serve those files
    # SPL : Stalker Pyramid Local
    config.add_route(
        'serve_files',
        'SPL' + '/{partial_file_path:[a-zA-Z0-9/\.]+}'
    )

    logger.debug(defaults.server_side_storage_path + '/{partial_file_path}')

    # *************************************************************************
    # DATA VIEWS
    # *************************************************************************

    # *************************************************************************
    # Entities

    config.add_route('dialog_upload_entity_thumbnail', 'entities/{id}/thumbnail/upload/dialog')
    config.add_route('dialog_upload_entity_reference', 'entities/{id}/references/upload/dialog')

    config.add_route('create_entity_users_dialog',     'entities/{id}/users/create/dialog')

    config.add_route('append_users_to_entity_dialog',  'entities/{id}/users/append/dialog')
    config.add_route('append_users_to_entity',         'entities/{id}/users/append')

    config.add_route('list_entity_users',              'entities/{id}/users/list')

    # get routes returns json
    config.add_route('get_entity_users',               'entities/{id}/users/')
    config.add_route('get_entity_users_not',           'entities/{id}/users/not')
    config.add_route('get_entity_references',          'entities/{id}/references/')
    config.add_route('get_entity_departments',         'entities/{id}/departments/')
    config.add_route('get_entity_groups',              'entities/{id}/groups/')
    config.add_route('get_entity_tasks',               'entities/{id}/tasks/')
    config.add_route('get_entity_tickets',             'entities/{id}/tickets/')
    config.add_route('get_entity_time_logs',           'entities/{id}/time_logs/')
    config.add_route('get_entity_projects',            'entities/{id}/projects/')
    config.add_route('get_entity_sequences',           'entities/{id}/sequences/')
    config.add_route('get_entity_vacations',           'entities/{id}/vacations/')

    config.add_route('list_entity_departments',        'entities/{id}/departments/list') # html
    config.add_route('list_entity_tasks',              'entities/{id}/tasks/list') # html
    config.add_route('list_entity_tickets',            'entities/{id}/tickets/list') # html
    config.add_route('list_entity_projects',           'entities/{id}/projects/list')
    config.add_route('list_entity_references',         'entities/{id}/references/list') # html


    config.add_route('view_entity_nav_bar',            'entities/{id}/nav_bar')
    config.add_route('view_entity_tasks',              'entities/{id}/tasks/view')

    # *************************************************************************
    # Thumbnail References and Links

    config.add_route('get_task_references',  'tasks/{id}/references/') # json
    config.add_route('get_asset_references', 'assets/id}/references/') # json
    config.add_route('get_shot_references',  'shots/{id}/references/') # json
    config.add_route('get_task_versions',    'tasks/{id}/versions/') # json

    config.add_route('get_references',       'references/')
    config.add_route('get_reference',        'references/{id}')

    config.add_route('upload_files',         'upload_files')
    config.add_route('assign_thumbnail',     'assign_thumbnail')
    config.add_route('assign_reference',     'assign_reference')

    # *************************************************************************
    # Studio
    config.add_route('dialog_create_studio',  'studios/create/dialog')
    config.add_route('dialog_update_studio',  'studios/update/dialog')

    config.add_route('create_studio',         'studios/create')
    config.add_route('update_studio',         'studios/{id}/update')

    config.add_route('view_studio',           'studios/{id}/view')
    config.add_route('summarize_studio',      'studios/{id}/summarize')

    config.add_route('get_studio_tasks',      'studios/{id}/tasks/')
    config.add_route('get_studio_vacations',  'studios/{id}/vacations/') # json

    config.add_route('list_studio_tasks',     'studios/{id}/tasks/list')
    config.add_route('list_studio_vacations', 'studios/{id}/vacations/list') # html


    # *************************************************************************
    # Project
    config.add_route('dialog_create_project',      'projects/create/dialog')
    config.add_route('dialog_update_project',      'projects/{id}/update/dialog')
    config.add_route('dialog_create_project_task', 'projects/{id}/tasks/create/dialog')
    config.add_route('dialog_create_asset',        'projects/{id}/assets/create/dialog')

    config.add_route('get_project_tasks',          'projects/{id}/tasks/') # json

    config.add_route('create_project',             'projects/create')
    config.add_route('update_project',             'projects/{id}/update')

    config.add_route('view_project',               'projects/{id}/view')

    config.add_route('list_projects',              'projects/list') # html
    config.add_route('list_project_users',         'projects/{id}/users/list')
    config.add_route('list_project_tasks',         'projects/{id}/tasks/list') # html
    config.add_route('list_project_assets',        'projects/{id}/assets/list')
    config.add_route('list_project_shots',         'projects/{id}/shots/list')
    config.add_route('list_project_sequences',     'projects/{id}/sequences/list')
    config.add_route('list_project_tickets',       'projects/{id}/tickets/list')
    config.add_route('list_project_references',    'projects/{id}/references/list')

    config.add_route('summarize_project',          'projects/{id}/summarize')

    config.add_route('get_projects',               'projects/')
    config.add_route('get_project_users',          'projects/{id}/users/')
    config.add_route('get_project_assets',         'projects/{id}/assets/')
    config.add_route('get_project_shots',          'projects/{id}/shots/')
    config.add_route('get_project_sequences',      'projects/{id}/sequences/')
    config.add_route('get_project_references',     'projects/{id}/references/') # json
    config.add_route('get_project_tickets',        'projects/{id}/tickets/') # json



    # *************************************************************************
    # ImageFormat
    config.add_route('dialog_create_image_format', 'image_formats/create/dialog')
    config.add_route('dialog_update_image_format', 'image_formats/{id}/update/dialog')

    config.add_route('create_image_format', 'image_formats/create')
    config.add_route('update_image_format', 'image_formats/{id}/update')

    config.add_route('list_image_formats', 'image_formats/list') # html
    config.add_route('get_image_formats', 'image_formats/') # json

    # *************************************************************************
    # Repository
    config.add_route('dialog_create_repository', 'repositories/create/dialog')
    config.add_route('dialog_update_repository', 'repositories/{id}/update/dialog')

    config.add_route('create_repository', 'repositories/create')
    config.add_route('update_repository', 'repositories/{id}/update')

    config.add_route('list_repositories', 'repositories/list') # html
    config.add_route('get_repositories', 'repositories/') # json

    # *************************************************************************
    # Structure
    config.add_route('dialog_create_structure', 'structures/create/dialog')
    config.add_route('dialog_update_structure', 'structures/{id}/update/dialog')

    config.add_route('create_structure', 'structures/create')
    config.add_route('update_structure', 'structures/{id}/update')
    config.add_route('get_structures',   'structures/') # json

    # *************************************************************************
    # User

    # dialogs
    config.add_route('dialog_create_department_user', 'departments/{id}/users/create/dialog')
    config.add_route('dialog_create_group_user',      'groups/{id}/users/create/dialog')
    config.add_route('dialog_create_user',            'users/create/dialog')

    config.add_route('dialog_update_user',    'users/{id}/update/dialog')
    config.add_route('dialog_create_vacation','users/{id}/vacations/create/dialog')

    config.add_route('append_user_to_departments_dialog', 'users/{id}/departments/append/dialog')
    config.add_route('append_user_to_departments', 'users/{id}/departments/append')
    config.add_route('append_user_to_department',  'users/{uid}/department/{did}/append') # unused

    config.add_route('append_user_to_groups_dialog', 'users/{id}/groups/append/dialog')
    config.add_route('append_user_to_groups', 'users/{id}/groups/append')
    config.add_route('append_user_to_group',  'users/{uid}/groups/{gid}/append')# unused

    config.add_route('create_user',           'users/create')
    config.add_route('update_user',           'users/{id}/update')
    config.add_route('view_user',             'users/{id}/view')
    config.add_route('summarize_user',        'users/{id}/summarize')

    config.add_route('get_users',             'users/') # json
    config.add_route('get_user_departments',  'users/{id}/departments/') # json
    config.add_route('get_user_groups',       'users/{id}/groups/') # json
    config.add_route('get_user_tasks',        'users/{id}/tasks/') # json
    config.add_route('get_user_vacations',    'users/{id}/vacations/') # json
    config.add_route('get_user_tickets',      'users/{id}/tickets/') # json

    config.add_route('list_users',            'users/list') # html
    config.add_route('list_user_tasks',       'users/{id}/tasks/list') # html
    config.add_route('list_user_vacations',   'users/{id}/vacations/list') # html
    config.add_route('list_user_departments', 'users/{id}/departments/list') # html
    config.add_route('list_user_groups',      'users/{id}/groups/list') # html
    config.add_route('list_user_projects',    'users/{id}/projects/list') # html
    config.add_route('list_user_time_logs',   'users/{id}/time_logs/list') # html
    config.add_route('list_user_tickets',   'users/{id}/tickets/list') # html

    config.add_route('view_user_tasks',       'users/{id}/tasks/view') # html
    config.add_route('view_user_versions',    'users/{id}/versions/view')
    config.add_route('view_user_tickets',     'users/{id}/tickets/view')

    config.add_route('check_login_availability', 'check_availability/login/{login}')
    config.add_route('check_email_availability', 'check_availability/email/{email}')

    # *************************************************************************
    # FilenameTemplate
    config.add_route('dialog_create_filename_template', 'filename_templates/create/dialog')
    config.add_route('dialog_update_filename_template', 'filename_templates/{id}/update/dialog')

    config.add_route('create_filename_template', 'filename_templates/create')
    config.add_route('update_filename_template', 'filename_templates/{id}/update')

    config.add_route('get_filename_templates', 'filename_templates/') # json

    # ************************************************************************* 
    # StatusList
    config.add_route('dialog_create_status_list',     'status_lists/create/dialog')
    config.add_route('dialog_create_status_list_for', 'status_lists/{target_entity_type}/create/dialog')
    config.add_route('dialog_update_status_list',     'status_lists/{target_entity_type}/update/dialog')

    config.add_route('create_status_list', 'status_lists/create')
    config.add_route('update_status_list', 'status_lists/update')

    config.add_route('get_status_lists',     'status_lists/')
    config.add_route('get_status_lists_for', 'status_lists_for/{target_entity_type}/')

    # *************************************************************************
    # Status
    # TODO: separate dialog and action
    config.add_route('dialog_create_status', 'statuses/create/dialog')
    config.add_route('dialog_update_status', 'statuses/{id}/update/dialog')

    config.add_route('create_status', 'statuses/create')
    config.add_route('update_status', 'statuses/{id}/update')

    config.add_route('get_statuses',     'statuses/') # json
    config.add_route('get_statuses_for', 'statuses/{target_entity_type}/') # json
    config.add_route('get_statuses_of',  'status_lists/{id}/statuses/') # json

    # *************************************************************************
    # Assets

    config.add_route('dialog_update_asset', 'assets/{id}/update/dialog')

    config.add_route('create_asset',        'assets/create')
    config.add_route('update_asset',        'assets/{id}/update')

    config.add_route('view_asset',          'assets/{id}/view')
    config.add_route('summarize_asset',     'assets/{id}/summarize')
    config.add_route('get_asset_tickets',   'assets/{id}/tickets/')
    config.add_route('list_asset_tickets',  'assets/{id}/tickets/list')
    config.add_route('get_asset_types',     'assets/types/')

    # *************************************************************************
    # Shots
    config.add_route('dialog_create_shot', 'projects/{id}/shots/create/dialog')
    config.add_route('dialog_update_shot', 'shots/{id}/update/dialog')

    config.add_route('create_shot',        'shots/create')
    config.add_route('update_shot',        'shots/{id}/update')

    config.add_route('view_shot',          'shots/{id}/view')
    config.add_route('summarize_shot',     'shots/{id}/summarize')

    config.add_route('list_shot_tasks',    'shots/{id}/tasks/list') # html
    config.add_route('list_shot_tickets',  'shots/{id}/tickets/list') # html
    config.add_route('list_shot_versions', 'shots/{id}/versions/list') # html

    # *************************************************************************
    # Sequence
    config.add_route('dialog_create_sequence', 'projects/{id}/sequences/create/dialog')
    config.add_route('dialog_update_sequence', 'sequences/{id}/update/dialog')

    config.add_route('create_sequence', 'sequences/create')
    config.add_route('update_sequence', 'sequences/{id}/update')

    config.add_route('view_sequence',          'sequences/{id}/view')
    config.add_route('summarize_sequence',     'sequences/{id}/summarize')

    config.add_route('get_sequence_references', 'sequences/{id}/references/')  # json
    config.add_route('get_sequence_tickets',    'sequences/{id}/tickets/') # json
    config.add_route('get_sequence_tasks',      'sequences/{id}/tasks/') # json
    config.add_route('get_sequences',           'sequences/') # json

    config.add_route('list_sequence_tickets',   'sequences/{id}/tickets/list') # html
    config.add_route('list_sequence_tasks',     'sequences/{id}/tasks/list') # html
    config.add_route('list_sequence_versions',  'sequences/{id}/versions/list') # html

    # *************************************************************************
    # Task

    # Dialogs
    config.add_route('dialog_create_task_task',     'tasks/{id}/tasks/create/dialog')
    config.add_route('dialog_create_asset_task',    'assets/{id}/create/dialog')
    config.add_route('dialog_create_shot_task',     'shots/{id}/create/dialog')
    config.add_route('dialog_create_sequence_task', 'sequences/{id}/create/dialog')

    config.add_route('dialog_create_child_task',     'tasks/{id}/child_tasks/create/dialog')
    config.add_route('dialog_create_dependent_task', 'tasks/{id}/dependent_task/create/dialog')
    config.add_route('dialog_update_task',           'tasks/{id}/update/dialog')

    config.add_route('create_task',              'tasks/create')
    config.add_route('update_task',              'tasks/{id}/update')
    config.add_route('duplicate_task_hierarchy', 'tasks/{id}/duplicate')

    config.add_route('view_task',                'tasks/{id}/view')
    config.add_route('summarize_task',           'tasks/{id}/summarize')

    config.add_route('list_task_tasks',          'tasks/{id}/tasks/list') # html
    config.add_route('list_task_versions',       'tasks/{id}/versions/list') # html
    config.add_route('list_task_tickets',        'tasks/{id}/tickets/list') # html

    config.add_route('get_gantt_tasks',          'tasks/{id}/gantt')
    config.add_route('get_gantt_task_children',  'tasks/{id}/children/gantt')

    config.add_route('auto_schedule_tasks', 'auto_schedule_tasks')

    # RESTful test
    config.add_route('get_tasks',         'tasks/')
    config.add_route('get_task',          'tasks/{id}/')
    config.add_route('get_task_children', 'tasks/{id}/children/')

    # *************************************************************************
    # TimeLog
    config.add_route('dialog_create_time_log', 'tasks/{id}/time_logs/create/dialog')
    config.add_route('dialog_update_time_log', 'time_logs/{id}/update/dialog')

    config.add_route('create_time_log', 'time_logs/create')
    config.add_route('update_time_log', 'time_logs/{id}/update')

    config.add_route('get_task_time_logs',  'task/{id}/time_logs/') # json
    config.add_route('list_task_time_logs', 'task/{id}/time_logs/list') # html

    # *************************************************************************
    # Ticket
    config.add_route('dialog_create_ticket', 'projects/{id}/tickets/create/dialog')
    config.add_route('dialog_update_ticket', 'tickets/{id}/update/dialog')

    config.add_route('create_ticket', 'tickets/create')
    config.add_route('update_ticket', 'tickets/{id}/update')

    config.add_route('view_ticket',      'tickets/{id}/view')
    config.add_route('summarize_ticket', 'tickets/{id}/summarize')

    config.add_route('get_tickets',      'tickets/')

    config.add_route('get_task_tickets', 'tasks/{id}/tickets') # json

    config.add_route('request_task_review', 'tasks/{id}/request_review')

    # *************************************************************************
    # Vacation
    config.add_route('dialog_update_vacation', 'vacations/{id}/update/dialog')

    config.add_route('create_vacation', 'vacations/create')
    config.add_route('update_vacation', 'vacations/{id}/update')

    # *************************************************************************
    # Version
    config.add_route('dialog_create_task_version', 'tasks/{id}/versions/create/dialog')
    config.add_route('dialog_update_version',      'versions/{id}/update/dialog')

    config.add_route('create_version', 'versions/create')
    config.add_route('update_version', 'versions/{id}/update')

    config.add_route('assign_version', 'assign_version') # TODO: update this address

    config.add_route('view_version',          'versions/{id}/view')
    config.add_route('summarize_version',     'versions/{id}/summarize')
    config.add_route('list_version_outputs',  'versions/{id}/outputs/list') # html
    config.add_route('list_version_inputs',   'versions/{id}/inputs/list') # html
    config.add_route('list_version_children', 'versions/{id}/children/list') # html

    # *************************************************************************
    # Department

    config.add_route('dialog_create_department', 'departments/create/dialog')
    config.add_route('dialog_update_department', 'departments/{id}/update/dialog')

    config.add_route('create_department',     'departments/create')
    config.add_route('update_department',     'departments/update')
    config.add_route('summarize_department',  'departments/{id}/summarize')
    config.add_route('view_department',       'departments/{id}/view')
    config.add_route('get_departments',       'departments/')

    config.add_route('list_department_users', 'departments/{id}/users/list')
    config.add_route('list_department_tasks', 'departments/{id}/tasks/list')

    config.add_route('get_department_tasks',  'departments/{id}/tasks/')

    config.add_route('append_departments',   'departments/{id}/append') # TODO: this was not clear

    # *************************************************************************
    # Group

    config.add_route('dialog_create_group', 'groups/create/dialog')
    config.add_route('dialog_update_group', 'groups/{id}/update/dialog')

    config.add_route('create_group',        'groups/create')
    config.add_route('update_group',        'groups/{id}/update')
    config.add_route('view_group',          'groups/{id}/view')
    config.add_route('summarize_group',     'groups/{id}/summarize')

    config.add_route('get_groups',          'groups/')

    config.add_route('list_groups',         'groups/list')
    config.add_route('list_group_users',    'groups/{id}/users/list')
    config.add_route('list_permissions',    'groups/{id}/permissions/list') # html

    # *************************************************************************
    # Tag

    config.add_route('get_tags', 'tags/')

    config.scan(ignore='stalker.env')
    return config.make_wsgi_app()


# TODO: auto register creted_by and updated_by values by using SQLAlchemy
#       events 'before_update' and 'before_create'
