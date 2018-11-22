/*
 * View model for OctoPrint-PowerButton
 *
 * Author: Avishay Orpaz
 * License: AGPLv3
 */
$(function() {
    function PowerbuttonViewModel(parameters) {
        var self = this;

        self.printerStateViewModel = parameters[0];
	self.dt = ko.observable("--");

	n = 0;
	setInterval(function() {
		self.dt(n);
		n += 1;
	}, 2000);
	
	self.onDataUpdaterPluginMessage = function(plugin, message) {
		console.log(plugin)
		console.log(message)
	}
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PowerbuttonViewModel,
        dependencies: [ "printerStateViewModel" ],
        elements: [ "#powerState" ]
    });
});
