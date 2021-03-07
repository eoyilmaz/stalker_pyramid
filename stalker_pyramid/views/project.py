# -*- coding: utf-8 -*-

import pytz
import time
import json
import datetime
import logging

from pyramid.httpexceptions import HTTPOk, HTTPFound
from pyramid.response import Response
from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import (db, ImageFormat, Repository, Structure, Status,
                     StatusList, Project, Entity, Studio, defaults, Client,
                     Budget, BudgetEntry, Good, User, Type, SimpleEntity)
from stalker.models.project import ProjectUser
import transaction

from stalker_pyramid.views import (get_date_range,
                                   get_logged_in_user,
                                   milliseconds_since_epoch,
                                   PermissionChecker,
                                   get_multi_integer, get_multi_string)

from stalker_pyramid.views.role import query_role
from stalker_pyramid.views.type import query_type

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='create_project'
)
def create_project(request):
    """called when adding a new Project
    """
    logged_in_user = get_logged_in_user(request)

    came_from = request.params.get('came_from', '/')

    logger.debug('create_project  create_project create_project         :')
    # parameters
    name = request.params.get('name')
    code = request.params.get('code')
    fps = request.params.get('fps', 0)
    generic_text = request.params.get('generic_text')
    # get the dates
    start, end = get_date_range(request, 'start_and_end_dates')

    imf_id = request.params.get('image_format_id', -1)
    imf = ImageFormat.query.filter_by(id=imf_id).first()
    if not imf:
        imf = ImageFormat.query.first()

    repo_id = request.params.get('repository_id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()
    if not repo:
        repo = Repository.query.first()

    structure_id = request.params.get('structure_id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()
    if not structure:
        structure = Structure.query.first()

    status = Status.query.filter_by(code='PLN').first()
    if not status:
        # just use the first status for a project
        project_status_list = \
            StatusList.query.filter_by(target_entity_type='Project').first()
        status = project_status_list.statuses[0]

    type_id = request.params.get('type_id', None)
    # if not type_id:
    #     transaction.abort()
    #     return Response('Please enter a type name', 500)

    from stalker_pyramid.views.client import query_client
    clients = []
    brand_name = request.params.get('brand_name', None)
    if not brand_name:
        transaction.abort()
        return Response('Please enter a brand name', 500)

    brand = query_client(brand_name, 'Brand', logged_in_user)
    clients.append(brand)

    production_house_name = request.params.get('production_house_name', None)
    if not production_house_name:
        transaction.abort()
        return Response('Please enter a production house name', 500)

    production_house = query_client(production_house_name, 'Production House', logged_in_user)
    clients.append(production_house)

    agency_name = request.params.get('agency_name', None)
    if not agency_name:
        transaction.abort()
        return Response('Please enter a agency name', 500)

    agency = query_client(agency_name, 'Agency', logged_in_user)
    clients.append(agency)

    if not clients:
        transaction.abort()
        return Response('Can not find any client', 500)

    logger.debug('create_project          :')

    logger.debug('name          : %s' % name)
    logger.debug('code          : %s' % code)
    logger.debug('fps           : %s' % fps)
    logger.debug('imf_id        : %s' % imf_id)
    logger.debug('imf           : %s' % imf)
    logger.debug('repo_id       : %s' % repo_id)
    logger.debug('repo          : %s' % repo)
    logger.debug('structure_id  : %s' % structure_id)
    logger.debug('structure     : %s' % structure)
    logger.debug('start         : %s' % start)
    logger.debug('end           : %s' % end)
    logger.debug('generic_text  : %s' % generic_text)
    logger.debug('type_id     : %s' % type_id)
    new_project_id = ""

    if name and code and start and end:
        # status is always New
        # lets create the project
        logger.debug('code              : %s' % code)
        # status list
        status_list = StatusList.query \
            .filter_by(target_entity_type='Project').first()

        if type_id:
            project_type = \
                Type.query\
                    .filter_by(target_entity_type="Project")\
                    .filter_by(id=type_id).first()
        else:
            project_type = None

        try:
            logger.debug('code: %s' % code)
            logger.debug('type(code): %s' % type(code))
            logger.debug('fps: %s' % fps)
            logger.debug('type(fps): %s' % type(fps))
            new_project = Project(
                name=name,
                code=code,
                image_format=imf,
                repositories=[repo],
                created_by=logged_in_user,
                # fps=fps,
                structure=structure,
                status_list=status_list,
                status=status,
                start=start,
                end=end,
                clients=clients,
                generic_text=generic_text,
                type=project_type
            )

            DBSession.add(new_project)
            transaction.commit()
            project = Project.query.filter(Project.name == name).first()
            new_project_id = project.id
            # flash success message
            request.session.flash(
                'success:Project <strong>%s</strong> is created '
                'successfully' % name
            )
        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    return Response("/projects/%s/view" % new_project_id)


@view_config(
    route_name='update_project'
)
def update_project(request):
    """called when updating a Project
    """
    logged_in_user = get_logged_in_user(request)

    # parameters
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter_by(id=project_id).first()
    if not project:
        transaction.abort()
        return Response('Can not find a project with code: %s' % project_id, 500)

    imf_id = request.params.get('image_format_id', -1)
    imf = ImageFormat.query.filter_by(id=imf_id).first()
    if not imf:
        transaction.abort()
        return Response('Can not find a ImageFormat with code: %s' % imf_id, 500)

    repo_id = request.params.get('repository_id', -1)
    repo = Repository.query.filter_by(id=repo_id).first()
    if not repo:
        transaction.abort()
        return Response('Can not find a Repository with code: %s' % repo_id, 500)

    structure_id = request.params.get('structure_id', -1)
    structure = Structure.query.filter_by(id=structure_id).first()
    if not structure:
        transaction.abort()
        return Response('Can not find a structure with code: %s' % structure_id, 500)

    status_id = request.params.get('status_id', -1)
    status = Status.query.filter_by(id=status_id).first()
    if not status:
        transaction.abort()
        return Response('Can not find a status with code: %s' % status_id, 500)

    clients = []
    try:
        client_ids = get_multi_integer(request, 'client_ids')
        logger.debug('client_ids          : %s' % clients)
        clients = Client.query.filter(Client.id.in_(client_ids)).all()
    except ValueError:
        pass
    #if not clients:
    #    transaction.abort()
    #    return Response('Can not find any client', 500)

    name = request.params.get('name')
    fps = float(request.params.get('fps'))

    start, end = get_date_range(request, 'start_and_end_dates')
    generic_text = request.params.get('generic_text')
    type_id = request.params.get('type_id', None)

    logger.debug('update_project          :')

    logger.debug('name          : %s' % name)
    logger.debug('fps           : %s' % fps)
    logger.debug('imf_id        : %s' % imf_id)
    logger.debug('repo_id       : %s' % repo_id)
    logger.debug('repo          : %s' % repo)
    logger.debug('structure_id  : %s' % structure_id)
    logger.debug('structure     : %s' % structure)
    logger.debug('start         : %s' % start)
    logger.debug('end           : %s' % end)
    logger.debug('project       : %s' % project)
    logger.debug('client        : %s' % len(clients))
    logger.debug('generic_text  : %s' % generic_text)
    logger.debug('type_id : %s' % type_id)

    new_generic_data = json.loads(generic_text)

    if name and fps and start and end:
        project_type = Type.query.filter_by(target_entity_type="Project").filter_by(id=type_id).first()

        time_delta = milliseconds_since_epoch(start) - \
                     milliseconds_since_epoch(project.start)
        project.name = name
        project.image_format = imf
        project.repositories = [repo]
        project.updated_by = logged_in_user

        utc_now = datetime.datetime.now(pytz.utc)

        project.date_updated = utc_now
        project.fps = fps
        project.structure = structure
        project.status = status
        project.start = start
        project.end = end
        project.clients = clients
        project.type = project_type

        for attr in new_generic_data:
            project.set_generic_text_attr(attr, new_generic_data[attr])
        # update_budgetenties_startdate(project, time_delta)
        logger.debug('project updated %s ' % project.generic_text)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    request.session.flash(
        'success:Project with the code <strong>%s</strong> is updated.'
        % project.code
    )
    return Response(
        'success:Project with the code <strong>%s</strong> is updated.'
        % project.code
    )


@view_config(
    route_name='inline_update_project'
)
def inline_update_project(request):
    """Inline updates the given project with the data coming from the request
    """

    logger.debug('INLINE UPDATE PROJECT IS RUNNING')

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    # *************************************************************************
    # collect data
    attr_name = request.params.get('attr_name', None)
    attr_value = request.params.get('attr_value', None)

    logger.debug('attr_name %s', attr_name)
    logger.debug('attr_value %s', attr_value)

    # get task
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter(Project.id == project_id).first()

    # update the task
    if not project:
        transaction.abort()
        return Response("No project found with id : %s" % project_id, 500)

    if attr_name and attr_value:

        logger.debug('attr_name %s', attr_name)

        if attr_name == 'start_and_end_dates':
            start, end = get_date_range(request, 'attr_value')
            setattr(project, 'start', start)
            setattr(project, 'end', end)

            project.updated_by = logged_in_user
            project.date_updated = utc_now
        else:
            setattr(project, attr_name, attr_value)

    else:
        logger.debug('not updating')
        return Response("MISSING PARAMETERS", 500)

    return Response(
        'Project updated successfully %s %s' % (attr_name, attr_value)
    )


@view_config(
    route_name='change_project_status_dialog',
    renderer='templates/project/dialog/change_project_status_dialog.jinja2'
)
def change_project_status_dialog(request):
    """change_project_status_dialog
    """
    logger.debug('change_project_status_dialog is starts')

    project_id = request.matchdict.get('id')
    project = Project.query.filter_by(id=project_id).first()

    status_code = request.matchdict.get('status_code')
    came_from = request.params.get('came_from', '/')

    return {
        'status_code': status_code,
        'came_from': came_from,
        'project': project
    }


@view_config(
    route_name='change_project_status'
)
def change_project_status(request):

    from stalker_pyramid.views import get_logged_in_user
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    project_id = request.matchdict.get('id')
    project = Project.query.filter_by(id=project_id).first()

    if not project:
        transaction.abort()
        return Response('There is no project with id %s' % project_id, 500)

    status_code = request.matchdict.get('status_code')
    status = Status.query.filter(Status.code == status_code).first()

    if not status:
        transaction.abort()
        return Response('There is no status with code %s' % status_code, 500)

    note_str = request.params.get('note')
    from stalker_pyramid.views.note import create_simple_note
    note = create_simple_note(note_str,
                              status.name,
                              "status_%s" % status.code.lower(),
                              status.name,
                              logged_in_user,
                              utc_now)

    project.notes.append(note)

    archive_project = request.params.get('archive_project')
    if archive_project:
        logger.debug("archive_project %s" % archive_project)
        project.set_generic_text_attr("archive_project", archive_project)

    project.status = status
    project.updated_by = logged_in_user
    project.date_updated = utc_now

    request.session.flash('success: Project status is changed successfully')
    return Response('Project status is changed successfully')


@view_config(
    route_name='get_entity_projects',
    renderer='json'
)
def get_entity_projects(request):
    """
    """

    logger.debug('***get_entity_projects method starts ***')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    # logger.debug('entity.projects count :%s', len(entity.projects))

    return_data = []
    lead_role = query_role('Lead')
    # only list open projects

    status_cmpl = Status.query.filter(Status.code=='CMPL').first()

    if entity.entity_type == "User":
        entity_projects = Project.query.filter(Project.users.contains(entity)).filter(Project.status!=status_cmpl).order_by(Project.name).all()
    else:
        entity_projects = sorted(entity.projects, key=lambda x: x.name)

    for project in entity_projects:
        project_user = ProjectUser.query\
            .filter_by(project=project)\
            .filter_by(role=lead_role)\
            .first()

        lead = None
        if project_user:
            lead = User.query.get(project_user.user_id)

        return_data.append(
            {
                'id': project.id,
                'name': project.name,
                'lead_id': lead.id if lead else None,
                'lead_name': lead.name if lead else None,
                'date_created': milliseconds_since_epoch(project.date_created),
                'created_by_id': project.created_by.id if project.created_by else None,
                'created_by_name': project.created_by.name if project.created_by else None,
                'thumbnail_full_path': project.thumbnail.full_path if project.thumbnail else None,
                'status': project.status.name,
                'status_code': project.status.code.lower(),
                'description': len(project.users),
                'type_name': project.type.name if project.type else None,
                'percent_complete': project.percent_complete,
                'item_view_link': '/projects/%s/view' % project.id,
                'item_remove_link': '/entities/%s/delete/dialog?came_from=%s'%(project.id, request.current_route_path())
                if PermissionChecker(request)('Update_Project') and project.status.code == 'PLN' else None,
                'archive_project': project.get_generic_text_attr("archive_project")

            }
        )

    return return_data


@view_config(
    route_name='get_projects',
    renderer='json'
)
def get_projects(request):
    """returns all the Project instances in the database
    """
    return [
        {
            'id': proj.id,
            'name': proj.name
        }
        for proj in Project.query.all()
    ]


@view_config(
    route_name='get_project_lead',
    renderer='json'
)
def get_project_lead(request):
    """returns the project lead as a json data
    """
    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter(Project.id == project_id).first()
    lead_data = {}
    if project:
        lead = project.lead
        lead_data = {
            'id': lead.id,
            'name': lead.name,
            'login': lead.login
        }

    return lead_data


@view_config(
    route_name='get_project_tasks_cost',
    renderer='json'
)
def get_project_tasks_cost(request):
    """returns the project lead as a json data
    """
    project_id = request.matchdict.get('id', -1)

    budget_list = get_multi_integer(request, 'budget_ids', 'GET')
    budgets = Budget.query.filter(Budget.id.in_(budget_list)).all()

    if not budgets:
        transaction.abort()
        return Response('Can not find any budget !!', 500)

    sql_query = """
               select
        "PriceList_SimpleEntities".name as price_list_name,
        "Good_SimpleEntities".name as good_name,
        "Good_SimpleEntities".id as good_id,
        "Task_Goods".msrp as msrp,
        "Task_Goods".cost as cost,
        "Task_Goods".unit as unit,
        sum("Project_Users".rate*("Tasks".bid_timing * (case "Tasks".bid_unit
                                            when 'min' then 60
                                            when 'h' then 3600
                                            when 'd' then 32400
                                            when 'w' then 183600
                                            when 'm' then 590400
                                            when 'y' then 7696277
                                            else 0
                                        end)/3600)) as bid_total,
        sum("Project_Users".rate*("Tasks".schedule_timing * (case "Tasks".schedule_unit
                            when 'min' then 60
                            when 'h' then 3600
                            when 'd' then 32400
                            when 'w' then 183600
                            when 'm' then 590400
                            when 'y' then 7696277
                            else 0
                        end)/3600)) as schedule_total,
       sum("Project_Users".rate*(extract(epoch from "TimeLogs".end - "TimeLogs".start))/3600) as timelog_duration,
       budgetentries.name as budgetentries_name,
       budgetentries.price as budgetentries_price,
       "Task_Goods".id as good_id

       from "Tasks"
       join "Goods" as "Task_Goods" on "Task_Goods".id = "Tasks".good_id
       join "SimpleEntities" as "Good_SimpleEntities" on "Good_SimpleEntities".id = "Task_Goods".id
       join "PriceList_Goods" on "PriceList_Goods".good_id = "Task_Goods".id
       join "SimpleEntities" as "PriceList_SimpleEntities" on "PriceList_SimpleEntities".id = "PriceList_Goods".price_list_id
       join "TimeLogs" on "Tasks".id = "TimeLogs".task_id
       join "Project_Users" on "Project_Users".user_id = "TimeLogs".resource_id
       left outer join (
                    select "BudgetEntries_SimpleEntities".name as name,
                         "BudgetEntries".id as id,
                         "BudgetEntries".good_id as good_id,
                         "BudgetEntries".price as price
                    from "BudgetEntries"
                    join "SimpleEntities" as "BudgetEntries_SimpleEntities" on "BudgetEntries_SimpleEntities".id = "BudgetEntries".id
                    join "Budgets" on "Budgets".id = "BudgetEntries".budget_id
                    %(where_condition_budgets)s
                ) as budgetentries on budgetentries.good_id = "Task_Goods".id

       where "Project_Users".project_id = %(project_id)s  and not exists (
                            select 1 from "Tasks" as "All_Tasks"
                            where "All_Tasks".parent_id = "Tasks".id
                            )

       group by "Good_SimpleEntities".name,
                 "Good_SimpleEntities".id,
                 budgetentries.name,
                 budgetentries.price,
                 "Task_Goods".msrp,
                 "Task_Goods".cost,
                 "Task_Goods".unit,
                 "Task_Goods".id,
                 "PriceList_SimpleEntities".name
"""


    where_condition_budgets = ""
    temp_buffer = ["""where"""]
    for i, budget in enumerate(budgets):
        if i > 0:
            temp_buffer.append(' or')
        temp_buffer.append(""" "Budgets".id=%s""" % budget.id)

    where_condition_budgets = ''.join(temp_buffer)

    logger.debug("where_condition_budgets: %s" % where_condition_budgets)

    sql_query = sql_query % {'project_id': project_id,
                             'where_condition_budgets': where_condition_budgets
    }

    result = DBSession.connection().execute(sql_query)
    return_data = [
        {
            'price_list_name': r[0],
            'good_name': r[1],
            'good_id': r[2],
            'msrp': int(r[3]),
            'cost': int(r[4]),
            'unit': r[5],
            'bid':r[6],
            'scheduled':r[7],
            'realized_total':r[8],
            'budgetentries_name':r[9] if r[9] else " - ",
            'budgetentries_price':r[10] if r[10] else 0,
            'id': r[11]
        }
        for r in result.fetchall()
    ]

    return return_data


@view_config(
    route_name='add_project_entries_to_budget'
)
def add_project_entries_to_budget(request):
    """ adds entries to bugdet"""

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    project_id = request.matchdict.get('id', -1)
    project = Project.query.filter(Project.id == project_id).first()
    if not project:
        transaction.abort()
        return Response('Can not find a project with id: %s' % project_id, 500)

    budget_id = request.matchdict.get('bid', -1)
    budget = Budget.query.filter(Budget.id == budget_id).first()
    if not budget:
        transaction.abort()
        return Response('Can not find a budget with id: %s' % budget_id, 500)

    project_entries = get_project_tasks_cost(request)

    for project_entry in project_entries:
        new_budget_entry_type = query_type('BudgetEntry', project_entry['price_list_name'])
        new_budget = True

        good = Good.query.filter(Good.id == project_entry['good_id']).first()
        logger.debug('good: %s' % good.name)
        if good:
            for budget_entry in budget.entries:
                if budget_entry.name == project_entry['good_name']:
                    budget_entry.good = good
                    budget_entry.type = new_budget_entry_type
                    budget_entry.amount = project_entry['amount']
                    budget_entry.cost = project_entry['cost']
                    budget_entry.msrp = project_entry['msrp']
                    budget_entry.realized_total = project_entry['realized_total']
                    budget_entry.unit = project_entry['unit']
                    budget_entry.date_updated = utc_now
                    budget_entry.updated_by = logged_in_user
                    budget_entry.generic_text = 'Calendar'
                    new_budget = False

            if new_budget:
                new_budget_entry = BudgetEntry(
                    budget=budget,
                    good=good,
                    name=project_entry['good_name'],
                    type=new_budget_entry_type,
                    amount=project_entry['amount'],
                    cost=project_entry['cost'],
                    msrp=project_entry['msrp'],
                    price=int(project_entry['cost'])* int(project_entry['amount']),
                    realized_total=project_entry['realized_total'],
                    unit=project_entry['unit'],
                    description='',
                    created_by=logged_in_user,
                    date_created=utc_now,
                    date_updated=utc_now,
                    generic_text='Calendar'
                )
                DBSession.add(new_budget_entry)

    return Response(
        'success:Budget Entries are updated for <strong>%s</strong> project.'
        % project.name
    )




@view_config(
    route_name='get_project_tasks_today',
    renderer='json'
)
def get_project_tasks_today(request):
    """returns the project lead as a json data
    """
    project_id = request.matchdict.get('id', -1)
    action = request.matchdict.get('action', -1)

    today = datetime.date.now(tzinfo=pytz.utc)
    start = datetime.time(0, 0, tzinfo=pytz.utc)
    end = datetime.time(23, 59, 59, tzinfo=pytz.utc)

    start_of_today = datetime.datetime.combine(today, start)
    end_of_today = datetime.datetime.combine(today, end)

    start = time.time()

    sql_query = """select "Tasks".id,
           "SimpleEntities".name,
           array_agg(distinct("SimpleEntities_Resource".id)),
           array_agg(distinct("SimpleEntities_Resource".name)),
           "SimpleEntities_Status".name,
           "SimpleEntities_Status".html_class,
           (coalesce("Task_TimeLogs".duration, 0.0))::float /
           ("Tasks".schedule_timing * (case "Tasks".schedule_unit
                when 'min' then 60
                when 'h' then %(working_seconds_per_hour)s
                when 'd' then %(working_seconds_per_day)s
                when 'w' then %(working_seconds_per_week)s
                when 'm' then %(working_seconds_per_month)s
                when 'y' then %(working_seconds_per_year)s
                else 0
            end)) * 100.0 as percent_complete
    from "Tasks"
        join "SimpleEntities" on "Tasks".id = "SimpleEntities".id
        join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
        join "SimpleEntities" as "SimpleEntities_Resource" on "Task_Resources".resource_id = "SimpleEntities_Resource".id
        join "Statuses" on "Tasks".status_id = "Statuses".id
        join "SimpleEntities" as "SimpleEntities_Status" on "Statuses".id = "SimpleEntities_Status".id
        left outer join (
            select
                "TimeLogs".task_id,
                extract(epoch from sum("TimeLogs".end - "TimeLogs".start)) as duration
            from "TimeLogs"
            group by task_id
        ) as "Task_TimeLogs" on "Task_TimeLogs".task_id = "Tasks".id
        left outer join "TimeLogs" on "Tasks".id = "TimeLogs".task_id
        """

    if action == 'progress':
        sql_query += """where
            "Tasks".computed_start < '%(end_of_today)s' and
            "Tasks".computed_end > '%(start_of_today)s'"""
    elif action == 'end':
        sql_query += """where
            "Tasks".computed_end > '%(start_of_today)s' and
            "Tasks".computed_end <= '%(end_of_today)s'
            """

    sql_query += """   and "Tasks".project_id = %(project_id)s
        group by "Tasks".id,
             "SimpleEntities".name,
             "SimpleEntities_Status".name,
             "SimpleEntities_Status".html_class,
             "Task_TimeLogs".duration,
             "Tasks".schedule_timing,
             "Tasks".schedule_unit
        """

    studio = Studio.query.first()
    assert isinstance(studio, Studio)

    ws_per_hour = 3600
    ws_per_day = studio.daily_working_hours * ws_per_hour
    ws_per_week = studio.weekly_working_days * ws_per_day
    ws_per_month = ws_per_week * 4
    ws_per_year = studio.yearly_working_days * ws_per_day

    sql_query = sql_query % {
        'project_id': project_id,
        'start_of_today': start_of_today.strftime('%Y-%m-%d %H:%M:%S'),
        'end_of_today': end_of_today.strftime('%Y-%m-%d %H:%M:%S'),
        'working_seconds_per_hour': ws_per_hour,
        'working_seconds_per_day': ws_per_day,
        'working_seconds_per_week': ws_per_week,
        'working_seconds_per_month': ws_per_month,
        'working_seconds_per_year': ws_per_year
    }

    # logger.debug('sql_query : %s' % sql_query)

    result = DBSession.connection().execute(sql_query)

    data = [
        {
            'task_id': r[0],
            'task_name': r[1],
            'resources': [
                '<a href="/users/%(id)s/view">%(name)s</a>' % {
                    'id': r[2][i],
                    'name': r[3][i]
                } for i in range(len(r[2]))
            ],
            'status': r[4],
            'status_color': r[5],
            'percent_complete': r[6]
        } for r in result.fetchall()
    ]

    end = time.time()
    logger.debug('%s rows took : %s seconds' % (len(data), (end - start)))

    return data


@view_config(
    route_name='view_project_tasks',
    renderer='templates/project/view/view_project_tasks.jinja2'
)
@view_config(
    route_name='view_project',
    renderer='templates/project/view/view_project.jinja2'
)
def view_project(request):
    """creates a list_entity_tasks_by_filter by using the given entity and filter
    """
    logger.debug('inside view_project')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    filter_id = request.params.get('f_id', -1)
    filter_entity = Entity.query.filter_by(id=filter_id).first()
    is_warning_list = False
    if not filter_entity:
        is_warning_list = True
        filter_entity = Status.query.filter_by(code='WIP').first()

    projects = Project.query.all()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'create',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'entity': entity,
        'filter': filter_entity,
        'is_warning_list': is_warning_list,
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'projects': projects
    }


def get_project_user(project, role_name):

    user = None
    role = query_role(role_name)
    if role:
        project_user = ProjectUser.query.\
            filter(ProjectUser.role_id == role.id).\
            filter(ProjectUser.project_id == project.id).first()

        if project_user:
            user = User.query.\
                filter(User.id == project_user.user_id).first()

    return user
