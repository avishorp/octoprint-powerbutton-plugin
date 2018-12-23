/*
 * View model for OctoPrint-PowerButton
 *
 * Author: Avishay Orpaz
 * License: AGPLv3
 */
$(function() {
	var POWER_BUTTON_PLUGIN = "powerbutton"

	/* Plugin states */
	var STATE_UNKNOWN = 'unknown'          // Unknown state
	var STATE_ON = 'on'                    // Powered on
	var STATE_OFF = 'off'                  // Powered off
	var STATE_ON_PENDING = 'on_pending'    // Power-on command pending
	var STATE_OFF_PENDING = 'off_pending'  // Power-off command pending
	var STATE_ON_LOCKED = 'on_locked'      // Powered on and locked
	var STATE_AUTOOFF = 'auto_off'         // Wait for auto power off

	var CONNECT_BTN_TOOLTIP = "To connect to the printer, first turn its power on"

	// Enable tooltips
	$(document).tooltip()

	// Helper function - Convert a progress range of 0 - 100 to 0 to 12
	// Used for showing a progress bar for auto-off function
	function autoProgress(progress) {
		if (progress >= 100)
			return 12;
		if (progress <= 0)
			return 0;
			
		return Math.round((progress / 100.0)*12);
	}

	// Create a ViewModel
	/////////////////////

    function PowerbuttonViewModel(parameters) {
        var self = this;
/* Test */
var p = 100;
setTimeout(() => {
	setInterval(() => {  
		console.log(p)
	 self.autoPowerOffProgress(p)
	 p -= 10
	 if (p < 0) p = 100;
	}, 1000)
	
}, 3000)

		self.printerStateViewModel = parameters[0];
		self.switchState = ko.observable(STATE_UNKNOWN)
		self.autoPowerOffProgress = ko.observable(0)

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
			var progress = self.autoPowerOffProgress()

			if (state === STATE_OFF_PENDING || state === STATE_ON_PENDING)
				return 'slider-wait'
			else if (state === STATE_ON_LOCKED)
				return 'slider-lock'
			else
				return 'slider-auto' + autoProgress(progress)
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
					self.switchState(STATE_ON_LOCKED)
				}
				else
					console.error("PowerButton plugin: Power state error")
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

		// Preload images
		var loadImg = new Image()
		images = []
		loadImg.src = "/plugin/powerbutton/static/img/wait_circle.gif";
		for(var i = 0; i <=12; i++) {
			var loadImg = new Image()
			loadImg.src = "/plugin/powerbutton/static/img/auto" + i + ".png"
			images.push(loadImg)
		}
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
