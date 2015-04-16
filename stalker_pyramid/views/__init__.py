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
import calendar
import datetime

from pyramid.httpexceptions import HTTPServerError, HTTPForbidden
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.security import has_permission, authenticated_userid

from stalker import log, User, Tag
from stalker.db import DBSession
import transaction


logger = logging.getLogger(__name__)
logger.setLevel(log.logging_level)

# this is a dummy mail address change it in the config (*.ini) file
dummy_email_address = "Stalker Pyramid <stalker.pyramid@stalker.pyramid.com>"


def utc_to_local(utc_dt):
    """converts utc time to local time

    based on the answer of J.F. Sebastian on
    http://stackoverflow.com/questions/4563272/how-to-convert-a-python-utc-datetime-to-a-local-datetime-using-only-python-stand/13287083#13287083
    """
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= datetime.timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)


def local_to_utc(local_dt):
    """converts local datetime to utc datetime

    based on the answer of J.F. Sebastian on
    http://stackoverflow.com/questions/4563272/how-to-convert-a-python-utc-datetime-to-a-local-datetime-using-only-python-stand/13287083#13287083
    """
    # get the utc_dt as if the local_dt is utc and calculate the timezone
    # difference and add it to the local dt object
    logger.debug('utc_to_local(local_dt) : %s' % utc_to_local(local_dt))
    logger.debug('utc - local            : %s' % (utc_to_local(local_dt) - local_dt))
    logger.debug('local - (utc - local)  : %s' % (local_dt - (utc_to_local(local_dt) - local_dt)))
    return local_dt - (utc_to_local(local_dt) - local_dt)


def to_seconds(timing, unit):
    """converts timing to seconds"""
    return timing*seconds_in_unit(unit)


def seconds_in_unit(unit):

    if unit == 'min':
        return 60
    elif 'h':
        return 3600
    elif 'd':
        return 32400
        # TODO: this is not true, please use: stalker.defaults.daily_working_hours
    elif 'w':
        return 183600
        # TODO: this is not true, please use: stalker.defaults.weekly_working_hours
    elif 'm':
        return 734400
        # TODO: this is not true, please use: 4 * stalker.defaults.weekly_working_hours
    elif 'y':
        return 9573418
        # TODO: this is not true, please use: stalker.defaults.yearly_working_days * stalker.defaults.daily_working_hours
    else:
        return 0



class StdErrToHTMLConverter():
    """Converts stderr, stdout messages of TaskJuggler to html

    :param error: An exception
    """

    formatChars = {
        '\e[1m': '<strong>',
        '\e[21m': '</strong>',
        '\e[2m':  '<span class="dark">',
        '\e[22m': '</span>',
        '\n': '<br>',
        '\x1b[34m': '<span class="alert alert-info" style="overflow-wrap: break-word">',
        '\x1b[35m': '<span class="alert alert-warning" style="overflow-wrap: break-word">',
        '\x1b[31m': '<span class="alert alert-error" style="overflow-wrap: break-word">',
        '\x1b[0m': '</span>',
        'Warning:': '<strong>Warning:</strong>',
        'Info:': '<strong>Info:</strong>',
        'Error:': '<strong>Error:</strong>',
    }

    def __init__(self, error):
        if isinstance(error, Exception):
            self.error_message = str(error)
        else:
            self.error_message = error

    def replace_tjp_ids(self, message):
        """replaces tjp ids in error messages with proper links
        """
        import re
        pattern = r"Task[\w0-9\._]+[0-9]"

        all_tjp_ids = re.findall(pattern, message)
        new_message = message
        for tjp_id in all_tjp_ids:
            entity_type_and_id = tjp_id.split('.')[-1]
            entity_type = entity_type_and_id.split('_')[0]
            entity_id = entity_type_and_id.split('_')[1]

            # get the entity
            # entity = Entity.query.filter(Entity.id == entity_id).first()
            # assert isinstance(entity, Entity)

            link = '/%(class_name)ss/%(id)s/view' % {
                'class_name': entity_type.lower(),
                'id': entity_id
            }
            name = '%(name)s' % {
                'name': entity_type_and_id,
                # 'type': entity.entity_type
            }

            path = '<a href="%(link)s">%(name)s</a>' % {
                'link': link,
                'name': name
            }

            new_message = new_message.replace(tjp_id, path)
        return new_message

    def html(self, replace_links=False):
        """returns the html version of the message
        """
        # convert the error message to a string
        if isinstance(self.error_message, list):
            output_buffer = []
            for msg in self.error_message:
                # join the message in to <p> elements
                output_buffer.append('%s' % msg.strip())

            # convert the list to string
            str_buffer = '\n'.join(output_buffer)
        else:
            str_buffer = self.error_message

        if replace_links:
            str_buffer = self.replace_tjp_ids(str_buffer)

        # for each formatChar replace them with an html tag
        for key in self.formatChars.keys():
            str_buffer = str_buffer.replace(key, self.formatChars[key])
        # put everything inside a p
        str_buffer = '<p>%s</p>' % str_buffer

        return str_buffer


class PermissionChecker(object):
    """Helper class for permission check
    """

    def __init__(self, request):
        self.has_permission = has_permission
        self.request = request

    def __call__(self, perm):
        return self.has_permission(perm, self.request.context, self.request)


def multi_permission_checker(request, permissions):
    pc = PermissionChecker(request)
    return all(map(pc, permissions))


def log_param(request, param):
    if param in request.params:
        logger.debug('%s: %s' % (param, request.params[param]))
    else:
        logger.debug('%s not in params' % param)


@view_config(
    context=HTTPServerError
)
def server_error(exc, request):
    msg = exc.args[0] if exc.args else ''
    response = Response('Server Error: %s' % msg, 500)
    transaction.abort()
    return response


def get_time(request, time_attr):
    """Extracts a time object from the given request

    :param request: the request object
    :param time_attr: the attribute name
    :return: datetime.timedelta
    """
    time_part = datetime.datetime.strptime(
        request.params[time_attr][:-4],
        '%a, %d %b %Y %H:%M:%S'
    )

    return datetime.timedelta(
        hours=time_part.hour,
        minutes=time_part.minute
    )


def get_date(request, date_attr):
    """Extracts a UTC datetime object from the given request

    :param request: the request instance
    :param date_attr: the attribute name
    :return: datetime.datetime
    """
    # Always work with UTC
    return datetime.datetime.strptime(
        request.params[date_attr][:-4],
        '%a, %d %b %Y %H:%M:%S'
    )


def get_date_range(request, date_range_attr):
    """Extracts a UTC datetime object from the given request

    :param request: the request instance
    :param date_range_attr: the attribute name
    :return: datetime.datetime
    """
    date_range_string = request.params.get(date_range_attr)
    start_str, end_str = date_range_string.split(' - ')
    start = datetime.datetime.strptime(start_str, '%m/%d/%Y')
    end = datetime.datetime.strptime(end_str, '%m/%d/%Y')
    return start, end


def get_datetime(request, date_attr, time_attr):
    """Extracts a UTC  datetime object from the given request
    :param request: the request object
    :param date_attr: the attribute name
    :return: datetime.datetime
    """
    date_part = datetime.datetime.strptime(
        request.params[date_attr][:-4],
        '%a, %d %b %Y %H:%M:%S'
    )

    time_part = datetime.datetime.strptime(
        request.params[time_attr][:-4],
        '%a, %d %b %Y %H:%M:%S'
    )

    # update the time values of date_part with time_part
    return date_part.replace(
        hour=time_part.hour,
        minute=time_part.minute,
        second=time_part.second,
        microsecond=time_part.microsecond
    )


def get_logged_in_user(request):
    """Returns the logged in user

    :param request: Request object
    """
    user = User.query.filter_by(login=authenticated_userid(request)).first()
    if not user:
        raise HTTPForbidden(request)
    return user


def get_multi_integer(request, attr_name, method='POST'):
    """Extracts multi data from request.POST

    :param request: Request object
    :param attr_name: Attribute name to extract data from
    :return:
    """
    data = request.POST
    if method == 'GET':
        data = request.GET

    return [int(attr) for attr in data.getall(attr_name)]


def get_multi_string(request, attr_name):
    """Extracts multi data from request.POST

    :param request: Request object
    :param attr_name: Attribute name to extract data from
    :return:
    """
    return [attr for attr in request.GET.getall(attr_name)]


def get_color_as_int(request, attr_name):
    """Extracts a color from request
    """
    return int(request.params.get(attr_name, '#000000')[1:], 16)


def get_tags(request, parameter='tags[]'):
    """Extracts Tags from the given request

    :param request: Request object
    :return: A list of stalker.models.tag.Tag instances
    """
    # Tags
    tags = []
    tag_names = request.POST.getall(parameter)
    for tag_name in tag_names:
        logger.debug('tag_name : %s' % tag_name)
        if tag_name == '':
            continue
        tag = Tag.query.filter(Tag.name == tag_name).first()
        if not tag:
            logger.debug('new tag is created %s' % tag_name)
            tag = Tag(name=tag_name)
            DBSession.add(tag)
        tags.append(tag)
    return tags


def get_user_os(request):
    """returns the user operating system name
    """
    user_agent = request.headers['user-agent']

    if 'Windows' in user_agent:
        return 'windows'
    elif 'Linux' in user_agent:
        return 'linux'
    elif 'OS X' in user_agent:
        return 'osx'


def get_path_converter(request, task):
    """returns a partial function that converts the given path to another path
    that is visible to other OSes.
    """

    user_os = get_user_os(request)
    repo = task.project.repository

    path_converter = lambda x: x

    if user_os == 'windows':
        path_converter = repo.to_windows_path
    elif user_os == 'linux':
        path_converter = repo.to_linux_path
    elif user_os == 'osx':
        path_converter = repo.to_osx_path

    return path_converter


def seconds_since_epoch(dt):
    """converts the given datetime.datetime instance to an integer showing the
    seconds from epoch, and does it without using the strftime('%s') which
    uses the time zone info of the system.

    :param dt: datetime.datetime instance to be converted
    :returns int: showing the seconds since epoch
    """
    dts = dt - datetime.datetime(1970, 1, 1)
    return dts.days * 86400 + dts.seconds


def milliseconds_since_epoch(dt):
    """converts the given datetime.datetime instance to an integer showing the
    milliseconds from epoch, and does it without using the strftime('%s') which
    uses the time zone info of the system.

    :param dt: datetime.datetime instance to be converted
    :returns int: showing the milliseconds since epoch
    """
    dts = dt - datetime.datetime(1970, 1, 1)
    return dts.days * 86400000 + dts.seconds * 1000


def from_microseconds(t):
    """converts the given microseconds showing the time since epoch to datetime
    instance
    """
    epoch = datetime.datetime(1970, 1, 1)
    delta = datetime.timedelta(microseconds=t)
    return epoch + delta


def from_milliseconds(t):
    """converts the given milliseconds showing the time since epoch to datetime
    instance
    """
    return from_microseconds(t * 1000)


def get_parent_task_status(children_statuses):

    binary_status_codes = {
        'WFD':  256,
        'RTS':  128,
        'WIP':  64,
        'PREV': 32,
        'HREV': 16,
        'DREV': 8,
        'OH':   4,
        'STOP': 2,
        'CMPL': 1
    }

    children_to_parent_statuses_lut = [
        0, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 2, 0, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2
    ]

    parent_statuses_lut = ['WFD', 'RTS', 'WIP', 'CMPL']

    binary_status = 0
    for child_status_code in children_statuses:
        binary_status += binary_status_codes[child_status_code]

    status_index = children_to_parent_statuses_lut[binary_status]
    status = parent_statuses_lut[status_index]

    return status


def invalidate_all_caches():
    """invalidates all cache values.
    Based on: http://stackoverflow.com/a/14251064/3259351
    """
    from beaker.cache import cache_managers
    for _cache in cache_managers.values():
        _cache.clear()
