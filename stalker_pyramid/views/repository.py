# -*- coding: utf-8 -*-

import logging
import pytz
import datetime
from pyramid.httpexceptions import HTTPOk
from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import Repository

from stalker_pyramid.views import PermissionChecker, get_logged_in_user

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.WARNING)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='dialog_create_repository',
    renderer='templates/repository/dialog_create_repository.jinja2',
)
def dialog_create_repository(request):
    """fills the create repository dialog
    """
    # nothing is needed
    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='dialog_update_repository',
    renderer='templates/repository/dialog_create_repository.jinja2'
)
def dialog_update_repository(request):
    """fills the update repository dialog
    """
    repo_id = request.matchdict.get('id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()

    return {
        'mode': 'UPDATE',
        'repo': repo,
        'has_permission': PermissionChecker(request)
    }


@view_config(
    route_name='create_repository'
)
def create_repository(request):
    """creates a new repository
    """
    logged_in_user = get_logged_in_user(request)

    # get params
    name = request.params.get('name')
    windows_path = request.params.get('windows_path')
    linux_path = request.params.get('linux_path')
    osx_path = request.params.get('osx_path')

    if name and windows_path and linux_path and osx_path:
        # create a new Repository and save it to the database
        new_repository = Repository(
            name=name,
            windows_path=windows_path,
            linux_path=linux_path,
            osx_path=osx_path,
            created_by=logged_in_user
        )
        DBSession.add(new_repository)

    return HTTPOk()


@view_config(
    route_name='update_repository'
)
def update_repository(request):
    """updates a repository
    """
    logged_in_user = get_logged_in_user(request)

    repo_id = request.params.get('repo_id')
    repo = Repository.query.filter_by(id=repo_id).first()

    name = request.params.get('name')
    windows_path = request.params.get('windows_path')
    linux_path = request.params.get('linux_path')
    osx_path = request.params.get('osx_path')

    if repo and name and windows_path and linux_path and osx_path:
        repo.name = name
        repo.windows_path = windows_path
        repo.linux_path = linux_path
        repo.osx_path = osx_path
        repo.updated_by = logged_in_user
        utc_now = datetime.datetime.now(pytz.utc)
        repo.date_updated = utc_now

        DBSession.add(repo)

    return HTTPOk()


@view_config(
    route_name='get_repositories',
    renderer='json'
)
def get_repositories(request):
    """returns all the repositories in the database
    """
    return [
        {
            'id': repo.id,
            'code': repo.code,
            'name': repo.name,
            'linux_path': repo.linux_path,
            'osx_path': repo.osx_path,
            'windows_path': repo.windows_path
        }
        for repo in Repository.query.all()
    ]
