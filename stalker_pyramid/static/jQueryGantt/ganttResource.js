// Stalker Pyramid a Web Base Production Asset Management System
// Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
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


