# -*- coding: utf-8 -*-


import time
import pytz
import datetime
from beaker.cache import cache_region

from pyramid.httpexceptions import (HTTPFound, HTTPServerError)
from pyramid.response import Response
from pyramid.security import forget, remember
from pyramid.view import view_config, forbidden_view_config
from sqlalchemy import or_
import transaction

import stalker_pyramid
from stalker import (defaults, User, Department, Group, Project, Studio,
                     Permission, EntityType, Entity, Role, ClientUser,
                     ProjectUser, DepartmentUser, Client, Status)
from stalker.db.session import DBSession
from stalker_pyramid.views import (log_param, get_logged_in_user,
                                   PermissionChecker, get_multi_integer,
                                   get_tags, milliseconds_since_epoch,
                                   StdErrToHTMLConverter)

import logging
from stalker_pyramid.views.role import query_role
from stalker_pyramid.views.type import query_type

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@cache_region('long_term', 'load_users')
def cached_group_finder(login_name):
    if ':' in login_name:
        login_name = login_name.split(':')[1]

    # return the group of the given User object
    user_obj = User.query.filter_by(login=login_name).first()
    if user_obj:
        # just return the groups names
        return ['Group:%s' % x.name for x in user_obj.groups]
    return []


def group_finder(login_name, request):
    """Returns the group of the given login name. The login name will be in
    'User:{login}' format.

    :param login_name: The login name of the user, both '{login_name}' and
      'User:{login_name}' format is accepted.

    :param request: The Request object

    :return: Will return the groups of the user in ['Group:{group_name}']
      format.
    """
    return cached_group_finder(login_name)


class RootFactory(object):
    """The main purpose of having a root factory is to generate the objects
    used as the context by the request. But in our case it just used to
    determine the default ACLs.
    """

    @property
    def __acl__(self):
        # create the default acl and give admins all the permissions
        all_permissions = map(
            lambda x: x.action + '_' + x.class_name,
            Permission.query.all()
        )

        # start with default ACLs

        ACLs = [
            ('Allow', 'Group:%s' % defaults.admin_department_name,
             all_permissions),
            ('Allow', 'User:%s' % defaults.admin_name, all_permissions)
        ]

        # get all users and their ACLs
        all_users = User.query.all()
        for user in all_users:
            ACLs.extend(user.__acl__)

        # get all groups and their ACLs
        all_groups = Group.query.all()
        for group in all_groups:
            ACLs.extend(group.__acl__)

        return ACLs

    def __init__(self, request):
        pass


@view_config(
    route_name='create_user'
)
def create_user(request):
    """called when adding a User
    """

    logger.debug('***create user method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    came_from = request.params.get('came_from', '/')
    name = request.params.get('name', None)
    login = request.params.get('login', None)
    email = request.params.get('email', None)
    password = request.params.get('password', None)
    type_name = request.params.get('type_name', None)

    logger.debug('came_from : %s' % came_from)
    logger.debug('new user name : %s' % name)
    logger.debug('new user login : %s' % login)
    logger.debug('new user email : %s' % email)
    logger.debug('new user password : %s' % password)
    logger.debug('new user type_name : %s' % type_name)

    # create and add a new user
    if name and login and email and password and type_name:

        user_type = query_type("User", type_name)

        department_id = request.params.get('department_id', None)
        departments = []
        if department_id:
            department = Department.query.filter_by(id=department_id).first()
            departments = [department]
        else:
            # Departments
            if 'department_ids' in request.params:
                dep_ids = get_multi_integer(request, 'department_ids')
                departments = Department.query.filter(
                    Department.id.in_(dep_ids)).all()

        # Groups
        groups = []
        if 'group_ids' in request.params:
            grp_ids = get_multi_integer(request, 'group_ids')
            groups = Group.query.filter(
                Group.id.in_(grp_ids)).all()

        # Tags
        tags = get_tags(request)

        logger.debug('new user departments : %s' % departments)
        logger.debug('new user groups : %s' % groups)
        logger.debug('new user tags : %s' % tags)
        try:
            new_user = User(
                name=request.params['name'],
                login=request.params['login'],
                email=request.params['email'],
                password=request.params['password'],
                created_by=logged_in_user,
                departments=departments,
                groups=groups,
                tags=tags,
                type=user_type
            )

            DBSession.add(new_user)

            logger.debug('added new user successfully')

            request.session.flash(
                'success:User <strong>%s</strong> is created successfully' % name
            )

            logger.debug('***create user method ends ***')
            response = Response('User created successfully')
            response.status_int = 200
            return response

        except BaseException as e:
            # request.session.flash('error:' + e.message)
            # HTTPFound(location=came_from)
            transaction.abort()
            return Response('BaseException: %s' % e, 500)
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')

        return Response('There are missing parameters: ', 500)


@view_config(
    route_name='inline_update_user'
)
def inline_update_user(request):
    """Inline updates the given user with the data coming from the request
    """

    logger.debug('INLINE UPDATE USER IS RUNNING')

    logged_in_user = get_logged_in_user(request)

    logger.debug(request.params)

    # *************************************************************************
    # collect data
    attr_name = request.params.get('attr_name', -1)

    logger.debug('attr_name: %s' % attr_name)
    attr_val = request.params.get(attr_name, None)

    # get user
    user_id = request.params.get('id', -1)
    user = User.query.filter(User.id == user_id).first()

    # update the user
    if not user:
        transaction.abort()
        return Response("No user found with id : %s" % user_id, 500)

    if attr_val:
        if attr_name == 'rate':
            attr_val = float(attr_val)
        setattr(user, attr_name, attr_val)

        user.updated_by = logged_in_user
        utc_now = datetime.datetime.now(pytz.utc)

        user.date_updated = utc_now

    else:
        logger.debug('not updating')
        return Response("MISSING PARAMETERS", 500)

    return Response(
        'User updated successfully '
    )


@view_config(
    route_name='update_user'
)
def update_user(request):
    """called when updating a User
    """

    logger.debug('***update user method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    came_from = request.params.get('came_from', '/')
    user_id = request.matchdict.get('id')
    user = User.query.filter(User.id == user_id).first()

    name = request.params.get('name')
    login = request.params.get('login')
    email = request.params.get('email')
    password = request.params.get('password')
    type_name = request.params.get('type_name')

    logger.debug('user : %s' % user)
    logger.debug('user new name : %s' % name)
    logger.debug('user new login : %s' % login)
    logger.debug('user new email : %s' % email)
    logger.debug('user new password : %s' % password)
    logger.debug('user new type_name : %s' % type_name)

    if user and name and login and email and password and type_name:
        # departments = []
        #
        # # Departments
        # if 'department_ids' in request.params:
        #     dep_ids = get_multi_integer(request, 'department_ids')
        #     departments = Department.query \
        #         .filter(Department.id.in_(dep_ids)).all()
        #
        # # Groups
        # groups = []
        # if 'group_ids' in request.params:
        #     grp_ids = get_multi_integer(request, 'group_ids')
        #     groups = Group.query \
        #         .filter(Group.id.in_(grp_ids)).all()

        # Tags
        tags = get_tags(request)
        user_type = query_type("User", type_name)
        user.name = name
        user.login = login
        user.email = email
        user.type = user_type
        user.updated_by = logged_in_user

        date_updated = datetime.datetime.now(pytz.utc)

        user.date_updated = date_updated
        # user.departments = departments
        # user.groups = groups
        # user.tags = tags

        if password != 'DONTCHANGE':
            user.password = password

        DBSession.add(user)

        logger.debug('user is updated successfully')

        request.session.flash(
            'success:User <strong>%s</strong> is updated successfully' % name
        )
        logger.debug('***update user method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'user_id')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')
        HTTPServerError()

    return HTTPFound(
        location=came_from
    )


@view_config(
    route_name='get_entity_users_count',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_project_users_count',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_users_count',
    renderer='json',
    permission='List_User'
)
def get_users_count(request):
    """returns all users or one particular user from database
    """
    # if there is a simple flag, just return ids and names and login
    #simple = request.params.get('simple')

    # if there is an id it is probably a project
    entity_id = request.matchdict.get('id')

    entity_type = None
    if entity_id:
        sql_query = \
            'select entity_type from "SimpleEntities" where id=%s' % entity_id
        data = DBSession.connection().execute(sql_query).fetchone()
        entity_type = data[0] if data else None

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity_type: %s' % entity_type)

    if entity_id and entity_type not in ['Project', 'Department', 'Group', 'Task', 'User', 'Studio']:
        # there is no entity_type for that entity
        return []

    sql_query = """select
        count("Users".id)
    from "SimpleEntities"
    join "Users" on "SimpleEntities".id = "Users".id
    left outer join (
        select
            uid,
            array_agg(did) as dep_ids,
            array_agg(name) as dep_names
        from "Department_Users"
        join "SimpleEntities" on "Department_Users".did = "SimpleEntities".id
        group by uid
    ) as department_Users on department_Users.uid = "Users".id
    left outer join (
        select
            uid,
            array_agg(gid) as group_ids,
            array_agg(name) as group_names
        from "Group_Users"
        join "SimpleEntities" on "Group_Users".gid = "SimpleEntities".id
        group by uid
    ) as group_users on group_users.uid = "Users".id
    left outer join (
        select resource_id, count(task_id) as task_count from "Task_Resources" group by resource_id
    ) as tasks on tasks.resource_id = "Users".id
    left outer join (
        select
            owner_id,
            count("Tickets".id) as ticket_count
        from "Tickets"
        join "SimpleEntities" on "Tickets".status_id = "SimpleEntities".id
        where "SimpleEntities".name = 'New'
        group by owner_id, name
    ) as tickets on tickets.owner_id = "Users".id
    left outer join "Links" on "SimpleEntities".thumbnail_id = "Links".id
    """

    if entity_type == "Project":
        sql_query += """join "Project_Users" on "Users".id = "Project_Users".user_id
        where "Project_Users".project_id = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Department":
        sql_query += """join "Department_Users" on "Users".id = "Department_Users".uid
        where "Department_Users".did = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Group":
        sql_query += """join "Group_Users" on "Users".id = "Group_Users".uid
        where "Group_Users".gid = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "Task":
        sql_query += """join "Task_Resources" on "Users".id = "Task_Resources".resource_id
        where "Task_Resources".task_id = %(id)s
        """ % {'id': entity_id}
    elif entity_type == "User":
        sql_query += 'where "Users".id = %s' % entity_id

    return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(
    route_name='get_entity_users',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_project_users',
    renderer='json',
    permission='List_User'
)
@view_config(
    route_name='get_user',
    renderer='json',
    permission='Read_User'
)
def get_entity_users(request):
    """returns all users or one particular user from database
    """
    start = time.time()

    logger.debug("get_entity_users started")

    # if there is an id it is probably a project
    entity_id = request.matchdict.get('id')
    entity_type = None

    has_permission = PermissionChecker(request)
    has_update_user_permission = has_permission('Update_User')
    has_delete_user_permission = has_permission('Delete_User')
    has_read_rate_permission = has_permission('Update_Budget')

    delete_user_action = '/users/%(id)s/delete/dialog'

    if entity_id:
        sql_query = 'select entity_type from "SimpleEntities" where id=%s' % entity_id
        data = DBSession.connection().execute(sql_query).fetchone()
        entity_type = data[0] if data else None
        if entity_type in ['Project', 'Department', 'Group', 'Task', 'User', 'Client', 'Studio']:
            delete_user_action = '/entities/%(entity_id)s/%(id)s/remove/dialog'
        else:
            # there is no entity_type for that entity
            return []

    logger.debug('entity_id  : %s' % entity_id)
    logger.debug('entity_type: %s' % entity_type)


    sql_query = """select
        "Users".id,
        "User_SimpleEntities".name,
        "Users".login,
        "Users".email,
        department_users."dep_ids",
        department_users."dep_names",
        group_users."group_ids",
        group_users."group_names",
        tasks.task_count,
        tickets.ticket_count,
        "Links".full_path,
        "Users".rate,
        "Type_SimpleEntities".name,
        client_users."client_ids",
        client_users."client_names"
        %(new_attr)s

    from "Users"
    join "SimpleEntities" as "User_SimpleEntities" on "User_SimpleEntities".id = "Users".id
    left outer join (
        select
            uid,
            array_agg(did) as dep_ids,
            array_agg(name) as dep_names
        from "Department_Users"
        join "SimpleEntities" on "Department_Users".did = "SimpleEntities".id
        group by uid
    ) as department_users on department_users.uid = "Users".id
    left outer join (
        select
            uid,
            array_agg(gid) as group_ids,
            array_agg(name) as group_names
        from "Group_Users"
        join "SimpleEntities" on "Group_Users".gid = "SimpleEntities".id
        group by uid
    ) as group_users on group_users.uid = "Users".id
    left outer join (
        select resource_id, count(task_id) as task_count from "Task_Resources" group by resource_id
    ) as tasks on tasks.resource_id = "Users".id
    left outer join (
        select
            owner_id,
            count("Tickets".id) as ticket_count
        from "Tickets"
        join "SimpleEntities" on "Tickets".status_id = "SimpleEntities".id
        where "SimpleEntities".name = 'New'
        group by owner_id, name
    ) as tickets on tickets.owner_id = "Users".id
    left outer join "Links" on "User_SimpleEntities".thumbnail_id = "Links".id
    left outer join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "User_SimpleEntities".type_id
    left outer join (
        select
            uid,
            array_agg(cid) as client_ids,
            array_agg(name) as client_names
        from "Client_Users"
        join "SimpleEntities" on "Client_Users".cid = "SimpleEntities".id
        group by uid
    ) as client_users on client_users.uid = "Users".id
    """

    new_attr = """,
        "Role_SimpleEntities".name,
        "Role_SimpleEntities".id"""

    role_query = """left outer join "Roles" on "Entity_Users".rid = "Roles".id
    left outer join "SimpleEntities" as "Role_SimpleEntities" on "Roles".id = "Role_SimpleEntities".id"""

    if entity_type == "Project":
        sql_query += """join "Project_Users" as "Entity_Users" on "Users".id = "Entity_Users".user_id
        %(role_query)s
        where "Entity_Users".project_id = %(id)s
        """ % {'id': entity_id, 'role_query': role_query}

        new_attr = """,
        "Role_SimpleEntities".name,
        "Role_SimpleEntities".id,
        "Entity_Users".rate"""

        sql_query = sql_query % {'new_attr': new_attr}

    elif entity_type == "Department":
        sql_query += """join "Department_Users" as "Entity_Users" on "Users".id = "Entity_Users".uid
        %(role_query)s
        where "Entity_Users".did = %(id)s
        """ % {'id': entity_id, 'role_query': role_query}
        sql_query = sql_query % {'new_attr': new_attr}

    elif entity_type == "Group":
        sql_query += """join "Group_Users" as "Entity_Users" on "Users".id = "Entity_Users".uid

        where "Entity_Users".gid = %(id)s
        """ % {'id': entity_id}
        sql_query = sql_query % {'new_attr': ""}

    elif entity_type == "Task":
        sql_query += """join "Task_Resources" on "Users".id = "Task_Resources".resource_id
        where "Task_Resources".task_id = %(id)s
        """ % {'id': entity_id}
        sql_query = sql_query % {'new_attr': new_attr}

    elif entity_type == "Client":
        sql_query += """join "Client_Users" as "Entity_Users" on "Users".id = "Entity_Users".uid
        %(role_query)s
        where "Entity_Users".cid = %(id)s
        """ % {'id': entity_id, 'role_query': role_query}
        sql_query = sql_query % {'new_attr': new_attr}

    elif entity_type == "User":
        sql_query += 'where "Users".id = %s' % entity_id
        sql_query = sql_query % {'new_attr': ""}

    elif entity_type == "Studio":
        sql_query = sql_query % {'new_attr': ""}

    sql_query += 'order by "User_SimpleEntities".name'

    result = DBSession.connection().execute(sql_query)

    data = [
        {
            'id': r[0],
            'name': r[1],
            'login': r[2],
            'email': r[3],
            'departments': [
                {
                    'id': r[4][i],
                    'name': r[5][i]
                } for i, a in enumerate(r[4])
            ] if r[4] else [],
            'groups': [
                {
                    'id': r[6][i],
                    'name': r[7][i]
                } for i, a in enumerate(r[6])
            ] if r[6] else [],
            'tasksCount': r[8] or 0,
            'ticketsCount': r[9] or 0,
            'thumbnail_full_path': r[10] if has_read_rate_permission else None,
            'studio_rate': r[11] if has_read_rate_permission else r[11],
            'type_name': r[12],
            'update_user_action':'/users/%s/update/dialog' % r[0]
            if has_update_user_permission else None,
            'delete_user_action':delete_user_action % {
                'id': r[0], 'entity_id': entity_id
            } if has_delete_user_permission else None,
            'clients': [
                {
                    'id': r[13][i],
                    'name': r[14][i]
                } for i, a in enumerate(r[13])
            ] if r[13] else [],
            'role': r[15] if len(r) >= 16 else None,
            'rate': r[17] if (len(r) >= 18) and has_read_rate_permission else None
        } for r in result.fetchall()
    ]

    end = time.time()

    logger.debug('get_entity_users took : %s seconds for %s rows' % ((end - start), len(data)))
    logger.debug("get_entity_users ended")
    return data


@view_config(
    route_name='get_users',
    renderer='json',
    permission='List_User'
)
def get_users_simple(request):
    """simply return the users without dealing a lot of other details
    """

    logger.debug('get_users_simple starts')

    start = time.time()
    sql_query = """select
        "Users".id,
        "SimpleEntities".name,
        "Users".login,
        "Users".email,
        department_users."dep_ids",
        department_users."dep_names",
        group_users."group_ids",
        group_users."group_names",
        tasks.task_count,
        tickets.ticket_count,
        "Links".full_path,
        "Users".rate,
        "Type_SimpleEntities".name
    from "SimpleEntities"
    join "Users" on "SimpleEntities".id = "Users".id
    left outer join (
        select
            uid,
            array_agg(did) as dep_ids,
            array_agg(name) as dep_names
        from "Department_Users"
        join "SimpleEntities" on "Department_Users".did = "SimpleEntities".id
        group by uid
    ) as department_users on department_users.uid = "Users".id
    left outer join (
        select
            uid,
            array_agg(gid) as group_ids,
            array_agg(name) as group_names
        from "Group_Users"
        join "SimpleEntities" on "Group_Users".gid = "SimpleEntities".id
        group by uid
    ) as group_users on group_users.uid = "Users".id
    left outer join (
        select resource_id, count(task_id) as task_count from "Task_Resources" group by resource_id
    ) as tasks on tasks.resource_id = "Users".id
    left outer join (
        select
            owner_id,
            count("Tickets".id) as ticket_count
        from "Tickets"
        join "SimpleEntities" on "Tickets".status_id = "SimpleEntities".id
        where "SimpleEntities".name = 'New'
        group by owner_id, name
    ) as tickets on tickets.owner_id = "Users".id
    left outer join "Links" on "SimpleEntities".thumbnail_id = "Links".id
    left outer join "SimpleEntities" as "Type_SimpleEntities" on "Type_SimpleEntities".id = "SimpleEntities".type_id
    """
    has_permission = PermissionChecker(request)
    has_update_user_permission = has_permission('Update_User')
    has_delete_user_permission = has_permission('Delete_User')
    has_read_rate_permission = has_permission('Read_Budget')

    result = DBSession.connection().execute(sql_query)

    logger.debug('get_users_simple results')
    data = [
        {
            'id': r[0],
            'name': r[1],
            'login': r[2],
            'email': r[3],
            'departments': [
                {
                    'id': r[4][i],
                    'name': r[5][i]
                } for i, a in enumerate(r[4])
            ] if r[4] else [],
            'groups': [
                {
                    'id': r[6],
                    'name': r[7]
                } for i in range(len(r[6]))
            ] if r[6] else [],
            'tasksCount': r[8] or 0,
            'ticketsCount': r[9] or 0,
            'thumbnail_full_path': r[10] if r[10] else None,
            'studio_rate': r[11] if r[11] else None,
            'type_name': r[12],
            'update_user_action':'/users/%s/update/dialog' % r[0]
            if has_update_user_permission else None,
            'delete_user_action':'/users/%s/delete/dialog' % r[0]
            if has_delete_user_permission else None
        } for r in result.fetchall()
    ]

    end = time.time()
    logger.debug('get_users_simple took : %s seconds for %s rows' %
                 ((end - start), len(data)))
    return data


def get_permissions_from_multi_dict(multi_dict):
    """returns the permission instances from the given multi_dict
    """
    permissions = []

    # gather all access, actions, and class_names
    all_class_names = [entity_type.name for entity_type in
                       EntityType.query.all()]
    all_actions = defaults.actions

    logger.debug(all_class_names)
    logger.debug(all_actions)

    for key in multi_dict.keys():
        access = multi_dict[key]
        action_and_class_name = key.split('_')

        try:
            action = action_and_class_name[0]
            class_name = action_and_class_name[1]

            logger.debug('access     : %s' % access)
            logger.debug('action     : %s' % action)
            logger.debug('class_name : %s' % class_name)

        except IndexError:
            continue

        else:

            if access in ['Allow', 'Deny'] and \
               class_name in all_class_names and \
               action in all_actions:

                # get permissions
                permission = Permission.query \
                    .filter_by(access=access) \
                    .filter_by(action=action) \
                    .filter_by(class_name=class_name) \
                    .first()

                if permission:
                    permissions.append(permission)

    logger.debug(permissions)
    return permissions


@view_config(
    route_name='logout'
)
def logout(request):
    logged_in_user = get_logged_in_user(request)
    from stalker import AuthenticationLog
    from stalker.models.auth import LOGOUT
    al = AuthenticationLog(
        user=logged_in_user,
        date=datetime.datetime.now(pytz.utc),
        action=LOGOUT
    )
    DBSession.add(al)
    transaction.commit()

    headers = forget(request)
    return HTTPFound(
        location=request.route_url('login'),
        headers=headers
    )


@forbidden_view_config(
    renderer='templates/auth/login.jinja2'
)
@view_config(
    route_name='login',
    renderer='templates/auth/login.jinja2'
)
def login(request):
    """the login view
    """
    logger.debug('login start')
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/'

    came_from = request.params.get('came_from', referrer)

    login_name = request.params.get('login', '')
    password = request.params.get('password', '')
    has_error = False

    if 'submit' in request.params:
        # get the user again (first got it in validation)
        user_obj = User.query \
            .filter(or_(User.login == login_name, User.email == login_name))\
            .first()

        if user_obj:
            login_name = user_obj.login

        if user_obj and user_obj.check_password(password):
            from stalker import AuthenticationLog
            from stalker.models.auth import LOGIN
            al = AuthenticationLog(
                user_obj,
                date=datetime.datetime.now(pytz.utc),
                action=LOGIN
            )
            DBSession.add(al)
            transaction.commit()
            headers = remember(request, login_name)
            # form submission succeeded
            return HTTPFound(
                location=came_from,
                headers=headers,
            )
        else:
            has_error = True

    return {
        'login': login_name,
        'password': password,
        'has_error': has_error,
        'came_from': came_from
    }


@view_config(
    route_name='flash_message',
    renderer='templates/home.jinja2'
)
@view_config(
    route_name='home',
    renderer='templates/auth/view/view_user.jinja2'
)
@view_config(
    route_name='me_menu',
    renderer='templates/auth/me_menu.jinja2'
)
def home(request):
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()
    projects = Project.query.all()

    filter_id = request.params.get('f_id', -1)
    filter_entity = Entity.query.filter_by(id=filter_id).first()
    is_warning_list = False
    if not filter_entity:
        is_warning_list = True
        filter_entity = Status.query.filter_by(code='WIP').first()

    flash_message = request.params.get('flash')
    if flash_message:
        request.session.flash(flash_message)

    return {
        'stalker_pyramid': stalker_pyramid,
        'studio': studio,
        'logged_in_user': logged_in_user,
        'has_permission': PermissionChecker(request),
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'projects': projects,
        'filter': filter_entity,
        'is_warning_list': is_warning_list,
        'entity': logged_in_user
    }


@view_config(
    route_name='view_user',
    renderer='templates/auth/view/view_user.jinja2'
)
def view_user(request):
    logged_in_user = get_logged_in_user(request)

    studio = Studio.query.first()
    projects = Project.query.all()

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    filter_id = request.params.get('f_id', -1)
    filter_entity = Entity.query.filter_by(id=filter_id).first()
    is_warning_list = False
    if not filter_entity:
        is_warning_list = True
        filter_entity = Status.query.filter_by(code='WIP').first()

    flash_message = request.params.get('flash')
    if flash_message:
        request.session.flash(flash_message)

    return {
        'stalker_pyramid': stalker_pyramid,
        'studio': studio,
        'logged_in_user': logged_in_user,
        'has_permission': PermissionChecker(request),
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'projects': projects,
        'filter': filter_entity,
        'is_warning_list': is_warning_list,
        'entity': entity
    }


@view_config(
    route_name='check_login_availability',
    renderer='json'
)
def check_login_availability(request):
    """checks it the given login is available
    """
    login_name = request.matchdict['login']
    logger.debug('checking availability for: %s' % login_name)

    available = 1
    if login_name:
        user = User.query.filter(User.login == login_name).first()
        if user:
            available = 0

    return {
        'available': available
    }


@view_config(
    route_name='check_email_availability',
    renderer='json'
)
def check_email_availability(request):
    """checks it the given email is available
    """
    email = request.matchdict['email']
    logger.debug('checking availability for: %s' % email)

    available = 1
    if email:
        user = User.query.filter(User.email == email).first()
        if user:
            available = 0

    return {
        'available': available
    }


@view_config(
    route_name='get_entity_resources',
    permission='Read_User',
    renderer='json'
)
@view_config(
    route_name='get_resources',
    permission='Read_User',
    renderer='json'
)
@view_config(
    route_name='get_resource',
    permission='Read_User',
    renderer='json'
)
def get_resources(request):
    """returns Users for Resource View
    """
    # TODO: This is a very ugly function, please define the borders and use cases correctly and then clean it

    from stalker_pyramid.views.task import generate_recursive_task_query

    start = time.time()
    # return users for now
    # /resources/
    # /resources/26/
    resource_id = request.matchdict.get('id')
    logger.debug('resource_id: %s' % resource_id)

    parent_id = request.params.get('parent_id')
    logger.debug('parent_id: %s' % parent_id)

    execute = DBSession.connection().execute

    entity_type = None
    if resource_id:
        # get the entity type of that resource
        data = execute('select entity_type from "SimpleEntities" where id=%s' %
                       resource_id).fetchone()
        if data:
            entity_type = data[0]
        else:
            return []
    else:
        # default to User
        entity_type = "User"
    logger.debug('entity_type : %s' % entity_type)

    # get resource details plus time logs
    if not parent_id:
        if entity_type == 'Department':
            resource_sql_query = """select
                "SimpleEntities".id,
                "SimpleEntities".name,
                "SimpleEntities".entity_type,
                count(*) as resource_count
            from "SimpleEntities"
            join "Department_Users" on "Department_Users".did = "SimpleEntities".id
            where "SimpleEntities".entity_type = '%s'
            """ % entity_type
        elif entity_type == 'User':
            resource_sql_query = """select
                "SimpleEntities".id,
                "SimpleEntities".name,
                "SimpleEntities".entity_type,
                1 as resource_count
            from "SimpleEntities"
            where "SimpleEntities".entity_type = '%s'
            """ % entity_type
        elif entity_type in ['Studio', 'Project']:
            resource_sql_query = """select
                "SimpleEntities".id,
                "SimpleEntities".name,
                "SimpleEntities".entity_type,
                count(*) as resource_count
            from "SimpleEntities"
            join "Department_Users" on "Department_Users".did = "SimpleEntities".id
            """

        if resource_id and entity_type not in ["Studio", "Project"]:
            resource_sql_query += "and id=%s group by id, name, entity_type order by name" % resource_id
        else:
            resource_sql_query += "group by id, name, entity_type order by name"

        # if the given entity is a Department return all the time logs of the
        # users of that department
        time_log_query = """select
            "TimeLogs".id,
            "TimeLogs".task_id,
            extract(epoch from "TimeLogs".start) * 1000 as start,
            extract(epoch from "TimeLogs".end) * 1000 as end
        from "TimeLogs"
        """

        tasks_query = """select
            tasks.id,
            tasks.full_path,
            extract(epoch from "Tasks".computed_start) * 1000 as start,
            extract(epoch from "Tasks".computed_end) * 1000 as end
        -- start with tasks (with full names)
        from (
            %(recursive_task_query)s
        ) as tasks
            join "Tasks" on tasks.id = "Tasks".id
        """ % {
            'recursive_task_query':
            generate_recursive_task_query(ordered=False)
        }

        has_children = False

        if entity_type == "User":
            time_log_query += "where resource_id = %(id)s"

            tasks_query += """join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            where not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            ) and resource_id = %(id)s
            """

            has_children = False
        elif entity_type in ["Department", "Studio"]:
            time_log_query += """
            join "Department_Users" on "Department_Users".uid = "TimeLogs".resource_id
            where did = %(id)s"""

            tasks_query += """join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            join "Department_Users" on "Task_Resources".resource_id = "Department_Users".uid
            join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            where not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            )
            and did = %(id)s
            group by tasks.id, tasks.full_path, "Tasks".start, "Tasks".end, "Tasks".computed_start, "Tasks".computed_end
            order by start
            """

            has_children = True
        elif entity_type == "Project":
            # the resource is a Project return all the project tasks and
            # return all the time logs of the users in that project
            time_log_query += """
            join "Project_Users" on "Project_Users".user_id = "TimeLogs".resource_id
            -- where did = %(id)s
            """

            # tasks_query += """
            # -- select all the leaf tasks of the users of a specific Project
            # select
            #     "Tasks".id,
            #     "Task_SimpleEntities".name,
            #     extract(epoch from "Tasks".computed_start) * 1000 as start,
            #     extract(epoch from "Tasks".computed_end) * 1000 as end
            # from "Tasks"
            #     join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            #     where not (
            #         exists (
            #             select 1
            #             from "Tasks"
            #             where "Tasks".parent_id = tasks.id
            #         )
            #     ) and project_id = %(id)s
            # group by id, "Task_SimpleEntities".name, start, "end", "Tasks".computed_start, "Tasks".computed_end
            # order by start
            # """
            tasks_query += """join "Task_Resources" on "Tasks".id = "Task_Resources".task_id
            join "Project_Users" on "Project_Users".user_id = "Task_Resources".resource_id
            join "SimpleEntities" as "Task_SimpleEntities" on "Tasks".id = "Task_SimpleEntities".id
            where not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            )
            and "Project_Users".project_id = %(id)s
            group by tasks.id, tasks.full_path, "Tasks".start, "Tasks".end, "Tasks".computed_start, "Tasks".computed_end
            order by start
            """

            has_children = True

    else:
        # return departments ??? should also return Groups, Project etc.
        # that contains users
        resource_sql_query = """select
            "Users".id,
            "SimpleEntities".name,
            "SimpleEntities".entity_type,
            1 as resource_count
        from "Users"
        join "SimpleEntities" on "SimpleEntities".id = "Users".id
        join "Department_Users" on "Department_Users".uid = "Users".id
        join "Departments" on "Department_Users".did = "Departments".id
        where "Departments".id = %(id)s
        order by name
        """ % {'id': parent_id}

        time_log_query = """select
            "TimeLogs".id,
            "TimeLogs".task_id,
            extract(epoch from "TimeLogs".start) * 1000 as start,
            extract(epoch from "TimeLogs".end) * 1000 as end
        from "TimeLogs"
        where resource_id = %(id)s
        """

        tasks_query = """select
            tasks.id,
            tasks.full_path,
            extract(epoch from "Tasks".computed_start) * 1000 as start,
            extract(epoch from "Tasks".computed_end) * 1000 as end
        from (
            %(recursive_task_query)s
        ) as tasks
            join "Tasks" on tasks.id = "Tasks".id
            join "Task_Resources" on tasks.id = "Task_Resources".task_id
        where
            not (
                exists (
                    select 1
                    from "Tasks"
                    where "Tasks".parent_id = tasks.id
                )
            ) and resource_id = %(id)s
        """

        has_children = False

    # logger.debug('resource_sql_query : %s' % resource_sql_query)
    # logger.debug('time_log_query : %s' % time_log_query)
    # logger.debug('tasks_sql_query : %s' % tasks_query)

    resources_result = execute(resource_sql_query).fetchall()

    # logger.debug('resources_result : %s' % resources_result)

    link = '/%s/%s/view' % (entity_type.lower(), '%s')
    data = [
        {
            'id': rr[0],
            'name': rr[1],
            'type': rr[2],
            'resource_count': rr[3],
            'hasChildren': has_children,
            'link': link % rr[0],
            'time_logs': [
                {
                    'id': tr[0],
                    'task_id': tr[1],
                    'start': tr[2],
                    'end': tr[3]
                } for tr in execute(
                    time_log_query % {
                        'id': rr[0]
                    }).fetchall()
            ],
            'tasks': [
                {
                    'id': tr[0],
                    'name': tr[1],
                    'start': tr[2],
                    'end': tr[3]
                } for tr in execute(
                    tasks_query % {
                        'recursive_task_query':
                            generate_recursive_task_query(False),
                        'id': rr[0]
                    }
                ).fetchall()
            ]
        } for rr in resources_result
    ]

    end = time.time()
    logger.debug('get_resources took : %s seconds' % (end - start))

    data_count = len(data)
    content_range = '%s-%s/%s' % (0, data_count - 1, data_count)

    resp = Response(
        json_body=data
    )
    resp.content_range = content_range
    return resp


@view_config(
    route_name='delete_user_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_user_dialog(request):
    """deletes the user with the given id
    """
    logger.debug('delete_user_dialog is starts')

    user_id = request.matchdict.get('id')
    user = User.query.get(user_id)

    came_from = request.params.get('came_from', request.current_route_path())
    action = '/users/%s/delete?came_from=%s' % (user_id, came_from)

    message = \
        'Are you sure you want to ' \
        '<strong>delete User %s </strong>?' % user.name

    logger.debug('action: %s' % action)

    return {
        'came_from': came_from,
        'message': message,
        'action': action
    }


@view_config(
    route_name='delete_user',
    permission='Delete_User'
)
def delete_user(request):
    """deletes the user with the given id
    """
    user_id = request.matchdict.get('id')
    user = User.query.get(user_id)

    if not user:
        transaction.abort()
        return Response('Can not find a User with id: %s' % user_id, 500)

    try:
        DBSession.delete(user)

        transaction.commit()
        request.session.flash(
            'success: %s is deleted' % user.name
        )
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        request.session.flash(
            c.html()
        )
        return Response(c.html(), 500)

    return Response('Successfully deleted user: %s' % user_id)


@view_config(
    route_name='update_entity_user'
)
def update_entity_user(request):
    """updates user for given entity
    """
    logger.debug('update_entity_user_role is starts')
    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    entity_id = request.matchdict.get('id')
    entity = Entity.query.get(entity_id)
    if not entity:
        transaction.abort()
        return Response('Can not find a entity with id: %s' % entity_id, 500)

    user_id = request.params.get('id', -1)
    user = User.query.filter(User.id == user_id).first()

    rate = request.params.get('rate', None)

    role_name = request.params.get('role', None)
    role = query_role(role_name)

    type_name = request.params.get('type_name', None)
    type = query_type("User", type_name)

    logger.debug('user_id: %s' % user_id)
    logger.debug('role_name: %s' % role_name)
    logger.debug('rate: %s' % rate)
    logger.debug('entity.entity_type: %s' % entity.entity_type)

    if not user:
        transaction.abort()
        return Response('Can not find a User with id: %s' % user_id, 500)

    if type:
        user.type = type
        user.date_updated = utc_now
        user.updated_by = logged_in_user

    if user not in entity.users:
        entity.users.append(user)

    if entity.entity_type in ["Project", "Client", "Department"]:
        query_string = '%(class_name)sUser.query.filter(%(class_name)sUser.user_id == user_id).filter(%(class_name)sUser.%(attr_name)s == entity_id)'
        q = eval(query_string % {'class_name': entity.entity_type,
                                 'attr_name': '%s_id' % entity.entity_type.lower()
                                })
        entity_user = q.first()

        entity_user.role = role
        if rate:
            entity_user.rate = int(rate)
        logger.debug('entity_user: %s' % entity_user)
        logger.debug('entity_user.rate: %s' % entity_user.rate)

        entity_user.date_updated = utc_now
        entity_user.updated_by = logged_in_user

        DBSession.add(entity_user)

    if entity.entity_type == "Studio":
        if rate:
            user.rate = int(rate)
            logger.debug('rate: %s' % rate)
            user.date_updated = utc_now
            user.updated_by = logged_in_user

    return Response(
        'Successfully %s role is given to %s in %s' % (role_name,
                                                       user.name,
                                                       entity.name)
    )


@view_config(
    route_name='append_user_to_entity_dialog',
    renderer='templates/auth/dialog/append_user_to_entity_dialog.jinja2'
)
def append_user_to_entity_dialog(request):

    logger.debug('append_entities_to_entity_dialog is running')

    came_from = request.params.get('came_from', '/')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    if not entity:
        transaction.abort()
        return Response('Can not find a client with id: %s' % entity_id, 500)

    logger.debug('came_from: %s' % came_from)

    return {
        'has_permission': PermissionChecker(request),
        'milliseconds_since_epoch': milliseconds_since_epoch,
        'came_from': came_from,
        'entity': entity
    }


@view_config(
    route_name='append_user_to_entity'
)
def append_user_to_entity(request):

    logged_in_user = get_logged_in_user(request)
    utc_now = datetime.datetime.now(pytz.utc)

    came_from = request.params.get('came_from', '/')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()
    if not entity:
        transaction.abort()
        return Response('Can not find a entity with id: %s' % entity_id, 500)

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
    logger.debug(entity.users)

    if entity.entity_type == "Client":
        entity_user = ClientUser()
        entity_user.client = entity
    elif entity.entity_type == "Project":
        entity_user = ProjectUser()
        entity_user.project = entity
    elif entity.entity_type == "Department":
        entity_user = DepartmentUser()
        entity_user.department = entity

    entity_user.role = role
    entity_user.user = user
    entity_user.date_created = utc_now
    entity_user.created_by = logged_in_user

    DBSession.add(entity_user)

    if user not in entity.users:
        entity.users.append(user)
        request.session.flash('success:%s is added to %s user list' % (user.name, entity.name))

    logger.debug(entity.users)

    return Response(
        'Successfully %s is appended to %s as %s' % (user.name,
                                                     entity.name,
                                                     role_name
                                                   )
    )


@view_config(
    route_name='get_entity_role_user',
    renderer='json'
)
def get_entity_role_user(request):

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()
    if not entity:
        transaction.abort()
        return Response('Can not find a entity with id: %s' % entity_id, 500)

    role_name = request.params.get('role_name', None)
    role = query_role(role_name)

    entity_user = None
    logger.debug("role_name %s" % role_name)
    logger.debug("role %s" % role)

    if role:
        query_string = '%(class_name)sUser.query.filter(%(class_name)sUser.role_id == role.id).filter(%(class_name)sUser.%(attr_name)s == entity_id)'
        q = eval(query_string % {'class_name': entity.entity_type,
                             'attr_name': '%s_id' % entity.entity_type.lower()
                            })

        logger.debug("query_string %s" % query_string % {'class_name': entity.entity_type,
                             'attr_name': '%s_id' % entity.entity_type.lower()
                            })
        entity_user = q.first()

        logger.debug("entity_user %s" % entity_user)

    user_id = request.params.get('user_id', -1)
    user = User.query.filter(User.id == user_id).first()

    if user:
        query_string = '%(class_name)sUser.query.filter(%(class_name)sUser.user_id == user_id).filter(%(class_name)sUser.%(attr_name)s == entity_id)'
        q = eval(query_string % {'class_name': entity.entity_type,
                             'attr_name': '%s_id' % entity.entity_type.lower()
                            })
        entity_user = q.first()

    if not entity_user:

        return { 'id': '',
            'name': '',
            'role_name': ''
        }

    return {
            'id': entity_user.user.id,
            'name': entity_user.user.name,
            'role_name': entity_user.role.name
    }










