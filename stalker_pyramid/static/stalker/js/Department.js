// Stalker a Production Asset Management System
// Copyright (C) 2009-2014 Erkan Ozgur Yilmaz
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

define([
    "dojo/_base/declare"
], function (declare) {
    'use strict';
    return declare('Department', null, {
        id: null,
        name: '',
        users: [],

        constructor: function (kwargs) {
            this.grid = kwargs.grid;

            this.id = kwargs.id || null;
            this.name = kwargs.name || null;

            // some dynamic attributes
            this.users = kwargs.users || [];
        },

        link: function () {
            return templates.resourceLink(this);
        }

    });
});
