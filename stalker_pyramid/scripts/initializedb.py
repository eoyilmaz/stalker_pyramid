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

    # Task
    task_status_list = StatusList.query\
        .filter_by(target_entity_type='Task').first()
    if not task_status_list:
        task_status_list = StatusList(name='Task Statuses',
                                      target_entity_type='Task')

    # Asset
    asset_status_list = StatusList.query\
        .filter_by(target_entity_type='Asset').first()
    if not asset_status_list:
        asset_status_list = StatusList(name='Asset Statuses',
                                       target_entity_type='Asset')

    # Shot
    shot_status_list = StatusList.query\
        .filter_by(target_entity_type='Shot').first()
    if not shot_status_list:
        shot_status_list = StatusList(name='Shot Statuses',
                                      target_entity_type='Shot')

    # Sequence
    sequence_status_list = StatusList.query\
        .filter_by(target_entity_type='Sequence').first()
    if not sequence_status_list:
        sequence_status_list = StatusList(name='Sequence Statuses',
                                          target_entity_type='Sequence')

    # the statuses
    new = Status.query.filter(Status.code == 'NEW').first()  # from ticket
                                                             # statuses

    wip = Status.query.filter_by(code='WIP').first()
    if not wip:
        wip = Status(name='Work In Progress', code='WIP')

    hrev = Status.query.filter_by(code='HREV').first()
    if not hrev:
        hrev = Status(name='Has Revision', code='HREV')

    prev = Status.query.filter_by(code='PREV').first()
    if not prev:
        prev = Status(name='Pending Revision', code='PREV')

    completed = Status.query.filter_by(code='CMPL').first()
    if not completed:
        completed = Status(name='Completed', code='CMPL')

    # now use them in status lists
    project_status_list = [new, wip, completed]
    task_status_list.statuses = [new, wip, prev, hrev, completed]
    asset_status_list.statuses = [new, wip, prev, hrev, completed]
    shot_status_list.statuses = [new, wip, prev, hrev, completed]
    sequence_status_list.statuses = [new, wip, prev, hrev, completed]

    # create Review ticket type
    review = Type.query.filter_by(name='Review').first()
    if not review:
        # create the review type for Tickets
        review = Type(
            target_entity_type='Ticket',
            name='Review',
            code='Review'
        )

    db.DBSession.add_all([
        project_status_list, task_status_list, asset_status_list,
        shot_status_list, sequence_status_list, new, wip, hrev, prev,
        completed, review
    ])
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


if __name__ == '__main__':
    main()
