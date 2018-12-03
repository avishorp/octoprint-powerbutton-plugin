/*
 * View model for OctoPrint-PowerButton
 *
 * Author: Avishay Orpaz
 * License: AGPLv3
 */
$(function() {
	var POWER_BUTTON_PLUGIN = "powerbutton"

	var STATE_UNKNOWN = 'unknown'
	var STATE_ON = 'on'
	var STATE_OFF = 'off'
	var STATE_ON_PENDING = 'on_pending'
	var STATE_OFF_PENDING = 'off_pending'

	// Create a ViewModel
	/////////////////////

    function PowerbuttonViewModel(parameters) {
        var self = this;

		self.printerStateViewModel = parameters[0];
		self.switchState = ko.observable(STATE_UNKNOWN)

		self.checked = ko.observable(true)
		self.disabled = ko.observable(false)
		self.cssOption = ko.observable(null)

		// Subscribe to power state change. Will update
		// the display accordingly.
		self.switchState.subscribe(function(v) {
			console.log("New state: " + self.switchState())

			switch(v) {
				case STATE_ON:
					self.checked(true)
					self.disabled(false)
					self.cssOption('')
					break

				case STATE_ON_PENDING:
					self.checked(true)
					self.disabled(true)
					self.cssOption('slider-wait')
					break

				case STATE_OFF:
					self.checked(false)
					self.disabled(false)
					self.cssOption('')
					break

				case STATE_OFF_PENDING:
					self.checked(false)
					self.disabled(true)
					self.cssOption('slider-wait')
					break
			}
		})

		// Subscribe to switch changes (clicks)
		self.checked.subscribe(function(v) {
			if (v)
				self.switchState(STATE_ON_PENDING)
			else 
				self.switchState(STATE_OFF_PENDING)

			OctoPrint.plugins.powerbuttonplugin.requestPowerState(v, function(error) {
				if (error) {
					// TODO: Show error message

					// Failure
					if (self.switchState() === STATE_OFF_PENDING)
						self.switchState(STATE_ON)
					else if (self.switchState() === STATE_ON_PENDING)
						self.switchState(STATE_OFF)
				}

			})
		})
	
		self.onDataUpdaterPluginMessage = function(plugin, message) {
			if (plugin === "powerbutton") {

				if (message.newState === true)
					self.switchState(STATE_ON)
				else if (message.newState === false)
					self.switchState(STATE_OFF)
			}
		}

    }

    // Register the ViewModel
	/////////////////////////

    OCTOPRINT_VIEWMODELS.push({
        construct: PowerbuttonViewModel,
        dependencies: [ "printerStateViewModel" ],
        elements: [ "#power-button-top input", "#power-button-top span" ]
	});
	
	// Register the plugin
	//////////////////////
	(function (global, factory) {
		if (typeof define === "function" && define.amd) {
			define(["OctoPrintClient"], factory);
		} else {
			factory(window.OctoPrintClient);
		}

		// Preload the "wait circle" image
		var loadImg = new Image()
		loadImg.src = "/plugin/powerbutton/static/img/wait_circle.gif";
	})(window || this, function(OctoPrintClient) {

		var PowerButtonPluginClient = function(base) {
			this.base = base;
		};
	
		PowerButtonPluginClient.prototype.requestPowerState = function(newState, cb) {
			
			// Issue an API request
			OctoPrint.ajaxWithData("POST", "api/plugin/" + POWER_BUTTON_PLUGIN, JSON.stringify({
				command: "power",
				newState: newState? "on" : "off"
			}), {
				contentType: "application/json"
			}).done(function() {
				cb(null)
			})
		};
	
		OctoPrintClient.registerPluginComponent("powerbuttonplugin", PowerButtonPluginClient);
		return PowerButtonPluginClient;
	});

});
