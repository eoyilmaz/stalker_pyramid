# -*- coding: utf-8 -*-

import logging
import pytz
import datetime

from pyramid.httpexceptions import HTTPServerError, HTTPOk
from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import Project, StatusList, Status, Sequence, Entity, Studio
import stalker_pyramid

from stalker_pyramid.views import get_logged_in_user, milliseconds_since_epoch, \
    PermissionChecker

from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='create_sequence'
)
def create_sequence(request):
    """runs when adding a new sequence
    """
    logged_in_user = get_logged_in_user(request)

    name = request.params.get('name')
    code = request.params.get('code')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    project_id = request.params.get('project_id')
    project = Project.query.filter_by(id=project_id).first()

    logger.debug('project_id   : %s' % project_id)

    if name and code and status and project:
        # get descriptions
        description = request.params.get('description')

        # get the status_list
        status_list = StatusList.query.filter_by(
            target_entity_type='Sequence'
        ).first()

        # there should be a status_list
        # TODO: you should think about how much possible this is
        if status_list is None:
            return HTTPServerError(detail='No StatusList found')

        new_sequence = Sequence(
            name=name,
            code=code,
            description=description,
            status_list=status_list,
            status=status,
            created_by=logged_in_user,
            project=project
        )

        DBSession.add(new_sequence)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('code      : %s' % code)
        logger.debug('status    : %s' % status)
        logger.debug('project   : %s' % project)
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='update_sequence'
)
def update_sequence(request):
    """runs when adding a new sequence
    """
    logged_in_user = get_logged_in_user(request)

    sequence_id = request.params.get('sequence_id')
    sequence = Sequence.query.filter_by(id=sequence_id).first()

    name = request.params.get('name')
    code = request.params.get('code')

    status_id = request.params.get('status_id')
    status = Status.query.filter_by(id=status_id).first()

    if sequence and code and name and status:
        # get descriptions
        description = request.params.get('description')

        #update the sequence
        sequence.name = name
        sequence.code = code
        sequence.description = description
        sequence.status = status
        sequence.updated_by = logged_in_user
        date_updated = datetime.datetime.now(pytz.utc)
        sequence.date_updated = date_updated
        DBSession.add(sequence)

    else:
        logger.debug('there are missing parameters')
        logger.debug('name      : %s' % name)
        logger.debug('status    : %s' % status)
        HTTPServerError()

    return HTTPOk()


@view_config(
    route_name='get_sequences',
    renderer='json'
)
def get_sequences(request):
    """returns all sequences as a json data
    """
    return [
        {
            'id': sequence.id,
            'name': sequence.name,
            'status': sequence.status.name,
            'status_color': sequence.status.html_class,
            'user_id': sequence.created_by.id,
            'user_name': sequence.created_by.name,
            'thumbnail_full_path': sequence.thumbnail.full_path
            if sequence.thumbnail else None
        }
        for sequence in Sequence.query.all()
    ]


@view_config(
    route_name='get_project_sequences_count',
    renderer='json'
)
@view_config(
    route_name='get_entity_sequences_count',
    renderer='json'
)
def get_project_sequences_count(request):
    """returns the count of sequences in a project
    """
    project_id = request.matchdict.get('id', -1)

    sql_query = """select
        count(1)
    from "Sequences"
        join "Tasks" on "Sequences".id = "Tasks".id
    where "Tasks".project_id = %s""" % project_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='get_project_sequences',
    renderer='json'
)
@view_config(
    route_name='get_entity_sequences',
    renderer='json'
)
def get_project_sequences(request):
    """returns the related sequences of the given project as a json data
    """
    # TODO: use pure SQL query
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    return [
        {
            'thumbnail_full_path': sequence.thumbnail.full_path if sequence.thumbnail else None,
            'code': sequence.code,
            'id': sequence.id,
            'name': sequence.name,
            'status': sequence.status.name,
            'status_code': sequence.status.code.lower(),
            'status_color': sequence.status.html_class if sequence.status.html_class else 'grey',
            'created_by_id': sequence.created_by.id if sequence.created_by else None,
            'created_by_name': sequence.created_by.name if sequence.created_by else None,
            'description': sequence.description,
            'date_created': milliseconds_since_epoch(sequence.date_created),
            'percent_complete': sequence.percent_complete
        }
        for sequence in entity.sequences
    ]


@view_config(
    route_name='list_sequence_tasks',
    renderer='templates/task/list/list_sequence_tasks.jinja2'
)
def list_sequence_tasks(request):
    """called when reviewing tasks
    """
    logger.debug('list_sequence_tasks starts******************')
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    entity_id = request.matchdict.get('id')
    if not entity_id:
        entity = studio
    else:
        entity = Entity.query.filter_by(id=entity_id).first()

    task_type = request.params.get('task_type', None)

    logger.debug('task_type %s', task_type)

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
        'came_from': came_from,
        'task_type':task_type
    }
