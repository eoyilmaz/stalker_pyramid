import os
from setuptools import setup, find_packages

NAME = 'stalker_pyramid'
PACKAGES = find_packages()
META_PATH = os.path.join("stalker_pyramid", "__init__.py")
KEYWORDS = [
    'web', 'wsgi', 'bfg', 'pylons', 'pyramid', 'production',
    'asset', 'management', 'vfx', 'animation', 'houdini', 'nuke',
    'fusion', 'xsi', 'blender', 'vue'
]
CLASSIFIERS = [
    "Programming Language :: Python",
    "Framework :: Pyramid",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: End Users/Desktop",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    "Topic :: Database",
    "Topic :: Software Development",
    "Topic :: Utilities",
    "Topic :: Office/Business :: Scheduling",
]
INSTALL_REQUIRES = [
    'pyramid>=1.4',
    'sqlalchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_beaker',
    'pyramid_debugtoolbar',
    'pyramid_mailer',
    'zope.sqlalchemy',
    'waitress',
    'jinja2<3.0.0',
    'pyramid_jinja2',
    'pillow',
    'stalker>=0.2.24.3',
    'exifread',
    'webtest',
    'mocker',
    'tzlocal',
    'pytz',
    'beaker',
]
TEST_REQUIRES = ['pytest', 'pytest-xdist', 'pytest-cov', 'coverage']
DATA_FILES = [(
    '',
    ['LICENSE', 'INSTALL', 'MANIFEST.in', 'README.md']),
]

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    import codecs
    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()


README = read(HERE, 'README.md')
CHANGES = read(HERE, 'CHANGELOG')
META_FILE = read(META_PATH)


def find_meta(meta):
    """
    Extract __*meta*__ from META_FILE.
    """
    import re
    meta_match = re.search(
        r"^__{meta}__ = ['\"]([^'\"]*)['\"]".format(meta=meta),
        META_FILE, re.M
    )
    if meta_match:
        return meta_match.group(1)
    raise RuntimeError("Unable to find __{meta}__ string.".format(meta=meta))


if __name__ == '__main__':
    setup(
        name=NAME,
        description=find_meta('description'),
        long_description=README + '\n\n' + CHANGES,
        license=find_meta('license'),
        url=find_meta('uri'),
        version=find_meta('version'),
        author=find_meta('author'),
        author_email=find_meta('email'),
        classifiers=CLASSIFIERS,
        keywords=KEYWORDS,
        packages=PACKAGES,
        include_package_data=True,
        data_files=DATA_FILES,
        zip_safe=False,
        test_suite='stalker_pyramid',
        install_requires=INSTALL_REQUIRES,
        test_requires=TEST_REQUIRES,
        entry_points="""\
          [paste.app_factory]
          main = stalker_pyramid:main
          [console_scripts]
          initialize_stalker_pyramid_db = stalker_pyramid.scripts.initializedb:main
          """,
    )
