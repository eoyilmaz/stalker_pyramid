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
"""This is a helper script for moving old style references (saved in SPL) to
new style (saved in Repository) references.

It moves the reference files to their new places in the file server and also
will generate the missing Web versions for them.
"""

import os
import sys

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)


from stalker import db, Task
from stalker_pyramid.views.link import MediaManager


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def move_references():
    """moves the old style references to their new places
    """
    mm = MediaManager()

    # get all tasks that has a reference
    tasks = Task.query.filter(Task.references!=None).all()

    print 'Number of Tasks that has a reference: %s' % len(tasks)

    processed_references = {}
    for t in tasks:
        # go over references
        task_references = t.references
        for r in task_references:
            if r.full_path.startswith('SPL'):
                if r.id not in processed_references:
                    # convert the path to absolute path
                    current_full_path = \
                        mm.convert_file_link_to_full_path(r.full_path)

                    # create a new reference out of this path
                    new_ref = None
                    if os.path.exists(current_full_path):
                        print 'moving %s' % current_full_path
                        with open(current_full_path) as f:
                            new_ref = \
                                mm.upload_reference(t, f, r.original_filename)
                        print 'to %s' % new_ref.full_path

                        # also update tags
                        print 'adding tags: %s' % map(lambda x: x.name, r.tags)
                        new_ref.tags = r.tags
                        # add this new_ref to DBSession
                        db.DBSession.add(new_ref)

                    # store this reference to be deleted
                    processed_references[r.id] = {
                        'old_ref': r,
                        'new_ref': new_ref
                    }

                    # delete the old file
                    print 'removing old reference at: %s' % current_full_path
                    try:
                        os.remove(current_full_path)
                    except OSError:
                        pass

                    # also remove the thumbnail
                    current_thumbnail = r.thumbnail
                    if current_thumbnail:
                        current_thumbnail_full_path = \
                            mm.convert_file_link_to_full_path(
                                current_thumbnail.full_path
                            )
                        print 'also removing old thumbnail at: %s' % \
                            current_thumbnail_full_path
                        try:
                            os.remove(current_thumbnail_full_path)
                        except OSError:
                            pass
                else:
                    new_ref = processed_references[r.id]['new_ref']
                    if new_ref is not None:
                        if new_ref not in t.references:
                            t.references.append(new_ref)

                # remove this reference from this task
                t.references.remove(r)

    # find if there are any tasks still using the old link
    for v in processed_references.values():
        old_ref = v['old_ref']
        new_ref = v['new_ref']
        for task in Task.query.filter(Task.references.contains(old_ref)).all():
            print '%s is referencing %s, breaking this relation' % \
                (task, old_ref)
            task.references.remove(old_ref)
            if new_ref is not None:
                if new_ref not in task.references:
                    task.references.append(new_ref)

    # and delete old ones
    for v in processed_references.values():
        old_ref = v['old_ref']
        # delete the thumbnail
        with db.DBSession.no_autoflush:
            old_thumbnail = old_ref.thumbnail

        db.DBSession.delete(old_ref)
        if old_thumbnail:
            db.DBSession.delete(old_thumbnail)

    print "Processed %s Link objects!" % len(processed_references)

    # commit to database
    db.DBSession.commit()


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)

    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    db.setup(settings)
    # db.init() # no init needed

    move_references()


if __name__ == '__main__':
    main()
