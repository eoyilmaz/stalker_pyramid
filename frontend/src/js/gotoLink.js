define(['dijit/registry', 'dojo/on', 'dojo/query'],
    function(registry, on, query){
        // ********************************************************************
        // GO TO LINK
        //
        //
        var gotoLink = function(){

              // get the Link Elements
              var dataLinks = query('.DataLink');

              for (var i=0; i<dataLinks.length; i++){
                  on(dataLinks[i], 'click', function(){
                      var contentPane = registry.byId(this.getAttribute('stalker_target'));
                      if (contentPane){
                          contentPane.set('href', this.getAttribute('stalker_href'));
                          contentPane.refresh();
                      }
                  });
              }


        };
        return gotoLink;
});
