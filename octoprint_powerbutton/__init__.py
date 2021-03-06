# coding=utf-8
from __future__ import absolute_import
import flask
import octoprint_powerbutton.raspi_power as raspi_power
import time
from octoprint_powerbutton.power_ctrl_stub import StubPowerController 
from octoprint_powerbutton.power_states import *
from threading import Timer, Lock

# The state check interval in auto-power-off mode
AUTO_POWER_OFF_INTERVAL = 10

import octoprint.plugin

class PowerbuttonPlugin(octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.AssetPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.StartupPlugin,
                        octoprint.plugin.SimpleApiPlugin,
						octoprint.plugin.EventHandlerPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			power_ctrl_module = "raspi_power",
			raspi_power = dict(
				gpio_relay = 17,
				gpio_button = 22,
				gpio_red = 3,
				gpio_green = 2,
				led_polarity = False,
				button_polarity = True,
				relay_polarity = True
			),
			auto_power_off = dict(
				interval = 180,
				enabled = True
			),
			auto_connect = dict(
				enabled = False,
				port = "",
				baud = "",
				delay = 30,
				profile = ""
			)
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/powerbutton.js"],
			css=["css/powerbutton.css"],
			less=["less/powerbutton.less"]
			)

	##~~ TemplatePlugin mixin
	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			powerbutton=dict(
				displayName="Powerbutton Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="avishorp",
				repo="OctoPrint-PowerButton",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/avishorp/OctoPrint-PowerButton/archive/{target_version}.zip"
			)
		)

	def on_after_startup(self):
		# Create a lock for state notfication
		self.state_notif_lock = Lock()

	    # Create a Power controller module instance
		power_module_name = self._settings.get(["power_ctrl_module"])
		if power_module_name == "raspi_power":
			raspi_power_settings = self._settings.get(['raspi_power'])
			self.power_ctrl = raspi_power.RaspiPowerControl(self.on_power_state, raspi_power_settings)
		elif power_module_name == "stub":
			self.power_ctrl = StubPowerController(self._logger, self.on_power_state)
		else:
			self._logger.error("Only raspi_power or stub power control modules are supported")
			raise RuntimeError("Unsupported power control module")

		# Holds the auto-power-off countdown
		self.auto_power_off = None
		self.auto_power_off_lock = Lock()

		# Will hold the auto connect timer
		self.auto_connect_timer = None

    ## SimpleApiPlugin
        
	def get_api_commands(self):
		return dict(
				power = ['newState'],
				refresh_state = [],
				cancel_auto_off = []
				)

	def on_api_command(self, command, data):
		if command == "power":
			# Set the power mode (on/off)
			#############################
			if data["newState"] == "on":
				new_state = POWER_STATE_ON
			elif data["newState"] == "off":
				new_state = POWER_STATE_OFF
			else:
				return flask.make_response("Illegal power state parameter", 400)

			#time.sleep(5)  # For testing
			self._logger.info("Setting power to %s", "On" if new_state else "Off")
			self.power_ctrl.set_power_state(new_state)
		
		elif command == "refresh_state":
			# Resend the power state to the client
			######################################
			self.notify_power_state()

		elif command == "cancel_auto_off":
			# Cancel auto-power-off (if engaged) and set
			# the power state to "on"
			if (self.power_ctrl.get_power_state() == POWER_STATE_ON and self.auto_power_off > 0):
				self.auto_power_off_lock.acquire()
				self._logger.info("Canceling auto-power-off mode")
				self.auto_power_off = 0
				self.notify_power_state()
				self.auto_power_off_lock.release()

			else:
				self._logger.warn("Auto-power-off cancel request, but not in that mode")

	##

	def on_power_state(self, new_state):
		self._logger.info("Power state changed")
		self.notify_power_state()

		# If state has changed to "ON", and auto-connect is enabled,
		# start a timer to do the auto-connect
		auto_connect_enabled = self._settings.get_boolean(["auto_connect", "enabled"])
		auto_connect_delay = self._settings.get_int(["auto_connect", "delay"])
		if (new_state == POWER_STATE_ON and auto_connect_enabled == True and auto_connect_delay > 0):
			# Create a timer to perform the auto-connect
			self.auto_connect_timer = Timer(auto_connect_delay, self.on_auto_connect_timer)
			self.auto_connect_timer.start()

		# If te state has changed to "OFF" and an auto-connect timer is pending,
		# cancel it
		if (new_state == POWER_STATE_OFF and hasattr(self, "auto_connect_timer") and self.auto_connect_timer is not None):
			self.auto_connect_timer.cancel()


	def notify_power_state(self):
		self.state_notif_lock.acquire()

		auto_off_progress = None

		if (hasattr(self, 'power_ctrl')):
			raw_power_state = self.power_ctrl.get_power_state()
			if raw_power_state == POWER_STATE_OFF:
				power_state = "off"
			elif raw_power_state == POWER_STATE_LOCKED:
				power_state = "locked"
			elif raw_power_state == POWER_STATE_ON:
				power_state = "on"
			else:
				power_state = "unknown"

			if self.auto_power_off > 0:
				auto_off_progress = self.get_auto_power_off_time_percent()

			self._plugin_manager.send_plugin_message("powerbutton", 
				{ "powerState": power_state, "autoOffProgress": auto_off_progress })

		self.state_notif_lock.release()

	##

	def on_event(self, event, payload):
		if (event == "PrintStarted"):
			self.power_ctrl.set_power_state(POWER_STATE_LOCKED)
		elif (event == "PrintFailed"):
			# Get the current power state. If it's not "locked", leave
			# it alone
			if (self.power_ctrl.get_power_state() == POWER_STATE_LOCKED):
				self.power_ctrl.set_power_state(POWER_STATE_ON)
		elif (event == "PrintDone"):
			if (self.power_ctrl.get_power_state() == POWER_STATE_LOCKED):

				# If auto-power-off is enabled, set the countdown timer
				auto_power_off_time = self._settings.get_int(["auto_power_off", "interval"])
				auto_power_off_enabled = self._settings.get_boolean(["auto_power_off", "enabled"])
				if auto_power_off_enabled and auto_power_off_time > 0:
					# Set the auto power off countdown
					self.auto_power_off_lock.acquire()
					self.auto_power_off = auto_power_off_time
					self.auto_power_off_timer = Timer(AUTO_POWER_OFF_INTERVAL, self.on_timer)
					self.auto_power_off_timer.start()
					self.auto_power_off_lock.release()

				# Set power state to "On" (will send a notification with auto-off/on state)
				self.power_ctrl.set_power_state(POWER_STATE_ON)


	def on_timer(self):
		self.auto_power_off_lock.acquire()

		# Make sure wer'e still in auto-power-off mode
		if (self.power_ctrl.get_power_state() == POWER_STATE_ON and self.auto_power_off > 0):
			self.auto_power_off -= AUTO_POWER_OFF_INTERVAL

			if self.auto_power_off <= 0:
				self._logger.info("Auto-power-off timer expired, turning off printer")
				self._printer.disconnect()
				self.auto_power_off = 0
				self.power_ctrl.set_power_state(POWER_STATE_OFF)
			else:
				# Re-arm the timer
				self.auto_power_off_timer = Timer(AUTO_POWER_OFF_INTERVAL, self.on_timer)
				self.auto_power_off_timer.start()

		self.notify_power_state()
		self.auto_power_off_lock.release()

	def get_auto_power_off_time_percent(self):
		# Return the current auto-power-off timer state as percent
		auto_power_off_time = self._settings.get_int(["auto_power_off", "interval"])
		return self.auto_power_off*100/auto_power_off_time

	def on_auto_connect_timer(self):
		self._logger.info("Trying auto-connect")
		
		# Extract settings
		str_or_none = lambda s: None if s == "" else s
		port = str_or_none(self._settings.get(["auto_connect", "port"]))
		baud = str_or_none(self._settings.get(["auto_connect", "baud"]))
		profile = str_or_none(self._settings.get(["auto_connect", "profile"]))

		# Connect if not already connected
		conn_state, _, _, _ = self._printer.get_current_connection()
		if (conn_state == 'Closed'):
			self._printer.connect(port = port, baudrate = baud, profile = profile)

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Powerbutton Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PowerbuttonPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}



