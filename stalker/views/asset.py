# -*- coding: utf-8 -*-
# Copyright (c) 2009-2013, Erkan Ozgur Yilmaz
# 
# This module is part of Stalker and is released under the BSD 2
# License: http://www.opensource.org/licenses/BSD-2-Clause

from pyramid.httpexceptions import HTTPServerError
from pyramid.security import authenticated_userid
from pyramid.view import view_config
from stalker import User, Project, Type, StatusList, Status, Asset
from stalker.db import DBSession

import logging
from stalker import log
logger = logging.getLogger(__name__)
logger.setLevel(log.logging_level)

@view_config(
    route_name='add_asset',
    renderer='templates/asset/add_asset.jinja2',
    permission='Add_Asset'
)
def add_asset(request):
    """runs when adding a new Asset instance
    """
    login = authenticated_userid(request)
    logged_in_user = User.query.filter_by(login=login).first()
    
    if 'submitted' in request.params:
        logger.debug('request.params["submitted"]: %s' % request.params['submitted'])
        
        if request.params['submitted'] == 'add':
            
            if 'name' in request.params and \
               'code' in request.params and \
               'description' in request.params and \
               'type_name' in request.params and \
               'status_list_id' in request.params and \
               'status_id' in request.params:
                
                logger.debug('request.params["name"]: %s' %
                             request.params['name'])
                logger.debug('request.params["code"]: %s' %
                             request.params['name'])
                logger.debug('request.params["description"]: %s' %
                             request.params['description'])
                # logger.debug('request.params["project_id"]: %s' %
                #              request.params['project_id'])
                logger.debug('request.params["type_name"]: %s' %
                             request.params['type_name'])
                logger.debug('request.params["status_list_id"]: %s' %
                             request.params['status_list_id'])
                logger.debug('request.params["status_id"]: %s' %
                             request.params['status_id'])
                
                project_id = request.matchdict['project_id']
                
                # type will always return with a type name
                type_name = request.params['type_name']
                
                project = Project.query.filter_by(id=project_id).first()
                type_ = Type.query\
                    .filter_by(target_entity_type='Asset')\
                    .filter_by(name=type_name)\
                    .first()
                
                if type_ is None:
                    # create a new Type
                    type_ = Type(
                        name=type_name,
                        code=type_name,
                        target_entity_type='Asset'
                    )
                
                # get the status_list
                status_list = StatusList.query.filter_by(
                    target_entity_type='Asset'
                ).first()
                
                logger.debug('status_list: %s' % status_list)
                
                # there should be a status_list
                if status_list is None:
                    return HTTPServerError(
                        detail='No StatusList found'
                    )
                
                status_id = int(request.params['status_id'])
                logger.debug('status_id: %s' % status_id)
                status = Status.query.filter_by(id=status_id).first()
                logger.debug('status: %s' % status)
                
#                logger.debug('status: %s' % status)
#                logger.debug('status_list: %s' % status_list)
#                logger.debug('status in status_list: %s' % status in status_list)
                
                # get the info
                try:
                    logger.debug('*****************************')
                    logger.debug('code: %s' % request.params['code'])
                    new_asset = Asset(
                        name=request.params['name'],
                        code=request.params['code'],
                        description=request.params['description'],
                        project=project,
                        type=type_,
                        status_list=status_list,
                        status=status,
                        created_by=logged_in_user
                    )
                    
                    logger.debug('new_asset.status: ' % new_asset.status)
                    
                    #DBSession.add(new_asset)
                except (AttributeError, TypeError) as e:
                    logger.debug(e.message)
                else:
                    DBSession.add(new_asset)
                    #try:
                    #    transaction.commit()
                    #except IntegrityError as e:
                    #    logger.debug(e.message)
                    #    transaction.abort()
                    #else:
                    #    logger.debug('flushing the DBSession, no problem here!')
                    #    DBSession.flush()
                    #    logger.debug('finished adding Asset')
            else:
                logger.debug('there are missing parameters')
                def get_param(param):
                    if param in request.params:
                        logger.debug('%s: %s' % (param, request.params[param]))
                    else:
                        logger.debug('%s not in params' % param)
                get_param('name')
                get_param('code')
                get_param('description')
                get_param('project_id')
                get_param('type_name')
                get_param('status_list_id')
                get_param('status_id')

    project = Project.query.filter_by(id=request.matchdict['project_id']).first()

    return {
        'project': project,
        'projects': Project.query.all(),
        'types': Type.query.filter_by(target_entity_type='Asset').all(),
        'status_list':
            StatusList.query.filter_by(target_entity_type='Asset').first()
    }


@view_config(
    route_name='view_asset',
    renderer='templates/asset/view_asset.jinja2'
)
def view_asset(request):
    """runs when viewing an asset
    """

    login = authenticated_userid(request)
    logged_in_user = User.query.filter_by(login=login).first()

    asset_id = request.matchdict['asset_id']
    asset = Asset.query.filter_by(id=asset_id).first()

    return {
        'user': logged_in_user,
        'asset': asset
    }


@view_config(
    route_name='get_assets',
    renderer='json',
    permission='View_Asset'
)
def get_assets(request):
    """returns all the Assets of a given Project
    """
    proj_id = request.matchdict['project_id']
    return [
        {
            'id': asset.id,
            'name': asset.name,
            'type': asset.type.name,
            'status': asset.status.name,
            'user_id': asset.created_by.id,
            'user_link': '<a href="%s">%s</a>' %
                         ('view/user/%i' % asset.created_by.id,
                          asset.created_by.name),
            'user_name': asset.created_by.name,
            'description': asset.description
        }
        for asset in Asset.query.filter_by(project_id=proj_id).all()
    ]
