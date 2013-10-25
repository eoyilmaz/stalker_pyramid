# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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
import os
from pyramid.exceptions import Forbidden

from pyramid.httpexceptions import HTTPServerError, HTTPForbidden
from pyramid.view import view_config
from pyramid.response import Response, FileResponse
from pyramid.security import has_permission, authenticated_userid

from stalker import log, User, Tag, defaults
from stalker.db import DBSession


logger = logging.getLogger(__name__)
logger.setLevel(log.logging_level)

colors = {
    'New': 'red',
    'Waiting To Start': 'purple',
    'Work In Progress': 'pink',
    'Completed': 'green'
}


class StdErrToHTMLConverter():
    """Converts stderr, stdout messages of TaskJuggler to html

    :param error: An exception
    """

    formatChars = {
        '\e[1m': '<strong>',
        '\e[21m': '</strong>',
        '\e[2m':  '<div class="dark">',
        '\e[22m': '</div>',
        '\x1b[34m': '<div class="alert alert-info" style="overflow-wrap: break-word">',
        '\x1b[35m': '<div class="alert alert-warning" style="overflow-wrap: break-word">',
        '\x1b[31m': '<div class="alert alert-error" style="overflow-wrap: break-word">',
        '\x1b[0m': '</div>',
        'Warning:': '<strong>Warning:</strong>',
        'Info:': '<strong>Info:</strong>',
        'Error:': '<strong>Error:</strong>',
    }

    def __init__(self, error):
        if isinstance(error, Exception):
            self.error_message = error.message
        else:
            self.error_message = error

    def html(self):
        """returns the html version of the message
        """
        # convert the error message to a string
        if isinstance(self.error_message, list):
            buffer = []
            for msg in self.error_message:
                # join the message in to <p> elements
                buffer.append('%s' % msg.strip())

            # convert the list to string
            strBuffer = ''.join(buffer)
        else:
            strBuffer = self.error_message

        # for each formatChar replace them with an html tag
        for key in self.formatChars.keys():
            strBuffer = strBuffer.replace(key, self.formatChars[key])

        return strBuffer


class PermissionChecker(object):
    """Helper class for permission check
    """

    def __init__(self, request):
        self.has_permission = has_permission
        self.request = request

    def __call__(self, perm):
        return self.has_permission(perm, self.request.context, self.request)


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
    response = Response('Server Error: %s' % msg)
    response.status_int = 500
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


@view_config(
    route_name='busy_dialog',
    renderer='templates/busy_dialog.jinja2'
)
def busy_dialog(request):
    """generates a busy dialog
    """
    return {}


def get_logged_in_user(request):
    """Returns the logged in user

    :param request: Request object
    """
    user = User.query.filter_by(login=authenticated_userid(request)).first()
    if not user:
        raise HTTPForbidden(headers=request)
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


def get_tags(request):
    """Extracts Tags from the given request

    :param request: Request object
    :return: A list of stalker.models.tag.Tag instances
    """

    # Tags
    tags = []
    tag_names = request.POST.getall('tag_names')
    for tag_name in tag_names:
        logger.debug('tag_name %s' % tag_name)
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


@view_config(
    route_name='serve_files'
)
def serve_files(request):
    """serves files in the stalker server side storage
    """
    partial_file_path = request.matchdict['partial_file_path']
    file_full_path = os.path.join(
        defaults.server_side_storage_path,
        partial_file_path
    )
    return FileResponse(file_full_path)
