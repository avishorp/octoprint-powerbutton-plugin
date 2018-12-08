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
	var STATE_ON_LOCKED = 'on_locked'

	var CONNECT_BTN_TOOLTIP = "To connect to the printer, first turn its power on"

	// Enable tooltips
	$(document).tooltip()

	// Create a ViewModel
	/////////////////////

    function PowerbuttonViewModel(parameters) {
        var self = this;

		self.printerStateViewModel = parameters[0];
		self.switchState = ko.observable(STATE_UNKNOWN)

		self.checked = ko.pureComputed(function() {
			var state = self.switchState()
			return (state === STATE_ON || state === STATE_ON_PENDING || state === STATE_ON_LOCKED)
		}, self)
		self.disabled = ko.pureComputed(function() {
			var state = self.switchState()
			return (state === STATE_OFF_PENDING || state === STATE_ON_PENDING || state === STATE_ON_LOCKED)
		}, self)
		self.cssOption = ko.pureComputed(function() {
			var state = self.switchState()
			if (state === STATE_OFF_PENDING || state === STATE_ON_PENDING)
				return 'slider-wait'
			else if (state === STATE_ON_LOCKED)
				return 'slider-lock'
			else
				return ''
		}, self)
		
		self.visible = ko.pureComputed(function() {
			return self.switchState() === STATE_UNKNOWN? '' : 'switch-visible'
		}, self)
		
		var disableConnetcButton = function(v) {
			$('button#printer_connect').each(function(i,e) { 
				e.disabled = v 
				if (v)
					e.title = CONNECT_BTN_TOOLTIP
				else
					e.title = ''
			})

		}

		// Subscribe to switch changes (clicks)
		$('#power-button-top input').click(function(v) {
			var v = $(this)[0].checked
			var disconnectPromise = $.Deferred()

			if (v) {
				self.switchState(STATE_ON_PENDING)
				disconnectPromise.resolve()
			}
			else {
				self.switchState(STATE_OFF_PENDING)

				// Disable the "connect" button
				disableConnetcButton(true)

				// When switching off, disconnect first
				OctoPrint.connection.disconnect()
					.done(function() { disconnectPromise.resolve(); })
			}

			disconnectPromise.done(function() {
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
		})
	
		self.onDataUpdaterPluginMessage = function(plugin, message) {
			if (plugin === "powerbutton") {

				if (message.powerState === "on") {
					self.switchState(STATE_ON)

					// Enable the "connect" button
					disableConnetcButton(false)

				}
				else if (message.powerState === "off") {
					self.switchState(STATE_OFF)

					// Disable the "connect" button
					disableConnetcButton(true)
				}
				else if (message.powerState === "locked") {
					console.log("power_state locked")
				}
				else
					console.error("PowerButton plugin: Power state error")
			}
		}

		self.onUserLoggedIn = function() {
			OctoPrint.plugins.powerbuttonplugin.refreshPowerState()
		}

		self.onEventPrintStarted = function() {
			self.switchState(STATE_ON_LOCKED)
		}

		self.onEventPrintFailed = function() {
			self.switchState(STATE_ON)
		}

		self.onEventPrintDone = function() {
			self.switchState(STATE_ON)
		}

    }

    // Register the ViewModel
	/////////////////////////

    OCTOPRINT_VIEWMODELS.push({
        construct: PowerbuttonViewModel,
        dependencies: [ "printerStateViewModel" ],
        elements: [ "#power-button-top" ]
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
