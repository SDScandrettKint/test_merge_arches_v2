define([
    'jquery',
    'backbone',
    'knockout',
    'arches',
    'views/resource/related-resources-graph'
], function($, Backbone, ko, arches, RelatedResourcesGraph) {
    return Backbone.View.extend({
        initialize: function(options) {
            var self = this;
            this.searchResults = options.searchResults;
            this.editingInstanceId = options.editing_instance_id;
            this.context = options.context;
            this.showRelatedProperties = ko.observable(false);
            this.searchResults.showRelationships.subscribe(function(val){
                self.showRelatedResourcesGrid(val);
            })
            this.currentResource = ko.observable(this.editingInstanceId)
        },

        showRelatedResourcesGraph: function(e) {
            var resourceId = $(e.target).data('resourceid');
            var primaryName = $(e.target).data('primaryname');
            var typeId = $(e.target).data('entitytypeid');
            var searchItem = $(e.target).closest('.arches-search-item');
            var graphPanel = searchItem.find('.arches-related-resource-panel');
            var nodeInfoPanel = graphPanel.find('.node_info');
            if (!graphPanel.hasClass('view-created')) {
                new RelatedResourcesGraph({
                    el: graphPanel[0],
                    resourceId: resourceId,
                    resourceName: primaryName,
                    resourceTypeId: typeId
                });
            }
            nodeInfoPanel.hide();
            $(e.target).closest('li').toggleClass('graph-active');
            graphPanel.slideToggle(500);
        },

        showRelatedResourcesGrid: function(resourceinstance) {
            this.currentResource(resourceinstance.resourceinstanceid);
        },

        saveRelationships: function() {
            var candidateIds = _.pluck(this.searchResults.relationshipCandidates(), 'resourceinstanceid');
            var root_resourceinstanceid = this.currentResource();
            var self = this;
            var clearCandidates = function(self) {
                return function(data){
                    console.log(data);
                    self.searchResults.relationshipCandidates.removeAll();
                };
            }
            var successFunction = clearCandidates(self);

            //TODO Create a resource_x_resource model rather than calling jQuery here
            var payload = {
                relationship_type: 'a9deade8-54c2-4683-8d76-a031c7301a47',
                instances_to_relate: candidateIds,
                root_resourceinstanceid: root_resourceinstanceid
            }
            $.ajax({
                url: arches.urls.related_resources,
                data: payload,
                type: 'POST',
                dataType: 'json'
            })
            .done(successFunction)
            .fail(function(data){
                console.log('failed', data)
            });
        }
    });
});
