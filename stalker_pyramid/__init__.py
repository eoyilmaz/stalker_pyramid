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
"""
Stalker Pyramid is a Production Asset Management System (ProdAM) designed for
Animation and VFX Studios. See docs for more information.
"""
import pyramid_beaker

from zope.sqlalchemy import ZopeTransactionExtension

__version__ = '0.1.11'


# before anything about stalker create the defaults
from stalker.config import defaults

import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


stalker_server_external_url = None
stalker_server_internal_url = None


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    from pyramid.config import Configurator
    from pyramid.authentication import AuthTktAuthenticationPolicy
    from pyramid.authorization import ACLAuthorizationPolicy

    # setup the database to the given settings
    from stalker import db
    from stalker.db import DBSession

    from stalker_pyramid.views.auth import group_finder

    # use the ZopeTransactionExtension for session
    db.setup(settings)
    DBSession.remove()
    DBSession.configure(extension=ZopeTransactionExtension())

    # setup internal and external urls
    global stalker_server_external_url
    global stalker_server_internal_url
    stalker_server_external_url = settings.get('stalker.external_url')
    stalker_server_internal_url = settings.get('stalker.internal_url')

    # setup authorization and authentication
    authn_policy = AuthTktAuthenticationPolicy(
        'sosecret',
        hashalg='sha512',
        callback=group_finder
    )
    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(
        settings=settings,
        root_factory='stalker_pyramid.views.auth.RootFactory'
    )
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)

    # Configure Beaker sessions and caching
    session_factory = pyramid_beaker.session_factory_from_settings(settings)
    config.set_session_factory(session_factory)
    pyramid_beaker.set_cache_regions_from_settings(settings)

    config.include('pyramid_jinja2')
    config.include('pyramid_mailer')
    config.add_static_view('static', 'static', cache_max_age=3600)

    # *************************************************************************
    # Basics
    config.add_route('deform_test', '/deform_test')

    config.add_route('home', '/')
    config.add_route('me_menu', '/me_menu')
    config.add_route('signin', '/signin')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_route('flash_message', '/flash_message')

    # addresses like http:/localhost:6543/SPL/{some_path} will let SP to serve
    # those files
    # SPL   : Stalker Pyramid Local
    config.add_route(
        'serve_files',
        'SPL/{partial_file_path:[a-zA-Z0-9/\.]+}'
    )

    # addresses like http:/localhost:6543/FDSPL/{some_path} will serve the
    # files with their original filename in a forced download mode.
    # FDSPL : Forced Download Stalker Pyramid Local
    config.add_route(
        'forced_download_files',
        'FDSPL/{partial_file_path:[a-zA-Z0-9/\.]+}'
    )

    logger.debug(defaults.server_side_storage_path + '/{partial_file_path}')

    # *************************************************************************
    # DATA VIEWS
    # *************************************************************************

    # *************************************************************************
    # Entities

    config.add_route('get_search_result', '/search')  # json
    config.add_route('list_search_result', '/list/search_results')
    config.add_route('submit_search', '/submit_search')

    config.add_route('upload_entity_thumbnail_dialog', 'entities/{id}/thumbnail/upload/dialog')
    config.add_route('upload_entity_reference_dialog', 'entities/{id}/references/upload/dialog')
    config.add_route('upload_entity_output_dialog', 'entities/{id}/output/upload/dialog')

    config.add_route('create_entity_users_dialog',     'entities/{id}/users/create/dialog')

    config.add_route('append_users_to_entity_dialog',  'entities/{id}/users/append/dialog')
    config.add_route('append_users_to_entity',         'entities/{id}/users/append')
    config.add_route('remove_entity_from_entity_dialog','entities/{id}/{entity_id}/remove/dialog')
    config.add_route('remove_entity_from_entity',      'entities/{id}/{entity_id}/remove')

    config.add_route('delete_entity_dialog', 'entities/{id}/delete/dialog')
    config.add_route('delete_entity', 'entities/{id}/delete')

    # get routes returns json
    config.add_route('get_entity',                     'entities/{id}/')
    config.add_route('get_entity_users',               'entities/{id}/users/')
    config.add_route('get_entity_users_count',         'entities/{id}/users/count/')
    config.add_route('get_entity_users_not',           'entities/{id}/users/not')
    config.add_route('get_entity_references',          'entities/{id}/references/')
    config.add_route('get_entity_references_count',    'entities/{id}/references/count/')
    config.add_route('get_entity_departments',         'entities/{id}/departments/')
    config.add_route('get_entity_groups',              'entities/{id}/groups/')
    config.add_route('get_entity_tasks',               'entities/{id}/tasks/')
    config.add_route('get_entity_tasks_stats',         'entities/{id}/tasks_stats/')
    config.add_route('get_entity_tasks_by_filter',     'entities/{id}/tasks/filter/{f_id}/')

    config.add_route('get_entity_tickets',             'entities/{id}/tickets/')
    config.add_route('get_entity_tickets_count',       'entities/{id}/tickets/count/')
    config.add_route('get_entity_time_logs',           'entities/{id}/time_logs/')
    config.add_route('get_entity_projects',            'entities/{id}/projects/')
    config.add_route('get_entity_sequences',           'entities/{id}/sequences/')
    config.add_route('get_entity_sequences_count',     'entities/{id}/sequences/count/')
    config.add_route('get_entity_assets',              'entities/{id}/assets/')
    config.add_route('get_entity_assets_count',        'entities/{id}/assets/count/')
    config.add_route('get_entity_shots',               'entities/{id}/shots/')
    config.add_route('get_entity_shots_count',         'entities/{id}/shots/count/')
    config.add_route('get_entity_scenes',              'entities/{id}/scenes/')
    config.add_route('get_entity_scenes_count',        'entities/{id}/scenes/count/')
    config.add_route('get_entity_vacations',           'entities/{id}/vacations/')
    config.add_route('get_entity_vacations_count',     'entities/{id}/vacations/count/')
    config.add_route('get_entity_entities_out_stack',  'entities/{id}/{entities}/out_stack/' )
    config.add_route('get_entity_events',              'entities/{id}/events/')  #json
    config.add_route('get_entity_notes',               'entities/{id}/notes/') #json

    config.add_route('list_entity_users',              'entities/{id}/users/list')
    config.add_route('list_entity_departments',        'entities/{id}/departments/list')  # html
    config.add_route('list_entity_groups',             'entities/{id}/groups/list')  # html
    config.add_route('list_entity_scenes',             'entities/{id}/scenes/list')  # html
    config.add_route('list_entity_shots',              'entities/{id}/shots/list')  # html
    config.add_route('list_entity_tasks',              'entities/{id}/tasks/list')  # html
    config.add_route('list_entity_tasks_by_filter',    'entities/{id}/tasks/filter/{f_id}/list')  # html
    config.add_route('list_entity_tickets',            'entities/{id}/tickets/list')  # html
    config.add_route('list_entity_projects',           'entities/{id}/projects/list')
    config.add_route('list_entity_references',         'entities/{id}/references/list')  # html
    config.add_route('list_entity_vacations',          'entities/{id}/vacations/list')  # html
    config.add_route('list_entity_versions',           'entities/{id}/versions/list')  # html
    config.add_route('list_entity_resources',          'entities/{id}/resources/list')  # html
    config.add_route('list_entity_notes',              'entities/{id}/notes/list') #html


    config.add_route('append_entities_to_entity_dialog',  'entities/{id}/{entities}/append/dialog')
    config.add_route('append_entities_to_entity',         'entities/{id}/append')

    config.add_route('view_entity_nav_bar',            'entities/{id}/nav_bar')
    config.add_route('view_entity_tasks',              'entities/{id}/tasks/view')
    config.add_route('view_entity_group',              'entities/{eid}/groups/{id}/view')
    config.add_route('view_entity_department',         'entities/{eid}/departments/{id}/view')


    # *************************************************************************
    # Notes
    config.add_route('create_note', 'note/create')
    config.add_route('update_note', 'note/{id}/update')
    config.add_route('delete_note_dialog', 'notes/{id}/delete/dialog')
    config.add_route('delete_note', 'notes/{id}/delete')

    # *************************************************************************
    # Thumbnail  and Links

    config.add_route('upload_files',         'upload_files')
    config.add_route('assign_thumbnail',     'assign_thumbnail')

    # *************************************************************************
    # References

    config.add_route('get_task_references',        'tasks/{id}/references/')  # json
    config.add_route('get_task_references_count',  'tasks/{id}/references/count/')  # json
    config.add_route('get_asset_references',       'assets/id}/references/')  # json
    config.add_route('get_asset_references_count', 'assets/id}/references/count/')  # json

    config.add_route('get_shot_references',        'shots/{id}/references/')  # json
    config.add_route('get_shot_references_count',  'shots/{id}/references/count/')  # json

    config.add_route('get_references',       'references/')
    config.add_route('get_reference',        'references/{id}')

    config.add_route('assign_reference',     'assign_reference')
    config.add_route('delete_reference',     'references/{id}/delete')

    # *************************************************************************
    # Outputs

    config.add_route('list_task_outputs',           'tasks/{id}/outputs/list')  # html

    config.add_route('get_entity_outputs',          'entities/{id}/outputs/')
    config.add_route('get_entity_outputs_count',    'entities/{id}/outputs/count/')

    config.add_route('get_task_outputs',            'tasks/{id}/outputs/')
    config.add_route('get_task_outputs_count',      'tasks/{id}/outputs/count/')

    config.add_route('get_version_outputs',         'versions/{id}/outputs/')
    config.add_route('get_version_outputs_count',   'versions/{id}/outputs/count/')

    config.add_route('assign_output',               'assign_output')
    config.add_route('delete_output',               'outputs/{id}/delete')

    # *************************************************************************
    # Studio
    config.add_route('create_studio_dialog',  'studios/create/dialog')
    config.add_route('update_studio_dialog',  'studios/{id}/update/dialog')

    config.add_route('create_studio',         'studios/create')
    config.add_route('update_studio',         'studios/{id}/update')

    config.add_route('view_studio',           'studios/{id}/view')

    config.add_route('get_studio_tasks',      'studios/{id}/tasks/')
    config.add_route('get_studio_vacations',  'studios/{id}/vacations/')  # json
    config.add_route('get_studio_vacations_count',  'studios/{id}/vacations/count/')  # json

    config.add_route('list_studio_tasks',           'studios/{id}/tasks/list')
    config.add_route('list_studio_vacations',       'studios/{id}/vacations/list')  # html
    config.add_route('list_studio_users',           'studios/{id}/users/list')  # html
    config.add_route('list_studio_projects',        'studios/{id}/projects/list')  # html
    config.add_route('list_studio_departments',     'studios/{id}/departments/list')  # html
    config.add_route('list_studio_groups',          'groups/list')  # html

    config.add_route('schedule_info',               'schedule_info')  # json
    config.add_route('studio_scheduling_mode',      'studio_scheduling_mode')
    config.add_route('auto_schedule_tasks',         'auto_schedule_tasks')

    # *************************************************************************
    # Project
    config.add_route('project_dialog',             'projects/{id}/{mode}/dialog')

    config.add_route('get_project_tasks',          'projects/{id}/tasks/')  # json
    config.add_route('get_project_tasks_count',    'projects/{id}/tasks/count/')  # json
    config.add_route('get_project_lead',           'projects/{id}/lead/')  # json

    config.add_route('create_project',             'projects/create')
    config.add_route('update_project',             'projects/{id}/update')

    config.add_route('view_project',               'projects/{id}/view')
    config.add_route('view_project_reports',       'projects/{id}/view/reports')

    config.add_route('list_projects',              'projects/list')  # html
    config.add_route('list_project_users',         'projects/{id}/users/list')
    config.add_route('list_project_tasks',         'projects/{id}/tasks/list')  # html
    config.add_route('list_project_assets',        'projects/{id}/assets/list')
    config.add_route('list_project_shots',         'projects/{id}/shots/list')
    config.add_route('list_project_sequences',     'projects/{id}/sequences/list')
    config.add_route('list_project_tickets',       'projects/{id}/tickets/list')
    config.add_route('list_project_references',    'projects/{id}/references/list')
    config.add_route('list_project_reviews',       'projects/{id}/reviews/list')  # html
    config.add_route('list_project_dailies',       'projects/{id}/dailies/list')  # html
    # config.add_route('view_project_tasks_by_filter',    'projects/{id}/tasks/filter/{f_id}/list')  # html

    config.add_route('get_projects',               'projects/')
    config.add_route('get_project_users',          'projects/{id}/users/')
    config.add_route('get_project_users_count',    'projects/{id}/users/count/')
    config.add_route('get_project_assets',         'projects/{id}/assets/')
    config.add_route('get_project_assets_count',   'projects/{id}/assets/count/')
    config.add_route('get_project_shots',          'projects/{id}/shots/')
    config.add_route('get_project_shots_count',    'projects/{id}/shots/count/')
    config.add_route('get_project_sequences',      'projects/{id}/sequences/')
    config.add_route('get_project_sequences_count', 'projects/{id}/sequences/count/')
    config.add_route('get_project_scenes',          'projects/{id}/scenes/')
    config.add_route('get_project_scenes_count',    'projects/{id}/scenes/count/')
    config.add_route('get_project_references',     'projects/{id}/references/')  # json
    config.add_route('get_project_references_count', 'projects/{id}/references/count/')  # json
    config.add_route('get_project_tickets',         'projects/{id}/tickets/')  # json
    config.add_route('get_project_tickets_count',   'projects/{id}/tickets/count/')  # json
    config.add_route('get_project_reviews',         'projects/{id}/reviews/') #json
    config.add_route('get_project_reviews_count',      'projects/{id}/reviews/count/') #json
    config.add_route('get_project_dailies',         'projects/{id}/dailies/') #json
    config.add_route('get_project_dailies_count',   'projects/{id}/dailies/count/') #json

    config.add_route('get_project_tasks_today',    'projects/{id}/tasks/{action}/today/')  # json
    config.add_route('get_project_tasks_in_date',  'projects/{id}/tasks/{action}/{date}/')  # json

    # *************************************************************************
    # Dailies
    config.add_route('create_daily_dialog', 'dailies/create/dialog')
    config.add_route('update_daily_dialog', 'dailies/{id}/update/dialog')

    config.add_route('create_daily',        'dailies/create')
    config.add_route('update_daily',        'dailies/{id}/update')
    config.add_route('inline_update_daily', 'dailies/{id}/update/inline')
    config.add_route('inline_update_daily_dialog', 'dailies/{id}/update/inline/dialog')

    config.add_route('view_daily',          'dailies/{id}/view')
    config.add_route('get_daily_outputs',          'dailies/{id}/outputs/') # json

    config.add_route('append_link_to_daily_dialog', 'links/{id}/dailies/append/dialog')
    config.add_route('append_link_to_daily', 'links/{id}/dailies/{did}/append')
    config.add_route('remove_link_to_daily_dialog', 'links/{id}/dailies/{did}/remove/dialog')
    config.add_route('remove_link_to_daily', 'links/{id}/dailies/{did}/remove')


    # *************************************************************************
    # ImageFormat
    config.add_route('dialog_create_image_format', 'image_formats/create/dialog')
    config.add_route('dialog_update_image_format', 'image_formats/{id}/update/dialog')

    config.add_route('create_image_format', 'image_formats/create')
    config.add_route('update_image_format', 'image_formats/{id}/update')

    config.add_route('list_image_formats', 'image_formats/list')  # html
    config.add_route('get_image_formats', 'image_formats/')  # json

    # *************************************************************************
    # Repository
    config.add_route('dialog_create_repository', 'repositories/create/dialog')
    config.add_route('dialog_update_repository', 'repositories/{id}/update/dialog')

    config.add_route('create_repository', 'repositories/create')
    config.add_route('update_repository', 'repositories/{id}/update')

    config.add_route('list_repositories', 'repositories/list')  # html
    config.add_route('get_repositories', 'repositories/')  # json

    # serve files in repository
    config.add_route('serve_repository_files',
                     'repositories/{id}/{partial_file_path:[a-zA-Z0-9/\._\-\+\(\)]*}')

    config.add_route(
        'forced_download_repository_files',
        'FDrepositories/{id}/{partial_file_path:[a-zA-Z0-9/\._\-\+\(\)]*}'
    )


    config.add_route('video_player', 'video_player')  #html

    # *************************************************************************
    # Structure
    config.add_route('dialog_create_structure', 'structures/create/dialog')
    config.add_route('dialog_update_structure', 'structures/{id}/update/dialog')

    config.add_route('create_structure', 'structures/create')
    config.add_route('update_structure', 'structures/{id}/update')
    config.add_route('get_structures',   'structures/')  # json

    # *************************************************************************
    # User

    # dialogs
    config.add_route('create_user_dialog',      'users/create/dialog')
    config.add_route('update_user_dialog',      'users/{id}/update/dialog')

    config.add_route('dialog_create_department_user', 'departments/{id}/users/create/dialog')
    config.add_route('dialog_create_group_user',      'groups/{id}/users/create/dialog')

    config.add_route('append_user_to_departments_dialog', 'users/{id}/departments/append/dialog')
    config.add_route('append_user_to_departments', 'users/{id}/departments/append')
    config.add_route('append_user_to_department',  'users/{uid}/department/{did}/append')  # unused

    config.add_route('append_user_to_groups_dialog', 'users/{id}/groups/append/dialog')
    config.add_route('append_user_to_groups', 'users/{id}/groups/append')
    config.add_route('append_user_to_group',  'users/{uid}/groups/{gid}/append')  # unused

    config.add_route('create_user',           'users/create')
    config.add_route('update_user',           'users/{id}/update')
    config.add_route('view_user',             'users/{id}/view')
    config.add_route('view_user_settings',    'users/{id}/view_settings')

    config.add_route('get_user',              'users/{id}/')  # json
    config.add_route('get_users',             'users/')  # json
    config.add_route('get_users_count',       'users/count/')  # json
    config.add_route('get_user_departments',  'users/{id}/departments/')  # json
    config.add_route('get_user_groups',       'users/{id}/groups/')  # json
    config.add_route('get_user_tasks',        'users/{id}/tasks/')  # json
    config.add_route('get_user_tasks_count',  'users/{id}/tasks/count/')  # json
    config.add_route('get_user_tasks_responsible_of_count', 'users/{id}/tasks/responsible_of/count') # html
    config.add_route('get_user_vacations',    'users/{id}/vacations/')  # json
    config.add_route('get_user_vacations_count', 'users/{id}/vacations/count/')  # json
    config.add_route('get_user_tickets',      'users/{id}/tickets/')  # json
    config.add_route('get_user_open_tickets', 'users/{id}/open_tickets/')  # json
    config.add_route('get_user_reviews',      'users/{id}/reviews/') #json
    config.add_route('get_user_reviews_count',      'users/{id}/reviews/count/') #json
    config.add_route('get_user_events',       'users/{id}/events/')  # json
    # config.add_route('get_user_worked_hours', 'users/{id}/{frequency}/worked_hours/')  # json
    config.add_route('get_resources',         'resources/')
    config.add_route('get_entity_resources',  'entities/{id}/resources/')
    config.add_route('get_resource',          'resources/{id}/')

    config.add_route('list_users',            'users/list')  # html
    config.add_route('list_user_tasks',       'users/{id}/tasks/list')  # html
    config.add_route('list_user_vacations',   'users/{id}/vacations/list')  # html
    config.add_route('list_user_departments', 'users/{id}/departments/list')  # html
    config.add_route('list_user_groups',      'users/{id}/groups/list')  # html
    config.add_route('list_user_projects',    'users/{id}/projects/list')  # html
    config.add_route('list_user_time_logs',   'users/{id}/time_logs/list')  # html
    config.add_route('list_user_tickets',     'users/{id}/tickets/list')  # html
    config.add_route('list_user_tasks_responsible_of',       'users/{id}/tasks/list/responsible_of') # html
    config.add_route('list_user_tasks_watching',       'users/{id}/tasks/list/watching') # html
    config.add_route('list_user_reviews',              'users/{id}/reviews/list')  # html

    config.add_route('view_user_tasks',       'users/{id}/tasks/view')  # html
    config.add_route('view_user_versions',    'users/{id}/versions/view')
    config.add_route('view_user_tickets',     'users/{id}/tickets/view')

    config.add_route('delete_user', 'users/{id}/delete')
    config.add_route('delete_user_dialog', 'users/{id}/delete/dialog')

    config.add_route('check_login_availability', 'check_availability/login/{login}')
    config.add_route('check_email_availability', 'check_availability/email/{email}')

    # *************************************************************************
    # FilenameTemplate
    config.add_route('dialog_create_filename_template', 'filename_templates/create/dialog')
    config.add_route('dialog_update_filename_template', 'filename_templates/{id}/update/dialog')

    config.add_route('create_filename_template', 'filename_templates/create')
    config.add_route('update_filename_template', 'filename_templates/{id}/update')

    config.add_route('get_filename_templates', 'filename_templates/')  # json

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

    config.add_route('get_statuses',     'statuses/')  # json
    config.add_route('get_statuses_for', 'statuses/{target_entity_type}/')  # json
    config.add_route('get_statuses_of',  'status_lists/{id}/statuses/')  # json

    # *************************************************************************
    # Assets
    config.add_route('create_asset_dialog', 'assets/{id}/create/dialog')
    config.add_route('update_asset_dialog', 'assets/{id}/update/dialog')
    config.add_route('review_asset_dialog', 'assets/{id}/review/dialog')

    config.add_route('create_asset',        'assets/create')
    config.add_route('update_asset',        'assets/{id}/update')

    config.add_route('view_asset',          'assets/{id}/view')
    config.add_route('get_asset_tickets',   'assets/{id}/tickets/')
    config.add_route('list_asset_tickets',  'assets/{id}/tickets/list')


    config.add_route('get_assets_types', 'assets/types/')  # json
    config.add_route('get_assets_type_task_types', 'assets/types/{t_id}/task_types/')  # json
    config.add_route('get_assets_children_task_type',  'assets/children/task_type/')  # json


    # *************************************************************************
    # Shots
    config.add_route('create_shot_dialog', 'shots/{id}/create/dialog')
    config.add_route('update_shot_dialog', 'shots/{id}/update/dialog')
    config.add_route('review_shot_dialog', 'shots/{id}/review/dialog')

    config.add_route('create_shot',        'shots/create')
    config.add_route('update_shot',        'shots/{id}/update')

    config.add_route('view_shot',          'shots/{id}/view')

    config.add_route('list_shot_tasks',    'shots/{id}/tasks/list')  # html
    config.add_route('list_shot_tickets',  'shots/{id}/tickets/list')  # html
    config.add_route('list_shot_versions', 'shots/{id}/versions/list')  # html

    config.add_route('get_shots_children_task_type',  'shots/children/task_type/')  # json

    # *************************************************************************
    # Scene
    config.add_route('get_scenes_children_task_type',  'scenes/children/task_type/')  # json

    # *************************************************************************
    # Sequence
    config.add_route('create_sequence_dialog', 'sequences/{id}/create/dialog')
    config.add_route('update_sequence_dialog', 'sequences/{id}/update/dialog')
    config.add_route('review_sequence_dialog', 'sequences/{id}/review/dialog')

    config.add_route('create_sequence',        'sequences/create')
    config.add_route('update_sequence',        'sequences/{id}/update')

    config.add_route('view_sequence',          'sequences/{id}/view')

    config.add_route('get_sequence_references', 'sequences/{id}/references/')  # json
    config.add_route('get_sequence_references_count', 'sequences/{id}/references/count/')  # json
    config.add_route('get_sequence_tickets',    'sequences/{id}/tickets/')  # json
    config.add_route('get_sequence_tasks',      'sequences/{id}/tasks/')  # json
    config.add_route('get_sequences',           'sequences/')  # json

    config.add_route('list_sequence_tickets',   'sequences/{id}/tickets/list')  # html
    config.add_route('list_sequence_tasks',     'sequences/{id}/tasks/list')  # html
    config.add_route('list_sequence_shots',     'sequences/{id}/shots/list')  # html


    config.add_route('list_sequence_versions',  'sequences/{id}/versions/list')  # html

    # *************************************************************************
    # Task
    config.add_route('get_task_external_link',              'tasks/{id}/external_link')
    config.add_route('get_task_internal_link',              'tasks/{id}/internal_link')

    # Dialogs
    config.add_route('create_task_dialog',                  'tasks/{id}/create/dialog')
    config.add_route('update_task_dialog',                  'tasks/{id}/update/dialog')
    config.add_route('review_task_dialog',                  'tasks/{id}/review/dialog')
    config.add_route('cleanup_task_new_reviews_dialog',     'tasks/{id}/cleanup_new_reviews/dialog')

    # Actions
    config.add_route('create_task',                         'tasks/create')
    config.add_route('update_task',                         'tasks/{id}/update')
    config.add_route('inline_update_task',                  'tasks/{id}/update/inline')
    config.add_route('update_task_schedule_timing',         'tasks/{id}/update/schedule_timing')
    config.add_route('update_task_schedule_timing_dialog',  'tasks/{id}/update/schedule_timing/dialog')
    config.add_route('update_task_dependencies',            'tasks/{id}/update/dependencies')
    config.add_route('update_task_dependencies_dialog',     'tasks/{id}/update/dependencies/dialog')
    config.add_route('force_task_status_dialog',            'tasks/{id}/force_status/{status_code}/dialog')
    config.add_route('force_task_status',                   'tasks/{id}/force_status/{status_code}')
    config.add_route('resume_task_dialog',                  'tasks/{id}/resume/dialog')
    config.add_route('resume_task',                  'tasks/{id}/resume')
    config.add_route('review_task',                         'tasks/{id}/review')
    config.add_route('cleanup_task_new_reviews',            'tasks/{id}/cleanup_new_reviews')

    config.add_route('duplicate_task_hierarchy',            'tasks/{id}/duplicate')
    config.add_route('duplicate_task_hierarchy_dialog',     'tasks/{id}/duplicate/dialog')

    config.add_route('view_task',                'tasks/{id}/view')

    config.add_route('list_task_tasks',          'tasks/{id}/tasks/list')  # html
    config.add_route('list_task_versions',       'tasks/{id}/versions/list')  # html
    config.add_route('list_task_tickets',        'tasks/{id}/tickets/list')  # html
    config.add_route('list_task_references',     'tasks/{id}/references/list')  # html
    config.add_route('list_task_reviews',        'tasks/{id}/reviews/list')  # html

    config.add_route('get_gantt_tasks',          'tasks/{id}/gantt')
    config.add_route('get_gantt_task_children',  'tasks/{id}/children/gantt')

    config.add_route('get_tasks',         'tasks/')
    config.add_route('get_tasks_count',         'tasks/count/')

    config.add_route('get_task',          'tasks/{id}/')
    config.add_route('get_task_events',   'tasks/{id}/events/')  #json
    config.add_route('get_task_children_task_type',  'tasks/{type}/children/task_type/')  # json


    config.add_route('get_task_related_entities',  'tasks/{id}/related/{e_type}/') # json
    config.add_route('get_task_dependency',  'tasks/{id}/dependency/{type}/') # json
    config.add_route('get_task_tickets',  'tasks/{id}/tickets')  # json

    config.add_route('get_task_reviews',  'tasks/{id}/reviews/')  # json
    config.add_route('get_task_reviews_count',  'tasks/{id}/reviews/count/')  # json
    config.add_route('get_task_reviewers',  'tasks/{id}/reviewers/')  # json
    config.add_route('get_task_last_reviews',  'tasks/{id}/last_reviews/') #json

    config.add_route('request_review',     'tasks/{id}/request_review')
    config.add_route('request_review_task_dialog',     'tasks/{id}/request_review/dialog')

    config.add_route('approve_task',   'tasks/{id}/approve')
    config.add_route('request_revision',   'tasks/{id}/request_revision')
    config.add_route('request_extra_time', 'tasks/{id}/request_extra_time')
    config.add_route('request_extra_time_dialog', 'tasks/{id}/request_extra_time/dialog')

    config.add_route('get_task_resources',        'tasks/{id}/resources/') #json
    config.add_route('remove_task_user_dialog',   'tasks/{id}/remove/{user_type}/{user_id}/dialog')
    config.add_route('remove_task_user',          'tasks/{id}/remove/{user_type}/{user_id}')
    config.add_route('change_tasks_users_dialog', 'tasks/change/{user_type}/dialog')
    config.add_route('change_tasks_users',        'tasks/change/{user_type}')
    config.add_route('change_task_users_dialog',  'tasks/{id}/change/{user_type}/dialog')
    config.add_route('change_task_users',         'tasks/{id}/change/{user_type}')

    config.add_route('add_tasks_dependencies_dialog', 'tasks/add/dependencies/dialog')
    config.add_route('add_tasks_dependencies',        'tasks/add/dependencies')

    config.add_route('delete_task',        'tasks/{id}/delete')
    config.add_route('delete_task_dialog', 'tasks/{id}/delete/dialog')

    config.add_route('fix_task_statuses',      'tasks/{id}/fix/statuses/')
    config.add_route('fix_task_schedule_info', 'tasks/{id}/fix/schedule_info/')

    config.add_route('watch_task',   'tasks/{id}/watch')
    config.add_route('unwatch_task', 'tasks/{id}/unwatch')

    # *************************************************************************
    # TimeLog

    config.add_route('entity_time_log_dialog',   'entities/{id}/timelogs/create/dialog')
    config.add_route('task_time_log_dialog',     'tasks/{id}/timelogs/create/dialog')
    config.add_route('user_time_log_dialog',     'users/{id}/timelogs/create/dialog')
    config.add_route('asset_time_log_dialog',    'assets/{id}/timelogs/create/dialog')
    config.add_route('sequence_time_log_dialog', 'sequences/{id}/timelogs/create/dialog')
    config.add_route('shot_time_log_dialog', 'shots/{id}/timelogs/create/dialog')
    # TODO: Change the TimeLog Entity plural name so we can use 'time_logs' string here.
    config.add_route('time_log_update_dialog', 'timelogs/{id}/update/dialog')

    config.add_route('create_time_log', 'time_logs/create')
    config.add_route('update_time_log', 'time_logs/{id}/update')

    config.add_route('delete_time_log',  'time_logs/{id}/delete')

    config.add_route('get_task_time_logs',  'task/{id}/time_logs/')  # json
    config.add_route('list_task_time_logs', 'task/{id}/time_logs/list')  # html

    # *************************************************************************
    # Ticket
    config.add_route('create_ticket_dialog',   'tickets/{id}/create/dialog')

    config.add_route('create_ticket',          'tickets/create')
    config.add_route('update_ticket',          'tickets/{id}/update')

    config.add_route('list_ticket_tickets',    'tickets/{id}/tickets/')  # html

    config.add_route('view_ticket',            'tickets/{id}/view')

    config.add_route('get_tickets',            'tickets/')
    config.add_route('get_ticket_resolutions', 'tickets/resolutions/')
    config.add_route('get_ticket_workflow',    'tickets/workflow/')

    # *************************************************************************
    # Vacation
    config.add_route('entity_vacation_dialog', 'entities/{id}/vacations/create/dialog')
    config.add_route('studio_vacation_dialog', 'studios/{id}/vacations/create/dialog')
    config.add_route('user_vacation_dialog', 'users/{id}/vacations/create/dialog')
    config.add_route('vacation_update_dialog', 'vacations/{id}/update/dialog')

    config.add_route('create_vacation', 'vacations/create')
    config.add_route('update_vacation', 'vacations/{id}/update')
    config.add_route('delete_vacation',  'vacations/{id}/delete')

    # *************************************************************************
    # Version
    config.add_route('create_version_dialog',          'tasks/{tid}/versions/create/dialog')
    config.add_route('update_version_dialog',          'versions/{id}/update/dialog')

    config.add_route('create_version',                      'versions/create')

    config.add_route('view_version',                        'versions/{id}/view')
    config.add_route('list_version_outputs',                'versions/{id}/outputs/list')  # html
    config.add_route('list_version_inputs',                 'versions/{id}/inputs/list')  # html
    config.add_route('list_version_children',               'versions/{id}/children/list')  # html

    config.add_route('get_task_versions',                   'tasks/{id}/versions/')  # jsons
    config.add_route('get_entity_versions',                 'entities/{id}/versions/')  # json
    config.add_route('get_entity_versions_used_by_tasks',   'entities/{id}/version/used_by/tasks/') # json

    config.add_route('pack_version', 'versions/{id}/pack')  # json

    # *************************************************************************
    # Department

    # config.add_route('department_dialog',             'departments/{id}/{mode}/dialog')

    config.add_route('create_department_dialog', 'departments/create/dialog')
    config.add_route('update_department_dialog', 'departments/{id}/update/dialog')

    config.add_route('create_department',     'departments/create')
    config.add_route('update_department',     'departments/{id}/update')
    config.add_route('view_department',       'departments/{id}/view')
    config.add_route('get_departments',       'departments/')
    config.add_route('get_department',       'departments/{id}/')

    config.add_route('list_department_users', 'departments/{id}/users/list')
    config.add_route('list_department_tasks', 'departments/{id}/tasks/list')

    config.add_route('delete_department', 'departments/{id}/delete')
    config.add_route('delete_department_dialog', 'departments/{id}/delete/dialog')

    config.add_route('get_department_tasks',  'departments/{id}/tasks/')

    config.add_route('append_departments',   'departments/{id}/append')  # TODO: this was not clear

    # *************************************************************************
    # Group

    # config.add_route('group_dialog',             'groups/{id}/{mode}/dialog')

    config.add_route('create_group_dialog',      'groups/create/dialog')
    config.add_route('update_group_dialog',      'groups/{id}/update/dialog')

    config.add_route('create_group',        'groups/create')
    config.add_route('update_group',        'groups/{id}/update')
    config.add_route('view_group',          'groups/{id}/view')

    config.add_route('get_group',           'groups/{id}/')  # json
    config.add_route('get_groups',          'groups/')

    config.add_route('list_groups',         'groups/list')
    config.add_route('list_group_users',    'groups/{id}/users/list')
    config.add_route('list_group_permissions',    'groups/{id}/permissions/list')  # html

    config.add_route('delete_group_dialog', 'groups/{id}/delete/dialog')
    config.add_route('delete_group', 'groups/{id}/delete')

    config.add_route('get_group_permissions',    'groups/{id}/permissions/')  # html

    # *************************************************************************
    # Tag

    config.add_route('get_tags', 'tags/')

    # *************************************************************************
    # Type
    config.add_route('get_types', 'types/')

    config.scan(ignore='stalker.env')
    return config.make_wsgi_app()


# TODO: auto register created_by and updated_by values by using SQLAlchemy
#       events 'before_update' and 'before_create'
