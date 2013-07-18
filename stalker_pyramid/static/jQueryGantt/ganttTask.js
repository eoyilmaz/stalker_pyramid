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



function Task(kwargs) {
    'use strict';
    this.id = kwargs.id || null;
    this.name = kwargs.name || null;
    this.hierarchy_name = kwargs.hierarchy_name || null;
    this.description = kwargs.description || null;
    
    this.priority = kwargs.priority || 500;

    this.type = kwargs.type || null;

    this.status = "STATUS_UNDEFINED";

    this.children = [];
    this.child_ids = [];
    this.parent_id = kwargs.parent_id || null;
    this.parent = kwargs.parent || null;
    this.depend_ids = kwargs.depend_ids || [];
    this.depends = null;

    this.start = kwargs.start || null;
    this.duration = kwargs.duration || null;
    this.end = kwargs.end || null;

    this.schedule_model = kwargs.schedule_model;
    this.schedule_timing = (kwargs.schedule_timing || 10).toFixed(1);
    this.schedule_unit = kwargs.schedule_unit || 'h';
    this.schedule_constraint = kwargs.schedule_constraint || 0;

    this.schedule_seconds = kwargs.schedule_seconds || 0;
    this.total_logged_seconds = kwargs.total_logged_seconds || 0;

    this.progress = this.schedule_seconds > 0 ? this.total_logged_seconds / this.schedule_seconds * 100 : 0;

//    console.debug('this.total_logged_seconds : ', this.total_logged_seconds);
//    console.debug('this.schedule_seconds     : ', this.schedule_seconds);
//    console.debug('this.progress             : ', this.progress);

    this.bid_timing = (kwargs.bid_timing).toFixed(1);
    this.bid_unit = kwargs.bid_unit;

//    console.debug('schedule_constraint : ', this.schedule_constraint);
//    console.debug('schedule_model      : ', this.schedule_model);
//    console.debug('schedule_timing     : ', this.schedule_timing);
//    console.debug('schedule_unit       : ', this.schedule_unit);
//    console.debug('bid_timing          : ', this.bid_timing);
//    console.debug('bid_unit            : ', this.bid_unit);

    this.is_milestone = false;
    this.startIsMilestone = false;
    this.endIsMilestone = false;

    // some dynamic attributes
    this.collapsed = false;
    this.hidden = false;

    this.clippedStart = false;
    this.clippedEnd = false;

    this.rowElement = null; //row editor html element
    this.lowestChildRow = null; // for hierarchical row inserts

    this.ganttElements = []; //gantt html element
    this.master = kwargs.master || null;

    this.resources = kwargs.resources || [];
    this.resource_ids = kwargs.resource_ids || [];
    
    var i;
    if (this.resource_ids.length === 0){
        // no problem if there are no resources
        for (i = 0; i < this.resources.length; i++) {
            this.resource_ids.push(this.resources[i].id);
        }
    } else {
        if (this.master !== null){
            for (i = 0; i < this.resource_ids.length; i++){
                this.resources.push(this.master.getResource(this.resource_ids[i]));
            }
        }
    }

    this.time_logs = [];
    this.time_log_ids = [];

    // update the duration according to the schedule_timing value
    //this.update_duration_from_schedule_timing();
}

Task.prototype.clone = function () {
    'use strict';
    var ret = {};
    for (var key in this) {
        if (typeof(this[key]) !== "function") {
            ret[key] = this[key];
        }
    }
    return ret;
};

Task.prototype.getResourcesString = function () {
    'use strict';
    var ret = "";
    for (var i = 0; i < this.resources.length; i++) {
        var resource = this.resources[i];
        var res = this.master.getResource(resource.id);
        if (res) {
            ret = ret + (ret === "" ? "" : ", ") + res.name;
        }
    }
    return ret;
};

Task.prototype.getResourcesLinks = function () {
    'use strict';
    var ret = "";
    for (var i = 0; i < this.resources.length; i++) {
        ret = ret + (ret === "" ? "" : ", ") + this.resources[i].link();
    }
    return ret;
};

Task.prototype.getDependsLinks = function () {
    'use strict';
    var depends = this.getDepends();
    var ret = "";
    for (var i = 0; i < depends.length; i++) {
        ret = ret + (ret === "" ? "" : ", ") + depends[i].link();
    }
    return ret;
};

Task.prototype.link = function () {
    'use strict';
    var rendered;
    if (this.type === 'Project') {
        rendered = $.JST.createFromTemplate(this, "PROJECTLINK");
    } else {
        rendered = $.JST.createFromTemplate(this, "TASKLINK");
    }
    return rendered[0].outerHTML;
};


Task.prototype.createResource = function (kwargs) {
    'use strict';
    var resource = new Resource(kwargs);
    this.resources.push(resource);
    return resource;
};


//<%---------- TASK STRUCTURE ---------------------- --%>
Task.prototype.getRow = function () {
    'use strict';
    var index = -1;
    if (this.master)
        index = this.master.tasks.indexOf(this);
    return index;
};


Task.prototype.getParents = function () {
    'use strict';
    var parents = [];
    var current_task = this.getParent();
    while (current_task !== null) {
        parents.push(current_task);
        current_task = current_task.parent;
    }
    return parents;
};


Task.prototype.getParent = function () {
    'use strict';
    if (this.parent_id !== null && this.parent === null) {
        // there should be a parent
        // find the parent from parent_id
        var current_task;

        var parent_index = this.master.task_ids.indexOf(this.parent_id);
        if (parent_index !== -1) {
            this.parent = this.master.tasks[parent_index];
            // register the current task as a child of the parent task
            if (this.parent.child_ids.indexOf(this.id) === -1) {
                this.parent.child_ids.push(this.id);
                this.parent.children.push(this);
            }
        }
    }
    return this.parent;
};


Task.prototype.isParent = function () {
    'use strict';
    return this.children.length > 0;
};

Task.prototype.isLeaf = function () {
    'use strict';
    return this.children.length === 0;
};


Task.prototype.sortChildren = function(){
    'use strict';
    // sorts the children to their start dates
    this.children.sort(function (a, b) {
        return a.start - b.start;
    });
    // update child_ids
    this.child_ids = [];
    for (var i=0; i< this.children.length; i++){
        this.child_ids.push(this.children[i].id);
    }
};


Task.prototype.getChildren = function () {
    'use strict';
    return this.children;
};


Task.prototype.getDescendant = function () {
    'use strict';
    return this.children;
};

Task.prototype.getDepends = function () {
    'use strict';
    if (this.depends === null) {
        this.depends = [];
        if (this.depend_ids.length > 0) {
            // find the tasks
            var dep_id;
            var dep;
            var dep_index;
            for (var i = 0; i < this.depend_ids.length; i++) {
                dep_id = this.depend_ids[i];
                dep_index = this.master.task_ids.indexOf(dep_id);

                if (dep_index !== -1) {
                    dep = this.master.tasks[dep_index];
                    this.depends.push(dep);
                    // also update depends_string
                }
            }
        }
    }
    return this.depends;
};

Task.prototype.setDepends = function (depends) {
    'use strict';
    // if this is not an array but a string parse it as depends string
    var dependent_task;
    var i;
    if (typeof(depends) === 'string') {
        // parse it as depends string
        this.depends_string = depends;
        this.depends = [];
        this.depend_ids = [];
        var deps = this.depends_string.split(',');
        var dep_id;
        var depend_index;
        for (i = 0; i < deps.length; i++) {
            dep_id = deps[i].split(':')[0].trim(); // don't care about the lag
            depend_index = this.master.task_ids.indexOf(dep_id);
            if (depend_index !== -1) {
                dependent_task = this.master.tasks[depend_index];
                this.depends.push(dependent_task);
                this.depend_ids.push(dependent_task.id);
            }
        }
    } else if (depends instanceof Task) {
        // just set it to the depends list
        this.depends = [depends];
        this.depend_ids = [depends.id];
    } else if (depends instanceof Array) {
        // should be an array
        for (i = 0; i < depends.length; i++) {
            dependent_task = depends[i];
            if (dependent_task instanceof Task) {
                this.depends.push(dependent_task);
                this.depend_ids.push(dependent_task.id);
            }
        }
    }
    // somebody should tell GanttMaster to update the links after this.
};


Task.prototype.getSuperiors = function () {
    'use strict';
    // Returns the Tasks that this task depends to.
    return this.getDepends();
};


Task.prototype.getInferiors = function () {
    // Returns the tasks that depends to this task
    'use strict';
    var ret = [];
    var task = this;
    if (this.master) {
        ret = this.master.links.filter(function (link) {
            return link.from === task;
        });
    }
    return ret;
};


Task.prototype.update_duration_from_schedule_timing = function () {
    // updates the duration from schedule_timing    
};

Task.prototype.getProgress = function () {
    this.progress = this.schedule_seconds > 0 ? this.total_logged_seconds / this.schedule_seconds * 100 : 0;
    return this.progress;
};

Task.prototype.addTimeLog = function(time_log) {
    var time_log_id = time_log.id;
    var index = this.time_log_ids.indexOf(time_log_id);
    if (index == -1){
        // it is not in the list
        // update the time_log
        time_log.task_id = this.id;
        time_log.task = this;
        // update self
        this.time_logs.push(time_log);
        this.time_log_ids.push(time_log_id);
    } // if it is in the list do nothing
};

Task.prototype.addTimeLog_with_id = function(time_log_id){
    var time_log = this.master.getTimeLog(time_log_id);
    this.addTimeLog(time_log);
};


Task.prototype.toggleCollapse = function(kwargs){
    var row = this.rowElement;
    var folder = row.find(".folder");
    // toggles collapse state
    // get collapsed state
    var collapsed = folder.hasClass('collapsed');
    var child_task = null;
    var i = 0;
    if (collapsed){
        folder.removeClass('collapsed');
        folder.addClass('uncollapsed');
        // update collapsed attribute
        this.collapsed = false;
        // change child task rowElements
        for (i=0; i < this.children.length; i++ ){
            child_task = this.children[i];
            child_task.show();
        }
    } else {
        folder.removeClass('uncollapsed');
        folder.addClass('collapsed');
        // update collapsed attribute
        this.collapsed = true;
        for (i=0; i < this.children.length; i++ ){
            child_task = this.children[i];
            child_task.hide();
        }
    }
};

Task.prototype.hide = function(){
    // hide self and all child
    var rowElement = this.rowElement;
    if (rowElement !== null){
        rowElement.css('display', 'none');
    } else {
        // task has never been drawn
        // draw it
        // TODO: this should not be here, should be in the gridEditor
        this.master.editor.addTask(this);
        this.rowElement.css('display', 'none');
    }
    if (this.isParent()){
        for (var i=0; i < this.children.length; i++){
            var child = this.children[i];
            child.hide();
        }
    }
    this.hidden = true;
};

Task.prototype.show = function(){
    // show self and all child
    var rowElement = this.rowElement;
    if (rowElement !== null){
//        console.debug('there are rowElement');
        rowElement.css('display', 'table-row');
    } else {
        // task has never been drawn
        // draw it
//        console.debug('no rowElement');
        var self = this;
        this.lowestChildRow = this.master.editor.addTask(self);
        this.rowElement.css('display', 'table-row');
    }
    this.hidden = false;
    if (this.isParent()){
        if (!this.collapsed){
            for (var i=0; i < this.children.length; i++){
                var child = this.children[i];
                child.show();
            }
        }
    }
};

Task.prototype.isParentsCollapsed = function(){
    // returns true or false depending on any of its parent is collapsed
    var current_task = this.getParent();
    while (current_task !== null) {
        if (current_task.collapsed){
            this.hidden = true;
            return true;
        }
        current_task = current_task.parent;
    }
    return false;
};

Task.prototype.draw = function(editor){
//    console.debug('Task.draw start');
    
    // first draw self then the children
    var self = this;
    // hopefully we should have a rowElement
    this.lowestChildRow = editor.addTask(self);
    if (!this.collapsed){
        var child_task = null;
        for (var i=0; i<this.children.length; i++){
            child_task = this.children[i];
            child_task.draw(editor);
        }
        // add last children's lowestRow to self
        if (child_task){
            this.lowestChildRow = child_task.lowestChildRow;
        }
    }
//    console.debug('Task.draw end');
};
