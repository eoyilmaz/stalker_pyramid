function Resource(kwargs) {
    this.id = kwargs['id'] || null;
    this.name = kwargs['name'] || (this.id || '');
    this.task_ids = kwargs['task_ids'] || [];
    this.tasks = kwargs['tasks'] || [];
    this.master = kwargs['master'] || null;
    this.rowElement = null; // row editor html element
    this.type = 'Resource';
}

Resource.prototype.getRow = function(){
    var index = -1;
    if (this.master)
        index = this.master.resources.indexOf(this);
    return index;
};

Resource.prototype.link = function(){
    var rendered = $.JST.createFromTemplate(this, 'RESOURCELINK');
    return rendered[0].outerHTML;
};


