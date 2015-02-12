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


import datetime
from pyramid.view import view_config

from stalker import db, Project, Status, Budget, BudgetEntry

import transaction

from webob import Response
from stalker_pyramid.views import (get_logged_in_user, logger,
                                   PermissionChecker, milliseconds_since_epoch,
                                   local_to_utc)

from stalker_pyramid.views.task import generate_recursive_task_query
from stalker_pyramid.views.type import query_type


@view_config(
    route_name='create_budget_dialog',
    renderer='templates/budget/dialog/budget_dialog.jinja2'
)
def create_budget_dialog(request):
    """called when creating budget
    """
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    project_id = request.params.get('project_id', -1)
    project = Project.query.filter(Project.id == project_id).first()

    if not project:
        return Response('No project found with id: %s' % project_id, 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'project': project,
        'came_from': came_from,
        'mode': 'Create',
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_budget'
)
def create_budget(request):
    """runs when creating a budget
    """

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    name = request.params.get('name')
    description = request.params.get('description')

    type_name = request.params.get('type_name', None)
    budget_type = query_type('Budget', type_name)

    project_id = request.params.get('project_id', None)
    project = Project.query.filter(Project.id == project_id).first()

    if not name:
        return Response('Please supply a name', 500)

    if not description:
        return Response('Please supply a description', 500)

    # if not status:
    #     return Response('There is no status with code: %s' % status_id, 500)

    if not project:
        return Response('There is no project with id: %s' % project_id, 500)

    budget = Budget(
        project=project,
        name=name,
        type=budget_type,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now
    )
    db.DBSession.add(budget)

    return Response('Budget Created successfully')


@view_config(
    route_name='update_budget_dialog',
    renderer='templates/budget/dialog/budget_dialog.jinja2'
)
def update_budget_dialog(request):
    """called when updating dailies
    """
    came_from = request.params.get('came_from','/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()


    return {
        'mode':'Update',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'budget': budget,
        'came_from':came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='update_budget'
)
def update_budget(request):
    """runs when updating a budget
    """

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget with id : %s' % budget_id, 500)

    name = request.params.get('name')
    description = request.params.get('description')

    status_id = request.params.get('status_id')
    status = Status.query.filter(Status.id == status_id).first()

    if not name:
        return Response('Please supply a name', 500)

    if not description:
        return Response('Please supply a description', 500)

    if not status:
        return Response('There is no status with code: %s' % status.code, 500)

    budget.name = name
    budget.description = description
    budget.status = status
    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    request.session.flash('success: Successfully updated budget')
    return Response('Successfully updated budget')


@view_config(
    route_name='create_budgetentry_dialog',
    renderer='templates/budget/dialog/budgetentry_dialog.jinja2'
)
def create_budgetentry_dialog(request):
    """called when creating dailies
    """
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    budget_id = request.params.get('budget_id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        return Response('No budget found with id: %s' % budget_id, 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'budget': budget,
        'came_from': came_from,
        'mode': 'Create',
        'milliseconds_since_epoch': milliseconds_since_epoch
    }

@view_config(
    route_name='create_budgetentry'
)
def create_budgetentry(request):
    """runs when creating a budget
    """

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    name = request.params.get('name')
    description = request.params.get('description')
    amount = int(request.params.get('amount'))

    type_name = request.params.get('type_name', None)
    entry_type = query_type('BudgetEntries', type_name)

    budget_id = request.params.get('budget_id', None)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not name:
        return Response('Please supply a name', 500)

    if not description:
        return Response('Please supply a description', 500)

    # if not status:
    #     return Response('There is no status with code: %s' % status_id, 500)

    if not budget:
        return Response('There is no budget with id: %s' % budget_id, 500)

    budget_entry = BudgetEntry(
        budget=budget,
        name=name,
        type=entry_type,
        amount=amount,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now
    )
    db.DBSession.add(budget_entry)

    return Response('BudgetEntry Created successfully')


@view_config(
    route_name='get_project_budgets',
    renderer='json'
)
def get_budgets(request):
    """returns budgets with the given id
    """

    project_id = request.matchdict.get('id')
    logger.debug('get_budgets is working for the project which id is: %s' % project_id)

    status_code = request.params.get('status_code', None)
    status = Status.query.filter(Status.code == status_code).first()

    sql_query = """
        select
            "Budgets".id,
            "Budget_SimpleEntities".name,
            "Created_By_SimpleEntities".created_by_id,
            "Created_By_SimpleEntities".name,
            "Type_SimpleEntities".name,
            (extract(epoch from "Budget_SimpleEntities".date_created::timestamp at time zone 'UTC') * 1000)::bigint as date_created

        from "Budgets"
        join "SimpleEntities" as "Budget_SimpleEntities" on "Budget_SimpleEntities".id = "Budgets".id
        join "SimpleEntities" as "Created_By_SimpleEntities" on "Created_By_SimpleEntities".id = "Budget_SimpleEntities".created_by_id
        left outer join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Budget_SimpleEntities".type_id
        join "Projects" on "Projects".id = "Budgets".project_id

        where "Projects".id = %(project_id)s %(additional_condition)s
    """

    additional_condition = ''
    if status:
        additional_condition = 'and "Budgets_Statuses".id=%s' % status.id

    budgets = []

    sql_query = sql_query % {'project_id': project_id, 'additional_condition':additional_condition}

    result = db.DBSession.connection().execute(sql_query)
    update_budget_permission = \
        PermissionChecker(request)('Update_Budget')

    for r in result.fetchall():
        budget = {
            'id': r[0],
            'name': r[1],
            'created_by_id': r[2],
            'created_by_name': r[3],
            'item_view_link': '/budgets/%s/view' % r[0],
            'type_name': r[4],
            'date_created': r[5]
        }
        if update_budget_permission:
            budget['item_update_link'] = \
                '/budgets/%s/update/dialog' % budget['id']
            budget['item_remove_link'] =\
                '/budgets/%s/delete/dialog?came_from=%s' % (
                    budget['id'],
                    request.current_route_path()
                )

        budgets.append(budget)


    resp = Response(
        json_body=budgets
    )

    return resp


@view_config(
    route_name='get_project_budgets_count',
    renderer='json'
)
def get_budgets_count(request):
    """missing docstring
    """
    project_id = request.matchdict.get('id')
    logger.debug('get_budgets_count is working for the project which id is %s' % project_id)

    sql_query = """
        select count(1) from (
            select
                "Budgets".id
            from "Budgets"
            join "Projects" on "Projects".id = "Budgets".project_id

            where "Projects".id = %(project_id)s
        ) as data
    """
    sql_query = sql_query % {'project_id': project_id}

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = db.DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]

@view_config(
    route_name='get_budget_entries',
    renderer='json'
)
def get_budget_entries(request):
    """returns budgets with the given id
    """

    budget_id = request.matchdict.get('id')
    logger.debug('get_budget_entries is working for the project which id is: %s' % budget_id)

    sql_query = """
        select "BudgetEntries_SimpleEntities".id,
               "BudgetEntries_SimpleEntities".name,
               "Types_SimpleEntities".name as type_name,
               "BudgetEntries".amount,
               "BudgetEntries_SimpleEntities".description
        from "BudgetEntries"
        join "SimpleEntities" as "BudgetEntries_SimpleEntities" on "BudgetEntries_SimpleEntities".id = "BudgetEntries".id
        join "SimpleEntities" as "Types_SimpleEntities" on "Types_SimpleEntities".id = "BudgetEntries_SimpleEntities".type_id
        join "Budgets" on "Budgets".id = "BudgetEntries".budget_id
        where "Budgets".id = %(budget_id)s
    """

    sql_query = sql_query % {'budget_id': budget_id}

    result = db.DBSession.connection().execute(sql_query)
    entries = [
        {
            'id': r[0],
            'name': r[1],
            'type': r[2],
            'amount': r[3],
            'unit': 'hour',
            'unit_price': 10,
            'note': r[4]
        }
        for r in result.fetchall()
    ]

    resp = Response(
        json_body=entries
    )

    return resp



