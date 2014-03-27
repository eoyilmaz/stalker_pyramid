import os
import sys

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from stalker import db, StatusList, Status, Type


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def create_statuses_and_status_lists():
    """Creates the statuses needed for Project, Task, Asset, Shot and Sequence
    entities
    """
    # Also create basic Status and status lists for
    # Project, Asset, Shot, Sequence

    # Project
    project_status_list = StatusList.query\
        .filter_by(target_entity_type='Project').first()
    if not project_status_list:
        project_status_list = StatusList(name='Project Statuses',
                                         target_entity_type='Project')

    new = Status.query.filter_by(code='NEW').first()
    wip = Status.query.filter_by(code='WIP').first()
    cmpl = Status.query.filter_by(code='CMPL').first()

    # now use them in status lists
    project_status_list.statuses = [new, wip, cmpl]

    # Warning! Not using scoped_session here, it is the plain old session
    db.DBSession.add_all([
        project_status_list,
    ])
    db.DBSession.commit()


def create_ticket_types():
    """Creates the extra ticket types
    """
    # create Review ticket type
    review = Type.query.filter_by(name='Review').first()
    if not review:
        # create the review type for Tickets
        review = Type(
            target_entity_type='Ticket',
            name='Review',
            code='Review'
        )

    # Warning! Not using scoped_session here, it is the plain old session
    db.DBSession.add(review)
    db.DBSession.commit()


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)

    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    db.setup(settings)
    db.init()

    # create statuses
    create_statuses_and_status_lists()
    create_ticket_types()


if __name__ == '__main__':
    main()
