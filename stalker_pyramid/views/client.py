# -*- coding: utf-8 -*-

import pytz
import datetime
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from stalker import db, Client, User, ClientUser, Studio, ProjectUser
from stalker.db.session import DBSession

import transaction

from webob import Response
from stalker_pyramid.views import (get_logged_in_user, logger,
                                   PermissionChecker, milliseconds_since_epoch)
from stalker_pyramid.views.role import query_role
from stalker_pyramid.views.type import query_type


@view_config(
    route_name='update_client_dialog',
    renderer='templates/client/dialog/update_client_dialog.jinja2',
    permission='Update_Client'
)
@view_config(
    route_name='create_client_dialog',
    renderer='templates/client/dialog/create_client_dialog.jinja2',
    permission='Create_Client'
)
def client_dialog(request):
    """called when creating a client
    """

    came_from = request.params.get('came_from', '/')

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter(Client.id == client_id).first()

    mode = request.matchdict.get('mode', None)
    report_templates = [r['name'] for r in get_distinct_report_templates()]
    client_report_template_name = ""

    if client:
        report_template = get_report_template(client)
        if report_template:
            client_report_template_name = report_template['name']

    return {
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'entity': client,
        'logged_in_user': logged_in_user,
        'client': client,
        'came_from': came_from,
        'mode': mode,
        'report_templates': report_templates,
        'client_report_template_name': client_report_template_name,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_client',
    permission='Create_Client'
)
def create_client(request):
    """called when adding a new client
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    came_from = request.params.get('came_from', '/')

    # parameters
    name = request.params.get('name')
    description = request.params.get('description')
    report_template_name = request.params.get('report_template_name', None)

    type_name = request.params.get('type_name', None)

    logger.debug('create_client :')

    logger.debug('name          : %s' % name)
    logger.debug('description   : %s' % description)
    logger.debug('type_name : %s' % type_name)
    logger.debug('report_template_name : %s' % report_template_name)

    if name and description and type_name and report_template_name:
        client_type = query_type("Client", type_name)

        report_template = filter(lambda x: x['name'] == report_template_name, get_distinct_report_templates())
        logger.debug('report_template : %s' % report_template[0])
        generic_text_data = {
            'report_template': report_template[0]
        }
        import json
        try:
            new_client = Client(
                name=name,
                description=description,
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now,
                type=client_type,
                generic_text=json.dumps(generic_text_data)
            )

            DBSession.add(new_client)
            # flash success message
            request.session.flash(
                'success:Client <strong>%s</strong> is created '
                'successfully' % name
            )
        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)

    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    return Response(
        'success:Client with name <strong>%s</strong> is created.'
        % name
    )


def query_client(client_name, client_type, logged_in_user):
    """returns a Client instance either it creates a new one or gets it from DB
    """

    utc_now = datetime.datetime.now(pytz.utc)

    if not client_name:
        return None

    if not client_type:
        return None

    client_type = query_type("Client", client_type)
    client_query = Client.query.filter_by(type=client_type)
    client_ = client_query.filter_by(name=client_name).first()

    if not client_:

        try:
            new_client = Client(
                name=client_name,
                description='',
                created_by=logged_in_user,
                date_created=utc_now,
                date_updated=utc_now,
                type=client_type
            )

            DBSession.add(new_client)

        except BaseException as e:
            logger.debug("Exception for creating client")

    return client_


@view_config(
    route_name='update_client',
    permission='Update_Client'
)
def update_client(request):
    """called when updating a client
    """
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    # parameters
    name = request.params.get('name')
    description = request.params.get('description')
    type_name = request.params.get('type_name', None)
    report_template_name = request.params.get('report_template_name', None)

    logger.debug('update_client :')

    logger.debug('name          : %s' % name)
    logger.debug('description   : %s' % description)
    logger.debug('type_name : %s' % type_name)
    logger.debug('report_template_name query : %s' % report_template_name)

    if name and description and type_name and report_template_name:
        client_type = query_type("Client", type_name)

        report_template = filter(lambda x: x['name'] == report_template_name, get_distinct_report_templates())
        logger.debug('report_template[0] : %s' % report_template[0])

        client.name = name
        client.type = client_type
        client.description = description
        client.updated_by = logged_in_user
        client.date_updated = utc_now
        client.set_generic_text_attr("report_template", report_template[0])

        DBSession.add(client)
    else:
        transaction.abort()
        return Response('There are missing parameters', 500)

    request.session.flash(
        'success:Client <strong>%s</strong> is updated '
        'successfully' % name
    )

    return Response(
        'success:Client with name <strong>%s</strong> is updated.'
        % name
    )


@view_config(
    route_name='update_studio_client',
    permission='Update_Client'
)
def update_studio_client(request):
    """updates client with given parameters
    """
    logger.debug('update_studio_client is starts')
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    # studio_id = request.matchdict.get('id')
    # studio = Studio.query.get(studio_id)
    # if not studio:
    #     transaction.abort()
    #     return Response('Can not find a entity with id: %s' % studio_id, 500)

    client_id = request.params.get('id', -1)
    client = Client.query.filter(Client.id == client_id).first()

    description = request.params.get('description', '')

    type_name = request.params.get('type_name', None)
    type = query_type("Client", type_name)

    if not client:
        transaction.abort()
        return Response('Can not find a User with id: %s' % client_id, 500)

    if type:
        client.description = description
        client.type = type
        client.date_updated = utc_now
        client.updated_by = logged_in_user

    return Response(
        'Successfully %s is updated with given parameters' % (client.name)
    )



@view_config(
    route_name='get_clients',
    renderer='json',
    permission='List_Client'
)
@view_config(
    route_name='get_studio_clients',
    renderer='json',
    permission='List_Client'
)
def get_studio_clients(request):
    """returns client with the given id
    """

    logger.debug('get_studio_clients is working for the studio')

    type_name = request.params.get('type_name', None)

    logger.debug('type_name: %s' % type_name )

    sql_query = """
        select
            "Clients".id,
            "Client_SimpleEntities".name,
            "Client_SimpleEntities".description,
            "Thumbnail_Links".full_path,
            "Type_SimpleEntities".name,
            projects.project_count
        from "Clients"
        join "SimpleEntities" as "Client_SimpleEntities" on "Client_SimpleEntities".id = "Clients".id
        left outer join "Links" as "Thumbnail_Links" on "Client_SimpleEntities".thumbnail_id = "Thumbnail_Links".id

        left outer join  (
            select "Project_Clients".client_id as client_id,
                    count("Project_Clients".project_id) as project_count
                from "Project_Clients"
                group by "Project_Clients".client_id)as projects on projects.client_id = "Clients".id
        left join "SimpleEntities" as "Type_SimpleEntities" on "Client_SimpleEntities".type_id = "Type_SimpleEntities".id
        %(where_conditions)s
    """

    clients = []
    where_conditions = ""
    if type_name:
        where_conditions = """where "Type_SimpleEntities".name = '%(type_name)s'""" %({'type_name':type_name})

    sql_query = sql_query % {
        'where_conditions': where_conditions
    }

    result = DBSession.connection().execute(sql_query)
    update_client_permission = \
        PermissionChecker(request)('Update_Client')

    for r in result.fetchall():
        client = {
            'id': r[0],
            'name': r[1],
            'description': r[2],
            'thumbnail_full_path': r[3],
            'type_name': r[4],
            'projectsCount': r[5] if r[5] else 0
        }
        if update_client_permission:
            client['item_update_link'] = \
                '/clients/%s/update/dialog' % client['id']
            client['item_remove_link'] =\
                '/entities/%s/delete/dialog?came_from=%s' % (
                    client['id'],
                    request.current_route_path()
                )

        clients.append(client)

    resp = Response(
        json_body=clients
    )

    return resp


@view_config(
    route_name='get_client',
    renderer='json',
    permission='Read_Client'
)
def get_client(request):
    """RESTful version of getting a client
    """
    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter_by(id=client_id).first()

    return_data = [{'id':client.id,
                    'name':client.name
                   }]

    return return_data


@view_config(
    route_name='append_user_to_client_dialog',
    renderer='templates/client/dialog/append_user_to_client_dialog.jinja2',
    permission='Update_Client'
)
def append_user_to_client_dialog(request):
    """called when appending user to client
#     """

    logged_in_user = get_logged_in_user(request)
    came_from = request.params.get('came_from', '/')

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter(Client.id == client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    return {
        'has_permission': PermissionChecker(request),
        'logged_in_user': logged_in_user,
        'client': client,
        'came_from': came_from,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='get_client_users_out_stack',
    renderer='json',
    permission='List_User'
)
def get_client_users_out_stack(request):

    logger.debug('get_client_users_out_stack is running')

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter_by(id=client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    sql_query = """
        select
            "User_SimpleEntities".name,
            "User_SimpleEntities".id
        from "Users"
        left outer join "Client_Users" on "Client_Users".uid = "Users".id
        join "SimpleEntities" as "User_SimpleEntities" on "User_SimpleEntities".id = "Users".id

        where "Client_Users".cid != %(client_id)s or "Client_Users".cid is Null
        group by
            "User_SimpleEntities".name,
            "User_SimpleEntities".id
    """

    sql_query = sql_query % {'client_id': client_id}
    result = DBSession.connection().execute(sql_query)

    users = []
    for r in result.fetchall():
        user = {
            'name': r[0],
            'id': r[1]
        }
        users.append(user)

    resp = Response(
        json_body=users
    )

    return resp


@view_config(
    route_name='append_user_to_client',
    permission='Update_Client'
)
def append_user_to_client(request):

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    came_from = request.params.get('came_from', '/')

    client_id = request.matchdict.get('id', -1)
    client = Client.query.filter(Client.id == client_id).first()
    if not client:
        transaction.abort()
        return Response('Can not find a client with id: %s' % client_id, 500)

    user_id = request.params.get('user_id', -1)
    user = User.query.filter(User.id == user_id).first()
    if not user:
        transaction.abort()
        return Response('Can not find a user with id: %s' % user_id, 500)

    role_name = request.params.get('role_name', None)
    role = query_role(role_name)
    role.updated_by = logged_in_user
    role.date_created = utc_now

    logger.debug("%s role is created" % role.name)
    logger.debug(client.users)

    client_user = ClientUser()
    client_user.client = client
    client_user.role = role
    client_user.user = user
    client_user.date_created = utc_now
    client_user.created_by = logged_in_user

    DBSession.add(client_user)

    if user not in client.users:
        client.users.append(user)
        request.session.flash('success:%s is added to %s user list' % (user.name, client.name))

    logger.debug(client.users)

    return Response(
        'Successfully %s is appended to %s as %s' % (user.name,
                                                     client.name,
                                                     role_name
                                                   )
    )


@view_config(
    route_name='get_client_users',
    renderer='json',
    permission='List_User'
)
def get_client_users(request):
    """get_client_users
    """
# if there is an id it is probably a project
    client_id = request.matchdict.get('id')
    client = Client.query.filter(Client.id == client_id).first()

    has_permission = PermissionChecker(request)
    has_update_user_permission = has_permission('Update_User')
    has_delete_user_permission = has_permission('Delete_User')

    delete_user_action = '/users/%(id)s/delete/dialog'
    return_data = []
    for user in client.users:
        client_user = ClientUser.query.filter(ClientUser.user == user).first()
        return_data.append(
            {
                'id': user.id,
                'name': user.name,
                'login': user.login,
                'email': user.email,
                'role': client_user.role.name,
                'update_user_action': '/users/%s/update/dialog' % user.id if has_update_user_permission else None,
                'delete_user_action': delete_user_action % {
                    'id': user.id, 'entity_id': client_id
                } if has_delete_user_permission else None
            }
        )

    return return_data


def get_report_template(client):
    """returns the report_template attribute generated by using the given
    client value

    :param stalker.Client client: The client instance
    """
    # use the client.generic_text attribute
    # load JSON data
    # return the report_template attribute

    from stalker import Client
    if not isinstance(client, Client):
        raise TypeError(
            'Please supply a proper stalker.models.client.Client instance for '
            'the client argument and not '
        )

    import json
    if client.generic_text:
        logger.debug('client.generic_text: %s' % client.generic_text)

        generic_text = json.loads(
            client.generic_text
        )

        return generic_text.get('report_template', None)


def generate_report(budget, output_path=''):
    """generates report for the given client and budget

    :param stalker.Budget budget: The :class:``stalker.Budget`` instance
    :param str output_path: The output path of the resultant report
    """
    # check the budget argument
    from stalker import Budget
    if not isinstance(budget, Budget):
        raise TypeError(
            'Please supply a proper ``stalker.model.budget.Budget`` instance '
            'for the ``budget`` argument and not %s' %
            budget.__class__.__name__
        )

    # render the budget for the given client by using the clients report format
    clients = budget.project.clients
    report_temp_client = None
    for client in clients:
        logger.debug("client.type.name: %s" % client.type.name)
        if client.type.name == "Brand":
            report_temp_client = client

    if not report_temp_client:
        raise RuntimeError(
            'The Project has no client, please specify the client of this '
            'project in ``Project.clients`` attribute!!'
        )

    # get the report_template
    report_template = get_report_template(report_temp_client)

    logger.debug("report_template: %s" % report_template)

    if not report_template:
        raise RuntimeError(
            'The Client has no report_template, please define a '
            '"report_template" value in the Client.generic_text attribute '
            'with proper format (see documentation for the report_template '
            'format)!'
        )

    # load the template as an XLSX file for now (later expand it to other
    # formats like PDF - so the client should have different report templates)
    wb_path = report_template['template']['path']

    mapper_data = report_template['mapper']

    # client has a project
    # the project has a budget which is given
    # the budget has BudgetEntries
    # BudgetEntries have a name and then a price
    # Some cells in the excel file can contain multiple BudgetEntries
    # so the definition of a cell content can be a list
    # and the result will be reduced to a value:
    #
    # reduce(lambda x, y: x + y, map(float, ['2000', '323', '123'])

    from stalker import BudgetEntry
    import json

    import openpyxl
    wb = openpyxl.load_workbook(wb_path)

    from stalker_pyramid.views.project import get_project_user
    creative_director = get_project_user(budget.project, "Yaratici Yonetmen")
    creative_director_name = "Not Appended!!"
    if creative_director:
        creative_director_name = creative_director.name
    setattr(
        budget.project,
        "creative_director",
        creative_director_name
    )

    customer_director = get_project_user(budget.project, "Musteri Direktoru")
    customer_director_name = "Not Appended!!"
    if customer_director:
        customer_director_name = customer_director.name
    setattr(
        budget.project,
        "customer_director",
        customer_director_name
    )

    agency_producer = get_project_user(budget.project, "Ajans Yapimcisi")
    agency_producer_name = "Not Appended!!"
    if agency_producer:
        agency_producer_name = agency_producer.name
    setattr(
        budget.project,
        "agency_producer",
        agency_producer_name
    )

    studio_director = get_project_user(budget.project, "Studio Yonetmen")
    studio_director_name = "Not Appended!!"
    if studio_director:
        studio_director_name = studio_director.name
    setattr(
        budget.project,
        "studio_director",
        studio_director_name
    )

    studio_producer = get_project_user(budget.project, "Studio Yapimci")
    studio_producer_name = "Not Appended!!"
    if studio_producer:
        studio_producer_name = studio_producer.name
    setattr(
        budget.project,
        "studio_producer",
        studio_producer_name
    )

    production_firm = Client.query.filter(Client.id == budget.project.get_generic_text_attr('production_firm')).first()
    production_firm_name = "Not Appended!!"
    if production_firm:
        production_firm_name = production_firm.name
    setattr(
        budget.project,
        "production_firm",
        production_firm_name
    )
    logger.debug("production_firm_name: %s" % production_firm_name)

    adv_agency = Client.query.filter(Client.id == budget.project.get_generic_text_attr('adv_agency')).first()
    adv_agency_name = "Not Appended!!"
    if adv_agency:
        adv_agency_name = adv_agency.name

    setattr(
        budget.project,
        "adv_agency",
        adv_agency_name
    )
    logger.debug("adv_agency_name: %s" % adv_agency_name)

    setattr(
        budget.project,
        "product_project_name",
        budget.project.get_generic_text_attr('product_project_name')
    )
    logger.debug("budget.project.get_generic_text_attr('product_project_name'): %s" % budget.project.get_generic_text_attr('product_project_name'))

    # iterate through sheet_data on the mapper
    for sheet_data in mapper_data['sheets']:
        sheet_name = sheet_data['name']
        logger.debug('sheet_name: %s' % sheet_name)
        sheet = wb.get_sheet_by_name(sheet_name)

        # iterate through cells
        cells = sheet_data['cells']
        logger.debug('cells: %s' % cells)
        for cell_name in cells.keys():
            logger.debug('cell_name: %s' % cell_name)
            cell_data = cells[cell_name]

            result_buffer = []
            for entity_data in cell_data:
                # get the query data
                query_data = entity_data['query']
                result_template = entity_data['result']

                if query_data['name'] != '#STRING RESULT#':
                    # build the query
                    q = BudgetEntry.query\
                        .filter(BudgetEntry.budget == budget)
                    for k, v in query_data.items():
                        q = q.filter(getattr(BudgetEntry, k) == v)
                    filtered_entity = q.first()

                    if filtered_entity:
                        # add secondary data like stoppage_ratio
                        if filtered_entity.generic_text:
                            fe_generic_data = \
                                json.loads(filtered_entity.generic_text)

                            # TODO: Generalize this
                            stoppage_add = filtered_entity.get_generic_text_attr('stoppage_add')
                            filtered_entity.stoppage_add = 1 if stoppage_add == 'Var' else 0
                            filtered_entity.overtime = filtered_entity.get_generic_text_attr('overtime')

                            logger.debug('******filtered_entity.stoppage_add: %s' % filtered_entity.stoppage_add)

                            secondaryFactor = filtered_entity.get_generic_text_attr('secondaryFactor')
                            secondaryAmount = 0

                            for sFactor in secondaryFactor:
                                secondaryAmount += int(sFactor['second_amount'])

                            filtered_entity.secondaryAmount = secondaryAmount

                        # now generate the result
                        result_buffer.append(
                            float(
                                eval(
                                    result_template.format(
                                        item=filtered_entity,
                                        budget=budget,
                                        project=budget.project,
                                        client=report_temp_client
                                    )
                                )
                            )
                        )
                else:
                    # now generate the result
                    result_buffer.append(
                        result_template.format(
                            item=None,
                            budget=budget,
                            project=budget.project,
                            client=report_temp_client
                        )
                    )


            logger.debug('result_buffer: %s' % result_buffer)
            # we should have something like ['2334.3', '2656.4', ...]
            # render it to a one float value

            if result_buffer:
                cell_result = reduce(
                    lambda x, y: x + y,
                    result_buffer
                )
            else:
                cell_result = ''


            # write it down to the cell itself
            sheet[cell_name] = cell_result

    if not output_path:
        # generate a temp path
        import tempfile
        output_path = tempfile.mktemp(suffix='.xlsx')

    # we should have filled all the data to cells
    # now write it down to the given path
    wb.save(filename=output_path)
    return output_path


def get_distinct_report_templates():
    """returns distinct report templates from all clients
    """
    report_templates = []

    for c in Client.query.all():
        report_template = get_report_template(c)
        if report_template:
            # logger.debug('get_distinct_report_templates: %s' % report_template['name'])

            new_report_template = True
            for r in report_templates:
                if report_template['name'] == r['name']:
                    new_report_template = False

            if new_report_template:
                report_templates.append(report_template)

    logger.debug('report_templates: %s' % report_templates)

    return report_templates


def get_report_template_by_name(name):
    """returns the report template from all clients that matches the given name
    """
    for rt in get_distinct_report_templates():
        if rt and rt['name'] == name:
            return rt


# @view_config(
#     route_name='generate_report'
# )
# def generate_report_view(request):
#     """generates report and allows the user to download it
#     """
#     budget_id = request.matchdict['budget_id']
#
#     from stalker import Budget
#     budget = Budget.query.filter(Budget.id == budget_id).first()
#
#     if budget:
#         project = budget.project
#         client = project.client
#         if not client:
#             raise Response('No client in the project')
#
#         import tempfile
#         temp_report_path = generate_report(budget)
#
#         from pyramid.response import FileResponse
#         response = FileResponse(
#             temp_report_path,
#             request=request,
#             content_type='application/force-download'
#         )
#
#         report_file_nice_name = '%s_%s.xlsx' % (
#             project.code, budget.name.replace(' ', '_')
#         )
#         response.headers['content-disposition'] = \
#             str('attachment; filename=%s' % report_file_nice_name)
#
#         return response
