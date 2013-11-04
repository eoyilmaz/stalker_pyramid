// Stalker Pyramid a Web Base Production Asset Management System
// Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
//
// This file is part of Stalker Pyramid.
//
// This library is free software; you can redistribute it and/or
// modify it under the terms of the GNU Lesser General Public
// License as published by the Free Software Foundation;
// version 2.1 of the License.
//
// This library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public
// License along with this library; if not, write to the Free Software
// Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

define(['exports', 'dojox/widget/DialogSimple', 'dijit/registry', 'dojo/domReady!'],
    function (exports, DialogSimple, registry) {
        // module:
        //      stalker/js/dialogs
        // summary:
        //      creates the default dialogs

        var reg = new RegExp('{id}', 'g');

        var style = 'width: auto; height: auto; padding: 0px;';

        var dialog_killer = function (id) {
            var old_dialog = registry.byId(id);
            if (old_dialog) {
                old_dialog.destroyRecursive();
            }
        };

        // ********************************************************************
        exports.busy_dialog = function busy_dialog(kwargs) {
            var id = kwargs['id'] || 'busy_dialog';
            var title = kwargs['title'] || 'Stalker is busy...';
            var href = kwargs['href'] || 'dialog/busy';
            var style = kwargs['style'] || 'width: 350px; height: 70px;';

            dialog_killer(id);
            return new DialogSimple({
                id: id, title: title, href: href, resize: true, style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        exports.upload_thumbnail_dialog = function upload_thumbnail_dialog(entity_id) {
            dialog_killer('upload_thumbnail_dialog');
            return new DialogSimple({
                id: 'upload_thumbnail_dialog',
                title: 'Upload Thumbnail Dialog',
                href: '/entities/{id}/thumbnail/upload/dialog'.replace(reg, entity_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        exports.upload_reference_dialog = function upload_reference_dialog(entity_id) {
            dialog_killer('upload_reference_dialog');
            return new DialogSimple({
                id: 'upload_reference_dialog',
                title: 'Upload Reference Dialog',
                href: '/entities/{id}/references/upload/dialog'.replace(reg, entity_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // STUDIO
        exports.create_studio_dialog = function create_studio_dialog() {
            return new DialogSimple({
                id: 'studio_dialog',
                title: 'New Studio',
                href: '/studios/create/dialog',
                resize: true,
                style: 'width: 730px; height: auto; padding: 0px;',
                executeScripts: true
            });
        };

        exports.update_studio_dialog = function update_studio_dialog() {
            return new DialogSimple({
                id: 'studio_dialog',
                title: 'Update Studio',
                href: '/studios/-1/update/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // PROJECT
        exports.create_project_dialog = function create_project_dialog() {
            return new DialogSimple({
                id: 'project_dialog',
                title: 'New Project',
                href: '/projects/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_project_dialog = function update_project_dialog(project_id) {
            return new DialogSimple({
                id: 'project_dialog',
                title: 'Update Project',
                href: '/projects/{id}/update/dialog'.replace(reg, project_id),
                resize: true,
                style: style,
                executeScripts: true
            })
        };

        // ********************************************************************
        // IMAGE FORMAT
        exports.create_image_format_dialog = function create_image_format_dialog() {
            return new DialogSimple({
                id: 'image_format_dialog',
                title: 'New Image Format',
                href: '/image_formats/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_image_format_dialog = function update_image_format_dialog(imf_id) {
            return new DialogSimple({
                id: 'image_format_dialog',
                title: 'Update Image Format',
                href: '/image_formats/{id}/update/dialog'.replace(reg, imf_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // STRUCTURE
        exports.create_structure_dialog = function create_structure_dialog() {
            return new DialogSimple({
                id: 'structure_dialog',
                title: 'New Structure',
                href: '/structures/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_structure_dialog = function update_structure_dialog(structure_id) {
            return new DialogSimple({
                id: 'structure_dialog',
                title: 'Update Structure',
                href: '/structures/{id}/update/dialog'.replace(reg, structure_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // USER
        exports.create_user_dialog = function create_user_dialog(entity_id) {
            entity_id = entity_id || -1;
            return new DialogSimple({
                id: 'user_dialog',
                title: 'New User',
                href: '/users/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.create_department_user_dialog = function create_department_user_dialog(entity_id) {
            entity_id = entity_id || -1;
            return new DialogSimple({
                id: 'user_dialog',
                title: 'New User',
                href: '/departments/{id}/users/create/dialog'.replace(reg, entity_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.create_group_user_dialog = function create_group_user_dialog(entity_id) {
            entity_id = entity_id || -1;
            return new DialogSimple({
                id: 'user_dialog',
                title: 'New User',
                href: '/groups/{id}/users/create/dialog'.replace(reg, entity_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_user_dialog = function update_user_dialog(user_id) {
            return new DialogSimple({
                id: 'user_dialog',
                title: 'Update User',
                href: '/users/{id}/update/dialog'.replace(reg, user_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.append_user_dialog = function append_user_dialog(entity_id) {
            return new DialogSimple({
                id: 'append_user_dialog',
                title: 'Append User',
                href: '/entities/{id}/users/append/dialog'.replace(reg, entity_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // FILENAME TEMPLATE
        exports.create_filename_template_dialog = function create_filename_template_dialog() {
            return new DialogSimple({
                id: 'filename_template_dialog',
                title: 'New Filename Template',
                href: '/filename_templates/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_filename_template_dialog = function update_filename_template_dialog(ft_id) {
            var myDialog = new DialogSimple({
                id: 'filename_template_dialog',
                title: 'Update Filename Template',
                href: '/filename_templates/{id}/update/dialog'.replace(reg, ft_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // REPOSITORY
        exports.create_repository_dialog = function create_repository_dialog() {
            return new DialogSimple({
                id: 'repository_dialog',
                title: 'New Repository',
                href: '/repositories/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_repository_dialog = function update_repository_dialog(repo_id) {
            return new DialogSimple({
                id: 'repository_dialog',
                title: 'Update Repository',
                href: '/repositories/{id}/update/dialog'.replace(reg, repo_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // STATUS LIST
        exports.create_status_list_dialog = function create_status_list_dialog(target_entity_type) {
            var href;
            if (target_entity_type === null) {
                href = '/status_lists/create/dialog';
            } else {
                href = '/status_lists/{id}/create/dialog'.replace(reg, target_entity_type);
            }
            return new DialogSimple({
                id: 'status_list_dialog',
                title: 'New Status List',
                href: href,
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_status_list_dialog = function update_status_list_dialog(target_entity_type) {
            return new DialogSimple({
                id: 'status_list_dialog',
                title: 'Update Status List',
                href: '/status_lists/{id}/update/dialog'.replace(reg, target_entity_type),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // STATUS
        exports.create_status_dialog = function create_status_dialog() {
            return new DialogSimple({
                id: 'status_dialog',
                title: 'New Status',
                href: '/statuses/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_status_dialog = function update_status_dialog(status_id) {
            return new DialogSimple({
                id: 'status_dialog',
                title: 'Update Status',
                href: '/statuses/{id}/update/dialog'.replace(reg, status_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // ASSET
        exports.create_asset_dialog = function create_asset_dialog(project_id) {
            project_id = project_id || -1;
            return new DialogSimple({
                id: 'asset_dialog',
                title: 'New Asset',
                href: '/projects/{id}/assets/create/dialog'.replace(reg, project_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_asset_dialog = function update_asset_dialog(asset_id) {
            return new DialogSimple({
                id: 'asset_dialog',
                title: 'Update Asset',
                href: '/assets/{id}/update/dialog'.replace(reg, asset_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // SHOT
        exports.create_shot_dialog = function create_shot_dialog(project_id) {
            project_id = project_id || -1;
            return new DialogSimple({
                id: 'shot_dialog',
                title: 'New Shot',
                href: '/projects/{id}/shots/create/dialog'.replace(reg, project_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_shot_dialog = function update_shot_dialog(shot_id) {
            return new DialogSimple({
                id: 'shot_dialog',
                title: 'Update Shot',
                href: '/shots/{id}/update/dialog'.replace(reg, shot_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // SEQUENCE
        exports.create_sequence_dialog = function create_sequence_dialog(project_id) {
            project_id = project_id || -1;
            return new DialogSimple({
                id: 'sequence_dialog',
                title: 'New Sequence',
                href: '/projects/{id}/sequences/create/dialog'.replace(reg, project_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_sequence_dialog = function update_sequence_dialog(sequence_id) {
            return new DialogSimple({
                id: 'sequence_dialog',
                title: 'Update Sequence',
                href: '/sequences/{id}/update/dialog'.replace(reg, sequence_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // TASK
        exports.create_task_dialog = function create_task_dialog(project_id) {
            return new DialogSimple({
                id: 'task_dialog',
                title: 'New Task',
                href: '/projects/{id}/tasks/create/dialog'.replace(reg, project_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_task_dialog = function update_task_dialog(task_id) {
            return new DialogSimple({
                id: 'task_dialog',
                title: 'Update Task',
                href: '/tasks/{id}/update/dialog'.replace(reg, task_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.create_child_task_dialog = function create_child_task_dialog(task_id) {
            return new DialogSimple({
                id: 'task_dialog',
                title: 'New Child Task',
                href: '/tasks/{id}/child_tasks/create/dialog'.replace(reg, task_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.create_dependent_task_dialog = function create_dependent_task_dialog(task_id) {
            return new DialogSimple({
                id: 'task_dialog',
                title: 'New Dependent Task',
                href: '/tasks/{id}/dependent_tasks/create/dialog'.replace(reg, task_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // TIME LOG
        exports.create_time_log_dialog = function create_time_log_dialog(task_id) {
            return new DialogSimple({
                id: 'time_log_dialog',
                title: 'New TimeLog',
                href: '/tasks/{id}/time_logs/create/dialog'.replace(reg, task_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_time_log_dialog = function update_time_log_dialog(time_log_id) {
            return new DialogSimple({
                id: 'time_log_dialog',
                title: 'Update TimeLog',
                href: '/time_logs/{id}/update/dialog'.replace(reg, time_log_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };
        // ********************************************************************
        // TICKET
        exports.create_ticket_dialog = function create_ticket_dialog(project_id) {
            return new DialogSimple({
                id: 'ticket_dialog',
                title: 'New Ticket',
                href: '/projects/{id}/tickets/create/dialog'.replace(reg, project_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_ticket_dialog = function update_ticket_dialog(ticket_id) {
            return new DialogSimple({
                id: 'ticket_dialog',
                title: 'Update Ticket',
                href: '/tickets/{id}/update/dialog'.replace(reg, ticket_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };
         // ********************************************************************
        // VACATION
        exports.create_vacation_dialog = function create_vacation_dialog(user_id) {
            return new DialogSimple({
                id: 'vacation_dialog',
                title: 'New TimeLog',
                href: '/users/{id}/vacations/create/dialog'.replace(reg, user_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_vacation_dialog = function update_vacation_dialog(vacation_id) {
            return new DialogSimple({
                id: 'vacation_dialog',
                title: 'Update Vacation',
                href: '/vacations/{id}/update/dialog'.replace(reg, vacation_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // VERSION
        exports.create_version_dialog = function create_version_dialog(task_id) {
            return new DialogSimple({
                id: 'version_dialog',
                title: 'New Version',
                href: '/tasks/{id}/versions/create/dialog'.replace(reg, task_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_version_dialog = function update_version_dialog(version_id) {
            return new DialogSimple({
                id: 'version_dialog',
                title: 'Update Version',
                href: '/versions/{id}/update/dialog'.replace(reg, version_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };


        // ********************************************************************
        // DEPARTMENT
        exports.create_department_dialog = function create_department_dialog() {
            return new DialogSimple({
                id: 'department_dialog',
                title: 'New Department',
                href: '/departments/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_department_dialog = function update_department_dialog(department_id) {
            return new DialogSimple({
                id: 'department_dialog',
                title: 'Update Department',
                href: '/departments/{id}/update/dialog'.replace(reg, department_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.append_departments_dialog = function append_departments_dialog(user_id) {
            return new DialogSimple({
                id: 'append_department_dialog',
                title: 'Append Department',
                href: '/users/{id}/departments/append/dialog'.replace(reg, user_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        // ********************************************************************
        // GROUPS
        exports.create_group_dialog = function create_group_dialog() {
            return new DialogSimple({
                id: 'group_dialog',
                title: 'New Group',
                href: '/groups/create/dialog',
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.update_group_dialog = function update_group_dialog(group_id) {
            return new DialogSimple({
                id: 'group_dialog',
                title: 'Update Group',
                href: '/groups/{id}/update/dialog'.replace(reg, group_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };

        exports.append_group_dialog = function append_group_dialog(user_id) {
            return new DialogSimple({
                id: 'append_group_dialog',
                title: 'Append Group',
                href: '/users/{id}/groups/append/dialog'.replace(reg, user_id),
                resize: true,
                style: style,
                executeScripts: true
            });
        };
    });

