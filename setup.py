import os

from setuptools import setup, find_packages
import stalker

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README')).read()
CHANGES = open(os.path.join(here, 'CHANGELOG')).read()

requires = [
    'pyramid',
    'sqlalchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'waitress',
    'pyseq',
    'jinja2',
]

setup(name='stalker',
      version=stalker.__version__,
      description='A Production Asset Management (ProdAM) System',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Database",
        "Topic :: Software Development",
        "Topic :: Utilities",
        "Topic :: Office/Business :: Scheduling",
      ],
      author='Erkan Ozgur Yilmaz',
      author_email='eoyilmaz@gmail.com',
      url='http://code.google.com/p/stalker/',
      keywords=['web', 'wsgi', 'bfg', 'pylons', 'pyramid', 'production',
                'asset', 'management', 'vfx', 'animation', 'houdini', 'nuke',
                'fusion', 'xsi', 'blender', 'vue'],
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='stalker',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = stalker:main
      [console_scripts]
      initialize_stalker_db = stalker.scripts.initializedb:main
      """,
)

