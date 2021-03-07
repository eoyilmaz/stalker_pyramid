# -*- coding: utf-8 -*-

import datetime
import json
from pyramid.view import view_config

from stalker import db, Project, Status, Budget, BudgetEntry, Good, Entity, \
    Type, Studio, StatusList
from stalker.db.session import DBSession

import transaction

from webob import Response
import stalker_pyramid
import logging
from stalker_pyramid.views import get_date

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='edit_budgetentry',
    renderer='json',
    permission='Create_BudgetEntry'
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
            return {}
            # return Response('There is no entry with id %s' % id, 500)

        if entity.entity_type == 'Good':
            logger.debug('***create budgetentry method starts ***')
            return create_budgetentry(request)

        elif entity.entity_type == 'BudgetEntry':
            logger.debug('***update budgetentry method starts ***')
            return update_budgetentry(request)

        else:
            transaction.abort()
            return {}
            # return Response(
            #     'There is no budgetentry or good with id %s' % id,
            #     status=500
            # )

    elif oper == 'del':
        logger.debug('***delete budgetentry method starts ***')
        return delete_budgetentry(request)


@view_config(
    route_name='create_budgetentry',
    renderer='json',
    permission='Create_BudgetEntry'
)
def create_budgetentry(request):
    """runs when creating a budgetentry
    """
    logger.debug('***create_budgetentry method starts ***')
    import pytz
    from stalker_pyramid.views import get_logged_in_user 
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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

    name = request.params.get('name', good.name)
    msrp = request.params.get('msrp', good.msrp)
    cost = request.params.get('cost', good.cost)
    price = request.params.get('price', 0)

    if name == '':
        name = good.name

    amount = request.params.get('amount', None)
    second_amount = request.params.get('second_amount', None)

    stoppage_add = request.params.get('stoppage_add', 'Yok')
    overtime = request.params.get('overtime', 0)
    description = request.params.get('note', '')

    logger.debug("name %s " % name)
    logger.debug("msrp %s " % msrp)
    logger.debug("cost %s " % cost)
    logger.debug("price %s " % price)
    logger.debug("amount %s " % amount)
    logger.debug("second_amount %s " % second_amount)
    logger.debug("overtime %s " % overtime)
    logger.debug("stoppage_add %s " % stoppage_add)
    logger.debug("description %s " % description)

    generic_data = {
        'dataSource': 'Producer',
        'secondaryFactor': [
            {
                'unit': good.unit.split('*')[1],
                'amount': amount,
                'second_amount': second_amount
            }
        ],
        'overtime': overtime,
        'stoppage_add': stoppage_add
    }

    if not amount or amount == '0':
        transaction.abort()
        return Response('Please supply the "Birim"', 500)

    if not second_amount or second_amount == '0':
        transaction.abort()
        return Response('Please supply the "X"', 500)

    amount = float(amount)*float(second_amount)
    if price == '0' or price == 0:
        price = good.cost * amount

    budgetentry = None

    if amount and price:
        # data that's generate from good's data

        budgetentry = create_budgetentry_action(
                                    budget,
                                    good,
                                    name,
                                    amount,
                                    float(msrp),
                                    float(cost),
                                    float(price),
                                    description,
                                    json.dumps(generic_data),
                                    logged_in_user,
                                    utc_now
        )
        budgetentry = BudgetEntry.query.filter(BudgetEntry.name == name).first()
        logger.debug("budgetentry.id %s " % budgetentry.id)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)


    return {
                'id': budgetentry.id,
                'amount': amount/float(second_amount),
                'second_amount': second_amount,
                'price': price,
                'overtime': overtime,
                'stoppage_add': stoppage_add,
                'message': 'successfully created %s budgetentry!' % name,
                'message_type': 'success',
                'message_title': 'Success'
    }
    # Response('BudgetEntry Created successfully')


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
        name=name,
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
    DBSession.add(budget_entry)

    from sqlalchemy.exc import IntegrityError
    try:
        transaction.commit()
        DBSession.add(budget_entry)
        DBSession.add(good)
        DBSession.add(budget)

    except IntegrityError as e:
        logger.debug(str(e))
        transaction.abort()
        return Response(str(e), 500)
    else:
        DBSession.flush()

    budget_entry = BudgetEntry.query.filter(BudgetEntry.name == name).first()

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

    result = DBSession.connection().execute(sql_query)
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
    route_name='update_budgetentry',
    renderer='json',
    permission='Update_BudgetEntry'
)
def update_budgetentry(request):
    """updates the BudgetEntry with data from request
    """
    logger.debug('***update_budgetentry method starts ***')
    import pytz
    from stalker_pyramid.views import get_logged_in_user 
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    budgetentry_id = request.params.get('id')
    budgetentry = BudgetEntry.query.filter_by(id=budgetentry_id).first()

    if not budgetentry:
        transaction.abort()
        return Response('There is no budgetentry with id %s' % budgetentry_id, 500)

    good_id = request.params.get('good_id', None)
    good = Good.query.filter_by(id=good_id).first()
    if not good:
        good = budgetentry.good
    # good = Good.query.filter(Good.name == budgetentry.name).first()
    # user supply this data
    name = request.params.get('name', budgetentry.name)
    msrp = request.params.get('msrp', budgetentry.msrp)
    cost = request.params.get('cost', budgetentry.cost)
    price = request.params.get('price', None)

    amount = request.params.get('amount', None)
    second_amount = request.params.get('second_amount', None)

    overtime = float(request.params.get('overtime', 0))
    stoppage_add = request.params.get('stoppage_add', 0)

    description = request.params.get('note', '')

    logger.debug("name %s " % name)
    logger.debug("msrp %s " % msrp)
    logger.debug("cost %s " % cost)
    logger.debug("price %s " % price)
    logger.debug("amount %s " % amount)
    logger.debug("second_amount %s " % second_amount)
    logger.debug("overtime %s " % overtime)
    logger.debug("stoppage_add %s " % stoppage_add)
    logger.debug("description %s " % description)

    if not price:
        transaction.abort()
        return Response('Please supply price', 500)

    price = float(price)

    logger.debug("budgetentry.generic_text: %s" % budgetentry.generic_text)

    second_amount = float(second_amount)

    if budgetentry.get_generic_text_attr('dataSource') == 'Calendar':

        budgetentry.price = price
        budgetentry.description = description
        budgetentry.date_updated = utc_now
        budgetentry.updated_by = logged_in_user

        secondaryFactors = budgetentry.get_generic_text_attr("secondaryFactor")
        second_amount = 0

        if secondaryFactors:
            for secondaryFactor in secondaryFactors:
                if 'second_amount' in secondaryFactor:
                    second_amount += float(secondaryFactor["second_amount"])
        amount = budgetentry.amount/second_amount
        message = 'Warning: This entry is added from calendarr. So you can only change the price  of %s(%s)!'
        message_type = 'warning'
        message_title = 'Warning'
    else:

        if second_amount == '0' or amount == '0':
            return delete_budgetentry_action(budgetentry)

        budgetentry.amount = float(amount)*second_amount
        budgetentry.name = name
        budgetentry.msrp = float(msrp)
        budgetentry.cost = float(cost)
        budgetentry.good = good

        budgetentry.price = price if price != '0' else budgetentry.cost * (budgetentry.amount + overtime)
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

        message = 'successfully updated %s(%s) budgetentry!'
        message_type = 'success'
        message_title = 'Success'

        request.session.flash(
            'success:updated %s budgetentry!' % budgetentry.name
        )

    budgetentry.set_generic_text_attr("overtime", overtime)
    budgetentry.set_generic_text_attr("stoppage_add", stoppage_add)
    check_linked_good_budgetentries(budgetentry.good, budgetentry.budget)

    return {
            'id': budgetentry.id,
            'amount': amount,
            'second_amount': second_amount,
            'overtime': overtime,
            'stoppage_add': stoppage_add,
            'price': budgetentry.price,
            'message': message % (budgetentry.name, budgetentry.id),
            'message_type':message_type,
            'message_title':message_title
    }


@view_config(
    route_name='delete_budgetentry_dialog',
    renderer='templates/modals/confirm_dialog.jinja2',
    permission='Delete_BudgetEntry'
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
    route_name='delete_budgetentry',
    renderer='json',
    permission='Delete_BudgetEntry'
)
def delete_budgetentry(request):
    """deletes the budgetentry
    """
    logger.debug('delete_budgetentry is starts')

    dataSource = request.params.get('dataSource', None)
    good_id = None
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
    good_id = budgetentry.good.id
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
                DBSession.delete(budgetentry)
                transaction.commit()
            except Exception as e:
                transaction.abort()
                c = StdErrToHTMLConverter(e)
                transaction.abort()
                # return Response(c.html(), 500)
    else:
        try:
            DBSession.delete(budgetentry)
            transaction.commit()
        except Exception as e:
            transaction.abort()
            c = StdErrToHTMLConverter(e)
            transaction.abort()
            # return Response(c.html(), 500)
    return {
            'id': good_id,
            'amount': 0,
            'second_amount': 0,
            'overtime': 0,
            'stoppage_add': 'Yok',
            'price': 0,
            'message': 'successfully deleted %s!' % (budgetentry_name),
            'message_type': 'success',
            'message_title': 'Success'
        }
    # return Response('Successfully deleted budgetentry with name %s' % budgetentry_name)


def delete_budgetentry_action(budgetentry):

    logger.debug('delete_budgetentry_action %s' % budgetentry.name)
    budgetentry_name = budgetentry.name
    good_id = budgetentry.good.id
    try:
        DBSession.delete(budgetentry)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        from stalker_pyramid.views import StdErrToHTMLConverter
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        # return Response(c.html(), 500)
    logger.debug("delete_budgetentry_action good_id %s " % good_id)
    return {
            'id': good_id,
            'amount': 0,
            'second_amount': 0,
            'overtime': 0,
            'stoppage_add': 'Yok',
            'price': 0,
            'message': 'successfully deleted %s!' % (budgetentry_name),
            'message_type': 'success',
            'message_title': 'Success'
        }


@view_config(
    route_name='get_budget_calendar_items',
    renderer='json',
    permission='List_BudgetEntry'
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
    renderer='json',
    permission='List_BudgetEntry'
)
def get_budget_entries(request):
    """returns budgets with the given id
    """
    logger.debug("get_budget_entries starts")
    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget with id : %s' % budget_id, 500)

    logger.debug('get_budget_entries is working for the budget which id is: %s' % budget_id)

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
           "Goods_SimpleEntities".id,
           pricelists.id as type_id,
           "GoodTypes_SimpleEntities".name
        from "BudgetEntries"
        join "SimpleEntities" as "BudgetEntries_SimpleEntities" on "BudgetEntries_SimpleEntities".id = "BudgetEntries".id
        join "SimpleEntities" as "Types_SimpleEntities" on "Types_SimpleEntities".id = "BudgetEntries_SimpleEntities".type_id
        join (
                select "PriceList_SimpleEntities".id as id,
                "PriceList_SimpleEntities".name as name
                from "PriceLists"
                join "SimpleEntities" as "PriceList_SimpleEntities" on "PriceList_SimpleEntities".id = "PriceLists".id
        ) as pricelists on pricelists.name = "Types_SimpleEntities".name
        join "Budgets" on "Budgets".id = "BudgetEntries".budget_id
        join "Goods" on "BudgetEntries".good_id = "Goods".id
        join "SimpleEntities" as "Goods_SimpleEntities" on "Goods_SimpleEntities".id = "Goods".id
        left outer join "SimpleEntities" as "GoodTypes_SimpleEntities" on "GoodTypes_SimpleEntities".id = "Goods_SimpleEntities".type_id

        where "Budgets".id = %(budget_id)s
    """

    sql_query = sql_query % {'budget_id': budget_id}

    result = DBSession.connection().execute(sql_query)
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
            'good_id': r[12],
            'type_id': r[13],
            'good_type':r[14]
        }
        for r in result.fetchall()
    ]
    logger.debug("get_budget_entries ends %s" % len(entries))
    resp = Response(
        json_body=entries
    )

    return resp


@view_config(
    route_name='budgetentry_dialog',
    renderer='templates/budget/dialog/budgetentry_dialog.jinja2',
    permission='Create_BudgetEntry'
)
def budgetentry_dialog(request):
    """called when creating and updating budget entry
    """
    came_from = request.params.get('came_from', '/')

    # get logged in user
    from stalker_pyramid.views import (get_logged_in_user, PermissionChecker,
                                       milliseconds_since_epoch)
    logged_in_user = get_logged_in_user(request)


    mode = request.matchdict.get('mode', None)
    if not mode:
        mode = request.params.get('mode', None)

    budgetentry_id = request.matchdict.get('id', -1)
    budgetentry = BudgetEntry.query.filter(BudgetEntry.id == budgetentry_id).first()

    budget_id = request.params.get('budget_id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    if budgetentry:
        action = "/budgetentries/update?id=%s&budget_id=%s" % (budgetentry.id, budget_id)
    else:
        action = "/budgetentries/create?budget_id=%s" % budget_id

    if not budget:
        return Response('No budget found with id: %s' % budget_id, 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'budget': budget,
        'budgetentry': budgetentry,
        'action': action,
        'came_from': came_from,
        'mode': mode,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='budget_calendar_task_dialog',
    renderer='templates/budget/dialog/budget_calendar_item_dialog.jinja2',
    permission='Create_BudgetEntry'
)
@view_config(
    route_name='budget_calendar_folder_dialog',
    renderer='templates/budget/dialog/budget_calendar_item_dialog.jinja2',
    permission='Create_BudgetEntry'
)
@view_config(
    route_name='budget_calendar_milestone_dialog',
    renderer='templates/budget/dialog/budget_calendar_item_dialog.jinja2',
    permission='Create_BudgetEntry'
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
    route_name='budget_calendar_list_order',
    permission='Update_BudgetEntry'
)
def budget_calendar_list_order(request):
    """budget_calendar_list_order
    """
    logger.debug('budget_calendar_list_order method starts')

    import pytz
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
            secondaryFactor[index]['folder_id'] = item['folder_id']
            budgetentry.set_generic_text_attr("secondaryFactor", secondaryFactor)
            budgetentry.date_updated = utc_now
            budgetentry.updated_by = logged_in_user

    budget.set_generic_text_attr('folders', folders)
    budget.set_generic_text_attr('milestones', milestones)
    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    return Response('BudgetEntry Created successfully')


@view_config(
    route_name='budget_calendar_item_action',
    permission='Update_BudgetEntry'
)
def budget_calendar_item_action(request):
    """budget_calendar_item_action
    """
    logger.debug('budget_calendar_item_action method starts')

    import pytz
    from stalker_pyramid.views import get_logged_in_user 
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
    route_name='budget_calendar_item_delete',
    permission='Delete_BudgetEntry'
)
def budget_calendar_item_delete(request):
    """budget_calendar_folder_delete
    """
    logger.debug('***budget_calendar_folder_delete method starts ***')
    import pytz
    from stalker_pyramid.views import get_logged_in_user 
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
                DBSession.delete(budgetentry)
                transaction.commit()
            except Exception as e:
                transaction.abort()
                from stalker_pyramid.views import StdErrToHTMLConverter
                c = StdErrToHTMLConverter(e)
                transaction.abort()

    request.session.flash('success: item deleted successfully')
    return Response('milestone deleted successfully')


@view_config(
    route_name='budget_calendar_link_create',
    permission='Update_BudgetEntry'
)
def budget_calendar_link_create(request):
    """budget_calendar_link_create
    """
    logger.debug('***budget_calendar_link_create method starts ***')
    import pytz
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
    route_name='budget_calendar_task_action',
    permission='Create_BudgetEntry'
)
def budget_calendar_task_action(request):
    """budget_calendar_create_task
    """
    logger.debug('***budget_calendar_create_task method starts ***')

    import pytz
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
                                  float(amount)*float(second_amount),
                                  good.msrp,
                                  good.cost,
                                  float(good.cost * float(amount)*float(second_amount)),
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
            total_amount += (float(fact['amount'])*float(fact['second_amount']))

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

