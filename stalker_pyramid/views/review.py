# -*- coding: utf-8 -*-
import logging

import transaction
from pyramid.response import Response
from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import (User, Task, Project)

from stalker_pyramid.views import get_logged_in_user
from stalker_pyramid.views.task import generate_recursive_task_query

from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='get_task_reviewers',
    renderer='json'
)
def get_task_reviewers(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_task_reviewers is running')

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    sql_query = """
        select
            "Reviewers".name as reviewers_name,
            "Reviewers".id as reviewers_id

        from "Reviews"
            join "Tasks" as "Review_Tasks" on "Review_Tasks".id = "Reviews".task_id
            join "SimpleEntities" as "Reviewers" on "Reviewers".id = "Reviews".reviewer_id

        %(where_conditions)s

        group by "Reviewers".id, "Reviewers".name
    """

    where_conditions = """where "Review_Tasks".id = %(task_id)s""" % {
        'task_id': task.id
    }

    logger.debug('where_conditions %s ' % where_conditions)

    sql_query = sql_query % {'where_conditions': where_conditions}

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'reviewer_name': r[0],
            'reviewer_id': r[1]
        }
        for r in result.fetchall()
    ]

    return return_data


@view_config(
    route_name='get_task_reviews',
    renderer='json'
)
def get_task_reviews(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_task_reviews is running')

    task_id = request.matchdict.get('id', -1)
    # task = Task.query.filter(Task.id == task_id).first()

    # if not task:
    #     transaction.abort()
    #     return Response('There is no task with id: %s' % task_id, 500)

    where_conditions = """where "Review_Tasks".id = %(task_id)s""" % {
        'task_id': task_id
    }

    return get_reviews(request, where_conditions)


@view_config(
    route_name='get_task_reviews_count',
    renderer='json'
)
def get_task_reviews_count(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_task_reviews_count is running')

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    where_conditions = """where "Review_Tasks".id = %(task_id)s
    and "Reviews_Statuses".code ='NEW' """ % {'task_id': task_id}

    reviews = get_reviews(request, where_conditions)

    return len(reviews)


@view_config(
    route_name='get_task_last_reviews',
    renderer='json'
)
def get_task_last_reviews(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_task_last_reviews is running')

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.id == task_id).first()

    if not task:
        transaction.abort()
        return Response('There is no task with id: %s' % task_id, 500)

    where_condition1 = """where "Review_Tasks".id = %(task_id)s""" % {
        'task_id': task_id
    }

    logger.debug("task.status.code : %s" % task.status.code)
    if task.status.code == 'PREV':
        where_condition2 = """ and "Review_Tasks".review_number +1 = "Reviews".review_number"""
        where_conditions = '%s %s' % (where_condition1, where_condition2)
        reviews = get_reviews(request, where_conditions)
    else:
        # where_condition2 =""" and "Review_Tasks".review_number = "Reviews".review_number"""

        reviews = [
            {
                'review_number': task.review_number,
                'review_id': 0,
                'review_status_code': 'WTNG',
                'review_status_name': 'Waiting',
                'review_status_color': 'wip',
                'task_id': task.id,
                'task_review_number': task.review_number,
                'reviewer_id': responsible.id,
                'reviewer_name': responsible.name,
                'reviewer_thumbnail_full_path':
                responsible.thumbnail.full_path
                    if responsible.thumbnail else None,
                'reviewer_department': responsible.departments[0].name
                    if responsible.departments else '--No Department--'
            }
            for responsible in task.responsible
        ]

    return reviews


@view_config(
    route_name='get_user_reviews',
    renderer='json'
)
def get_user_reviews(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_user_reviews is running')

    reviewer_id = request.matchdict.get('id', -1)

    # also try to get reviews with specified status
    review_status = request.params.get('status', None)

    if review_status:
        where_conditions = \
            """where "Reviews".reviewer_id = %(reviewer_id)s and 
            "Reviews_Statuses".code = '%(status)s' """ % {
                'reviewer_id': reviewer_id,
                'status': review_status
            }
    else:
        where_conditions = """where "Reviews".reviewer_id = %(reviewer_id)s""" % {
            'reviewer_id': reviewer_id
        }

    return get_reviews(request, where_conditions)


@view_config(
    route_name='get_user_reviews_count',
    renderer='json'
)
def get_user_reviews_count(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_user_reviews_count is running')

    reviewer_id = request.matchdict.get('id', -1)

    # TODO: This can be done faster, check if there is an id with that value
    reviewer = User.query.filter(User.id == reviewer_id).first()
    if not reviewer:
        transaction.abort()
        return Response('There is no user with id: %s' % reviewer_id, 500)

    where_conditions = """where "Reviews".reviewer_id = %(reviewer_id)s
    and "Reviews_Statuses".code ='NEW' """ % {'reviewer_id': reviewer_id}

    reviews = get_reviews(request, where_conditions)

    return len(reviews)


@view_config(
    route_name='get_project_reviews',
    renderer='json'
)
def get_project_reviews(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_project_reviews is running')

    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter(Project.id == project_id).first()

    if not project:
        transaction.abort()
        return Response('There is no user with id: %s' % project_id, 500)

    where_conditions = 'where "Review_Tasks".project_id = %(project_id)s' %\
                       {'project_id': project_id}

    return get_reviews(request, where_conditions)


@view_config(
    route_name='get_project_reviews_count',
    renderer='json'
)
def get_project_reviews_count(request):
    """RESTful version of getting all reviews of a task
    """
    logger.debug('get_project_reviews_count is running')

    project_id = request.matchdict.get('id', -1)
    # project = Project.query.filter(Project.id == project_id).first()

    # if not project:
    #     transaction.abort()
    #     return Response('There is no project with id: %s' % project_id, 500)

    where_conditions = """
    where "Review_Tasks".project_id = %(project_id)s
    and "Reviews_Statuses".code = 'NEW'
    """ % {'project_id': project_id}

    reviews = get_reviews(request, where_conditions)

    return len(reviews)


def get_reviews(request, where_conditions):
    """TODO: add docstring
    """
    logger.debug('get_reviews is running')

    logged_in_user = get_logged_in_user(request)

    sql_query = """
    select
        "Reviews".review_number as review_number,
        "Reviews".id as review_id,
        "Reviews_Statuses".code as review_status_code,
        "Statuses_Simple_Entities".name as review_status_name,
        "Statuses_Simple_Entities".html_class as review_status_color,
        "Reviews".task_id as task_id,
        "ParentTasks".full_path as task_name,
        "ParentTasks".thumbnail_full_path as task_thumbnail_full_path,
        "Review_Tasks".review_number as task_review_number,
        "Reviews".reviewer_id as reviewer_id,
        "Reviewers_SimpleEntities".name as reviewer_name,
        "Reviewers_SimpleEntities_Links".full_path as reviewer_thumbnail_path,
        array_agg("Reviewer_Departments_SimpleEntities".name) as reviewer_departments,
        extract(epoch from"Reviews_Simple_Entities".date_created) * 1000 as date_created,
        "Reviews_Simple_Entities".description as review_description,
        "Review_Types".name as review_type,
        array_agg("Other_Reviews_Statuses".name) as other_reviews_statuses

    from "Reviews"
        join "SimpleEntities" as "Reviews_Simple_Entities" on "Reviews_Simple_Entities".id = "Reviews".id
        join "Tasks" as "Review_Tasks" on "Review_Tasks".id = "Reviews".task_id
        join "Statuses" as "Reviews_Statuses" on "Reviews_Statuses".id = "Reviews".status_id
        join "SimpleEntities" as "Statuses_Simple_Entities" on "Statuses_Simple_Entities".id = "Reviews".status_id
        join "SimpleEntities" as "Reviewers_SimpleEntities" on "Reviewers_SimpleEntities".id = "Reviews".reviewer_id
        join "Department_Users" as "Reviewers_Departments" on "Reviewers_Departments".uid = "Reviews".reviewer_id
        join "SimpleEntities" as "Reviewer_Departments_SimpleEntities" on "Reviewer_Departments_SimpleEntities".id = "Reviewers_Departments".did
        left join "SimpleEntities" as "Review_Types" on "Reviews_Simple_Entities".type_id = "Review_Types".id
        left join (%(recursive_task_query)s) as "ParentTasks" on "Review_Tasks".id = "ParentTasks".id

        left outer join "Links" as "Reviewers_SimpleEntities_Links" on "Reviewers_SimpleEntities_Links".id = "Reviewers_SimpleEntities".thumbnail_id

        left outer join "Reviews" as "Other_Reviews" on (
            "Reviews".task_id = "Other_Reviews".task_id and "Reviews".review_number = "Other_Reviews".review_number and "Reviews".reviewer_id != "Other_Reviews".reviewer_id
        )
        left outer join "SimpleEntities" as "Other_Reviews_Statuses" on "Other_Reviews".status_id = "Other_Reviews_Statuses".id

    %(where_conditions)s

    group by

        "Reviews".review_number,
        "Reviews".id,
        "Reviews_Statuses".code,
        "Reviews_Simple_Entities".date_created,
        "Statuses_Simple_Entities".name,
        "Statuses_Simple_Entities".html_class,
        "Reviews".task_id,
        "ParentTasks".full_path,
        "ParentTasks".thumbnail_full_path,
        "Review_Tasks".review_number,
        "Reviews".reviewer_id,
        "Reviewers_SimpleEntities".name,
        "Reviewers_SimpleEntities_Links".full_path,
        "Reviews_Simple_Entities".description,
        "Review_Types".name

    order by "Reviews_Simple_Entities".date_created desc
    """

    sql_query = sql_query % {
        'where_conditions': where_conditions,
        'recursive_task_query': generate_recursive_task_query()
    }

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'review_number': r['review_number'],
            'review_id': r['review_id'],
            'review_status_code': r['review_status_code'].lower(),
            'review_status_name': r['review_status_name'],
            'review_status_color': r['review_status_color'],
            'task_id': r['task_id'],
            'task_name': r['task_name'],
            'task_review_number': r['task_review_number'],
            'task_thumbnail_full_path': r['task_thumbnail_full_path'],
            'reviewer_id': r['reviewer_id'],
            'reviewer_name': r['reviewer_name'],
            'reviewer_thumbnail_full_path':r['reviewer_thumbnail_path'],
            'reviewer_department':r['reviewer_departments'],
            'date_created':r['date_created'],
            'is_reviewer':'1' if logged_in_user.id == r['reviewer_id'] else None,
            'review_description': r['review_description'],
            'review_type': r['review_type'] if r['review_type'] else '',
            'other_reviews_statuses': r['other_reviews_statuses']
        }
        for r in result.fetchall()
    ]

    return return_data


def get_reviews_count(request, where_conditions):
    """returns the count of reviews
    """
    sql_query = """
select
    count(1)
from "Reviews"
    join "Tasks" as "Review_Tasks" on "Review_Tasks".id = "Reviews".task_id
    join "Statuses" as "Reviews_Statuses" on "Reviews_Statuses".id = "Reviews".status_id
where %(where_conditions)s
    """

    sql_query = sql_query % {
        'where_conditions': where_conditions
    }

    return DBSession.connection().execute(sql_query).fetchone()[0]
