/*
 Copyright (c) 2012-2013 Open Lab
 Written by Roberto Bicchierai and Silvia Chelazzi http://roberto.open-lab.com
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
function GridEditor(master) {
    this.master = master; // is the a GanttEditor instance
    var gridEditor;
    if (this.master.grid_mode == 'Task'){
//        console.debug('GridEditor.__init__: this.master.grid_mode = Task');
        gridEditor = $.JST.createFromTemplate({}, "TASKSEDITHEAD");
    } else if (this.master.grid_mode == 'Resource') {
//        console.debug('GridEditor.__init__: this.master.grid_mode = Resource');
        gridEditor = $.JST.createFromTemplate({}, "RESOURCESEDITHEAD");
    }
    gridEditor.gridify();
    this.element = gridEditor;
}

GridEditor.prototype.addTask = function (task) {
//    console.debug('GridEditor.addTask start');

    var taskRow;
    if (task.type == 'Task' || task.type == 'Asset' || task.type == 'Shot' ||
        task.type == 'Sequence') {
        if (!task.isParent()) {
            taskRow = $.JST.createFromTemplate(task, "TASKROW");
        } else {
            taskRow = $.JST.createFromTemplate(task, "PARENTTASKROW");
        }
    } else if (task.type == 'Project') {
        taskRow = $.JST.createFromTemplate(task, "PROJECTROW");
    }

    //save row element on task
    task.rowElement = taskRow;
//    console.debug('drawing task: ', task.name, task);
    if (task.parent != null){
        // append under the lowestChildRow of the sibling or parent
        var child;
        var found_child = null;
        var children = task.parent.children;
//        console.debug('task.parent.children : ', children);
        // start from the task itself
        var sibling_index = task.parent.child_ids.indexOf(task.id) - 1;
//        console.debug('sibling_index : ', sibling_index);
        found_child = children[sibling_index];
        if (found_child){
//            console.debug('inserting after sibling');
            taskRow.insertAfter(found_child.lowestChildRow); // lowestChildRow is self if this is a leaf task
        } else {
//            console.debug('found no sibling, appending directly under parents lowestChildRow');
            // insert directly under parent
//            console.debug('parents current lowestChildRow : ', task.parent.lowestChildRow);
            taskRow.insertAfter(task.parent.lowestChildRow);
        }
//        console.debug('updating task.lowestChildRow to self');
        task.lowestChildRow = taskRow;
//        console.debug('updating task.parent.lowestChildRow');
        task.parent.lowestChildRow = taskRow;
    } else {
//        console.debug('no parent directly adding to editor');
        this.element.append(taskRow);
//        console.debug('setting task.lowestChildRow to self');
        task.lowestChildRow = taskRow;
//        console.debug('finished adding to editor');
    }

    this.bindRowEvents(task);

//    console.debug('GridEditor.addTask end');
    return taskRow;
};

GridEditor.prototype.addResource = function (resource) {
    var resourceRow = $.JST.createFromTemplate(resource, "RESOURCEROW");
    //save row element on resource
    resource.rowElement = resourceRow;
    this.element.append(resourceRow);
    return resourceRow;
};


GridEditor.prototype.refreshRowIndices = function () {
    if (this.master.grid_mode=='Task'){
        this.element.find(".taskRowIndex").each(function (i, el) {
            $(el).html(i + 1);
        });
    } else if (this.master.grid_mode == 'Resource'){
        this.element.find(".resourceRowIndex").each(function (i, el) {
            $(el).html(i + 1);
        });
    }
//    console.debug('GridEditor.refreshRowIndices end');
};


GridEditor.prototype.refreshTaskRow = function (task) {
    var row = task.rowElement;
    if (row == null){
        // skip this task
        return;
    }

    row.find(".taskRowIndex").html(task.getRow() + 1);
    row.find(".indentCell").css("padding-left", task.getParents().length * 15);
    row.find(".name").html(task.name);
    row.find(".id").html(task.id);

    row.find(".timing").html(task.schedule_model.toUpperCase()[0] + ":" + task.schedule_timing + task.schedule_unit);
    row.find(".start").html(new Date(task.start).format("yyyy-mm-dd HH:00")).updateOldValue(); // called on dates only because for other field is called on focus event
    row.find(".end").html(new Date(task.end).format("yyyy-mm-dd HH:00")).updateOldValue();
};


GridEditor.prototype.refreshResourceRow = function (resource) {
    var row = resource.rowElement;
    row.find(".resourceRowIndex").html(resource.getRow() + 1);
    row.find(".id").html(resource.id);
    row.find(".name").html(resource.name);
};


GridEditor.prototype.refresh = function () {
    if (this.master.grid_mode == 'Task'){
        for (var i = 0; i < this.master.tasks.length; i++) {
            this.refreshTaskRow(this.master.tasks[i]);
        }
    } else if (this.master.grid_mode == 'Resource'){
        for (var i = 0; i < this.master.resources.length; i++) {
            this.refreshResourceRow(this.master.resources[i]);
        }
    }
};


GridEditor.prototype.reset = function () {
//    console.debug('GridEditor.reset start');
    this.element.find("[dataId]").remove();
//    console.debug('GridEditor.reset end');
};


GridEditor.prototype.bindRowEvents = function(task){
    // bind the row events
    var row = task.rowElement;
    var folder = row.find(".folder");
    var master = this.master;

    folder.mousedown(function(){
        task.toggleCollapse();
        // redraw gantt chart
        task.master.gantt.refreshGantt();
        // store collapse state
        master.storeTaskCollapseState();
    });
};
