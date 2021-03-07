# -*- coding: utf-8 -*-

import pytz
import datetime
import json
from pyramid.view import view_config

from stalker import db, Project, Status, Budget, BudgetEntry, Good, Entity, \
    Type, Studio, StatusList, Task
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
    route_name='create_budget_dialog',
    renderer='templates/budget/dialog/create_budget_dialog.jinja2',
    permission='Create_Budget'
)
def create_budget_dialog(request):
    """called when creating budget
    """
    came_from = request.params.get('came_from', '/')
    # logger.debug('came_from %s: '% came_from)

    # get logged in user
    from stalker_pyramid.views import get_logged_in_user,\
        milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)

    project_id = request.params.get('project_id', -1)
    project = Project.query.filter(Project.id == project_id).first()

    if not project:
        return Response('No project found with id: %s' % project_id, 500)

    from stalker_pyramid.views.auth import PermissionChecker
    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'project': project,
        'came_from': came_from,
        'mode': 'Create',
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_budget',
    permission='Create_Budget'
)
def create_budget(request):
    """runs when creating a budget
    """
    from stalker_pyramid.views import get_logged_in_user, milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    project_id = request.params.get('project_id', None)
    project = Project.query.filter(Project.id == project_id).first()

    if not project:
        return Response('There is no project with id: %s' % project_id, 500)

    name = request.params.get('name', None)
    type_id = request.params.get('type_id', None)
    type_ = Type.query.filter(Type.id == type_id).first()
    description = request.params.get('description', "")

    logger.debug("type_id : %s" % type_id)
    logger.debug("name : %s" % name)
    logger.debug("description : %s" % description)

    if not name:
        return Response('Please supply a name', 500)

    if not type_:
        return Response('There is no type with id: %s' % type_id, 500)


    status = Status.query.filter(Status.name == 'Planning').first()

    generic_data = {
            'approved_total_price': 0,
            'total_price': 0,
            'total_msrp': 0,
            'total_cost': 0,
            'realized_total_price': 0,
            'milestones': [],
            'folders': [],
            'links': [],
            'calendar_editing': 'OFF',
            'start_date': milliseconds_since_epoch(project.start),
            'end_date': milliseconds_since_epoch(project.end),
            'related_budgets': []
    }

    budget = Budget(
        project=project,
        name=name,
        type=type_,
        status=status,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        generic_text=json.dumps(generic_data)
    )
    DBSession.add(budget)
    transaction.commit()
    budget = Budget.query.filter(Budget.name == name).first()
    new_budget_id = budget.id

    # related_budgets = budget.get_generic_text_attr('related_budgets')
    # related_budgets.append(budget.id)
    # budget.set_generic_text_attr('related_budgets', related_budgets)

    return Response("/budgets/%s/view" % new_budget_id)


@view_config(
    route_name='update_budget_dialog',
    renderer='templates/budget/dialog/update_budget_dialog.jinja2',
    permission='Update_Budget'
)
def update_budget_dialog(request):
    """called when updating dailies
    """
    from stalker_pyramid.views import get_logged_in_user,\
        milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)
    came_from = request.params.get('came_from', '/')

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    studio = Studio.query.first()

    from stalker_pyramid.views.auth import PermissionChecker
    return {
        'mode': 'Update',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': budget,
        'came_from': came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch,
    }


@view_config(
    route_name='update_budget',
    permission='Update_Budget'
)
def update_budget(request):
    """runs when updating a budget
    """
    logger.debug("update_budget starts")

    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    if not budget:
        transaction.abort()
        return Response('No budget with id : %s' % budget_id, 500)

    name = request.params.get('name', None)
    type_id = request.params.get('type_id', -1)
    type_ = Type.query.filter(Type.id == type_id).first()
    start_date = request.params.get('start_date', None)
    end_date = request.params.get('end_date', None)
    description = request.params.get('description', " ")


    logger.debug("type_id : %s" % type_id)
    logger.debug("name : %s" % name)
    logger.debug("description : %s" % description)
    logger.debug("start_date : %s" % start_date)
    logger.debug("end_date : %s" % end_date)

    if not name:
        return Response('Please supply a name', 500)

    if not type_:
        return Response('There is no type with id: %s' % type_id, 500)

    if not start_date:
        return Response('Please supply a start_date', 500)

    if not end_date:
        return Response('Please supply a end_date', 500)

    budget.name = name
    budget.description = description
    budget.type = type_

    # related_budgets = budget.get_generic_text_attr('related_budgets')
    #
    # if not related_budgets:
    #     data = json.loads(budget.generic_text)
    #     data['related_budgets'] = []
    #     budget.generic_text = json.dumps(data)
    #
    # logger.debug("related :  %s" % budget.get_generic_text_attr('related_budgets'))

    time_delta = int(start_date) - budget.get_generic_text_attr('start_date')

    budget.set_generic_text_attr('start_date', int(start_date))
    budget.set_generic_text_attr('end_date', int(end_date))

    check_project_start_end_date(budget.project)
    from stalker_pyramid.views.budgetentry import update_budgetenties_startdate
    update_budgetenties_startdate(budget, time_delta)

    budget.date_updated = utc_now
    budget.updated_by = logged_in_user

    logger.debug("update_budget ends")

    request.session.flash('success: Successfully updated budget')
    return Response('Successfully updated budget')


@view_config(
    route_name='inline_update_budget',
    permission='Update_Budget'
)
def inline_update_budget(request):
    """Inline updates the given budget with the data coming from the request
    """

    logger.debug('INLINE UPDATE BUDGET IS RUNNING')

    from stalker_pyramid.views import get_logged_in_user, \
        get_date_range, milliseconds_since_epoch
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    # *************************************************************************
    # collect data
    attr_name = request.params.get('attr_name', None)
    attr_value = request.params.get('attr_value', None)

    logger.debug('attr_name %s', attr_name)
    logger.debug('attr_value %s', attr_value)

    # get task
    budget_id = request.matchdict.get('id', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()

    # update the task
    if not budget:
        transaction.abort()
        return Response("No budget found with id : %s" % budget_id, 500)

    if attr_name and attr_value:

        logger.debug('attr_name %s', attr_name)

        if attr_name == 'start_and_end_dates':
            logger.debug('attr_name %s', attr_name)
            start, end = attr_value.split(' - ')

            budget.set_generic_text_attr('start_date', int(start))
            budget.set_generic_text_attr('end_date', int(end))

            logger.debug("int(start) : %s" % budget.get_generic_text_attr('start_date'))
            logger.debug("int(end) : %s" % budget.get_generic_text_attr('end_date'))

            check_project_start_end_date(budget.project)

            budget.updated_by = logged_in_user
            budget.date_updated = utc_now
        else:
            setattr(budget, 'attr_name', attr_value)

    else:
        logger.debug('not updating')
        return Response("MISSING PARAMETERS", 500)

    return Response(
        'Budget updated successfully %s %s' % (attr_name, attr_value)
    )


def check_project_start_end_date(project):
    """updates project start end date by checking budgets' start end dates
    """

    budgets = project.budgets
    logger.debug('check_project_start_end_date budgets : %s' % len(budgets))
    start = 0
    end = 0
    for budget in budgets:
        if budget.status.code not in ['RJD', 'CNCLD']:
            start_asmilliseconds = budget.get_generic_text_attr('start_date')
            end_asmilliseconds = budget.get_generic_text_attr('end_date')

            if start == 0 or start_asmilliseconds < start:
                start = start_asmilliseconds
            if end == 0 or end_asmilliseconds > end:
                end = end_asmilliseconds
    if start != 0:
        from stalker_pyramid.views import from_milliseconds
        project.start = from_milliseconds(start)
        project.end = from_milliseconds(end)

    logger.debug('check_project_start_end_date ends')


@view_config(
    route_name='get_project_budgets',
    renderer='json',
    permission='List_Budget'
)
def get_budgets(request):
    """returns budgets with the given id
    """

    project_id = request.matchdict.get('id')
    logger.debug(
        'get_budgets is working for the project which id is: %s' % project_id
    )

    status_code = request.params.get('status_code', None)
    status = Status.query.filter(Status.code == status_code).first()

    sql_query = """
        select
            "Budgets".id,
            "Budget_SimpleEntities".name,
            "Created_By_SimpleEntities".created_by_id,
            "Created_By_SimpleEntities".name,
            "Type_SimpleEntities".name,
            (extract(epoch from "Budget_SimpleEntities".date_created) * 1000)::bigint as date_created,
            "Budget_SimpleEntities".description,
            "Statuses_SimpleEntities".name,
            "Statuses".code,
            "Budget_SimpleEntities".generic_text

        from "Budgets"
        join "SimpleEntities" as "Budget_SimpleEntities" on "Budget_SimpleEntities".id = "Budgets".id
        join "Statuses" on "Statuses".id = "Budgets".status_id
        join "SimpleEntities" as "Statuses_SimpleEntities" on "Statuses_SimpleEntities".id = "Statuses".id
        join "SimpleEntities" as "Created_By_SimpleEntities" on "Created_By_SimpleEntities".id = "Budget_SimpleEntities".created_by_id
        left outer join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "Budget_SimpleEntities".type_id
        join "Projects" on "Projects".id = "Budgets".project_id

        where "Projects".id = %(project_id)s %(additional_condition)s
    """

    additional_condition = ''
    if status:
        additional_condition = 'and "Budgets_Statuses".id=%s' % status.id

    budgets = []

    sql_query = sql_query % {
        'project_id': project_id,
        'additional_condition': additional_condition
    }

    from stalker_pyramid.views.auth import PermissionChecker
    result = DBSession.connection().execute(sql_query)
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
            'description': r[6],
            'status_name': r[7],
            'status_code': r[8],
            'generic_data': json.loads(r[9]) if r[9] else {},
        }
        if update_budget_permission:
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
    renderer='json',
    permission='List_Budget'
)
def get_budgets_count(request):
    """missing docstring
    """
    project_id = request.matchdict.get('id')
    logger.debug(
        'get_budgets_count is working for the project which id is %s' %
        project_id
    )

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
    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]


@view_config(
    route_name='view_budget_calendar',
    renderer='templates/budget/view/view_budget_calendar.jinja2',
    permission='Read_Budget'
)
@view_config(
    route_name='view_budget_table_summary',
    renderer='templates/budget/view/view_budget_table.jinja2',
    permission='Read_Budget'
)
@view_config(
    route_name='view_budget_table_detail',
    renderer='templates/budget/view/view_budget_table.jinja2',
    permission='Read_Budget'
)
@view_config(
    route_name='view_budget_report',
    renderer='templates/budget/view/view_budget_report.jinja2',
    permission='Read_Budget'
)
def view_budget(request):
    """view_budget
    """
    logger.debug('view_budget')
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    total_price = budget.get_generic_text_attr('total_price')
    total_cost = budget.get_generic_text_attr('total_cost')
    approved_total_price = budget.get_generic_text_attr('approved_total_price')

    projects = Project.query.all()
    mode = request.matchdict.get('mode', None)

    logger.debug("mode %s " % mode)
    came_from = request.params.get('came_from', request.url)

    from stalker_pyramid.views import milliseconds_since_epoch
    from stalker_pyramid.views.auth import PermissionChecker
    return {
        'mode': mode,
        'entity': budget,
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'stalker_pyramid': stalker_pyramid,
        'generic_data': json.loads(budget.generic_text),
        'budget_calendar_editing': "ON",
        'approved_total_price': approved_total_price,
        'total_price': total_price,
        'total_cost':total_cost,
        'projects': projects,
        'studio': studio,
        'came_from': came_from
    }


@view_config(
    route_name='change_budget_status_dialog',
    renderer='templates/budget/dialog/change_budget_status_dialog.jinja2',
    permission='Update_Budget'
)
def change_budget_status_dialog(request):
    """change_budget_status_dialog
    """
    logger.debug('change_budget_status_dialog is starts')

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    status_code = request.matchdict.get('status_code')
    came_from = request.params.get('came_from', '/')

    budget_total_price = budget.get_generic_text_attr('total_price')

    return {
        'status_code': status_code,
        'came_from': came_from,
        'budget': budget,
        'budget_total_price': budget_total_price
    }


@view_config(
    route_name='change_budget_status',
    permission='Update_Budget'
)
def change_budget_status(request):

    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    status_code = request.matchdict.get('status_code')
    status = Status.query.filter(Status.code == status_code).first()

    if not status:
        transaction.abort()
        return Response('There is no status with code %s' % status_code, 500)

    approved_total_price = request.params.get('approved_total_price', None)

    if approved_total_price:
        budget.set_generic_text_attr("approved_total_price", approved_total_price)

    description = request.params.get('description', '')

    from stalker_pyramid.views.note import create_simple_note
    note = create_simple_note(description,
                              status.name,
                              "status_%s" % status.code.lower(),
                              status.name,
                              logged_in_user,
                              utc_now)

    budget.notes.append(note)

    budget.status = status
    budget.updated_by = logged_in_user
    budget.date_updated = utc_now

    return Response('Budget status is changed successfully')


@view_config(
    route_name='duplicate_budget_dialog',
    renderer='templates/budget/dialog/duplicate_budget_dialog.jinja2',
    permission='Create_Budget'
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
    route_name='duplicate_budget',
    permission='Create_Budget'
)
def duplicate_budget(request):

    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    name = request.params.get('name', None)
    description = request.params.get('description', '')
    status_code = request.params.get('status_code', 'PLN')
    logger.debug("status_code %s " % status_code)
    from stalker_pyramid.views.type import query_type
    budget_type = budget.type
    project = budget.project
    status = Status.query.filter(Status.code == status_code).first()

    if not name:
        return Response('Please supply a name', 500)

    if not status:
        return Response('Please supply a status', 500)

    new_budget = Budget(
        project=project,
        name=name,
        type=budget_type,
        status=status,
        description=description,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        generic_text=budget.generic_text
    )
    DBSession.add(new_budget)

    # related_budgets = budget.get_generic_text_attr('related_budgets')
    # related_budgets.append(new_budget.id)
    # budget.set_generic_text_attr('related_budgets', related_budgets)

    for budget_entry in budget.entries:
        new_budget_entry = BudgetEntry(
            budget=new_budget,
            good=budget_entry.good,
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
        DBSession.add(new_budget_entry)

    if status_code == 'ATV':
        project.set_generic_text_attr('active_budget_id', new_budget.id)
        logger.debug("active_budget_id %s " % project.get_generic_text_attr('active_budget_id'))

    request.session.flash('success: Budget is duplicated successfully')
    return Response('Budget is duplicated successfully')


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
    route_name='generate_report',
    permission='Create_Budget'

)
def generate_report_view(request):
    """generates report and allows the user to download it
    """
    from stalker_pyramid.views import get_logged_in_user 
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

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
        # client = project.client
        # if not client:
        #     raise Response('No client in the project')

        status = Status.query.filter(Status.code == "PREV").first()
        budget.status = status
        budget.updated_by = logged_in_user
        budget.date_updated = utc_now

        logger.debug('generating report:')
        from stalker_pyramid.views.client import generate_report
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


@view_config(
    route_name='set_budget_totals',
    permission='Update_Budget'
)
def set_budget_totals(request):
    """set_budget_totals
    """
    logger.debug('set_budget_totals method starts')
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()

    if not budget:
        transaction.abort()
        return Response('There is no budget with id %s' % budget_id, 500)

    total_cost = request.params.get('total_cost', 0)
    total_price = request.params.get('total_price', 0)
    total_msrp = request.params.get('total_msrp', 0)

    budget.set_generic_text_attr("total_cost", total_cost)
    budget.set_generic_text_attr("total_price", total_price)
    budget.set_generic_text_attr("total_msrp", total_msrp)

    budget.updated_by = logged_in_user
    budget.date_updated = utc_now

    return Response("Successfully, total cost is set to %s and total price is set to %s" %
                    (total_cost, total_price))


@view_config(
    route_name='create_budget_tasks_into_project',
    permission='Update_Project'
)
def create_budget_tasks_into_project(request):
    """create_budget_tasks_into_project
    """
    logger.debug('create_budget_tasks_into_project method starts')
    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    budget_id = request.matchdict.get('id')
    budget = Budget.query.filter_by(id=budget_id).first()
    status_list = StatusList.query \
        .filter_by(target_entity_type='Task') \
        .first()

    folders = budget.get_generic_text_attr("folders")

    new_tasks_list = []
    for folder in folders:
        budget_id = request.matchdict.get('id')
        budget = Budget.query.filter_by(id=budget_id).first()
        status_list = StatusList.query \
            .filter_by(target_entity_type='Task') \
            .first()

        kwargs = {}
        kwargs['project'] = budget.project
        kwargs['parent'] = None
        kwargs['name'] = folder['name']
        kwargs['code'] = folder['name']
        kwargs['description'] = folder['description']
        kwargs['created_by'] = logged_in_user
        kwargs['date_created'] = utc_now
        kwargs['type'] = None
        kwargs['status_list'] = status_list

        kwargs['schedule_model'] = 'effort'
        kwargs['schedule_timing'] = 1
        kwargs['schedule_unit'] = 'h'

        kwargs['responsible'] = []
        kwargs['resources'] = []
        kwargs['depends'] = []

        kwargs['priority'] = 500
        new_tasks_list.append(kwargs)
        create_task_to_project(kwargs)
        DBSession.add(budget)

    budgetentries = BudgetEntry.query.filter(BudgetEntry.budget == budget).all()
    for budgetentry in budgetentries:
        if budgetentry.get_generic_text_attr('dataSource') == 'Calendar':
            secondaryFactors = budgetentry.get_generic_text_attr("secondaryFactor")
            logger.debug('secondaryFactors: %s' % secondaryFactors)

            if secondaryFactors:
                for secondaryFactor in secondaryFactors:
                    kwargs = {}
                    kwargs['project'] = budget.project
                    filtered_folders = filter(lambda x: x['id'] == secondaryFactor['folder_id'], folders)
                    parent = None
                    if filtered_folders:
                        folder = filtered_folders[0]
                        with DBSession.no_autoflush:
                            parent = Task.query.filter(Task.name == folder['name']).first()

                    kwargs['parent'] = parent
                    kwargs['name'] = secondaryFactor['task_name']
                    kwargs['code'] = secondaryFactor['task_name']
                    # kwargs['description'] = secondaryFactor['description'] if secondaryFactor['description'] else ""
                    kwargs['created_by'] = logged_in_user
                    kwargs['date_created'] = utc_now
                    kwargs['type'] = None
                    kwargs['status_list'] = status_list

                    kwargs['schedule_model'] = 'effort'
                    kwargs['schedule_timing'] = budgetentry.amount
                    kwargs['schedule_unit'] = 'd'

                    kwargs['responsible'] = []
                    kwargs['resources'] = []
                    kwargs['depends'] = []

                    kwargs['priority'] = 500
                    new_tasks_list.append(kwargs)
                    create_task_to_project(kwargs)
                    DBSession.add(budget)
                    DBSession.add_all(budgetentries)

    # for new_task_kwargs in new_tasks_list:
    #     create_task_to_project(new_task_kwargs)

    return Response("successfully")


def create_task_to_project(kwargs):
    from stalker.exceptions import CircularDependencyError, StatusError
    from sqlalchemy.exc import IntegrityError
    try:
        new_entity = Task(**kwargs)
        logger.debug('task %s' % new_entity.name)
        DBSession.add(new_entity)

    except (AttributeError, TypeError, CircularDependencyError) as e:
        logger.debug('The Error Message: %s' % e)
        response = Response('%s' % e, 500)
        transaction.abort()
        return response
    else:
        DBSession.add(new_entity)
        try:
            transaction.commit()
            # DBSession.add_all(kwargs.values())
            DBSession.add(kwargs['project'])
            DBSession.add(kwargs['status_list'])
            # DBSession.add(kwargs['parent'])
        except IntegrityError as e:
            logger.debug('The Error Message: %s' % str(e))
            transaction.abort()
            return Response(str(e), 500)
        else:
            logger.debug('flushing the DBSession, no problem here!')
            DBSession.flush()
            logger.debug('finished adding Task')

    return Response('Task created successfully')









