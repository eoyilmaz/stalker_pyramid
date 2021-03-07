function Project(kwargs){
    this.id = kwargs['id'] || null;
    this.name = kwargs['name'] || name;
    
    this.start = kwargs['start'] || null;
    this.duration = kwargs['duration'] || null;
    this.end = kwargs['end'] || null;    
    
    this.task_ids = [];
    this.tasks = [];
    
    
    this.rowElement; //row editor html element
    this.ganttElement; //gantt html element
    this.master;
}

Project.prototype.clone = function () {
  var ret = {};
  for (var key in this) {
    if (typeof(this[key]) != "function") {
      ret[key] = this[key];
    }
  }
  return ret;
};

Project.prototype.link = function(){
    var target = "'central_content'";
    var address =  "'view/project/" + this.id +"'"
    return '<a href="javascript:redirectLink('+target+','+address +');">' + this.name +'</a>';

    //return "<a class='DataLink' href='#' stalker_target='central_pane' stalker_href='view/project/" + this.id + "'>" + this.name + "</a>";
};


//<%---------- PROJECT STRUCTURE ---------------------- --%>
Project.prototype.getRow = function() {
  var index = -1;
  if (this.master)
    index = this.master.projects.indexOf(this);
  return index;
};
