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
import logging
import datetime

import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message


from stalker.db import DBSession
from stalker import (Entity, Note, Type)

from stalker_pyramid.views import (get_logged_in_user,
                                   milliseconds_since_epoch,
                                   StdErrToHTMLConverter, local_to_utc,
                                   get_multi_integer, dummy_email_address)
from stalker_pyramid.views.task import get_task_full_path, \
    get_task_external_link
from stalker_pyramid.views.type import query_type


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='create_note'
)
def create_note(request):
    """Creates note for requested an entity
    """
    logger.debug('create_note is running')

    utc_now = local_to_utc(datetime.datetime.now())
    logged_in_user = get_logged_in_user(request)

    entity_ids = get_multi_integer(request, 'entity_ids')
    entities = Entity.query.filter(Entity.id.in_(entity_ids)).all()

    content = request.params.get('message', None)
    note_type = request.params.get('type', None)

    if not entities:
        transaction.abort()
        return Response('There is no entity with id: %s' % entity_ids, 500)

    logger.debug('content %s' % content)

    if not content:
        transaction.abort()
        return Response( 'No content', 500)

    if content == '':
        transaction.abort()
        return Response( 'No content', 500)

    if not note_type:
        transaction.abort()
        return Response( 'No type', 500)

    if note_type == '':
        transaction.abort()
        return Response( 'No type', 500)

    note_type = query_type('Note', note_type)
    note = Note(
        content=content,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )

    from stalker import Task
    DBSession.add(note)
    mailer = get_mailer(request)

    for entity in entities:
        entity.notes.append(note)
        if isinstance(entity, Task):
            task = entity

            recipients = []
            for resource in task.resources:
                recipients.append(resource.email)

            for responsible in task.responsible:
                recipients.append(responsible.email)

            # create an email
            task_full_path = get_task_full_path(task.id)
            message = Message(
                subject='Note Added: "%(task_full_path)s"' % {
                    'task_full_path': task_full_path
                },
                sender=dummy_email_address,
                recipients=recipients,
                body='%(user)s has added the following note to '
                     '%(task_full_path)s:\n\n%(note)s' %
                     {
                         'user': logged_in_user.name,
                         'task_full_path': task_full_path,
                         'note': content
                     },
                html='<b>%(user)s</b> has added the following note to '
                     '%(task_external_link)s:<br><br>%(note)s' %
                     {
                         'user': logged_in_user.name,
                         'task_external_link': get_task_external_link(task.id),
                         'note': content
                     }
            )
            mailer.send_to_queue(message)

    logger.debug('note is created by %s' % logged_in_user.name)
    request.session.flash('success: note is created by %s' % logged_in_user.name)

    return Response('Task note is created')


@view_config(
    route_name='get_entity_notes',
    renderer='json'
)
def get_entity_notes(request):
    """RESTful version of getting all notes of a task
    """
    logger.debug('get_entity_notes is running')

    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter(Entity.id == entity_id).first()

    if not entity:
        transaction.abort()
        return Response('There is no entity with id: %s' % entity_id, 500)

    sql_query = """
        select  "User_SimpleEntities".id as user_id,
                "User_SimpleEntities".name,
                "Users_Thumbnail_Links".full_path,
                "Notes_SimpleEntities".id as note_id,
                "Notes_SimpleEntities".description,
                "Notes_SimpleEntities".date_created,
                "Notes_Types_SimpleEntities".id,
                "Notes_Types_SimpleEntities".name,
                "Notes_Types_SimpleEntities".html_class,
                dailies.name as daily_name,
                dailies.id as daily_id

        from "Notes"
        join "SimpleEntities" as "Notes_SimpleEntities" on "Notes_SimpleEntities".id = "Notes".id
        left outer join "SimpleEntities" as "Notes_Types_SimpleEntities" on "Notes_Types_SimpleEntities".id = "Notes_SimpleEntities".type_id
        join "SimpleEntities" as "User_SimpleEntities" on "Notes_SimpleEntities".created_by_id = "User_SimpleEntities".id
        left outer join "Links" as "Users_Thumbnail_Links" on "Users_Thumbnail_Links".id = "User_SimpleEntities".thumbnail_id
        join "Entity_Notes" as "Search_Entity_Notes" on "Notes".id = "Search_Entity_Notes".note_id
        left outer join (
        select
               "Daily_SimpleEntities".name,
               "Daily_SimpleEntities".id,
               "Daily_Notes".note_id

            from "Dailies"
            join "SimpleEntities" as "Daily_SimpleEntities" on "Daily_SimpleEntities".id = "Dailies".id
            join "Entity_Notes" as "Daily_Notes" on "Daily_Notes".entity_id = "Dailies".id
         ) as dailies on dailies.note_id = "Search_Entity_Notes".note_id
        where "Search_Entity_Notes".entity_id = %(entity_id)s
        order by "Notes_SimpleEntities".date_created desc
        """

    sql_query = sql_query % {'entity_id': entity_id}

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'created_by_id': r[0],
            'created_by_name': r[1],
            'created_by_thumbnail': r[2],
            'note_id': r[3],
            'content': r[4],
            'created_date': milliseconds_since_epoch(r[5]),
            'note_type_id': r[6],
            'note_type_name': r[7],
            'note_type_color': r[8],
            'daily_name': r[9],
            'daily_id': r[10]
        }
        for r in result.fetchall()
    ]
    return return_data


@view_config(
    route_name='delete_note_dialog',
    renderer='templates/modals/confirm_dialog.jinja2'
)
def delete_note_dialog(request):
    """deletes the note with the given id
    """
    logger.debug('delete_note_dialog is starts')

    note_id = request.matchdict.get('id')

    action = '/notes/%s/delete' % note_id
    came_from = request.params.get('came_from', '/')
    message = 'Are you sure to delete this note?'

    logger.debug('action: %s' % action)

    return {
        'message': message,
        'came_from': came_from,
        'action': action
    }


@view_config(
    route_name='delete_note',
    permission='Delete_Note'
)
def delete_note(request):
    """deletes the task with the given id
    """
    logger.debug('delete_note is starts')

    note_id = request.matchdict.get('id')
    note = Note.query.filter_by(id=note_id).first()

    if not note:
        transaction.abort()
        return Response('Can not find an Note with id: %s' % note_id, 500)

    try:
        DBSession.delete(note)
        transaction.commit()
    except Exception as e:
        transaction.abort()
        c = StdErrToHTMLConverter(e)
        transaction.abort()
        return Response(c.html(), 500)

    return Response('Successfully deleted note')
