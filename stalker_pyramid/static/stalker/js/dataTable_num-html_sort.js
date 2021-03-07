jQuery.extend( jQuery.fn.dataTableExt.oSort, {
    "num-html-pre": function (a) {
        'use strict';
        var x = String(a).replace(/<[\s\S]*?>/g, "");
        return parseFloat(x);
    },

    "num-html-asc": function (a, b) {
        'use strict';
        return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },

    "num-html-desc": function (a, b) {
        'use strict';
        return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    }
});
