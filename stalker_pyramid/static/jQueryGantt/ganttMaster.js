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
function GanttMaster(kwargs) {
    this.__version__ = '0.1.0.a5';
    this.tasks = [];
    this.task_ids = []; // lookup table for quick task access
    this.root_tasks = [];
    this.root_task_ids = [];
    this.parent_tasks = [];
    this.parent_task_ids = [];

    this.time_logs = [];
    this.time_log_ids = [];

    this.links = [];

    this.cookie = null;
    this.json = null;

    this.editor; //element for editor
    this.gantt; //element for gantt

    // Mode of View:
    // There are two modes for the grid Task or Resource
    // and two modes for the gantt Task or TimeLog
    this.grid_mode = kwargs['grid_mode'] || 'Task'; // 'Resource'
    this.gantt_mode = kwargs['gantt_mode'] || 'Task'; // 'TimeLog'

    this.element;

    this.resources = []; //list of resources
    this.resource_ids = []; //lookup table for quick resource access

    this.minEditableDate = 0;
    this.maxEditableDate = Infinity;

    this.minDate = new Date();
    this.maxDate = new Date();

    this.timing_resolution = 3600000; // as miliseconds, for now it is 1 hour

    // this is in minutes from midnight because Stalker is designed in that way
    this.working_hours = {
        'mon': [
            [540, 1080]
        ],
        'tue': [
            [540, 1080]
        ],
        'wed': [
            [540, 1080]
        ],
        'thu': [
            [540, 1080]
        ],
        'fri': [
            [540, 1080]
        ],
        'sat': [],
        'sun': []
    };

    this.start = new Date().getTime();
    this.end = new Date().getTime();

    this.daily_working_hours = 9; // this is the default
    this.weekly_working_hours = 45;
    this.weekly_working_days = 5;
    this.yearly_working_days = 260.714; // 5 * 52.1428

    this.canWriteOnParent = true;
    this.canWrite = true;

    this.firstDayOfWeek = Date.firstDayOfWeek;

    this.currentTask; // task currently selected;

    this.__currentTransaction;  // a transaction object holds previous state during changes
//    this.__undoStack = [];
//    this.__redoStack = [];


    this.task_link_template;
    this.resource_link_template;

    var self = this;
}

GanttMaster.prototype.init = function (place) {
    this.element = place;

    var self = this;

    //load templates
    $("#gantEditorTemplates").loadTemplates().remove();  // TODO: Remove inline jquery, this should be injected
    $("#gantEditorTemplates").loadTemplates().remove();  // TODO: Remove inline jquery, this should be injected

    //create editor
    this.editor = new GridEditor(this);
    this.editor.element.width(place.width() * .9 - 10);
    place.append(this.editor.element);

    //create gantt
//    this.gantt = new GanttDrawer("m", new Date().getTime() - 3600000 * 24 * 2, new Date().getTime() + 3600000 * 24 * 15, this, place.width() * .6);
    this.gantt = new GanttDrawer('m', this.start, this.end, this, place.width() * .6);

    //setup splitter
    var splitter = $.splittify.init(place, this.editor.element, this.gantt.element, 50);
    splitter.secondBox.css("overflow-y", "auto").scroll(function () {
        splitter.firstBox.scrollTop(splitter.secondBox.scrollTop());
    });

    //bindings
    place.bind("refreshTasks.gantt",function () {
        self.redrawTasks();
    }).bind("refreshTask.gantt",function (e, task) {
            self.drawTask(task);
        }).bind("zoomPlus.gantt",function () {
            self.gantt.zoomGantt(true);
        }).bind("zoomMinus.gantt", function () {
            self.gantt.zoomGantt(false);
        });
};

GanttMaster.messages = {
    "CHANGE_OUT_OF_SCOPE": "NO_RIGHTS_FOR_UPDATE_PARENTS_OUT_OF_EDITOR_SCOPE",
    "START_IS_MILESTONE": "START_IS_MILESTONE",
    "END_IS_MILESTONE": "END_IS_MILESTONE",
    "TASK_HAS_CONSTRAINTS": "TASK_HAS_CONSTRAINTS",
    "GANTT_ERROR_DEPENDS_ON_OPEN_TASK": "GANTT_ERROR_DEPENDS_ON_OPEN_TASK",
    "GANTT_ERROR_DESCENDANT_OF_CLOSED_TASK": "GANTT_ERROR_DESCENDANT_OF_CLOSED_TASK",
    "TASK_HAS_EXTERNAL_DEPS": "TASK_HAS_EXTERNAL_DEPS",
    "GANTT_ERROR_LOADING_DATA_TASK_REMOVED": "GANTT_ERROR_LOADING_DATA_TASK_REMOVED",
    "CIRCULAR_REFERENCE": "CIRCULAR_REFERENCE",
    "ERROR_SETTING_DATES": "ERROR_SETTING_DATES",
    "CANNOT_DEPENDS_ON_ANCESTORS": "CANNOT_DEPENDS_ON_ANCESTORS",
    "CANNOT_DEPENDS_ON_DESCENDANTS": "CANNOT_DEPENDS_ON_DESCENDANTS",
    "INVALID_DATE_FORMAT": "INVALID_DATE_FORMAT",
    "GANTT_QUARTER_SHORT": "GANTT_QUARTER_SHORT",
    "GANTT_SEMESTER_SHORT": "GANTT_SEMESTER_SHORT"
};


GanttMaster.prototype.createTask = function (kwargs) {
    return new Task(kwargs);
};


GanttMaster.prototype.createResource = function (kwargs) {
    return new Resource(kwargs);
};


//update depends strings
GanttMaster.prototype.updateDepends = function () {
    //remove all deps
    for (var i = 0; i < this.tasks.length; i++) {
        this.tasks[i].depends = [];
    }

    for (var i = 0; i < this.links.length; i++) {
        var link = this.links[i];
        link.to.depends.push(link.from.id);
    }
};


/**
 * a ganttData contains tasks, resources, roles
 * @param ganttData
 * @param Deferred
 */
GanttMaster.prototype.loadGanttData = function (ganttData, Deferred) {
//    console.debug('GanttMaster.loadGanttData start');
    var deferred = new Deferred;
    this.beginTransaction();

    this.timing_resolution = ganttData.timing_resolution || this.timing_resolution;
    this.working_hours = ganttData.working_hours || this.working_hours;
    this.daily_working_hours = ganttData.daily_working_hours || this.daily_working_hours;
    this.weekly_working_hours = ganttData.weekly_working_hours || this.weekly_working_hours;
    this.weekly_working_days = ganttData.weekly_working_days || this.weekly_working_days;

    this.start = ganttData.start || -1;
    this.end = ganttData.end || -1;
    this.gantt.originalStartMillis = ganttData.start;
    this.gantt.originalEndMillis = ganttData.end;

    this.canWrite = ganttData.canWrite;
    this.canWriteOnParent = ganttData.canWriteOnParent;

    if (ganttData.minEditableDate)
        this.minEditableDate = computeStart(ganttData.minEditableDate);
    else
        this.minEditableDate = -Infinity;

    if (ganttData.maxEditableDate)
        this.maxEditableDate = computeEnd(ganttData.maxEditableDate);
    else
        this.maxEditableDate = Infinity;

//    console.debug('GanttMaster.loadGanttData 3');

    // reset
    this.reset();

    // load resources
    this.loadResources(ganttData.resources);
    this.loadTasks(ganttData.tasks);
    this.loadTimeLogs(ganttData.time_logs);

    // now draw everything
    this.drawData();

    this.endTransaction();
    var self = this;

    // TODO: this is ridiculous, it should start when something is finished, not after a certain time
//    this.gantt.element.oneTime(200, function () {
//        self.gantt.centerOnToday();
        deferred.resolve('success');
//    });


    return deferred.promise;
};

GanttMaster.prototype.loadResources = function (resources) {
    // loads data in the following format
    //
    // resources = {
    //     'keys' : ['id', 'name']
    //     'data' : [
    //         [resource1.id, resource1.name],
    //         [resource2.id, resource2.name],
    //         ...
    //         [resourceN.id, resourceN.name]
    //     ]
    // }
    //

    var keys = resources.keys;
    var key_count = keys.length;
    var kwargs = {};
    kwargs['master'] = this;
    var data = resources.data;

    var resource;
    for (var i = 0; i < data.length; i++) {
        for (var j = 0; j < key_count; j++) {
            kwargs[keys[j]] = data[i][j];
        }
        resource = new Resource(kwargs);
        this.resources.push(resource);
        this.resource_ids.push(resource.id);
    }
};


GanttMaster.prototype.loadTasks = function (tasks) {
    //
    // loads data in the following format:
    //
    // tasks = {
    //     'keys' : [key1, key2, ...., keyN]
    //     'data' : [
    //         [task1.key1, task1.key2, ....., task1.keyN],
    //         [task2.key1, task2.key2, ....., task2.keyN],
    //         ...
    //         [taskN.key1, taskN.key2, ....., taskN.keyN],
    //     ]
    // }
    //

//    console.debug('GanttMaster.loadTasks start');
    //var factory = new TaskFactory();

    var keys = tasks.keys;
    var key_count = keys.length;
    var kwargs = {};
    kwargs['master'] = this;
    var data = tasks.data;

    var task;
    for (var i = 0; i < data.length; i++) {
        for (var j = 0; j < key_count; j++) {
            kwargs[keys[j]] = data[i][j];
        }
        task = new Task(kwargs);
        task.depends = null;
        this.tasks.push(task);  //append task at the end
        this.task_ids.push(task.id);
    }

    // find root tasks
//    console.debug('getting root tasks start');
    this.root_tasks = [];
    var current_task;
    for (var i = 0; i < this.tasks.length; i++) {
        // just find root tasks
        // also register parents
//        if (this.tasks[i].getParent() == null) { // this fills parent.children array
        current_task = this.tasks[i];
        if (current_task.parent_id == null) {
            this.root_tasks.push(current_task);
            this.root_task_ids.push(current_task);
        } else {
            // fill parent.children array
            current_task.getParent();
        }
        // also fill the task.depends
        this.tasks[i].getDepends();
    }
//    console.debug('getting root tasks end');

//    console.debug('root_tasks : ', this.root_tasks);
//    console.debug('tasks      : ', this.tasks);
    
    var loop_through_child = function (task, children) {
        if (children == null) {
            children = []
        }
        children.push(task);
        var current_task_children = task.getChildren();
        for (var n = 0; n < current_task_children.length; n++) {
            children = loop_through_child(current_task_children[n], children);
        }
        return children;
    };

    var sorted_task_list = [];
    // now go from root to child
    for (var i = 0; i < this.root_tasks.length; i++) {
        sorted_task_list = loop_through_child(this.root_tasks[i], sorted_task_list);
    }

    // update tasks
    this.tasks = sorted_task_list;
    // update the lookup table
    this.task_ids = [];
    for (var i = 0; i < this.tasks.length; i++) {
        this.task_ids.push(this.tasks[i].id);
    }
    // set the first task selected
//    this.currentTask = this.tasks[0];

    // loop through all parent tasks and sort their children
    for (var i = 0; i < this.tasks.length; i++) {
        task = this.tasks[i];
        if (task.isParent()){
            this.parent_tasks.push(task);
            this.parent_task_ids.push(task.id);
            task.sortChildren();
        }
    }
//    console.debug('GanttMaster.loadTasks end');
};


GanttMaster.prototype.loadTimeLogs = function (time_logs) {
    //
    // loads data in the following format:
    //
    // time_logs = {
    //     'keys' : [key1, key2, ...., keyN]
    //     'data' : [
    //         [time_log1.key1, time_log1.key2, ....., time_log1.keyN],
    //         [time_log2.key1, time_log2.key2, ....., time_log2.keyN],
    //         ...
    //         [time_logN.key1, time_logN.key2, ....., time_logN.keyN],
    //     ]
    // }
    //
//    console.debug('GanttMaster.loadTimeLogs start');
    var keys = time_logs.keys;
    var key_count = keys.length;
    var kwargs = {};
    kwargs['master'] = this;
    var data = time_logs.data;
 
    var time_log;
    for (var i = 0; i < data.length; i++) {
        for (var j = 0; j < key_count; j++) {
            kwargs[keys[j]] = data[i][j];
        }
        time_log = new TimeLog(kwargs);

        this.time_logs.push(time_log);
        this.time_log_ids.push(time_log.id);
        // to update the task relation
        time_log.getTask();
    }
//    console.debug('GanttMaster.loadTimeLogs end');
};

GanttMaster.prototype.drawData = function () {
//    console.debug('GanttMaster.drawData start');
    // before drawing restore collapse state of tasks
    this.restoreTaskCollapseState();

    this.drawResources();
    this.drawRootTasks();
    this.drawTimeLogs();
//    console.debug(this);
//    console.debug('GanttMaster.drawData end');
};


GanttMaster.prototype.drawResources = function () {
    if (this.grid_mode == 'Resource') {
        for (var i = 0; i < this.resources.length; i++) {
            this.editor.addResource(this.resources[i]);
        }
    }
};


//GanttMaster.prototype.drawTasks = function () {
//    var task;
//    //var prof=new Profiler("gm_loadTasks_addTaskLoop");
//    for (var i = 0; i < this.tasks.length; i++) {
//        task = this.tasks[i];
//        
//        if (task.isParentsCollapsed()){
//            continue;
//        }
//
//        //add Link collection in memory
//        if (this.gantt_mode == 'Task') {
//            this.updateLinks(task);
//        }
//
//        //append task to editor
//        if (this.grid_mode == 'Task') {
//            this.editor.addTask(task);
//        }
//    }
//};

GanttMaster.prototype.drawRootTasks = function () {
//    console.debug('GanttMaster.drawRootTasks start');
    var root_task;
    //var prof=new Profiler("gm_loadTasks_addTaskLoop");
    for (var i = 0; i < this.root_tasks.length; i++) {
        root_task = this.root_tasks[i];
        // give the drawer function and let the task manage its hierarchy itself
        root_task.draw(this.editor);

//        if (task.isParentsCollapsed()){
//            continue;
//        }

        //add Link collection in memory
//        if (this.gantt_mode == 'Task') {
//            this.updateLinks(task);
//        }

        //append task to editor
//        if (this.grid_mode == 'Task') {
//            this.editor.addTask(task);
//        }
    }
//    console.debug('GanttMaster.drawRootTasks end');
};

GanttMaster.prototype.drawTimeLogs = function () {
    // do nothing for now
    //this.gantt.refreshGantt();
//    if (this.gantt_mode == 'TimeLog'){
//        this.gantt.redrawTimeLogs();
//    }
};


GanttMaster.prototype.getTask = function (taskId) {
    if (typeof(taskId) == 'string') {
        taskId = parseInt(taskId);
    }
    var task_index = this.task_ids.indexOf(taskId);
    return this.tasks[task_index];
};


GanttMaster.prototype.getTimeLog = function (time_log_id) {
    if (typeof(time_log_id) == 'string') {
        time_log_id = parseInt(time_log_id);
    }
    var time_log_index = this.time_log_ids.indexOf(time_log_id);
    return this.time_logs[time_log_index];
};


GanttMaster.prototype.getResource = function (resId) {
    var resource_index = this.resource_ids.indexOf(resId);
    return this.resources[resource_index];
};


GanttMaster.prototype.taskIsChanged = function () {
    var master = this;

    //refresh is executed only once every 50ms
    this.element.stopTime("gnnttaskIsChanged");
    this.element.oneTime(50, "gnnttaskIsChanged", function () {
        master.editor.refresh();
        master.gantt.refreshGantt();
    });
};


GanttMaster.prototype.refresh = function () {
    this.editor.refresh();
    this.gantt.refreshGantt();
};

GanttMaster.prototype.reset = function () {
    this.tasks = [];
    this.task_ids = [];
    this.resources = [];
    this.resource_ids = [];
    this.time_logs = [];
    this.time_log_ids = [];
    this.links = [];
    delete this.currentTask;

    this.editor.reset();
    this.gantt.reset();
};

GanttMaster.prototype.changeMode = function (grid_mode, gantt_mode) {
    // remove elements
    this.editor.reset();
    this.gantt.reset();

    this.grid_mode = grid_mode;
    this.gantt_mode = gantt_mode;

    // redraw them
    this.drawResources();
    this.drawTasks();
//    this.drawTimeLogs();
    this.gantt.refreshGantt();
};

GanttMaster.prototype.saveGantt = function (forTransaction) {
    //var prof = new Profiler("gm_saveGantt");
    var saved = [];
    for (var i = 0; i < this.tasks.length; i++) {
        var task = this.tasks[i];

        // skip if project
        if (task.type == 'Project') {
            continue;
        }

        var cloned = task.clone();
        delete cloned.master;
        delete cloned.rowElement;
        delete cloned.ganttElements;

        delete cloned.children;
        //delete cloned.resources;
        delete cloned.depends;
        delete cloned.parent;

        saved.push(cloned);
    }

    var ret = {tasks: saved};

    if (!forTransaction) {
        ret.resources = this.resources;
        ret.canWrite = this.canWrite;
        ret.canWriteOnParent = this.canWriteOnParent;
    }

    //prof.stop();
    return ret;
};


GanttMaster.prototype.updateLinks = function (task) {
    //console.debug("updateLinks");

    // TODO: may be we need to check if the gantt_mode == 'Task'

    //remove my depends
    this.links = this.links.filter(function (link) {
        return link.to != task;
    });

    // just update the depends list
    if (task.getDepends().length > 0) {
        //cannot depend from an ancestor
        var parents = task.getParents();
        //cannot depend from descendants
        var descendants = task.getDescendant();

        var deps = task.depends;
        var newDepsString = "";

        var visited = [];
        for (var j = 0; j < deps.length; j++) {
            var dep = deps[j];
            var lag = 0;

            if (dep) {
                this.links.push(new Link(dep, task, lag));
                newDepsString = newDepsString + (newDepsString.length > 0 ? "," : "") + dep;
            }
        }

        task.depends_string = newDepsString;

    }
};


//<%----------------------------- TRANSACTION MANAGEMENT ---------------------------------%>
GanttMaster.prototype.beginTransaction = function () {
//    console.debug('GanttMaster.beginTransaction start');
    if (!this.__currentTransaction) {
        this.__currentTransaction = {
//            snapshot: JSON.stringify(this.saveGantt(true)),
            errors: []
        };
    } else {
        console.error("Cannot open twice a transaction");
    }
//    console.debug('GanttMaster.beginTransaction end');
    return this.__currentTransaction;
};


GanttMaster.prototype.endTransaction = function () {
    if (!this.__currentTransaction) {
        console.error("Transaction never started.");
        return true;
    }

    var ret = true;

    this.gantt.originalStartMillis = this.start;
    this.gantt.originalEndMillis = this.end;

    this.taskIsChanged(); //enqueue for gantt refresh
    this.__currentTransaction = undefined;

    return ret;
};

//this function notify an error to a transaction -> transaction will rollback
GanttMaster.prototype.setErrorOnTransaction = function (errorMessage, task) {
    if (this.__currentTransaction) {
        this.__currentTransaction.errors.push({msg: errorMessage, task: task});
    } else {
        console.error(errorMessage);
    }
};

// inhibit undo-redo
GanttMaster.prototype.checkpoint = function () {
    this.__undoStack = [];
    this.__redoStack = [];
};

GanttMaster.prototype.getDateInterval = function () {
    var start = Infinity;
    var end = -Infinity;
    for (var i = 0; i < this.tasks.length; i++) {
        var task = this.tasks[i];
        if (task.type == 'Project') {
            continue;
        }
        if (start > task.start)
            start = task.start;
        if (end < task.end)
            end = task.end;
    }

    this.minDate = start;
    this.maxDate = end;
    return {
        start: this.minDate,
        end: this.maxDate
    }
};

GanttMaster.prototype.storeTaskCollapseState = function(){
    // stores the task collapse state in a cookie
    // needs a cookie like dojo.cookie in master.cookie
    var task_collapse_state = [];
    // preserve the previous list
    var cookie_data = this.cookie("TaskCollapseState");
    if (cookie_data){
        task_collapse_state = this.json.parse(cookie_data);
    }
//    console.debug('current task_collapse_state:', task_collapse_state);
    var index;
    var task;
    for (var i=0; i < this.parent_tasks.length; i++){
        task = this.parent_tasks[i];
        index = task_collapse_state.indexOf(task.id);
        if (task.collapsed){
            // store if it is not already in the list
            if (index == -1){
                task_collapse_state.push(task.id);
            }
        } else {
            // remove it from the list if it is there
            if (index != -1){
                task_collapse_state.splice(index, 1);
            }
        }
    }
    // then store data
    this.cookie(
        "TaskCollapseState",
        this.json.stringify(task_collapse_state)
    );
};

GanttMaster.prototype.restoreTaskCollapseState = function(){
    // restores the task collapse state in a cookie
    // @param cookie: dojo.cookie
//    console.debug('GanttMaster.restoreTaskCollapseState start');
//    console.debug('restoring task collapse state');
    var task_collapse_state = [];
    var task_id;
    var task;
    var cookie_data = this.cookie("TaskCollapseState");
    if (cookie_data){
        task_collapse_state = this.json.parse(cookie_data);
        if (task_collapse_state){
            for (var i = 0; i < task_collapse_state.length; i++){
                task_id = task_collapse_state[i];
                // get the task
                task = this.getTask(task_id);
                if (task){
                    task.collapsed = true;
                }
            }
        }
    }
//    console.debug('GanttMaster.restoreTaskCollapseState end');
};
