# -*- coding: utf-8 -*-

import pytz
import datetime
import json
from pyramid.view import view_config

from stalker import db, Project, Status, Entity, Invoice, Budget, Client, Payment
from stalker.db.session import DBSession

import transaction

from webob import Response
import stalker_pyramid

import logging
#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='create_invoice_dialog',
    renderer='templates/invoice/dialog/invoice_dialog.jinja2'
)
def create_invoice_dialog(request):
    """called when creating invoice
    """

    logger.debug(
        'create_invoice_dialog'
    )
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    from stalker_pyramid.views import get_logged_in_user,\
        milliseconds_since_epoch
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
    route_name='create_invoice'
)
def create_invoice(request):
    """runs when creating a invoice
    """
    from stalker_pyramid.views import get_logged_in_user, milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)


    description = request.params.get('description')

    amount = request.params.get('amount')
    unit = request.params.get('unit')

    budget_id = request.params.get('budget_id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    client_id = request.params.get('client_id', -1)
    client = Client.query.filter(Client.id == client_id).first()

    logger.debug("client %s" % client.id)

    if not client:
        return Response('Please supply a client', 500)

    if not description:
        return Response('Please supply a description', 500)

    if not budget:
        return Response('There is no budget with id: %s' % budget_id, 500)

    invoice = Invoice(
        budget=budget,
        client=client,
        amount=int(amount),
        unit=unit,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now
    )
    DBSession.add(invoice)

    return Response('Invoice Created successfully')

@view_config(
    route_name='create_invoice_dialog',
    renderer='templates/invoice/dialog/invoice_dialog.jinja2'
)
def create_invoice_dialog(request):
    """called when creating invoice
    """

    logger.debug(
        'create_invoice_dialog'
    )
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    from stalker_pyramid.views import get_logged_in_user,\
        milliseconds_since_epoch
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
    route_name='create_payment_dialog',
    renderer='templates/invoice/dialog/payment_dialog.jinja2'
)
def create_payment_dialog(request):
    """called when creating invoice
    """

    logger.debug(
        'create_payment_dialog'
    )
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    from stalker_pyramid.views import get_logged_in_user,\
        milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)

    invoice_id = request.params.get('invoice_id', -1)
    invoice = Invoice.query.filter(Invoice.id == invoice_id).first()

    if not invoice:
        return Response('No invoice found with id: %s' % invoice_id, 500)

    from stalker_pyramid.views.auth import PermissionChecker
    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'invoice': invoice,
        'came_from': came_from,
        'mode': 'Create',
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_payment'
)
def create_payment(request):
    """runs when creating a payment
    """
    from stalker_pyramid.views import get_logged_in_user, milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    description = request.params.get('description')

    amount = request.params.get('amount')
    unit = request.params.get('unit')

    invoice_id = request.params.get('invoice_id', -1)
    invoice = Invoice.query.filter(Invoice.id == invoice_id).first()

    if not invoice:
        return Response('Please supply a invoice', 500)

    if not description:
        return Response('Please supply a description', 500)


    payment = Payment(
        invoice=invoice,
        amount=int(amount),
        unit=unit,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now
    )
    DBSession.add(invoice)

    return Response('Invoice Created successfully')

@view_config(
    route_name='update_payment'
)
def update_payment(request):
    """edits the edit_payment with data from request
    """
    logger.debug('***edit edit_payment method starts ***')
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    payment_id = request.params.get('id')
    payment = Payment.query.filter_by(id=payment_id).first()

    if not payment:
        transaction.abort()
        return Response('There is no payment with id %s' % id, 500)

    amount = request.params.get('amount', None)
    unit = request.params.get('unit', None)
    description = request.params.get('description', None)
    if amount and unit and description:
        payment.amount = int(amount)
        payment.unit = unit
        payment.description = description
        payment.date_updated = utc_now
        payment.updated_by = logged_in_user

    request.session.flash(
        'success:updated %s payment!' % payment.id
    )
    return Response('successfully updated %s payment!' % payment.id)




@view_config(
    route_name='list_payment_dialog',
    renderer='templates/invoice/dialog/list_payment_dialog.jinja2'
)
def list_payment_dialog(request):
    """called when creating invoice
    """

    logger.debug(
        'list_payment_dialog'
    )
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    from stalker_pyramid.views import get_logged_in_user,\
        milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)

    invoice_id = request.params.get('invoice_id', -1)
    invoice = Invoice.query.filter(Invoice.id == invoice_id).first()

    if not invoice:
        return Response('No invoice found with id: %s' % invoice_id, 500)

    from stalker_pyramid.views.auth import PermissionChecker
    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'invoice': invoice,
        'came_from': came_from,
        'mode': 'Update',
        'milliseconds_since_epoch': milliseconds_since_epoch
    }

@view_config(
    route_name='get_entity_invoices',
    renderer='json'
)
@view_config(
    route_name='get_budget_invoices',
    renderer='json'
)
def get_invoices(request):
    """returns invoices with the given id
    """

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter(Entity.id == entity_id).first()
    logger.debug(
        'get_invoices is working for the entity which id is: %s' % entity_id
    )

    sql_query = """
        select
            "Invoices".id,
            "Invoice_SimpleEntities".name,
            "Invoices".amount,
            "Invoices".unit,
            "Invoice_SimpleEntities".description,
            (extract(epoch from "Invoice_SimpleEntities".date_created) * 1000)::bigint as date_created,
            "Clients".id,
            "Client_SimpleEntities".name,
            array_agg("Payments".amount::float/"Invoices".amount*100),
            sum("Payments".amount)::float/"Invoices".amount *100 as percent


        from "Invoices"
        join "SimpleEntities" as "Invoice_SimpleEntities" on "Invoice_SimpleEntities".id = "Invoices".id
        join "Budgets" on "Budgets".id = "Invoices".budget_id
        join "Projects" on "Projects".id = "Budgets".project_id
        join "Clients" on "Clients".id = "Invoices".client_id
        join "SimpleEntities" as "Client_SimpleEntities" on "Client_SimpleEntities".id = "Clients".id
        left outer join "Payments" on "Payments".invoice_id = "Invoices".id
        where %(where_condition)s
        group by
            "Invoices".id,
            "Invoice_SimpleEntities".name,
            "Invoices".amount,
            "Invoices".unit,
            "Invoice_SimpleEntities".description,
            "Invoice_SimpleEntities".date_created,
            "Clients".id,
            "Client_SimpleEntities".name
    """

    where_condition = ''
    if entity.entity_type == "Budget":
        where_condition = '"Budgets".id=%s' % entity.id

    if entity.entity_type == "Project":
        where_condition = '"Projects".id=%s' % entity.id

    invoices = []

    sql_query = sql_query % {
        'where_condition': where_condition
    }

    from stalker_pyramid.views.auth import PermissionChecker
    result = DBSession.connection().execute(sql_query)
    update_budget_permission = \
        PermissionChecker(request)('Update_Budget')

    for r in result.fetchall():
        invoice = {
            'id': r[0],
            'name': r[1],
            'amount': r[2],
            'unit': r[3],
            'description': r[4],
            'date_created': r[5],
            'client_id': r[6],
            'client_name': r[7],
            'payments': r[8],
            'percent': r[9]
        }
        # if update_budget_permission:
        invoice['item_view_link'] = \
            '/invoices/%s/view' % invoice['id']

        invoice['item_update_link'] = \
            '/invoices/%s/update/dialog' % invoice['id']
        invoice['item_remove_link'] =\
            '/entities/%s/delete/dialog?came_from=%s' % (
                invoice['id'],
                request.current_route_path()
            )
        invoice['item_duplicate_link'] =\
            '/invoices/%s/duplicate/dialog?came_from=%s' % (
                invoice['id'],
                request.current_route_path()
            )

        invoices.append(invoice)

    resp = Response(
        json_body=invoices
    )

    return resp


@view_config(
    route_name='get_entity_invoices_count',
    renderer='json'
)
@view_config(
    route_name='get_budget_invoices_count',
    renderer='json'
)
def get_invoices_count(request):
    """missing docstring
    """
    budget_id = request.matchdict.get('id')
    logger.debug(
        'get_invoices_count is working for the budget which id is %s' %
        budget_id
    )

    sql_query = """
        select count(1) from (
            select
                "Invoices".id
            from "Invoices"
            join "Budgets" on "Budgets".id = "Invoices".budget_id

            where "Budgets".id = %(budget_id)s
        ) as data
    """
    sql_query = sql_query % {'budget_id': budget_id}

    from sqlalchemy import text  # to be able to use "%" sign use this function
    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]


@view_config(
    route_name='get_invoice_payments',
    renderer='json'
)
def get_payments(request):
    """returns payments with the given id
    """

    entity_id = request.matchdict.get('id')
    entity = Entity.query.filter(Entity.id == entity_id).first()
    logger.debug(
        'get_payments is working for the entity which id is: %s' % entity_id
    )

    sql_query = """
        select
            "Payments".id,
            "Payments".amount,
            "Payments".unit,
            "Payment_SimpleEntities".description,
            (extract(epoch from "Payment_SimpleEntities".date_created) * 1000)::bigint as date_created

        from "Payments"
        join "SimpleEntities" as "Payment_SimpleEntities" on "Payment_SimpleEntities".id = "Payments".id
        join "Invoices" on "Invoices".id = "Payments".invoice_id

        where %(where_condition)s
    """

    where_condition = ''
    if entity.entity_type == "Invoice":
        where_condition = '"Invoices".id=%s' % entity.id

    payments = []

    sql_query = sql_query % {
        'where_condition': where_condition
    }

    from stalker_pyramid.views.auth import PermissionChecker
    result = DBSession.connection().execute(sql_query)
    update_budget_permission = \
        PermissionChecker(request)('Update_Budget')

    for r in result.fetchall():
        payment = {
                'id': r[0],
                'amount': r[1],
                'unit': r[2],
                'description': r[3],
                'date_created': r[4]
        }
        # if update_budget_permission:
        payment['item_update_link'] = \
            '/invoices/%s/update/dialog' % payment['id']
        payment['item_remove_link'] =\
            '/entities/%s/delete/dialog?came_from=%s' % (
                payment['id'],
                request.current_route_path()
            )
        payment['item_duplicate_link'] =\
            '/invoices/%s/duplicate/dialog?came_from=%s' % (
                payment['id'],
                request.current_route_path()
            )

        payments.append(payment)

    resp = Response(
        json_body=payments
    )

    return resp
