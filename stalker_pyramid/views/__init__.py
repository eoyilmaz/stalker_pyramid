# -*- coding: utf-8 -*-

import logging
import pytz
import datetime
import json

from pyramid.httpexceptions import HTTPServerError, HTTPForbidden
from pyramid.view import view_config
from pyramid.response import Response
from pyramid.security import has_permission, authenticated_userid

from stalker import User, Tag
from stalker.db.session import DBSession
import transaction


from stalker_pyramid import logger_name
logger = logging.getLogger(logger_name)

# this is a dummy mail address change it in the config (*.ini) file
dummy_email_address = "Stalker Pyramid <stalker.pyramid@stalker.pyramid.com>"


def to_seconds(timing, unit):
    """converts timing to seconds"""
    return timing*seconds_in_unit(unit)


def seconds_in_unit(unit):
    # logger.debug("seconds_in_unit: %s" % unit)
    if unit == 'min':
        return 60
    elif unit == 'h':
        return 3600
    elif unit == 'd':
        return 32400
        # TODO: please use: stalker.defaults.daily_working_hours
    elif unit == 'w':
        return 183600
        # TODO: please use: stalker.defaults.weekly_working_hours
    elif unit == 'm':
        return 734400
        # TODO: please use: 4 * stalker.defaults.weekly_working_hours
    elif unit == 'y':
        return 9573418
        # TODO: please use: stalker.defaults.yearly_working_days * stalker.defaults.daily_working_hours
    else:
        return 0


class StdErrToHTMLConverter(object):
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

    @classmethod
    def replace_tjp_ids(cls, message):
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
    """Default server_error view
    :param exc:
    :param request:
    :return:
    """
    msg = exc.args[0] if exc.args else ''
    response = Response('Server Error: %s' % str(exc), 500)
    transaction.abort()
    return response


def get_time(request, time_attr):
    """Extracts a time object from the given request

    :param request: the request object
    :param time_attr: the attribute name
    :return: datetime.timedelta
    """
    # logger.debug("request.params[time_attr]: %s" % request.params[time_attr])
    try:
        time_part = datetime.datetime.strptime(
            request.params[time_attr][:-4],
            '%a, %d %b %Y %H:%M:%S'
        )
    except ValueError:
        time_part = datetime.datetime.strptime(
            request.params[time_attr],
            '%H:%M'
        )

    return datetime.timedelta(
        hours=time_part.hour,
        minutes=time_part.minute
    )


def convert_seconds_to_time_range(seconds):

    if seconds == 0:
        return '0'

    units = ['y', 'm', 'w', 'd', 'h', 'min']
    time_range_string = ''
    # remainder = 0
    # integer_division = 0
    # current_unit = ''
    # sec_in_unit = ''
    logger.debug("seconds %s " % seconds)
    for i in range(0, len(units)):
        current_unit = units[i]
        logger.debug("i %s " % i)
        logger.debug("current_unit %s " % current_unit)

        sec_in_unit = seconds_in_unit(current_unit)
        logger.debug("sec_in_unit %s " % sec_in_unit)

        integer_division = int(seconds / sec_in_unit)
        logger.debug("integer_division %s " % integer_division)

        remainder = seconds % sec_in_unit
        logger.debug("remainder %s " % remainder)

        if integer_division > 0:
            if time_range_string != ' ':
                time_range_string += ' '
            time_range_string += '%s %s' % (integer_division, current_unit)

        seconds = remainder
    return time_range_string


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
    ).replace(tzinfo=pytz.utc)


def get_date_range(request, date_range_attr):
    """Extracts a UTC datetime object from the given request

    :param request: the request instance
    :param date_range_attr: the attribute name
    :return: datetime.datetime
    """
    import tzlocal
    local_tz = tzlocal.get_localzone()

    date_range_string = request.params.get(date_range_attr)
    start_str, end_str = date_range_string.split(' - ')
    start = datetime.datetime.strptime(start_str, '%d/%m/%Y').replace(tzinfo=local_tz)
    end = datetime.datetime.strptime(end_str, '%d/%m/%Y').replace(tzinfo=local_tz)
    return start, end


def get_datetime(request, date_attr, time_attr):
    """Extracts a UTC  datetime object from the given request
    :param request: the request object
    :param date_attr: the date attribute name
    :param time_attr: the time attribute name
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
    :param method: HTTP request method
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
    :param parameter: the name of the parameter
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

    if user_os == 'windows':
        return repo.to_windows_path
    elif user_os == 'linux':
        return repo.to_linux_path
    elif user_os == 'osx':
        return repo.to_osx_path

    return lambda x: x


def seconds_since_epoch(dt):
    """converts the given datetime.datetime instance to an integer showing the
    seconds from epoch, and does it without using the strftime('%s') which
    uses the time zone info of the system.

    :param dt: datetime.datetime instance to be converted
    :returns int: showing the seconds since epoch
    """
    dts = dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
    return dts.days * 86400 + dts.seconds


def milliseconds_since_epoch(dt):
    """converts the given datetime.datetime instance to an integer showing the
    milliseconds from epoch, and does it without using the strftime('%s') which
    uses the time zone info of the system.

    :param dt: datetime.datetime instance to be converted
    :returns int: showing the milliseconds since epoch
    """
    if dt.tzinfo is None:
        dts = dt - datetime.datetime(1970, 1, 1)
    else:
        import pytz
        dts = dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
    return dts.days * 86400000 + dts.seconds * 1000


def from_microseconds(t):
    """converts the given microseconds showing the time since epoch to datetime
    instance
    """
    epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
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


def update_generic_text(generic_text, attr, data, action):

    list_attr = []
    generic_data = {}
    logger.debug('update_generic_text %s ' % generic_text)
    logger.debug('attr %s ' % attr)
    logger.debug('data %s ' % data)
    if generic_text and generic_text != "":
        generic_data = json.loads(generic_text)
        if attr in generic_data:
            list_attr = generic_data[attr]

    if action == 'add':
        list_attr.append(data)

    elif action == 'remove':
        for obj in list_attr:
            if "id" in obj:
                if obj["id"] == data["id"]:
                    list_attr.remove(obj)

    elif action == 'equal':
        list_attr = data

    generic_data[attr] = list_attr
    generic_text = json.dumps(generic_data)

    logger.debug(generic_text)

    return generic_text


def measure_time(f):
    import time

    def inner_f():
        start = time.time()
        return_data = f()
        end = time.time()
        logger.debug('%s: %0.3f sec' % (f.__name__, (end - start)))
        return return_data

    return inner_f
