function TimeLog(kwargs) {
    this.id = kwargs['id'] || null;

    this.task_id = kwargs['task_id'] || null;
    this.task = kwargs['task'] || null;

    this.resource_id = kwargs['resource_id'] || null;
    this.resource = kwargs['resource'] || null;

    this.start = kwargs['start'] || null;
    this.end = kwargs['end'] || null;

    this.rowElement = null; // row editor html element of the resource
    this.ganttElement = null; // gantt html element

    this.master = kwargs['master'] || null;
}

TimeLog.prototype.getResource = function(){
    // getter for the resource
    if (this.resource == null){
        this.resource = this.master.getResource(this.resource_id);
        this.rowElement = this.resource.rowElement;
    }
    return this.resource;
};

TimeLog.prototype.setResource = function(resource_id){
    // set the resource with id
    this.resource_id = resource_id;
    this.resource = this.master.getResource(resource_id);
};

TimeLog.prototype.getTask = function(){
    // getter for the task
    if (this.task == null){
        this.task = this.master.getTask(this.task_id);
        this.task.addTimeLog(this);
    }
    return this.task;
};

TimeLog.prototype.setTask = function(task_id){
    // set the task with id
    this.task_id = task_id;
    this.task = this.master.getTask(task_id);
    // also update the task
    this.task.addTimeLog(this);
};

