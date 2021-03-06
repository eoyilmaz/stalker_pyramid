# -*- coding: utf-8 -*-
import pytz
import datetime
import json
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.response import Response

from stalker import (defaults, Good, Project, Studio, PriceList)
from stalker.db.session import DBSession
from stalker_pyramid.views import update_generic_text
import transaction

from stalker_pyramid.views import (log_param, get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch,
                                   StdErrToHTMLConverter)

import logging
from stalker_pyramid.views.type import query_type

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


def query_price_list(price_list_name):
    """returns a Type instance either it creates a new one or gets it from DB
    """
    if not price_list_name:
        return None

    price_list_ = PriceList.query.filter_by(name=price_list_name).first()

    if price_list_name and price_list_ is None:
        # create a new PriceList
        logger.debug('creating new price_list: %s' % (
            price_list_name)
        )
        price_list_ = PriceList(
            name=price_list_name
        )
        DBSession.add(price_list_)

    return price_list_


@view_config(
    route_name='get_studio_price_lists',
    renderer='json',
    permission='List_PriceList'
)
@view_config(
    route_name='get_price_lists',
    renderer='json',
    permission='List_PriceList'
)
def get_price_list(request):
    """
        give all define price_list in a list
    """
    logger.debug('***get_price_list method starts ***')

    return [
        {
            'id': priceList.id,
            'name': priceList.name

        }
        for priceList in PriceList.query.order_by(PriceList.name.asc()).all()
    ]


@view_config(
    route_name='get_studio_goods',
    renderer='json',
    permission='List_Good'

)
@view_config(
    route_name='get_goods',
    renderer='json',
    permission='List_Good'
)
def get_goods(request):
    """
        give all define goods in a list
    """
    logger.debug('***get_studio_goods method starts ***')

    goods = Good.query.order_by(Good.name.asc()).all()

    return_data = []
    for good in goods:

        related_goods = []
        linked_goods = []
        stopage_ratio = 0
        if good.generic_text != "":
            generic_data = json.loads(good.generic_text)
            if "related_goods" in generic_data:
                related_goods = generic_data["related_goods"]
            if "linked_goods" in generic_data:
                linked_goods = generic_data["linked_goods"]
            if "stopage_ratio" in generic_data:
                stopage_ratio = generic_data["stopage_ratio"]

        return_data.append({
            'id': good.id,
            'name': good.name,
            'cost': good.cost,
            'msrp': good.msrp,
            'unit': good.unit,
            'created_by_id': good.created_by_id,
            'created_by_name': good.created_by.name,
            'updated_by_id': good.updated_by_id if good.updated_by else None,
            'updated_by_name': good.updated_by.name if good.updated_by else None,
            'date_updated': milliseconds_since_epoch(good.date_updated),
            'price_list_name': good.price_lists[0].name if good.price_lists else None,
            'price_list_id': good.price_lists[0].id if good.price_lists else None,
            'type_name': good.type.name if good.type else None,
            'related_goods': related_goods,
            'linked_goods': linked_goods,
            'stopage_ratio': stopage_ratio
        })

    return return_data


@view_config(
    route_name='get_goods_names',
    renderer='json'
)
def get_goods_names(request):
    """
        give all define goods name in a list
    """
    logger.debug('***get_studio_goods method starts ***')

    goods = Good.query.order_by(Good.name.asc()).all()

    return_data = []
    for good in goods:

        return_data.append({
            'id': good.id,
            'name': good.name
        })

    return return_data


@view_config(
    route_name='get_good_related_goods',
    renderer='json',
    permission='List_Good'
)
def get_good_related_goods(request):
    """
        give all define goods in a list
    """
    logger.debug('***get_studio_goods method starts ***')

    good_id = request.matchdict.get('id', -1)
    good = Good.query.filter(Good.id == good_id).first()

    related_goods = []
    if good.generic_text != "":
        generic_data = json.loads(good.generic_text)
        if generic_data.has_key("related_goods"):
            related_goods = generic_data["related_goods"]

    return related_goods


@view_config(
    route_name='create_good_dialog',
    renderer='templates/good/dialog/create_good_dialog.jinja2',
    permission='Create_Good'
)
def create_good_dialog(request):
    """ calls create good dialog with necessary info.
    """
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    if not studio:
        transaction.abort()
        return Response("There is no Studio instance\n"
                        "Please create a studio first", 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'studio': studio,
        'came_from': came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_good',
    permission='Create_Good'
)
def create_good(request):
    """creates a new Good
    """

    logger.debug('***create good method starts ***')

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    came_from = request.params.get('came_from', '/')
    name = request.params.get('name', None)
    msrp = request.params.get('msrp', None)
    unit = request.params.get('unit', None)
    cost = request.params.get('cost', None)
    price_list_name = request.params.get('price_list_name', None)
    type_name = request.params.get('type_name', None)
    stopage_ratio = request.params.get('stopage_ratio', None)

    logger.debug('came_from : %s' % came_from)
    logger.debug('name : %s' % name)
    logger.debug('msrp : %s' % msrp)
    logger.debug('unit : %s' % unit)
    logger.debug('cost : %s' % cost)
    logger.debug('price_list_name : %s' % price_list_name)
    logger.debug('stopage_ratio : %s' % stopage_ratio)
    logger.debug('type_name : %s' % type_name)

    # create and add a new good
    if name and msrp and unit and cost and price_list_name and stopage_ratio and type_name:
        good_type = query_type('Good', type_name)
        price_list = query_price_list(price_list_name)
        try:
            # create the new group
            new_good = Good(
                name=name,
                msrp=int(msrp),
                unit=unit,
                cost=int(cost),
                type=good_type,
                price_lists=[price_list],
                generic_text=json.dumps({'stopage_ratio': stopage_ratio})
            )

            new_good.created_by = logged_in_user
            new_good.date_created = utc_now
            new_good.date_updated = utc_now
            new_good.price_lists = [price_list]

            DBSession.add(new_good)

            logger.debug('added new good successfully')

            request.session.flash(
                'success:Good <strong>%s</strong> is '
                'created successfully' % name
            )

            logger.debug('***create good method ends ***')

        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)
    else:
        logger.debug('not all parameters are in request.params')
        transaction.abort()
        return Response(
            'There are missing parameters: '
            'name: %s' % name, 500
        )

    return Response('successfully created %s!' % name)


@view_config(
    route_name='edit_good',
    permission='Create_Good'
)
def edit_good(request):
    """edits the good with data from request
    """
    logger.debug('***edit good method starts ***')
    oper = request.params.get('oper', None)

    if oper == 'edit':
        return update_good(request)
    elif oper == 'del':
        return delete_good(request)


@view_config(
    route_name='update_good',
    permission='Update_Good'
)
def update_good(request):
    """updates the good with data from request
    """

    logger.debug('***update good method starts ***')

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    good_id = request.params.get('id')
    good = Good.query.filter_by(id=good_id).first()

    if not good:
        transaction.abort()
        return Response('There is no good with id: %s' % good_id, 500)

    name = request.params.get('name', None)
    msrp = request.params.get('msrp', None)
    unit = request.params.get('unit', None)
    cost = request.params.get('cost', None)
    price_list_name = request.params.get('price_list_name', None)
    type_name = request.params.get('type_name', None)
    stopage_ratio = request.params.get('stopage_ratio', None)

    logger.debug('name : %s' % name)
    logger.debug('msrp : %s' % msrp)
    logger.debug('unit : %s' % unit)
    logger.debug('cost : %s' % cost)

    if name and msrp and unit and cost and stopage_ratio and type_name:
        good_type = query_type('Good', type_name)
        price_list = query_price_list(price_list_name)

        good.name = name
        good.msrp = int(msrp)
        good.unit = unit
        good.cost = int(cost)
        good.price_lists = [price_list]
        good.type = good_type
        good.updated_by = logged_in_user
        good.date_updated = utc_now

        good.set_generic_text_attr('stopage_ratio', stopage_ratio)

        DBSession.add(good)

        logger.debug('good is updated successfully')

        request.session.flash(
                'success:Good <strong>%s</strong> is updated successfully' % name
        )

        logger.debug('***update group method ends ***')
    else:
        logger.debug('not all parameters are in request.params')

        response = Response(
            'There are missing parameters: ', 500
        )
        transaction.abort()
        return response

    response = Response('successfully updated %s good!' % name)
    return response


@view_config(
    route_name='delete_good',
    permission='Delete_Good'
)
def delete_good(request):
    """deletes the good with data from request
    """

    logger.debug('***delete good method starts ***')

    good_id = request.params.get('id')
    good = Good.query.filter_by(id=good_id).first()

    if not good:
        transaction.abort()
        return Response('There is no good with id: %s' % good_id, 500)

    good_name = good.name
    try:
        DBSession.delete(good)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted good with name %s' % good_name)


@view_config(
    route_name='update_good_relation_dialog',
    renderer='templates/good/dialog/update_good_relation_dialog.jinja2',
    permission='Update_Good'
)
def update_good_relation_dialog(request):
    """ calls create good dialog with necessary info.
    """
    # get logged in user
    logged_in_user = get_logged_in_user(request)

    good_id = request.matchdict.get('id', -1)
    good = Good.query.filter(Good.id == good_id).first()

    if not good:
        transaction.abort()
        return Response("There is no good instance", 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'good': good,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }

@view_config(
    route_name='update_good_relation',
    permission='Update_Good'
)
def update_good_relation(request):
    """updates the good with data from request
    """

    logger.debug('***update_good_relation method starts ***')

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    good_id = request.matchdict.get('id')
    good = Good.query.filter_by(id=good_id).first()

    if not good:
        transaction.abort()
        return Response('There is no good with id: %s' % good_id, 500)

    related_good_id = request.params.get('related_good_id', None)
    related_good = Good.query.filter_by(id=related_good_id).first()

    ratio = request.params.get('ratio', None)

    logger.debug('related_good_id : %s' % related_good_id)
    logger.debug('ratio : %s' % ratio)

    if related_good and ratio:

        good.generic_text = update_generic_text(good.generic_text,
                                                 "related_goods",
                                                 {
                                                    'id': related_good.id,
                                                    'name': related_good.name,
                                                    'ratio': ratio
                                                 },
                                                 'add')
        good.updated_by = logged_in_user
        good.date_updated = utc_now

        related_good.generic_text = update_generic_text(related_good.generic_text,
                                                             "linked_goods",
                                                             {
                                                                'id': good.id,
                                                                'name': good.name,
                                                                'ratio': ratio
                                                             },
                                                             'add')
        related_good.updated_by = logged_in_user
        related_good.date_updated = utc_now


    else:
        logger.debug('not all parameters are in request.params')

        response = Response(
            'There are missing parameters: '
            'good_id: %s, name: %s' % (related_good_id, ratio), 500
        )
        transaction.abort()
        return response

    response = Response('successfully updated %s good!' % good.name)
    return response


@view_config(
    route_name='delete_good_relation_dialog',
    renderer='templates/modals/confirm_dialog.jinja2',
    permission='Update_Good'
)
def delete_good_relation_dialog(request):
    """works when task has at least one answered review
    """
    logger.debug('delete_good_relation_dialog is starts')

    good_id = request.matchdict.get('id')
    good = Good.query.filter_by(id=good_id).first()

    related_good_id = request.params.get('related_good_id')
    related_good = Good.query.filter_by(id=related_good_id).first()

    action = '/goods/%s/delete/relation?related_good_id=%s' % (good_id, related_good_id)
    came_from = request.params.get('came_from', '/')

    message = '%s will be removed from %s related good list' \
              '<br><br>Are you sure?' % (related_good.name, good.name)

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='delete_good_relation',
    permission='Update_Good'
)
def delete_good_relation(request):
    """delete_good_relation data from request
    """

    logger.debug('***delete_good_relation method starts ***')

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    good_id = request.matchdict.get('id')
    good = Good.query.filter_by(id=good_id).first()

    if not good:
        transaction.abort()
        return Response('There is no good with id: %s' % good_id, 500)

    related_good_id = request.params.get('related_good_id', None)
    related_good = Good.query.filter_by(id=related_good_id).first()

    logger.debug('related_good_id : %s' % related_good_id)

    if related_good:

        good.generic_text = update_generic_text(good.generic_text,
                                                     "related_goods",
                                                     {
                                                        'id': related_good.id
                                                     },
                                                     'remove')

        good.updated_by = logged_in_user
        good.date_updated = utc_now

        related_good.generic_text = update_generic_text(related_good.generic_text,
                                                             "linked_goods",
                                                             {
                                                                'id': good.id
                                                             },
                                                             'remove')
        related_good.updated_by = logged_in_user
        related_good.date_updated = utc_now

    else:
        logger.debug('not all parameters are in request.params')

        response = Response(
            'There are missing parameters: '
            'related_good_id: %s' % (related_good_id), 500
        )
        transaction.abort()
        return response

    response = Response('successfully updated %s good!' % good.name)
    return response
