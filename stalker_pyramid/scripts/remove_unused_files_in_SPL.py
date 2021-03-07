# -*- coding: utf-8 -*-
"""This is a helper script for removing unused files in SPL.

Walks through SPL and checks if there is a Link instance per file in SPL and
removes the ones that doesn't have a related Link instance.
"""

import os
import sys

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)


from stalker import db, defaults, Link


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def remove_unused_files():
    """removes unused files from SPL
    """
    path = os.path.expandvars(
        os.path.expanduser(defaults.server_side_storage_path)
    ).replace('\\', '/')

    for dir_path, dir_names, file_names in os.walk(path):
        for f in file_names:
            full_path = os.path.join(dir_path, f)
            spl_relative_path = full_path.replace(path, 'SPL')
            l = Link.query.filter(Link.full_path == spl_relative_path).first()
            if l is None:
                print(spl_relative_path)
                os.remove(full_path)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)

    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    db.setup(settings)
    # db.init() # no init needed

    remove_unused_files()


if __name__ == '__main__':
    main()
