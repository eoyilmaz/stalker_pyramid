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
"""This is a helper script that you can run as a cron job per weekly
"""
import os
import sys
import datetime

import transaction

from jinja2 import Template

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from pyramid_mailer.mailer import Mailer
from pyramid_mailer.message import Message

from stalker import db, Task, User
from stalker_pyramid.views import dummy_email_address, utc_to_local

mailer = None
stalker_server_external_url = None
here = os.path.dirname(os.path.realpath(sys.argv[0]))
templates_path = os.path.join(here, 'templates')
mail_html_template_path = os.path.join(
    templates_path,
    'weekly_digest_template.jinja2'
)

mail_html_template_content = None
mail_html_template = None


def usage(argv):
    """shows usage
    """
    cmd = os.path.basename(argv[0])
    print(
        'usage: %s ,config_uri>\n'
        '(example: "%s development.ini")' % (cmd, cmd)
    )
    sys.exit(1)


def get_week_dates(date):
    """returns the start and end of week days of now
    """
    day_of_week = date.isoweekday()
    start_of_week = date - datetime.timedelta(days=day_of_week - 1)
    end_of_week = start_of_week + datetime.timedelta(days=6, hours=23,
                                                     minutes=59, seconds=59)
    return start_of_week, end_of_week


def get_this_week_dates():
    """returns the start and end date of this week
    """
    now = datetime.datetime.utcnow()\
        .replace(hour=0, minute=0, second=0, microsecond=0)

    return get_week_dates(now)


def convert_seconds_to_text(seconds):
    """returns a meaningful text out of the given seconds
    """

    return


def send_remainder(user):
    """sends the reminder mail to the user
    """
    recipients = [user.email]

    start_of_week, end_of_week = get_this_week_dates()

    tasks_ending_this_week = Task.query.join(Task.resources, User.tasks)\
        .filter(Task.computed_start < end_of_week)\
        .filter(Task.computed_end > start_of_week)\
        .filter(Task.computed_end < end_of_week)\
        .filter(User.id == user.id)\
        .order_by(Task.end)\
        .all()

    tasks_continues = Task.query.join(Task.resources, User.tasks)\
        .filter(Task.computed_start < end_of_week)\
        .filter(Task.computed_end > end_of_week)\
        .filter(User.id == user.id)\
        .order_by(Task.end)\
        .all()

    # skip if he/she doesn't have any tasks
    if len(tasks_ending_this_week) == 0 and len(tasks_continues) == 0:
        return

    rendered_template = mail_html_template.render(
        user=user,
        tasks_ending_this_week=tasks_ending_this_week,
        tasks_continues=tasks_continues,
        start_of_week=start_of_week,
        end_of_week=end_of_week,
        utc_to_local=utc_to_local,
        stalker_url=stalker_server_external_url
    )

    with open('/home/eoyilmaz/tmp/rendered_html_template_%s.html' % user.id,
              'w+') as f:
        f.write(rendered_template)

    message = Message(
        subject='Stalker Weekly Digest',
        sender=dummy_email_address,
        recipients=recipients,
        body='This is an HTMl email',
        html=rendered_template
    )

    mailer.send_to_queue(message)


def main(argv=sys.argv):
    """main function
    """
    if len(argv) != 2:
        usage(argv)

    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    # global here
    global stalker_server_external_url
    global mailer
    global mail_html_template
    global mail_html_template_content

    # here = os.path.dirname(os.path.realpath(sys.argv[0]))
    stalker_server_external_url = settings.get('stalker.external_url')
    mailer = Mailer.from_settings(settings)

    with open(mail_html_template_path) as f:
        mail_html_template_content = f.read()

    mail_html_template = Template(mail_html_template_content)

    db.setup(settings)

    for user in User.query.all():
        send_remainder(user)

    transaction.commit()


if __name__ == '__main__':
    main()
