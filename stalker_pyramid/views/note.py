# -*- coding: utf-8 -*-
import pytz
import logging
import datetime
import os

import transaction
from pyramid.response import Response
from pyramid.view import view_config
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message, Attachment

from stalker.db.session import DBSession
from stalker import (db, Entity, Note, Type)

from stalker_pyramid.views import (get_logged_in_user,
                                   milliseconds_since_epoch,
                                   StdErrToHTMLConverter,
                                   get_multi_integer, dummy_email_address)
from stalker_pyramid.views.link import replace_img_data_with_links, \
    MediaManager
# from stalker_pyramid.views.task import get_task_full_path, \
#     get_task_external_link
from stalker_pyramid.views.type import query_type


#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)


@view_config(
    route_name='create_note'
)
def create_note(request):
    """Creates note for requested an entity
    """
    logger.debug('create_note is running')

    utc_now = datetime.datetime.now(pytz.utc)

    logged_in_user = get_logged_in_user(request)

    entity_ids = get_multi_integer(request, 'entity_ids')
    entities = Entity.query.filter(Entity.id.in_(entity_ids)).all()

    content = request.params.get('content', None)

    logger.debug('content : %s ' % content)

    content_as_text = request.params.get('content_as_text', content)
    note_type = request.params.get('type', None)

    if not entities:
        transaction.abort()
        return Response('There is no entity with id: %s' % entity_ids, 500)

    if not content:
        transaction.abort()
        return Response('No content', 500)

    if content == '':
        transaction.abort()
        return Response( 'No content', 500)

    if not note_type:
        transaction.abort()
        return Response( 'No type', 500)

    if note_type == '':
        transaction.abort()
        return Response('No type', 500)

    from stalker_pyramid.views.task import get_task_full_path, get_task_external_link
    attachments = []
    total_attachement_size = 0
    if content:
        # convert images to Links
        content, links = replace_img_data_with_links(content)

        if links:
            # update created_by attributes of links
            for link in links:
                link.created_by = logged_in_user

                # manage attachments
                link_full_path = \
                    MediaManager.convert_file_link_to_full_path(link.full_path)
                link_data = open(link_full_path, "rb").read()

                link_extension = os.path.splitext(link.filename)[1].lower()
                mime_type = ''
                if link_extension in ['.jpeg', '.jpg']:
                    mime_type = 'image/jpg'
                elif link_extension in ['.png']:
                    mime_type = 'image/png'

                # check the link size
                # do not send attachments bigger than 10 MB
                try:
                    current_link_size = os.path.getsize(link_full_path)
                    if total_attachement_size < 10485760 \
                       and current_link_size < 10485760:
                        attachment = Attachment(
                            link.filename,
                            mime_type,
                            link_data
                        )
                        attachments.append(attachment)
                        total_attachement_size += current_link_size
                except OSError:
                    # link doesn't exist
                    pass

            DBSession.add_all(links)

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

            for watcher in task.watchers:
                recipients.append(watcher.email)

            # also add other note owners to the list
            for note in task.notes:
                note_created_by = note.created_by
                if note_created_by:
                    recipients.append(note_created_by.email)

            # make the list unique
            recipients = list(set(recipients))

            logger.debug('sending %s note to %s' % (task.id, recipients))

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
                         'note': content_as_text
                     },
                html='<b>%(user)s</b> has added the following note to '
                     '%(task_external_link)s:<br><br>%(note)s' %
                     {
                         'user': logged_in_user.name,
                         'task_external_link': get_task_external_link(task.id),
                         'note': content_as_text
                     },
                attachments=attachments
            )
            try:
                mailer.send_to_queue(message)
            except ValueError:
                # no internet connection
                # or not a maildir
                pass

    logger.debug('note is created by %s' % logged_in_user.name)
    request.session.flash('success: note is created by %s' % logged_in_user.name)

    return Response('Task note is created')


def create_simple_note(content, n_type, html_class, code, logged_in_user, utc_now):

    note_type = query_type('Note', n_type)
    note_type.html_class = html_class
    note_type.code = code

    note = Note(
        content=content,
        created_by=logged_in_user,
        date_created=utc_now,
        date_updated=utc_now,
        type=note_type
    )
    DBSession.add(note)

    return note


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

    if entity.entity_type != "User":
        sql_query = """
        select
            "User_SimpleEntities".id as user_id,
            "User_SimpleEntities".name as name,
            "Users_Thumbnail_Links".full_path as full_path,
            "Notes_SimpleEntities".id as note_id,
            "Notes_SimpleEntities".description as description,
            "Notes_SimpleEntities".date_created as date_created,
            "Notes_Types_SimpleEntities".id as note_type_id,
            "Notes_Types_SimpleEntities".name as note_type_name,
            "Notes_Types_SimpleEntities".html_class as html_class,
            dailies.name as daily_name,
            dailies.id as daily_id,
            "Entity_Notes".entity_id as entity_id,
            "Entities_SimpleEntities".name as entity_name

        from "Notes"
        join "SimpleEntities" as "Notes_SimpleEntities" on "Notes_SimpleEntities".id = "Notes".id
        left outer join "SimpleEntities" as "Notes_Types_SimpleEntities" on "Notes_Types_SimpleEntities".id = "Notes_SimpleEntities".type_id
        join "SimpleEntities" as "User_SimpleEntities" on "Notes_SimpleEntities".created_by_id = "User_SimpleEntities".id
        left outer join "Links" as "Users_Thumbnail_Links" on "Users_Thumbnail_Links".id = "User_SimpleEntities".thumbnail_id
        join "Entity_Notes" on "Notes".id = "Entity_Notes".note_id
        left outer join (
            select
                "Daily_SimpleEntities".name,
                "Daily_SimpleEntities".id,
                "Daily_Notes".note_id

            from "Dailies"
            join "SimpleEntities" as "Daily_SimpleEntities" on "Daily_SimpleEntities".id = "Dailies".id
            join "Entity_Notes" as "Daily_Notes" on "Daily_Notes".entity_id = "Dailies".id
        ) as dailies on dailies.note_id = "Entity_Notes".note_id
        join "SimpleEntities" as "Entities_SimpleEntities" on "Entity_Notes".entity_id = "Entities_SimpleEntities".id
        where "Entity_Notes".entity_id = %(entity_id)s
        order by "Notes_SimpleEntities".date_created desc
        """
    else:
        sql_query = """
        select
            "User_SimpleEntities".id as user_id,
            "User_SimpleEntities".name as name,
            "Users_Thumbnail_Links".full_path as full_path,
            "Notes_SimpleEntities".id as note_id,
            "Notes_SimpleEntities".description as description,
            "Notes_SimpleEntities".date_created as date_created,
            "Notes_Types_SimpleEntities".id as note_type_id,
            "Notes_Types_SimpleEntities".name as note_type_name,
            "Notes_Types_SimpleEntities".html_class as html_class,
            '' as daily_name,
            -1 as daily_id,
            "Entity_Notes".entity_id as entity_id,
            "ParentTasks".path_names as entity_name

        from "Notes"
            join "SimpleEntities" as "Notes_SimpleEntities" on "Notes_SimpleEntities".id = "Notes".id
            left outer join "SimpleEntities" as "Notes_Types_SimpleEntities" on "Notes_Types_SimpleEntities".id = "Notes_SimpleEntities".type_id
            join "SimpleEntities" as "User_SimpleEntities" on "Notes_SimpleEntities".created_by_id = "User_SimpleEntities".id
            left outer join "Links" as "Users_Thumbnail_Links" on "Users_Thumbnail_Links".id = "User_SimpleEntities".thumbnail_id
            join "Entity_Notes" on "Notes".id = "Entity_Notes".note_id
            join (%(recursive_task_query)s) as "ParentTasks" on "Entity_Notes".entity_id = "ParentTasks".id
            join "Task_Resources" on "Task_Resources".task_id = "ParentTasks".id
        where "Task_Resources".resource_id = %(entity_id)s and "Notes_Types_SimpleEntities".name != 'Auto Extended Time'
        order by "Notes_SimpleEntities".date_updated desc
        limit 50
        """

    from stalker_pyramid.views.task import generate_recursive_task_query
    sql_query = sql_query % {
        'entity_id': entity_id,
        'recursive_task_query': generate_recursive_task_query()
    }

    result = DBSession.connection().execute(sql_query)

    return_data = [
        {
            'created_by_id': r["user_id"],
            'created_by_name': r["name"],
            'created_by_thumbnail': r["full_path"],
            'note_id': r["note_id"],
            'content': r["description"],
            'created_date': milliseconds_since_epoch(r["date_created"]),
            'note_type_id': r["note_type_id"],
            'note_type_name': r["note_type_name"],
            'note_type_color': r["html_class"],
            'daily_name': r["daily_name"],
            'daily_id': r["daily_id"],
            'entity_id': r["entity_id"],
            'entity_name': r["entity_name"],
            'related_entity_id': entity_id,
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
