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
import json
from pyramid.view import view_config

from stalker import db, Project, Status, Budget, BudgetEntry, Good, Entity, \
    Type, Studio

import transaction

from webob import Response
import stalker_pyramid
from stalker_pyramid.views import (get_logged_in_user, logger,
                                   PermissionChecker, milliseconds_since_epoch,
                                   local_to_utc, StdErrToHTMLConverter,
                                   get_multi_string, update_generic_text)
from stalker_pyramid.views.client import generate_report

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

    budget_type = query_type('Budget', 'Planning')

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

    logger.debug("budget_type: %s" % budget_type)

    generic_data = {
            'approved_total_price': 0,
            'total_price': 0,
            'realized_total_price': 0,
            'calendar_query': ''
    }

    budget = Budget(
        project=project,
        name=name,
        type=budget_type,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        generic_text=json.dumps(generic_data)
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
        'mode': 'Update',
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'budget': budget,
        'came_from': came_from,
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
    description = request.params.get('description', " ")

    type_id = request.params.get('type_id')
    type = Type.query.filter(Type.id == type_id).first()

    if not name:
        return Response('Please supply a name', 500)

    if not type:
        return Response('There is no type with code: %s' % type_id, 500)

    budget.name = name
    budget.description = description
    budget.type = type
    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    request.session.flash('success: Successfully updated budget')
    return Response('Successfully updated budget')


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
            (extract(epoch from "Budget_SimpleEntities".date_created::timestamp at time zone 'UTC') * 1000)::bigint as date_created,
            "Budget_SimpleEntities".description

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

    sql_query = sql_query % {'project_id': project_id, 'additional_condition': additional_condition}

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
            'date_created': r[5],
            'description': r[6]
        }
        # if update_budget_permission:
        budget['item_update_link'] = \
            '/budgets/%s/update/dialog' % budget['id']
        budget['item_remove_link'] =\
            '/entities/%s/delete/dialog?came_from=%s' % (
                budget['id'],
                request.current_route_path()
            )
        budget['item_duplicate_link'] =\
            '/budgets/%s/duplicate/dialog?came_from=%s' % (
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
    route_name='view_budget_calendar',
    renderer='templates/budget/view/view_budget_calendar.jinja2'
)
@view_config(
    route_name='view_budget_table',
    renderer='templates/budget/view/view_budget_table.jinja2'
)
@view_config(
    route_name='view_budget_report',
    renderer='templates/budget/view/view_budget_report.jinja2'
)
def view_budget(request):
    """view_budget_calendar
    """
    logger.debug('view_budget_calendar')
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    budget_id = request.matchdict.get('id')

    budget = Budget.query.filter_by(id=budget_id).first()
    generic_data = json.loads(budget.generic_text)
    budget_calendar_query = generic_data.get('calendar_query', '')
    total_price = generic_data.get('total_price', 0)
    approved_total_price = generic_data.get('approved_total_price', 0)

    projects = Project.query.all()
    mode = request.matchdict.get('mode', None)
    came_from = request.params.get('came_from', request.url)

    return {
        'mode': mode,
        'entity': budget,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'stalker_pyramid': stalker_pyramid,
        'budget_calendar_query': budget_calendar_query,
        'approved_total_price': approved_total_price,
        'total_price': total_price,
        'projects': projects,
        'studio': studio,
        'came_from': came_from
    }


@view_config(
    route_name='save_budget_calendar'
)
def save_budget_calendar(request):
    """saves the data that is created on budget calendar as a string and
    """
    logger.debug('***save_budget_calendar method starts ***')
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget with id : %s' % budget_id, 500)

    budgetentries_data = get_multi_string(request, 'budgetentries_data')

    if not budgetentries_data:
        return Response('No task is defined on calendar for budget id %s' % budget_id, 500)

    # budget.generic_text = '&'.join(budgetentries_data)
    budget.generic_text = update_generic_text(budget.generic_text,
                                                         "calendar_query",
                                                         '&'.join(budgetentries_data),
                                                         'equal')

    for budget_entry in budget.entries:
        generic_data = json.loads(budget_entry.generic_text)
        if generic_data['dataSource'] == 'Calendar':
            # delete_budgetentry_action(budget_entry)
            logger.debug('***delete *** %s ' % budget_entry.name)
            db.DBSession.delete(budget_entry)
    db.DBSession.flush()
    transaction.commit()

    for budgetentry_data in budgetentries_data:
        logger.debug('budgetentry_data: %s' % budgetentry_data)

        id_, text, gid, sdate, duration, resources = \
            budgetentry_data.split('-')
        good_id = gid.split('_')[1]
        good = Good.query.filter_by(id=good_id).first()

        logger.debug('good: %s' % good)
        # if not good:
        #     transaction.abort()
        #     return Response('Please supply a good', 500)

        num_of_resources = int(resources.split('_')[1])
        amount = int(duration.split('_')[1]) * num_of_resources

        generic_data = {
            'dataSource': 'Calendar',
            'secondaryFactor': {'unit': good.unit.split('*')[1], 'amount': num_of_resources},
            'overtime': 0,
            'stoppage_add': 0
        }

        if amount or amount > 0:
            # after transaction commit
            # the ``budget``s state becomes "detached"
            # so reload it
            budget = Budget.query.filter(Budget.id == budget_id).first()
            assert budget in db.DBSession

            create_budgetentry_action(
                budget,
                good,
                amount,
                good.cost * amount,
                ' ',
                json.dumps(generic_data),
                logged_in_user,
                utc_now
            )
            request.session.flash(
                'success:created %s BudgetEntry!' % good.name
            )
            db.DBSession.flush()
            transaction.commit()

    return Response('Budget Calendar Saved Succesfully')


@view_config(
    route_name='edit_budgetentry'
)
def edit_budgetentry(request):
    """edits the budgetentry with data from request
    """
    logger.debug('***edit budgetentry method starts ***')
    oper = request.params.get('oper', None)

    if oper == 'edit':
        e_id = request.params.get('id')
        logger.debug('***edit_budgetentry good: %s ***' % e_id)

        entity = Entity.query.filter_by(id=e_id).first()

        if not entity:
            transaction.abort()
            return Response('There is no entry with id %s' % e_id, 500)

        if entity.entity_type == 'Good':
            logger.debug('***create budgetentry method starts ***')
            return create_budgetentry(request)
        elif entity.entity_type == 'BudgetEntry':
            logger.debug('***update budgetentry method starts ***')
            return update_budgetentry(request)
        else:
            transaction.abort()
            return Response('There is no budgetentry or good with id %s' % e_id, 500)

    elif oper == 'del':
        logger.debug('***delete budgetentry method starts ***')
        return delete_budgetentry(request)


@view_config(
    route_name='create_budgetentry_dialog',
    renderer='templates/budget/dialog/budgetentry_dialog.jinja2'
)
def create_budgetentry_dialog(request):
    """called when creating dailies
    """
    came_from = request.params.get('came_from', '/')

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
    logger.debug('***create_budgetentry method starts ***')
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    good_id = request.params.get('good_id', None)
    if not good_id:
        good_id = request.params.get('id', None)

    logger.debug('good_id %s ' % good_id)
    good = Good.query.filter_by(id=good_id).first()
    if not good:
        transaction.abort()
        return Response('Please supply a good', 500)

    budget_id = request.params.get('budget_id', None)
    budget = Budget.query.filter(Budget.id == budget_id).first()
    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    amount = request.params.get('amount', 0)
    second_amount = request.params.get('second_amount',0)
    amount = int(amount)*int(second_amount)
    price = request.params.get('price', 0)
    description = request.params.get('description', '')

    generic_data = {'dataSource': 'Producer',
                    'secondaryFactor': {'unit': good.unit.split('*')[1], 'amount': second_amount},
                    'overtime': 0,
                    'stoppage_add': 0}

    if not amount or amount == '0':
        transaction.abort()
        return Response('Please supply the amount', 500)

    if price == '0':
        price = good.cost * amount

    if amount and price:
        # data that's generate from good's data

        create_budgetentry_action(budget,
                                  good,
                                  amount,
                                  int(price),
                                  description,
                                  json.dumps(generic_data),
                                  logged_in_user,
                                  utc_now)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    return Response('BudgetEntry Created successfully')


def create_budgetentry_action(budget, good, amount, price, description, gData, logged_in_user, utc_now):
    """create_budgetentry_action
    """
    logger.debug('good_id: %s' % good.id)
    logger.debug('amount: %s' % amount)

    for budget_entry in budget.entries:
        if budget_entry.name == good.name:
            logger.debug('Adds budget_entry amount %s ***' % budget_entry.amount)
            budget_entry.amount += amount
            budget_entry.price += price
            return

    realize_total = good.msrp
    entry_type = query_type('BudgetEntries', good.price_lists[0].name)

    budget_entry = BudgetEntry(
        budget=budget,
        good=good,
        name=good.name,
        type=entry_type,
        amount=amount,
        price=price,
        realize_total=realize_total,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        generic_text=gData
    )
    db.DBSession.add(budget_entry)

    if good.generic_text != "":
        generic_data = json.loads(good.generic_text)
        linked_goods = generic_data.get('linked_goods', None)
        if linked_goods:
            for l_good in linked_goods:
                linked_good = \
                    Good.query.filter(Good.id == l_good["id"]).first()

                logger.debug("%s is added" % linked_good.name)

                create_budgetentry_action(
                    budget,
                    linked_good,
                    amount,
                    linked_good.cost * amount,
                    description,
                    gData,
                    logged_in_user,
                    utc_now
                )


@view_config(
    route_name='update_budgetentry'
)
def update_budgetentry(request):
    """updates the BudgetEntry with data from request
    """
    logger.debug('***update_budgetentry method starts ***')
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budgetentry_id = request.params.get('id')
    budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()

    # good = Good.query.filter(Good.name == budgetentry.name).first()
    # user supply this data
    amount = request.params.get('amount', None)
    second_amount = request.params.get('second_amount', None)
    overtime = int(request.params.get('overtime', 0))
    stoppage_add = request.params.get('stoppage_add', 0)

    price = request.params.get('price', None)

    logger.debug("overtime %s " % overtime)
    logger.debug("stoppage_add %s " % stoppage_add)

    if not price:
        transaction.abort()
        return Response('Please supply price', 500)
    price = int(price)
    description = request.params.get('note', '')

    generic_data = json.loads(budgetentry.generic_text)

    logger.debug("budgetentry.generic_text: %s" % budgetentry.generic_text)

    if 'dataSource' in generic_data \
       and generic_data['dataSource'] == 'Calendar':

        budgetentry.price = price
        budgetentry.description = description
        budgetentry.date_updated = utc_now
        budgetentry.updated_by = logged_in_user
    else:
        if not amount or amount == '0':
            transaction.abort()
            return Response('Please supply the amount', 500)


        second_amount = int(second_amount)
        amount = int(amount)*second_amount
        budgetentry.amount = amount

        budgetentry.price = price if price != '0' else budgetentry.cost * (amount + overtime)
        budgetentry.description = description
        budgetentry.date_updated = utc_now
        budgetentry.updated_by = logged_in_user

    budgetentry.generic_text = update_generic_text(budgetentry.generic_text,
                                                    "secondaryFactor",
                                                    {'unit': budgetentry.good.unit.split('*')[1], 'amount': second_amount},
                                                     'equal')

    budgetentry.generic_text = update_generic_text(budgetentry.generic_text,
                                                         "overtime",
                                                         overtime,
                                                         'equal')

    budgetentry.generic_text = update_generic_text(budgetentry.generic_text,
                                                         "stoppage_add",
                                                         stoppage_add,
                                                         'equal')
    # budgetentry.generic_text = json.dumps(generic_data)

    request.session.flash(
        'success:updated %s budgetentry!' % budgetentry.name
    )
    return Response('successfully updated %s budgetentry!' % budgetentry.name)


@view_config(
    route_name='delete_budgetentry_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_budgetentry_dialog(request):
    """delete_budgetentry_dialog
    """
    logger.debug('delete_budgetentry_dialog is starts')

    budgetentry_id = request.matchdict.get('id')
    budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()

    action = '/budgetentries/%s/delete' % budgetentry_id
    came_from = request.params.get('came_from', '/')

    message = '%s will be deleted' \
              '<br><br>Are you sure?' % budgetentry.name

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='delete_budgetentry'
)
def delete_budgetentry(request):
    """deletes the budgetentry
    """

    budgetentry_id = request.matchdict.get('id')
    budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()

    if not budgetentry:
        transaction.abort()
        return Response('There is no budgetentry with id: %s' % budgetentry_id, 500)

    if budgetentry.type.name == 'Calendar':
        transaction.abort()
        return Response('You can not delete CalenderBasedEntry', 500)

    budgetentry_name = budgetentry.name
    try:
        db.DBSession.delete(budgetentry)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        # return Response(c.html(), 500)
    return Response('Successfully deleted budgetentry with name %s' % budgetentry_name)


def delete_budgetentry_action(budgetentry):

    logger.debug('delete_budgetentry_action %s' % budgetentry.name)
    budgetentry_name = budgetentry.name
    try:
        db.DBSession.delete(budgetentry)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        # return Response(c.html(), 500)
    return Response('Successfully deleted good with name %s' % budgetentry_name)


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
        select
           "BudgetEntries_SimpleEntities".id,
           "BudgetEntries_SimpleEntities".name,
           "Types_SimpleEntities".name as type_name,
           "BudgetEntries".amount,
           "BudgetEntries".cost,
           "BudgetEntries".msrp,
           "BudgetEntries".price,
           "BudgetEntries".realized_total,
           "BudgetEntries".unit,
           "BudgetEntries_SimpleEntities".description,
           "BudgetEntries_SimpleEntities".generic_text,
           "Goods_SimpleEntities".generic_text
        from "BudgetEntries"
        join "SimpleEntities" as "BudgetEntries_SimpleEntities" on "BudgetEntries_SimpleEntities".id = "BudgetEntries".id
        join "SimpleEntities" as "Types_SimpleEntities" on "Types_SimpleEntities".id = "BudgetEntries_SimpleEntities".type_id
        join "Budgets" on "Budgets".id = "BudgetEntries".budget_id
        join "Goods" on "BudgetEntries".good_id = "Goods".id
        join "SimpleEntities" as "Goods_SimpleEntities" on "Goods_SimpleEntities".id = "Goods".id

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
            'cost': r[4],
            'msrp': r[5],
            'price': r[6],
            'realized_total': r[7],
            'unit': r[8],
            'note': r[9],
            'generic_data': json.loads(r[10]) if r[10] else {},
            'good_generic_data': json.loads(r[11]) if r[11] else {}
        }
        for r in result.fetchall()
    ]

    resp = Response(
        json_body=entries
    )

    return resp


@view_config(
    route_name='change_budget_type_dialog',
    renderer='templates/budget/dialog/change_budget_type_dialog.jinja2'
)
def change_budget_type_dialog(request):
    """change_budget_type_dialog
    """
    logger.debug('change_budget_type_dialog is starts')

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    type_name = request.matchdict.get('type_name')
    came_from = request.params.get('came_from', '/')

    generic_data = json.loads(budget.generic_text)
    budget_total_price = generic_data.get('total_price', 0)

    return {
        'type_name': type_name,
        'came_from': came_from,
        'budget': budget,
        'budget_total_price': budget_total_price
    }


@view_config(
    route_name='change_budget_type'
)
def change_budget_type(request):

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    type_name = request.matchdict.get('type_name')
    type = query_type('Budget', type_name)

    approved_total_price = request.params.get('approved_total_price', 0)
    total_price = request.params.get('total_price', 0)


    logger.debug("approved_total_price : %s" % approved_total_price)

    budget.generic_text = update_generic_text(budget.generic_text,
                                                         "approved_total_price",
                                                         approved_total_price,
                                                         'equal')

    budget.generic_text = update_generic_text(budget.generic_text,
                                                         "total_price",
                                                         total_price,
                                                         'equal')

    logger.debug("budget.generic_text : %s" % budget.generic_text)

    budget.type = type
    budget.updated_by = logged_in_user
    budget.date_updated = utc_now

    request.session.flash('success: Budget type is changed successfully')
    return Response('Budget type is changed successfully')


@view_config(
    route_name='duplicate_budget_dialog',
    renderer='templates/budget/dialog/duplicate_budget_dialog.jinja2'
)
def duplicate_budget_dialog(request):
    """duplicate_budget_dialog
    """
    logger.debug('duplicate_budget_dialog is starts')

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    action = '/budgets/%s/duplicate' % budget_id

    came_from = request.params.get('came_from', '/')

    message = 'Are you sure you want to <strong>change %s type</strong>?'% budget.name

    logger.debug('action: %s' % action)

    return {
        'budget': budget,
        'message': message,
        'came_from': came_from,
        'action': action
    }

@view_config(
    route_name='duplicate_budget'
)
def duplicate_budget(request):

    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    name = request.params.get('dup_budget_name')
    description = request.params.get('dup_budget_description')

    budget_type = query_type('Budget', 'Planning')
    project = budget.project

    if not name:
        return Response('Please supply a name', 500)

    if not description:
        return Response('Please supply a description', 500)

    new_budget = Budget(
        project=project,
        name=name,
        type=budget_type,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        generic_text=budget.generic_text
    )
    db.DBSession.add(budget)
    for budget_entry in budget.entries:
        new_budget_entry = BudgetEntry(
                budget=new_budget,
                good= budget_entry.good,
                name=budget_entry.name,
                type=budget_entry.type,
                amount=budget_entry.amount,
                cost=budget_entry.cost,
                msrp=budget_entry.msrp,
                price=budget_entry.price,
                unit=budget_entry.unit,
                description=budget_entry.description,
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now,
                generic_text=budget_entry.generic_text
            )
        db.DBSession.add(new_budget_entry)

    request.session.flash('success: Budget is duplicated successfully')
    return Response('Budget is duplicated successfully')


@view_config(
    route_name='create_budgetentry_dialog',
    renderer='templates/budget/dialog/budgetentry_dialog.jinja2'
)
def create_budgetentry_dialog(request):
    """called when creating dailies
    """
    came_from = request.params.get('came_from', '/')

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


class ReportExporter(object):
    """A base class for report exporters
    """

    def __init__(self, name='', template=''):
        self.name = name
        self.template = template

    def export(self):
        """virtual method that needs to be implemented on child classes
        """
        raise NotImplementedError()


@view_config(
    route_name='generate_report'
)
def generate_report_view(request):
    """generates report and allows the user to download it
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict['id']

    from stalker import Budget
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if budget:
        # type = query_type('Budget', 'Pending')
        # total_price = request.params.get('total_price', 0)
        #
        # logger.debug('total_price %s ' % total_price)
        #
        # budget.generic_text = update_generic_text(budget.generic_text,
        #                                          'total_price',
        #                                          total_price,
        #                                          'equal')
        #
        # budget.type = type
        # budget.updated_by = logged_in_user
        # budget.date_updated = utc_now

        project = budget.project
        client = project.client
        if not client:
            raise Response('No client in the project')

        logger.debug('generating report:')
        temp_report_path = generate_report(budget)
        logger.debug('temp_report_path: %s' % temp_report_path)

        from pyramid.response import FileResponse
        response = FileResponse(
            temp_report_path,
            request=request,
            content_type='application/force-download'
        )

        report_file_nice_name = '%s_%s.xlsx' % (
            project.code, budget.name.replace(' ', '_')
        )
        response.headers['content-disposition'] = \
            str('attachment; filename=%s' % report_file_nice_name)

        return response