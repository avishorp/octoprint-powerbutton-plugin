/*
 * View model for OctoPrint-PowerButton
 *
 * Author: Avishay Orpaz
 * License: AGPLv3
 */
$(function() {
	var POWER_BUTTON_PLUGIN = "powerbutton"

	// Create a ViewModel
	/////////////////////

    function PowerbuttonViewModel(parameters) {
        var self = this;

		self.printerStateViewModel = parameters[0];
		self.switchState = ko.observable("unknown")
		self.checked = ko.observable(true)

		// Subscribe to power state change. Will update
		// the display accordingly.
		self.switchState.subscribe(function(v) {
			if (v === "on") {
				console.log("XXX on")
				self.checked(true)
			}
			else {
				console.log("XXX off")
				self.checked(false)
			}
		})

		// Subscribe to switch changes (clicks)
		self.checked.subscribe(function(v) {
			OctoPrint.plugins.powerbuttonplugin.requestPowerState(v)
		})
	
		self.onDataUpdaterPluginMessage = function(plugin, message) {
			if (plugin === "powerbutton") {
				if (message.newState === true)
					self.switchState("on")
				else if (message.newState === false)
					self.switchState("off")
			}
		}
    }

    // Register the ViewModel
	/////////////////////////

    OCTOPRINT_VIEWMODELS.push({
        construct: PowerbuttonViewModel,
        dependencies: [ "printerStateViewModel" ],
        elements: [ "#power-button-switch" ]
	});
	
	// Register the plugin
	//////////////////////
	(function (global, factory) {
		if (typeof define === "function" && define.amd) {
			define(["OctoPrintClient"], factory);
		} else {
			factory(window.OctoPrintClient);
		}
	})(window || this, function(OctoPrintClient) {

		var PowerButtonPluginClient = function(base) {
			this.base = base;
		};
	
		PowerButtonPluginClient.prototype.requestPowerState = function(newState) {
			console.log("requested power state")
			OctoPrint.ajaxWithData("POST", "api/plugin/" + POWER_BUTTON_PLUGIN, JSON.stringify({
				command: "power",
				newState: newState? "on" : "off"
			}), {
				contentType: "application/json"
			})
		};
	
		OctoPrintClient.registerPluginComponent("powerbuttonplugin", PowerButtonPluginClient);
		return PowerButtonPluginClient;
	});

});
