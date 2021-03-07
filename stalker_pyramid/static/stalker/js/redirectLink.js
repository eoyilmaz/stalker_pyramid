define(['dijit/registry', 'dojo/on', 'dojo/query'],
    function (registry, on, query) {
        // ********************************************************************
        // GO TO LINK
        //
        //
        var redirectLink = function (kwargs) {
            var target = kwargs.target;
            var address = kwargs.address;

            var contentPane = registry.byId(target);
            if (contentPane) {
                contentPane.set('href', address);
                contentPane.refresh();
            }


        };
        return redirectLink;
    });
