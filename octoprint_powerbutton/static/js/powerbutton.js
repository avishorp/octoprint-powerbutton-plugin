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
		self.switchState = ko.observable(STATE_OFF)

		self.checked = ko.pureComputed(function() {
			var state = self.switchState()
			return (state === STATE_ON || state === STATE_ON_PENDING)
		}, self)
		self.disabled = ko.pureComputed(function() {
			var state = self.switchState()
			return (state === STATE_OFF_PENDING || state === STATE_ON_PENDING)
		}, self)
		self.cssOption = ko.pureComputed(function() {
			var state = self.switchState()
			return (state === STATE_OFF_PENDING || state === STATE_ON_PENDING)? 'slider-wait' : ''
		}, self)

		// Subscribe to switch changes (clicks)
		$('#power-button-top input').click(function(v) {
			var v = $(this)[0].checked
			
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
			console.log("update ")
			console.log(message)
			if (plugin === "powerbutton") {

				if (message.newState === true)
					self.switchState(STATE_ON)
				else if (message.newState === false)
					self.switchState(STATE_OFF)
			}
		}

		self.onUserLoggedIn = function() {
			OctoPrint.plugins.powerbuttonplugin.refreshPowerState()
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
	
		// Request the server to apply a new power state
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

		// Request the server to refresh (resend) the current power state
		PowerButtonPluginClient.prototype.refreshPowerState = function() {
			// Issue an API request
			OctoPrint.ajaxWithData("POST", "api/plugin/" + POWER_BUTTON_PLUGIN, JSON.stringify({
				command: "refresh_state"
			}), {
				contentType: "application/json"
			})
		}
	
		OctoPrintClient.registerPluginComponent("powerbuttonplugin", PowerButtonPluginClient);
		return PowerButtonPluginClient;
	});

});
