# -*- coding: utf-8 -*-
import pytz
import datetime

from pyramid.httpexceptions import HTTPServerError, HTTPFound
from pyramid.view import view_config

from stalker.db.session import DBSession
from stalker import User, Department, Entity, Studio, Project, defaults, \
    DepartmentUser

import logging
import transaction
from webob import Response
import stalker_pyramid
from stalker_pyramid.views import (PermissionChecker, get_logged_in_user,
                                   log_param, get_tags, StdErrToHTMLConverter)
from stalker_pyramid.views.role import query_role

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.WARNING)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='create_department'
)
def create_department(request):
    """creates a new Department
    """

    logger.debug('***create department method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    came_from = request.params.get('came_from', '/')
    name = request.params.get('name')

    logger.debug('new department name : %s' % name)

    if name:
        description = request.params.get('description')

        lead_id = request.params.get('lead_id', -1)
        lead = User.query.filter_by(id=lead_id).first()

        # Tags
        tags = get_tags(request)

        logger.debug('new department description : %s' % description)
        logger.debug('new department lead : %s' % lead)
        logger.debug('new department tags : %s' % tags)

        try:
            new_department = Department(
                name=name,
                description=description,
                created_by=logged_in_user,
                tags=tags
            )

            # # create a new Department_User with lead role
            # lead_role = query_role('Lead')
            # dpu = DepartmentUser(
            #     department=new_department,
            #     user=lead,
            #     role=lead_role
            # )

            DBSession.add(new_department)
            # DBSession.add(dpu)

            logger.debug('added new department successfully!')

            request.session.flash(
                'success:Department <strong>%s</strong> is created '
                'successfully!' % name
            )

            logger.debug('***create department method ends ***')

        except BaseException as e:
            request.session.flash('error: %s' % e)
            HTTPFound(location=came_from)
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        response = Response(
            'There are missing parameters: '
            'name: %s' % name, 500
        )
        transaction.abort()
        return response

    response = Response('successfully created %s department!' % name)
    return response


@view_config(
    route_name='update_department'
)
def update_department(request):
    """updates an Department
    """

    logger.debug('***update department method starts ***')

    logged_in_user = get_logged_in_user(request)

    # get params
    came_from = request.params.get('came_from', '/')
    department_id = request.matchdict.get('id', -1)
    department = Department.query.filter_by(id=department_id).first()

    name = request.params.get('name')

    logger.debug('department : %s' % department)
    logger.debug('department new name : %s' % name)

    if department and name:

        description = request.params.get('description')

        lead_id = request.params.get('lead_id', -1)
        lead = User.query.filter_by(id=lead_id).first()

        # Tags
        tags = get_tags(request)

        logger.debug('department new description : %s' % description)
        logger.debug('department new lead : %s' % lead)
        logger.debug('department new tags : %s' % tags)

        # update the department
        department.name = name
        department.description = description

        department.lead = lead
        lead_role = query_role('Lead')
        # get the current department lead
        dpu = DepartmentUser.query\
            .filter(DepartmentUser.department == department)\
            .filter(DepartmentUser.role == lead_role)\
            .first()
        if not dpu:
            dpu = DepartmentUser(
                department=department,
                user=lead,
                role=lead_role
            )
            DBSession.add(dpu)
        else:
            dpu.user = lead

        department.tags = tags
        department.updated_by = logged_in_user
        utc_now = datetime.datetime.now(pytz.utc)
        department.date_updated = utc_now

        DBSession.add(department)

        logger.debug('department is updated successfully')

        request.session.flash(
            'success:Department <strong>%s</strong> '
            'is updated successfully' % name
        )

        logger.debug('***update department method ends ***')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'department_id')
        log_param(request, 'name')
        HTTPServerError()

    return Response('Successfully updated department: %s' % department_id)


@view_config(
    route_name='view_entity_department',
    renderer='templates/department/view/view_department.jinja2'
)
def view_entity_department(request):
    """create department dialog
    """
    logger.debug('***view_entity_department method starts ***')

    logged_in_user = get_logged_in_user(request)

    entity_id = request.matchdict.get('eid', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('entity_type     : %s' % entity.entity_type)

    department_id = request.matchdict.get('id', -1)
    department = Department.query.filter_by(id=department_id).first()

    studio = Studio.query.first()
    projects = Project.query.all()

    return {
        'entity': entity,
        'department': department,
        'actions': defaults.actions,
        'logged_in_user': logged_in_user,
        'stalker_pyramid': stalker_pyramid,
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'projects': projects
    }


@view_config(
    route_name='get_departments',
    renderer='json'
)
def get_departments(request):
    """returns all the departments in the database
    """
    return [
        {
            'id': dep.id,
            'name': dep.name
        }
        for dep in Department.query.order_by(Department.name.asc()).all()
    ]


@view_config(
    route_name='get_department',
    renderer='json'
)
def get_department(request):
    """returns all the departments in the database
    """
    department_id = request.matchdict.get('id', -1)
    department = Department.query.filter_by(id=department_id).first()

    return[
        {
            'id': department.id,
            'name': department.name,
            'thumbnail_full_path': department.thumbnail.full_path if department.thumbnail else None,
        }
    ]


@view_config(
    route_name='get_departments',
    renderer='json'
)
def get_departments(request):
    """returns all the departments in the database
    """
    sql_query = """select
    "SimpleEntities".id
    "SimpleEntities".name
from "Departments"
join "SimpleEntities" on "Departments".id = "SimpleEntities".id
order by "SimpleEntities".name
"""

    result = DBSession.connection().execute(sql_query)

    return [
        {
            'id': r[0],
            'name': r[1]
        }
        for r in result.fetchall()
    ]


@view_config(
    route_name='get_entity_departments',
    renderer='json'
)
@view_config(
    route_name='get_user_departments',
    renderer='json'
)
def get_entity_departments(request):
    """
    """
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    update_department_permission = \
        PermissionChecker(request)('Update_Department')

    departments = []

    lead_role = query_role('Lead')
    has_update_user_permission = PermissionChecker(request)('Update_User')

    # TODO: Update this to use raw SQL
    for department in entity.departments:

        lead = DepartmentUser.query\
            .filter_by(department=department)\
            .filter_by(role=lead_role)\
            .first()

        dep = {
            'name': department.name,
            'id': department.id,
            'lead_id': lead.id if lead else None,
            'lead_name': lead.name if lead else None,
            'thumbnail_full_path':
                department.thumbnail.full_path if department.thumbnail else None,
            'created_by_id': department.created_by.id,
            'created_by_name': department.created_by.name,
            'description': len(department.users),
            'item_view_link': '/departments/%s/view' % department.id
        }

        if update_department_permission and has_update_user_permission:
            dep['item_update_link'] = \
                '/departments/%s/update/dialog' % department.id
            dep['item_remove_link'] = '/entities/%s/%s/remove/dialog?came_from=%s' % (entity.id, department.id, request.current_route_path())
        departments.append(dep)

    return departments


@view_config(
    route_name='delete_department_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_department_dialog(request):
    """deletes the department with the given id
    """
    logger.debug('delete_department_dialog is starts')

    department_id = request.matchdict.get('id')
    department = Department.query.get(department_id)

    action = '/departments/%s/delete'% department_id

    came_from = request.params.get('came_from', '/')

    message = 'Are you sure you want to <strong>delete %s Department</strong>?'% department.name

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='delete_department',
    permission='Delete_Department'
)
def delete_department(request):
    """deletes the department with the given id
    """
    department_id = request.matchdict.get('id')
    department = Department.query.get(department_id)
    name = department.name

    if not department:
        transaction.abort()
        return Response(
            'Can not find a Department with id: %s' % department_id, 500
        )

    try:
        DBSession.delete(department)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    request.session.flash(
        'success: <strong>%s Department</strong> is deleted '
        'successfully' % name
    )

    return Response('Successfully deleted department: %s' % department_id)
