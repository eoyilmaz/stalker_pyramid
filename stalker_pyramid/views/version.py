# -*- coding: utf-8 -*-

import logging
import os

from pyramid.view import view_config
from pyramid.response import Response

from sqlalchemy import distinct

from stalker import db, Task, Version, Entity, User, defaults
from stalker.db.session import DBSession

from stalker_pyramid.views import (
    get_logged_in_user,
    get_user_os,
    PermissionChecker,
    milliseconds_since_epoch,
)
from stalker_pyramid.views.link import MediaManager
from stalker_pyramid.views.task import generate_recursive_task_query

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
from stalker_pyramid import (
    cgru_host_mask_alembic,
    cgru_host_mask_playblast,
    logger_name,
)

logger = logging.getLogger(logger_name)


@view_config(
    route_name="create_version_dialog",
    renderer="templates/version/dialog/create_version_dialog.jinja2",
)
def create_version_dialog(request):
    """creates a create_version_dialog by using the given task"""
    logger.debug("inside create_version_dialog")

    # get logged in user
    logged_in_user = get_logged_in_user(request)

    task_id = request.matchdict.get("tid", -1)
    task = Task.query.filter(Task.task_id == task_id).first()

    takes = list(
        map(
            lambda x: x[0],
            DBSession.query(distinct(Version.take_name))
            .filter(Version.task == task)
            .all(),
        )
    )

    if defaults.version_take_name not in takes:
        takes.append(defaults.version_take_name)

    return {
        "has_permission": PermissionChecker(request),
        "logged_in_user": logged_in_user,
        "task": task,
        "default_take_name": defaults.version_take_name,
        "take_names": [defaults.version_take_name],
    }


@view_config(
    route_name="update_version_dialog",
    renderer="templates/version/dialog/update_version_dialog.jinja2",
)
def update_version_dialog(request):
    """updates a create_version_dialog by using the given task"""
    # get logged in user
    logged_in_user = get_logged_in_user(request)

    version_id = request.matchdict.get("id", -1)
    version = Version.query.filter_by(id=version_id).first()

    return {
        "mode": "UPDATE",
        "has_permission": PermissionChecker(request),
        "logged_in_user": logged_in_user,
        "task": version.task,
        "version": version,
    }


@view_config(route_name="create_version", permission="Create_Version")
def create_version(request):
    """runs when creating a version"""
    logger.debug("create_version start")
    logged_in_user = get_logged_in_user(request)

    task_id = request.params.get("task_id")
    task = Task.query.filter(Task.id == task_id).first()

    take_name = request.params.get("take_name", "Main")
    is_published = True if request.params.get("is_published") == "true" else False
    description = request.params.get("description")
    bind_to_originals = (
        True if request.params.get("bind_to_originals") == "true" else False
    )
    export_alembics_param = (
        True if request.params.get("export_alembics") == "true" else False
    )
    do_playblast_param = True if request.params.get("do_playblast") == "true" else False

    # toggle export_alembics and do_playblast
    # if no bind_to_originals with bind_to_originals
    export_alembics_param = bind_to_originals and export_alembics_param
    do_playblast_param = bind_to_originals and do_playblast_param

    file_object = request.POST.getall("file_object")[0]

    logger.debug(f"file_object: {file_object}")
    logger.debug(f"take_name: {take_name}")
    logger.debug(f"is_published: {is_published}")
    logger.debug(f"description: {description}")
    logger.debug(f"bind_to_originals: {bind_to_originals}")
    logger.debug(f"export_alembics: {export_alembics_param}")
    logger.debug(f"do_playblast: {do_playblast_param}")

    if not task:
        logger.debug("create_version end")
        return Response(f"No task with id: {task_id}", 500)

    extension = os.path.splitext(file_object.filename)[-1]
    if extension == ".mb":
        logger.debug("create_version end")
        return Response("This is a MayaBinary file, please upload MayaAscii", 500)

    mm = MediaManager()
    v = mm.upload_version(
        task=task,
        file_object=file_object.file,
        take_name=take_name,
        extension=extension,
    )

    v.created_by = logged_in_user
    v.updated_by = logged_in_user
    v.is_published = is_published
    v.created_with = "StalkerPyramid"
    v.description = description

    # check if bind_to_originals is true
    unknown_references = []
    if not extension == ".ma":
        logger.debug("create_version end")
        return Response("Version is uploaded successfully!")

    if bind_to_originals:
        from stalker_pyramid.views import archive

        arch = archive.Archiver()
        unknown_references = arch.bind_to_original(
            v.absolute_full_path, project=task.project
        )

    if not unknown_references:
        if export_alembics_param:
            submit_alembic_job(
                v.absolute_full_path,
                v.task.project.code,
                host_mask=cgru_host_mask_alembic,
            )

        if do_playblast_param:
            submit_playblast_job(
                v.absolute_full_path,
                v.task.project.code,
                host_mask=cgru_host_mask_playblast,
            )

        DBSession.add(v)
        logger.debug("version added to: {}".format(v.absolute_full_path))

    else:
        # delete the version
        os.remove(v.absolute_full_path)
        DBSession.delete(v)
        # DBSession.rollback()
        logger.debug("There are unknown references, not creating the version!!!")
        logger.debug("\n".join(unknown_references))
        logger.debug("create_version end")
        return Response(
            "There are unknown references: <br><br>{}"
            "<br><br>CANCELING UPLOAD!!!!".format(
                "<br>".join(unknown_references)
            ),
            500,
        )

    logger.debug("create_version end")
    return Response("Version is uploaded successfully!")


@view_config(route_name="do_playblast")
def do_playblast(request):
    """does playblast on farm

    :param request:
    :return:
    """
    # TODO: Check if there is already an open playblast job for this version
    logger.debug("running do_playblast!")
    version_id = request.matchdict.get("id")
    version = Version.query.get(version_id)
    if version.absolute_full_path.endswith(".ma"):
        logger.debug(f"version_id: {version_id}")
        logger.debug(f"version   : {version}")
        if version:
            submit_playblast_job(
                version.absolute_full_path,
                version.task.project.code,
                host_mask=cgru_host_mask_playblast,
            )
        return Response("Playblast job created, check Afanasy!")
    else:
        return Response("This is not a Maya version!")


@view_config(route_name="export_alembics")
def export_alembics(request):
    """does playblast on farm

    :param request:
    :return:
    """
    logger.debug("running export_alembics!")
    version_id = request.matchdict.get("id")
    version = Version.query.get(version_id)
    if version.absolute_full_path.endswith(".ma"):
        logger.debug(f"version_id: {version_id}")
        logger.debug(f"version   : {version}")
        if version:
            submit_alembic_job(
                version.absolute_full_path,
                version.task.project.code,
                host_mask=cgru_host_mask_alembic,
            )
    else:
        return Response("This is not a Maya version!")
    return Response("Export Alembics job created, check Afanasy!")


def submit_job(job_name, block_name, command, host_mask=""):
    """Submits an Afanasy job

    :param job_name:
    :param block_name:
    :param command:
    :param str host_mask: The host mask.
    :return:
    """
    import af
    from stalker_pyramid import cgru_working_directory

    block = af.Block(block_name, "maya")
    block.setCommand(" ".join(command))
    block.setNumeric(1, 1, 1, 1)
    block.setWorkingDirectory(cgru_working_directory)

    job = af.Job(job_name)
    job.blocks = [block]
    if host_mask != "":
        host_mask = host_mask.replace('"', "")
        job.setHostsMask(host_mask)
    status, data = job.send()

    if not status:
        RuntimeError("Something went wrong!")


def submit_alembic_job(path, project_code="", host_mask=""):
    """creates a afanasy job that exports the alembics on a given scene

    :param str path: Path to a maya file
    :param project_code: Project.code
    :param str host_mask: The host mask.
    """
    job_name = "{}:{} - Alembic Export".format(project_code, os.path.basename(path))
    block_name = job_name
    command = [
        "mayapy%s" % os.getenv("MAYA_VERSION", "2022"),
        "-c",
        '"import pymel.core as pm;'
        "from anima.dcc.mayaEnv import afanasy_publisher;"
        "afanasy_publisher.export_alembics('{path}');\"".format(path=path),
    ]
    submit_job(job_name, block_name, command, host_mask=host_mask)


def submit_playblast_job(path, project_code="", host_mask=""):
    """creates a afanasy job that exports the alembics on a given scene

    :param str path: Path to a maya file
    :param project_code: Project.code
    :param str host_mask: The host mask.
    """
    job_name = "{}:{} - Playblast".format(project_code, os.path.basename(path))
    block_name = job_name

    command = [
        "mayapy%s" % os.getenv("MAYA_VERSION", "2022"),
        "-c",
        '"import pymel.core as pm;'
        "from anima.dcc.mayaEnv import afanasy_publisher;"
        "afanasy_publisher.export_playblast('{path}');\"".format(
            path=path,
        ),
    ]
    submit_job(job_name, block_name, command, host_mask=host_mask)


@view_config(route_name="get_entity_versions", renderer="json")
@view_config(route_name="get_task_versions", renderer="json")
def get_entity_versions(request):
    """returns all the Shots of the given Project"""
    logger.debug("get_versions is running")

    entity_id = request.matchdict.get("id", -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    user_os = get_user_os(request)

    logger.debug(f"entity_id : {entity_id}")
    logger.debug(f"user os: {user_os}")

    repo = entity.project.repository

    path_converter = lambda x: x
    if repo:
        if user_os == "windows":
            path_converter = repo.to_windows_path
        elif user_os == "linux":
            path_converter = repo.to_linux_path
        elif user_os == "osx":
            path_converter = repo.to_osx_path

    return_data = [
        {
            "id": version.id,
            "task": {"id": version.task.id, "name": version.task.name},
            "take_name": version.take_name,
            "parent": {
                "id": version.parent.id,
                "version_number": version.parent.version_number,
                "take_name": version.parent.take_name,
            }
            if version.parent
            else None,
            "absolute_full_path": path_converter(version.absolute_full_path),
            "created_by": {
                "id": version.created_by.id if version.created_by else None,
                "name": version.created_by.name if version.created_by else None,
            },
            "is_published": version.is_published,
            "version_number": version.version_number,
            "date_created": milliseconds_since_epoch(version.date_updated),
            "created_with": version.created_with,
            "description": version.description,
            "task_full_path": version.task.name,
        }
        for version in entity.versions
    ]

    return return_data


@view_config(route_name="get_user_versions", renderer="json")
def get_user_versions(request):
    """returns all the Versions that the queried User has created"""
    logger.debug("*******get_user_versions is running")

    user_id = request.matchdict.get("id", -1)
    user = User.query.filter_by(id=user_id).first()

    sql_query = """
        select
            "Versions".id,
            "Versions".is_published,
            "Version_SimpleEntities".date_updated,
            "Versions".take_name,
            "Versions".version_number,
            "Versions".created_with,
            "Version_SimpleEntities".description,
            tasks.id,
            tasks.name,
            tasks.path,
            tasks.full_path

        from "Versions"
        join "SimpleEntities" as "Version_SimpleEntities" on "Version_SimpleEntities".id = "Versions".id
        join "Users" on "Version_SimpleEntities".created_by_id = "Users".id
        join (
            %(tasks_hierarchical_name)s
        ) as tasks on tasks.id = "Versions".task_id

        where "Users".id = %(user_id)s
        order by "Version_SimpleEntities".date_updated desc

        """

    sql_query = sql_query % {
        "user_id": user_id,
        "tasks_hierarchical_name": generate_recursive_task_query(ordered=False),
    }

    from sqlalchemy import text  # to be able to use "%" sign use this function

    result = DBSession.connection().execute(text(sql_query))

    return_data = [
        {
            "id": r[0],
            "is_published": r[1],
            "date_created": milliseconds_since_epoch(r[2]),
            "take_name": r[3],
            "version_number": r[4],
            "created_with": r[5],
            "description": r[6],
            "task_name": r[8],
            "task_path": r[9],
            "task_full_path": r[10],
            "task": {"id": r[7], "name": r[10]},
            "absolute_full_path": "",
            "created_by": {"id": user.id, "name": user.name},
        }
        for r in result.fetchall()
    ]

    return return_data


@view_config(route_name="get_user_versions_count", renderer="json")
def get_user_versions_count(request):
    """returns user versions count"""
    logger.debug("*******get_user_versions is running")

    user_id = request.matchdict.get("id", -1)
    user = User.query.filter_by(id=user_id).first()

    sql_query = """
        select
            count("Versions".id)
        from "Versions"
            join "SimpleEntities" as "Version_SimpleEntities" on "Version_SimpleEntities".id = "Versions".id
            join "Users" on "Version_SimpleEntities".created_by_id = "Users".id
        where "Users".id = %(user_id)s
    """

    sql_query = sql_query % {"user_id": user_id}

    from sqlalchemy import text

    result = DBSession.connection().execute(text(sql_query))

    return result.fetchone()[0]


@view_config(
    route_name="list_version_outputs",
    renderer="templates/version/content_list_version_outputs.jinja2",
)
def list_version_outputs(request):
    """lists the versions of the given task"""
    version_id = request.matchdict.get("id", -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug(f"entity_id : {version_id}")
    return {"version": version, "has_permission": PermissionChecker(request)}


@view_config(
    route_name="list_version_inputs",
    renderer="templates/version/content_list_version_inputs.jinja2",
)
def list_version_inputs(request):
    """lists the versions of the given task"""
    logger.debug("list_version_inputs is running")

    version_id = request.matchdict.get("id", -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug(f"entity_id : {version_id}")
    return {"version": version, "has_permission": PermissionChecker(request)}


@view_config(
    route_name="list_version_children",
    renderer="templates/version/content_list_versions_children.jinja2",
)
def list_version_children(request):
    """lists the versions of the given task"""
    logger.debug("list_version_children is running")

    version_id = request.matchdict.get("id", -1)
    version = Version.query.filter_by(id=version_id).first()

    logger.debug(f"entity_id : {version_id}")
    return {"version": version, "has_permission": PermissionChecker(request)}


# @view_config(
#     route_name='get_version_outputs_count',
#     renderer='json'
# )
# def get_version_outputs_count(request):
#     """returns the count of the given version
#     """
#     version_id = request.params.get('id')
#
#     sql_query = """select
# count("Links".id)
# from "Versions"
# join "Version_Outputs" on "Versions".id = "Version_Outputs".version_id
# join "Links" on "Version_Outputs".link_id = "Links".id
# where "Versions".id = %(id)s
#     """ % {'id': version_id}
#
#     return DBSession.connection().execute(sql_query).fetchone()[0]

#
# @view_config(
#     route_name='get_task_version_outputs_count',
#     renderer='json'
# )
# def get_task_version_outputs_count(request):
#     """returns the count of the given version
#     """
#     task_id = request.params.get('id')
#
#     sql_query = """select
#     count("Links".id)
# from "Tasks"
# join "Versions" on "Tasks".id = "Versions".task_id
# join "Version_Outputs" on "Versions".id = "Version_Outputs".version_id
# join "Links" on "Version_Outputs".link_id = "Links".id
# where "Tasks".id = %(id)s
#     """ % {'id': task_id}
#
#     return DBSession.connection().execute(sql_query).fetchone()[0]


@view_config(route_name="pack_version")
def pack_version(request):
    """packs the requested version and returns a download link for it"""
    version_id = request.matchdict.get("id")
    version = Version.query.get(version_id)

    if version:
        # before doing anything check if the file exists
        import os

        version_filename_without_extension = os.path.splitext(version.filename)[0]
        archive_name = "{}{}".format(version_filename_without_extension, ".zip")
        archive_path = os.path.join(version.absolute_path, archive_name)

        # create a temp file so this process knows that there is another process
        # zipping the file
        archive_lock_file_path = "{}.lock".format(archive_path)

        logger.debug("ZIP Path: {}".format(archive_path))
        if os.path.exists(archive_path):
            # just serve the same file
            logger.debug("ZIP exists, not creating it again!")
            new_zip_path = archive_path
        elif os.path.exists(archive_lock_file_path):
            # somebody else is preparing the file
            # so wait
            logger.debug("ZIP is created by another process, waiting!")

            # check the utime of the lock file
            # if it is longer than 30 minutes delete the file
            # and return an Error
            import datetime

            file_date = datetime.datetime.fromtimestamp(
                os.path.getmtime(archive_lock_file_path)
            )
            now = datetime.datetime.now()

            if now - file_date > datetime.timedelta(minutes=30):
                os.remove(archive_lock_file_path)
                from pyramid.httpexceptions import HTTPError

                raise HTTPError("Lock File deleted please refresh!")

            import time

            while os.path.exists(archive_lock_file_path):
                # sleep for 10 seconds
                time.sleep(10)
                logger.debug("ZIP is created by another process, still waiting!")
            new_zip_path = archive_path
        else:
            # create the zip file
            logger.debug("ZIP does not exists, creating it!")

            # create lock file
            with open(archive_lock_file_path, "a"):
                os.utime(archive_lock_file_path, None)

            import shutil
            from stalker_pyramid.views.archive import Archiver

            path = version.absolute_full_path

            exclude_mask = [
                ".jpg",
                ".jpeg",
                ".png",
                ".tga",
                ".tif",
                ".tiff",
                ".ass",
                ".bmp",
                ".gif",
            ]

            arch = Archiver(exclude_mask=exclude_mask)
            task = version.task
            if False:
                assert isinstance(version, Version)
                assert isinstance(task, Task)
            project_name = version_filename_without_extension
            project_path = arch.flatten(path, project_name=project_name)

            # append link file
            stalker_link_file_path = os.path.join(
                project_path, "scenes/stalker_links.txt"
            )

            import stalker_pyramid

            version_upload_link = "{}/tasks/{}/versions/list".format(
                stalker_pyramid.stalker_server_external_url, task.id
            )
            request_review_link = "{}/tasks/{}/view".format(
                stalker_pyramid.stalker_server_external_url, task.id
            )
            with open(stalker_link_file_path, "w+") as f:
                f.write(
                    "Version Upload Link: {}\nRequest Review Link: {}\n".format(
                        version_upload_link, request_review_link
                    )
                )
            zip_path = arch.archive(project_path)

            new_zip_path = os.path.join(
                version.absolute_path, os.path.basename(zip_path)
            )

            # move the zip right beside the original version file
            shutil.move(zip_path, new_zip_path)

            # now remove the temp files
            shutil.rmtree(project_path, ignore_errors=True)

            # remove the lock file
            os.remove(archive_lock_file_path)

        # open the zip file in browser
        # serve the file new_zip_path
        from pyramid.response import FileResponse

        logger.debug(f"serving packed version file: {new_zip_path}")

        response = FileResponse(
            new_zip_path,
            request=request,
            content_type="application/force-download",
        )

        # update the content-disposition header
        response.headers["content-disposition"] = str(
            "attachment; filename=" + os.path.basename(new_zip_path)
        )

        return response
