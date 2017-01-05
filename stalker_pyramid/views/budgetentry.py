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
    Type, Studio, StatusList

import transaction

from webob import Response
import stalker_pyramid
# from stalker_pyramid.views import (get_logged_in_user, logger,
#                                    PermissionChecker, milliseconds_since_epoch,
#                                    local_to_utc, StdErrToHTMLConverter,
#                                    get_multi_string, update_generic_text)
# from stalker_pyramid.views.client import generate_report
#
# from stalker_pyramid.views.task import generate_recursive_task_query
# from stalker_pyramid.views.type import query_type
import logging
from stalker_pyramid.views import get_date

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='edit_budgetentry'
)
def edit_budgetentry(request):
    """edits the budgetentry with data from request
    """
    logger.debug('***edit budgetentry method starts ***')
    oper = request.params.get('oper', None)

    if oper == 'edit':
        id = request.params.get('id')
        logger.debug('***edit_budgetentry good: %s ***' % id)

        entity = Entity.query.filter_by(id=id).first()

        if not entity:
            transaction.abort()
            return Response('There is no entry with id %s' % id, 500)

        if entity.entity_type == 'Good':
            logger.debug('***create budgetentry method starts ***')
            return create_budgetentry(request)

        elif entity.entity_type == 'BudgetEntry':
            logger.debug('***update budgetentry method starts ***')
            return update_budgetentry(request)

        else:
            transaction.abort()
            return Response(
                'There is no budgetentry or good with id %s' % id,
                status=500
            )

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
    from stalker_pyramid.views import (get_logged_in_user,
                                       milliseconds_since_epoch)
    logged_in_user = get_logged_in_user(request)

    budget_id = request.params.get('budget_id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        return Response('No budget found with id: %s' % budget_id, 500)

    from stalker_pyramid.views.auth import PermissionChecker
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
    """runs when creating a budgetentry
    """
    logger.debug('***create_budgetentry method starts ***')
    from stalker_pyramid.views import get_logged_in_user, local_to_utc
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
    second_amount = request.params.get('second_amount', 1)
    msrp = request.params.get('msrp', good.msrp)
    cost = request.params.get('cost', good.cost)

    logger.debug('create_budgetentry msrp %s ' % msrp)
    logger.debug('create_budgetentry cost %s ' % cost)
    
    price = request.params.get('price', 0)
    description = request.params.get('description', '')

    generic_data = {
        'dataSource': 'Producer',
        'secondaryFactor': [
            {
                'unit': good.unit.split('*')[1],
                'amount': amount,
                'second_amount': second_amount
            }
        ],
        'overtime': 0,
        'stoppage_add': 0
    }

    if not amount or amount == '0':
        transaction.abort()
        return Response('Please supply the amount', 500)

    amount = int(amount)*int(second_amount)
    if price == '0':
        price = good.cost * amount

    if amount and price:
        # data that's generate from good's data

        create_budgetentry_action(
                                    budget,
                                    good,
                                    good.name,
                                    amount,
                                    float(msrp),
                                    float(cost),
                                    float(price),
                                    description,
                                    json.dumps(generic_data),
                                    logged_in_user,
                                    utc_now
        )

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    return Response('BudgetEntry Created successfully')


def create_budgetentry_action(budget, good, name, amount, msrp, cost, price, description, gData, logged_in_user, utc_now):
    """create_budgetentry_action
    """
    logger.debug('create_budgetentry_action')
    logger.debug('good_id: %s' % good.id)
    logger.debug('amount: %s' % amount)
    logger.debug('cost: %s' % cost)
    logger.debug('msrp: %s' % msrp)
    logger.debug('name: %s' % name)

    for budget_entry in budget.entries:
        if budget_entry.name == good.name:
            logger.debug(
                'Adds budget_entry amount %s *** %s' %
                (budget_entry.amount, budget_entry.name)
            )
            budget_entry.amount += amount
            budget_entry.price += price

            new_generic_data = json.loads(gData)
            dataSource = new_generic_data["dataSource"]

            if dataSource != "Calendar":
                return

            new_secondaryFactor = new_generic_data["secondaryFactor"]
            secondaryFactor = budget_entry.get_generic_text_attr('secondaryFactor')
            secondaryFactor.extend(new_secondaryFactor)

            budget_entry.set_generic_text_attr("secondaryFactor", secondaryFactor)
            return

    realize_total = good.msrp
    from stalker_pyramid.views.type import query_type
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
    budget_entry.cost = cost
    budget_entry.msrp = msrp
    budget_entry.name = name

    if good.generic_text != "":
        linked_goods = good.get_generic_text_attr('linked_goods')
        if linked_goods:
            for l_good in linked_goods:
                linked_good = \
                    Good.query.filter(Good.id == l_good["id"]).first()

                generic_data = {
                    'dataSource': 'Linked',
                    'secondaryFactor': [
                        {
                            'unit': linked_good.unit.split('*')[1],
                            'amount': amount,
                            'second_amount':1
                        }
                    ],
                    'overtime': 0,
                    'stoppage_add': 0
                }

                create_budgetentry_action(
                    budget,
                    linked_good,
                    linked_good.name,
                    amount,
                    linked_good.msrp,
                    linked_good.cost,
                    linked_good.cost * amount,
                    description,
                    json.dumps(generic_data),
                    logged_in_user,
                    utc_now
                )

    return budget_entry


def update_budgetenties_startdate(entity, time_delta):
    """updates the BudgetEntry start date in all budgets which status is planning
    """
    logger.debug('update_budgetenties_startdate')

    sql_query = """
        select
           array_agg("BudgetEntries".id),
           "Budgets".id
        from "BudgetEntries"
        join "Budgets" on "Budgets".id = "BudgetEntries".budget_id
        join "Statuses" on "Budgets".status_id = "Statuses".id

        where "Statuses".code = 'PLN' %(where_clause)s

        group by "Budgets".id
        """
    where_clause = ""
    if entity.entity_type == "Project":
        where_clause = """and "Budgets".project_id =  %(project_id)s""" % {'project_id': entity.id}

    elif entity.entity_type == "Budget":
        where_clause = """and "Budgets".id =  %(budget_id)s""" % {'budget_id': entity.id}

    sql_query = sql_query % {'where_clause': where_clause}
    # logger.debug('sql_query: %s' % sql_query)

    result = db.DBSession.connection().execute(sql_query)
    lists = [
        {
            'budgetEntries': r[0],
            'budget_id': r[1]
        }
        for r in result.fetchall()
    ]

    for list in lists:

        budget = Budget.query.filter(Budget.id == list['budget_id']).first()

        if budget:
            logger.debug('list[budgetEntries]: %s' % list['budgetEntries'])
            milestones = budget.get_generic_text_attr("milestones")
            folders = budget.get_generic_text_attr("folders")

            if milestones:
                for milestone in milestones:
                    milestone['start_date'] = int(milestone['start_date'])+time_delta

                budget.set_generic_text_attr("milestones", milestones)

            if folders:
                for folder in folders:
                    folder['start_date'] = int(folder['start_date'])+time_delta

                budget.set_generic_text_attr("folders", folders)

            logger.debug('time_delta: %s' % time_delta)
            for entry_id in list['budgetEntries']:
                logger.debug('entry_id: %s' % entry_id)
                budgetEntry = BudgetEntry.query.filter(BudgetEntry.id == entry_id).first()
                logger.debug('budgetEntry.name: %s' % budgetEntry.name)
                if budgetEntry:
                    secondaryFactors = budgetEntry.get_generic_text_attr("secondaryFactor")
                    logger.debug('secondaryFactors: %s' % secondaryFactors)

                    if secondaryFactors:
                        for secondaryFactor in secondaryFactors:
                            if 'start_date' in secondaryFactor:
                                logger.debug('secondaryFactor[start_date]: %s' % secondaryFactor['start_date'])
                                secondaryFactor['start_date'] = int(secondaryFactor['start_date'])+time_delta

                        budgetEntry.set_generic_text_attr("secondaryFactor", secondaryFactors)

    return Response('successfully updated budgetentries!')


def update_folder_tasks_startdate(budget, folder_id, time_delta):
    """updates the BudgetEntry start date in given folder
    """
    logger.debug('update_folder_tasks_startdate')

    budgetEntries = BudgetEntry.query.filter(BudgetEntry.budget == budget).all()

    for budgetEntry in budgetEntries:
        secondaryFactors = budgetEntry.get_generic_text_attr("secondaryFactor")
        if secondaryFactors:
            for secondaryFactor in secondaryFactors:
                if 'folder_id' in secondaryFactor:
                    if secondaryFactor['folder_id'] == folder_id:
                        if 'start_date' in secondaryFactor:
                            logger.debug('secondaryFactor[start_date]: %s' % secondaryFactor['start_date'])
                            logger.debug('time_delta: %s' % time_delta)

                            secondaryFactor['start_date'] = \
                                int(secondaryFactor['start_date'])+time_delta
                            logger.debug('secondaryFactor[start_date]: %s' % secondaryFactor['start_date'])

            budgetEntry.set_generic_text_attr("secondaryFactor", secondaryFactors)

    return Response('successfully updated budgetentries!')


@view_config(
    route_name='update_budgetentry'
)
def update_budgetentry(request):
    """updates the BudgetEntry with data from request
    """
    logger.debug('***update_budgetentry method starts ***')
    from stalker_pyramid.views import get_logged_in_user, local_to_utc
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

    logger.debug("budgetentry.generic_text: %s" % budgetentry.generic_text)

    second_amount = int(second_amount)

    if budgetentry.get_generic_text_attr('dataSource') == 'Calendar':


        budgetentry.price = price
        budgetentry.description = description
        budgetentry.date_updated = utc_now
        budgetentry.updated_by = logged_in_user
        request.session.flash(
                "warning: You can not update calendar based entry's amount"
        )
    else:
        if not amount or amount == '0':
            transaction.abort()
            return Response('Please supply the amount', 500)

        budgetentry.amount = float(amount)*second_amount

        budgetentry.price = price if price != '0' else budgetentry.cost * (amount + overtime)
        budgetentry.description = description
        budgetentry.date_updated = utc_now
        budgetentry.updated_by = logged_in_user

        budgetentry.set_generic_text_attr("secondaryFactor",
                                          [{
                                              'unit': budgetentry.good.unit.split('*')[1],
                                              'amount': amount,
                                              'second_amount': second_amount
                                          }]
        )
        request.session.flash(
            'success:updated %s budgetentry!' % budgetentry.name
        )

    budgetentry.set_generic_text_attr("overtime", overtime)
    budgetentry.set_generic_text_attr("stoppage_add", stoppage_add)
    check_linked_good_budgetentries(budgetentry.good, budgetentry.budget)


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
    logger.debug('delete_budgetentry is starts')

    dataSource = request.params.get('dataSource', None)
    if dataSource and dataSource == 'Calendar':
        task_id = request.matchdict.get('id')
        budgetentry_id, secondaryFactor_id = task_id.split('_')
        logger.debug('budgetentry_id %s ' % budgetentry_id)
        logger.debug('secondaryFactor_id %s ' % secondaryFactor_id)
    else:
        budgetentry_id = request.matchdict.get('id')

    budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()

    if not budgetentry:
        transaction.abort()
        return Response('There is no budgetentry with id: %s' % budgetentry_id, 500)

    budgetentry_name = budgetentry.name

    from stalker_pyramid.views import StdErrToHTMLConverter
    if dataSource and dataSource == 'Calendar':
        secondaryFactor = budgetentry.get_generic_text_attr("secondaryFactor")
        secondaryFactor_id = int(secondaryFactor_id)
        secondaryFactor = secondaryFactor[:secondaryFactor_id] + secondaryFactor[secondaryFactor_id+1:]
        logger.debug('secondaryFactor %s ' % secondaryFactor)
        if len(secondaryFactor) != 0:
            budgetentry.set_generic_text_attr("secondaryFactor", secondaryFactor)
        else:
            try:
                db.DBSession.delete(budgetentry)
                transaction.commit()
            except Exception as e:
                transaction.abort()
                c = StdErrToHTMLConverter(e)
                transaction.abort()
                # return Response(c.html(), 500)
    else:
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
        from stalker_pyramid.views import StdErrToHTMLConverter
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        # return Response(c.html(), 500)
    return Response('Successfully deleted good with name %s' % budgetentry_name)


@view_config(
    route_name='get_budget_calendar_items',
    renderer='json'
)
def get_budget_calendar_items(request):
    """returns budget items
    """

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    item_type = request.params.get('item_type', None)
    if not item_type:
        transaction.abort()
        return Response('Missing parameters')
    logger.debug("item_type: %s" % item_type )
    items_data = budget.get_generic_text_attr(item_type)

    return items_data


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
           "Goods_SimpleEntities".generic_text,
           "Goods_SimpleEntities".id
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
            'good_generic_data': json.loads(r[11]) if r[11] else {},
            'good_id': r[12]
        }
        for r in result.fetchall()
    ]

    resp = Response(
        json_body=entries
    )

    return resp


@view_config(
    route_name='create_budgetentry_dialog',
    renderer='templates/budget/dialog/budgetentry_dialog.jinja2'
)
def create_budgetentry_dialog(request):
    """called when creating dailies
    """
    came_from = request.params.get('came_from', '/')

    # get logged in user
    from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                       milliseconds_since_epoch)
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
    route_name='budget_calendar_task_dialog',
    renderer='templates/budget/dialog/budget_calendar_item_dialog.jinja2'
)
@view_config(
    route_name='budget_calendar_folder_dialog',
    renderer='templates/budget/dialog/budget_calendar_item_dialog.jinja2'
)
@view_config(
    route_name='budget_calendar_milestone_dialog',
    renderer='templates/budget/dialog/budget_calendar_item_dialog.jinja2'
)
def budget_calendar_item_dialog(request):
    """budget_calendar_item_dialog
    """
    logger.debug('budget_calendar_item_dialog is starts')

    from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                       milliseconds_since_epoch)
    logged_in_user = get_logged_in_user(request)

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget found with id: %s' % budget_id, 500)

    came_from = request.params.get('came_from', '/')
    mode = request.params.get('mode', None)

    if not mode:
        return Response('Missing parameters')

    import copy
    item = copy.copy(request.params)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'budget': budget,
        'came_from': came_from,
        'item': item,
        'mode': mode,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='budget_calendar_list_order'
)
def budget_calendar_list_order(request):
    """budget_calendar_list_order
    """
    logger.debug('budget_calendar_list_order method starts')

    from stalker_pyramid.views import get_logged_in_user, local_to_utc
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget with id : %s' % budget_id, 500)

    items = request.params.get('items', None)
    if not items:
        transaction.abort()
        return Response('Missing parameters')

    item_list = json.loads(items)

    folders = budget.get_generic_text_attr('folders')
    milestones = budget.get_generic_text_attr('milestones')

    for item in item_list:
        logger.debug(item)
        if item['type'] == "folder":
            filtered_folders = filter(lambda x: x['id'] == item['id'], folders)
            filtered_folders[0]['gantt_index'] = item['gantt_index']

        if item['type'] == "milestone":
            filtered_milestones = filter(lambda x: x['id'] == item['id'], milestones)
            filtered_milestones[0]['gantt_index'] = item['gantt_index']

        if item['type'] == "task":
            budgetentry_id, secondaryFactor_id = (item['id']).split('_')
            budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()
            index = int(secondaryFactor_id)
            secondaryFactor = budgetentry.get_generic_text_attr("secondaryFactor")
            secondaryFactor[index]['gantt_index'] = item['gantt_index']
            budgetentry.set_generic_text_attr("secondaryFactor", secondaryFactor)
            budgetentry.date_updated = utc_now
            budgetentry.updated_by = logged_in_user

    budget.set_generic_text_attr('folders', folders)
    budget.set_generic_text_attr('milestones', milestones)
    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    return Response('BudgetEntry Created successfully')


@view_config(
    route_name='budget_calendar_item_action'
)
def budget_calendar_item_action(request):
    """budget_calendar_item_action
    """
    logger.debug('budget_calendar_item_action method starts')

    from stalker_pyramid.views import get_logged_in_user, local_to_utc
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget with id : %s' % budget_id, 500)

    mode = request.params.get('mode', None)
    item_id = request.params.get('id', None)
    name = request.params.get('name', None)
    start_date = request.params.get('start_date', None)
    description = request.params.get('description', None)
    gantt_index = request.params.get('index', None)
    item_type = request.matchdict.get('item_type', None)
    dialog_action = request.params.get('dialog_action', None)
    item_type_pl = "%ss" % item_type

    if not item_type:
        transaction.abort()
        return Response('Missing parameters')

    if not mode:
        transaction.abort()
        return Response('Missing parameters')

    if not item_id:
        transaction.abort()
        return Response('Please supply an id', 500)

    if not start_date:
        transaction.abort()
        return Response('Please supply the start date', 500)

    logger.debug("mode : %s" % mode)
    logger.debug("item_id : %s" % item_id)
    logger.debug("name : %s" % name)
    logger.debug("start_date : %s" % start_date)
    logger.debug("description : %s" % description)
    logger.debug("gantt_index : %s" % gantt_index)
    logger.debug("dialog_action : %s" % dialog_action)

    items = budget.get_generic_text_attr(item_type_pl)

    if mode == 'Create':
        if not name:
            transaction.abort()
            return Response('Please supply the name', 500)

        new_item = {
            'id': item_id,
            'name': name,
            'start_date': int(start_date),
            'gantt_index': gantt_index,
            'description': description if description else " "
        }

        if item_type_pl == "milestones":
            new_item['links'] = []

        items.append(new_item)

    elif mode == 'Update':
        filtered_items = filter(lambda x: x['id'] == item_id, items)
        if filtered_items:
            item = filtered_items[0]

            if item_type_pl == "folders" and dialog_action:
                time_delta = int(start_date) - item['start_date']
                update_folder_tasks_startdate(budget, item_id, time_delta)

            item['start_date'] = int(start_date)
            if name:
                item['name'] = name
            if description:
                item['description'] = description
            if gantt_index:
                item['gantt_index'] = gantt_index

    budget.set_generic_text_attr(item_type_pl, items)
    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    # request.session.flash('success: %s Created successfully' % name)
    return Response('Item Created successfully')


@view_config(
    route_name='budget_calendar_item_delete'
)
def budget_calendar_item_delete(request):
    """budget_calendar_folder_delete
    """
    logger.debug('***budget_calendar_folder_delete method starts ***')
    from stalker_pyramid.views import get_logged_in_user, local_to_utc
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', None)
    budget = Budget.query.filter(Budget.id == budget_id).first()
    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    item_type = request.matchdict.get('item_type', None)
    if not item_type:
        transaction.abort()
        return Response('There is no item_type', 500)

    item_id = request.params.get('id', None)
    if not item_id:
        transaction.abort()
        return Response('There is no item_id', 500)

    item_list_name = "%ss" % item_type
    if item_type != 'task':
        items = budget.get_generic_text_attr(item_list_name)
        filtered_items = filter(lambda x: x['id'] == item_id, items)
        deleted_item = filtered_items[0]
        items.remove(deleted_item)

        if item_type == 'milestone':
            links = budget.get_generic_text_attr("links")
            deleted_links = filter(lambda x: x['source'] == item_id, links)
            deleted_links.extend(filter(lambda x: x['target'] == item_id, links))
            for deleted_link in deleted_links:
                links.remove(deleted_link)
            budget.set_generic_text_attr("links", links)

        budget.set_generic_text_attr(item_list_name, items)
        budget.date_updated = utc_now
        budget.updated_by = logged_in_user
    else:

        budgetentry_id, secondaryFactor_id = item_id.split('_')
        budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()
        secondaryFactor = budgetentry.get_generic_text_attr("secondaryFactor")
        secondaryFactor_id = int(secondaryFactor_id)
        secondaryFactor = secondaryFactor[:secondaryFactor_id] + secondaryFactor[secondaryFactor_id+1:]

        if len(secondaryFactor) != 0:
            budgetentry.set_generic_text_attr("secondaryFactor", secondaryFactor)
        else:
            try:
                db.DBSession.delete(budgetentry)
                transaction.commit()
            except Exception as e:
                transaction.abort()
                from stalker_pyramid.views import StdErrToHTMLConverter
                c = StdErrToHTMLConverter(e)
                transaction.abort()

    request.session.flash('success: item deleted successfully')
    return Response('milestone deleted successfully')


@view_config(
    route_name='budget_calendar_link_create'
)
def budget_calendar_link_create(request):
    """budget_calendar_link_create
    """
    logger.debug('***budget_calendar_link_create method starts ***')
    from stalker_pyramid.views import get_logged_in_user, local_to_utc
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', None)
    budget = Budget.query.filter(Budget.id == budget_id).first()
    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    source = request.params.get('source', None)
    target = request.params.get('target', '')
    type = request.params.get('type', '')
    id = request.params.get('id', '')

    links = budget.get_generic_text_attr("links")

    new_link = {
        'source': source,
        'target': target,
        'type': type,
        'id': id
    }
    if new_link not in links:
        links.append(new_link)


    budget.set_generic_text_attr("links", links)
    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    return Response('Link Created successfully')


@view_config(
    route_name='budget_calendar_task_action'
)
def budget_calendar_task_action(request):
    """budget_calendar_create_task
    """
    logger.debug('***budget_calendar_create_task method starts ***')

    from stalker_pyramid.views import get_logged_in_user, local_to_utc
    logged_in_user = get_logged_in_user(request)
    utc_now = local_to_utc(datetime.datetime.now())

    budget_id = request.matchdict.get('id', None)
    budget = Budget.query.filter(Budget.id == budget_id).first()
    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    good_id = request.params.get('good_id', None)
    good = Good.query.filter_by(id=good_id).first()

    if not good:
        transaction.abort()
        return Response('Please supply a good', 500)

    mode = request.params.get('mode', None)
    task_id = request.params.get('id', None)
    gantt_index = request.params.get('index', None)
    task_name = request.params.get('name', None)
    folder_id = request.params.get('folder_id', None)
    start_date = request.params.get('start_date', None)
    amount = request.params.get('amount', 0)
    second_amount = request.params.get('second_amount', 0)
    description = request.params.get('description', '')

    if not mode:
        transaction.abort()
        return Response('Missing parameters')

    if not amount or amount == '0':
        transaction.abort()
        return Response('Please supply the amount', 500)

    if not start_date:
        transaction.abort()
        return Response('Please supply the start date', 500)

    if not folder_id:
        transaction.abort()
        return Response('Please supply the folder_id', 500)

    if not gantt_index:
        transaction.abort()
        return Response('Please supply the gantt_index', 500)

    start_date = int(start_date)

    logger.debug("mode : %s" % mode)
    logger.debug("name : %s" % task_name)
    logger.debug("folder_id : %s" % folder_id)
    logger.debug("start_date : %s" % start_date)
    logger.debug("amount : %s" % amount)
    logger.debug("second_amount : %s" % second_amount)
    logger.debug("description : %s" % description)
    logger.debug("gantt_index : %s" % gantt_index)

    if mode == 'Create':
        if not task_name:
            transaction.abort()
            return Response('Please supply task name', 500)

        generic_data = {
            'dataSource': 'Calendar',
            'secondaryFactor': [
                {
                    'start_date': start_date,
                    'task_name': task_name,
                    'unit': good.unit.split('*')[1],
                    'amount': amount,
                    'second_amount': second_amount,
                    'folder_id':folder_id,
                    'gantt_index':gantt_index,
                    'description':description if description else " "
                }
            ],
            'overtime': 0,
            'stoppage_add': 0
        }

        create_budgetentry_action(budget,
                                  good,
                                  good.name,
                                  int(amount)*int(second_amount),
                                  good.msrp,
                                  good.cost,
                                  int(good.cost * int(amount)*int(second_amount)),
                                  description,
                                  json.dumps(generic_data),
                                  logged_in_user,
                                  utc_now)

    elif mode == 'Update':
        if not task_id:
            transaction.abort()
            return Response('Please supply task id', 500)

        budgetentry_id, secondaryFactor_id = task_id.split('_')
        budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()

        if not budgetentry:
            transaction.abort()
            return Response('There is no budgetentry with id: %s' % budgetentry_id, 500)

        budgetentry.date_updated = utc_now
        budgetentry.updated_by = logged_in_user
        index = int(secondaryFactor_id)

        secondaryFactor = budgetentry.get_generic_text_attr("secondaryFactor")
        secondaryFactor[index]['start_date'] = start_date
        secondaryFactor[index]['unit'] = good.unit.split('*')[1]
        secondaryFactor[index]['amount'] = amount
        secondaryFactor[index]['second_amount'] = second_amount
        secondaryFactor[index]['folder_id'] = folder_id
        secondaryFactor[index]['gantt_index'] = gantt_index

        if task_name:
            secondaryFactor[index]['task_name'] = task_name
        if description:
            secondaryFactor[index]['description'] = description

        budgetentry.set_generic_text_attr("secondaryFactor", secondaryFactor)
        total_amount = 0

        for fact in secondaryFactor:
            total_amount += (int(fact['amount'])*int(fact['second_amount']))

        budgetentry.amount = total_amount

        check_linked_good_budgetentries(budgetentry.good, budget)

    return Response('Task Created successfully')


def check_linked_good_budgetentries(good, budget):
    """budget_calendar_create_task
    """
    logger.debug('***check_linked_good_budgetentries method starts ***')

    linked_goods = good.get_generic_text_attr('linked_goods')
    if linked_goods:
        for l_good in linked_goods:
            linked_good = Good.query.filter(Good.id == l_good["id"]).first()
            linked_budgetentry = BudgetEntry.query.filter(BudgetEntry.budget == budget).\
                filter(BudgetEntry.good == linked_good).first()
            if linked_good and linked_budgetentry:
                related_goods = linked_good.get_generic_text_attr('related_goods')
                total_amount = 0
                for r_good in related_goods:
                    related_good = Good.query.filter(Good.id == r_good["id"]).first()
                    related_budgetentry = BudgetEntry.query.filter(BudgetEntry.budget == budget).\
                        filter(BudgetEntry.good == related_good).first()
                    if related_budgetentry:
                        total_amount += related_budgetentry.amount
                linked_budgetentry.amount = total_amount
                linked_budgetentry.price = linked_budgetentry.cost * linked_budgetentry.amount

                logger.debug("linked_budgetentry.amount %s" % linked_budgetentry.amount)
                logger.debug("linked_budgetentry %s" % linked_budgetentry.name)

