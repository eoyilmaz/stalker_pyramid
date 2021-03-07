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
