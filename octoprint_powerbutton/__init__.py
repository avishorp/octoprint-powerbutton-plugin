# coding=utf-8
from __future__ import absolute_import
import flask
import time
from threading import Timer, Lock

from octoprint_powerbutton.state import *
from octoprint_powerbutton.octobox import *

# The state check interval in auto-power-off mode
AUTO_POWER_OFF_INTERVAL = 10

import octoprint.plugin

power_state_codes = {
	POWER_STATE_OFF: "off",
	POWER_STATE_ON: "on",
	POWER_STATE_AUTOOFF: "auto_off",
	POWER_STATE_LOCKED: "locked",
	POWER_STATE_DROPPED: "drop"
}


class PowerbuttonPlugin(octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.AssetPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.StartupPlugin,
						octoprint.plugin.ShutdownPlugin,
                        octoprint.plugin.SimpleApiPlugin,
						octoprint.plugin.EventHandlerPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			power_ctrl_module = "raspi_power",
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
		# Create an Octobox instance
		self.octobox = Octobox()

		# Create a state manager instance
		self.state_mgr = PowerbuttonState(self._logger)

		# Will hold the auto connect timer
		self.auto_connect_timer = None

		self._logger.info("Startup completed")

		# Connect the state change notifications to all consumers
		self.state_mgr.subscribe(self.state_log)
		self.state_mgr.subscribe(self.notify_power_state)
		self.state_mgr.subscribe(self.relay_ctrl)
		self.state_mgr.subscribe(self.led_ctrl)

		self.octobox.subscribe_button_press(self.handle_button_press)
		self.octobox.subscribe_drop(self.handle_drop)


	def state_log(self, new_state, old_state):
		print(new_state)
		print(old_state)

	def on_shutdown(self):
		self._logger.info("Shutting down")
		self.octobox.stop()
		self.state_mgr.stop()

    ## SimpleApiPlugin
        
	def get_api_commands(self):
		return dict(
				power = ['newState'],
				refresh_state = [],
				cancel_auto_off = []
				)

	def on_api_command(self, command, data):
		self._logger.info(command)
		if not hasattr(self, 'state_mgr'):
			# Not initialized yet!
			return

		if command == "power":
			# Set the power mode (on/off)
			#############################
			if data["newState"] == "on" or data["newState"] == "off":
				self.state_mgr.dispatch('web_toggle', data["newState"])
			else:
				return flask.make_response("Illegal power state parameter", 400)
	
		elif command == "refresh_state":
			# Resend the power state to the client
			######################################
			self.notify_power_state(self.state_mgr.get_state(), None)

		elif command == "cancel_auto_off":
			# Cancel auto-power-off (if engaged) and set
			# the power state to "on"
			#if (self.power_ctrl.get_power_state() == POWER_STATE_ON and self.auto_power_off > 0):
			#	self.auto_power_off_lock.acquire()
			#	self._logger.info("Canceling auto-power-off mode")
			#	self.auto_power_off = 0
			#	self.notify_power_state()
			#	self.auto_power_off_lock.release()

			#else:
			#	self._logger.warn("Auto-power-off cancel request, but not in that mode")
			pass

	##

	# def on_power_state(self, new_state):
	# 	self._logger.info("Power state changed")
	# 	self.notify_power_state()

	# 	# If state has changed to "ON", and auto-connect is enabled,
	# 	# start a timer to do the auto-connect
	# 	auto_connect_enabled = self._settings.get_boolean(["auto_connect", "enabled"])
	# 	auto_connect_delay = self._settings.get_int(["auto_connect", "delay"])
	# 	if (new_state == POWER_STATE_ON and auto_connect_enabled == True and auto_connect_delay > 0):
	# 		# Create a timer to perform the auto-connect
	# 		self.auto_connect_timer = Timer(auto_connect_delay, self.on_auto_connect_timer)
	# 		self.auto_connect_timer.start()

	# 	# If te state has changed to "OFF" and an auto-connect timer is pending,
	# 	# cancel it
	# 	if (new_state == POWER_STATE_OFF and hasattr(self, "auto_connect_timer") and self.auto_connect_timer is not None):
	# 		self.auto_connect_timer.cancel()


	def notify_power_state(self, new_state, old_state):
		if new_state["power_state"] == POWER_STATE_AUTOOFF:
			auto_power_off_countdown = new_state["auto_power_off_countdown"]

			# Calculate as percent
			auto_power_off_interval = self._settings.get_int(["auto_power_off", "interval"])
			auto_power_off_countdown = int(auto_power_off_countdown*100.0/auto_power_off_interval)

		else:
			auto_power_off_countdown = 0

		self._plugin_manager.send_plugin_message("powerbutton", 
			{ "powerState": power_state_codes[new_state["power_state"]], "autoOffProgress": auto_power_off_countdown })

	def relay_ctrl(self, new_state, old_state):
		p = new_state["power_state"]
		if old_state is None or (p != old_state["power_state"]):
			if p == POWER_STATE_ON or p == POWER_STATE_AUTOOFF or p == POWER_STATE_LOCKED:
				self.octobox.set_relay(True)
			else:
				self.octobox.set_relay(False)

	def led_ctrl(self, new_state, old_state):
		p = new_state["power_state"]
		if old_state is None or (p != old_state["power_state"]):
			if p ==	POWER_STATE_OFF:
				pattern = PATT_LED_RED
			elif p == POWER_STATE_ON:
				pattern = PATT_LED_GREEN
			elif p == POWER_STATE_LOCKED:
				pattern = PATT_LED_YELLOW
			elif p == POWER_STATE_AUTOOFF:
				pattern = PATT_LED_GREEN_BLINK
			else:
				# Drop
				pattern = PATT_LED_RED_BLINK

			self.octobox.set_led_pattern(pattern)

	def handle_button_press(self, short):
		if short:
			self.state_mgr.dispatch('btn_short')
		else:
			self.state_mgr.dispatch('btn_long')

	def handle_drop(self):
		self.state_mgr.dispatch('drop')

	# 	self.state_notif_lock.acquire()

	# 	auto_off_progress = None

	# 	if (hasattr(self, 'power_ctrl')):
	# 		raw_power_state = self.power_ctrl.get_power_state()
	# 		if raw_power_state == POWER_STATE_OFF:
	# 			power_state = "off"
	# 		elif raw_power_state == POWER_STATE_LOCKED:
	# 			power_state = "locked"
	# 		elif raw_power_state == POWER_STATE_ON:
	# 			power_state = "on"
	# 		else:
	# 			power_state = "unknown"

	# 		if self.auto_power_off > 0:
	# 			auto_off_progress = self.get_auto_power_off_time_percent()

	# 		self._plugin_manager.send_plugin_message("powerbutton", 
	# 			{ "powerState": power_state, "autoOffProgress": auto_off_progress })

	# 	self.state_notif_lock.release()

	# ##

	def on_event(self, event, payload):
		if event == "PrintStarted":
			self.state_mgr.dispatch("print_started")
		elif event == "PrintFailed":
			self.state_mgr.dispatch("print_failed")
		elif event == "PrintDone":
			auto_power_off_countdown = self._settings.get_int(["auto_power_off", "interval"])
			auto_power_off_enabled = self._settings.get_int(["auto_power_off", "enabled"])

			self.state_mgr.dispatch("print_done", auto_power_off_countdown, auto_power_off_enabled)

	# 	if (event == "PrintStarted"):
	# 		self.power_ctrl.set_power_state(POWER_STATE_LOCKED)
	# 	elif (event == "PrintFailed"):
	# 		# Get the current power state. If it's not "locked", leave
	# 		# it alone
	# 		if (self.power_ctrl.get_power_state() == POWER_STATE_LOCKED):
	# 			self.power_ctrl.set_power_state(POWER_STATE_ON)
	# 	elif (event == "PrintDone"):
	# 		if (self.power_ctrl.get_power_state() == POWER_STATE_LOCKED):

	# 			# If auto-power-off is enabled, set the countdown timer
	# 			auto_power_off_time = self._settings.get_int(["auto_power_off", "interval"])
	# 			auto_power_off_enabled = self._settings.get_boolean(["auto_power_off", "enabled"])
	# 			if auto_power_off_enabled and auto_power_off_time > 0:
	# 				# Set the auto power off countdown
	# 				self.auto_power_off_lock.acquire()
	# 				self.auto_power_off = auto_power_off_time
	# 				self.auto_power_off_timer = Timer(AUTO_POWER_OFF_INTERVAL, self.on_timer)
	# 				self.auto_power_off_timer.start()
	# 				self.auto_power_off_lock.release()

	# 			# Set power state to "On" (will send a notification with auto-off/on state)
	# 			self.power_ctrl.set_power_state(POWER_STATE_ON)


	# def on_timer(self):
	# 	self.auto_power_off_lock.acquire()

	# 	# Make sure wer'e still in auto-power-off mode
	# 	if (self.power_ctrl.get_power_state() == POWER_STATE_ON and self.auto_power_off > 0):
	# 		self.auto_power_off -= AUTO_POWER_OFF_INTERVAL

	# 		if self.auto_power_off <= 0:
	# 			self._logger.info("Auto-power-off timer expired, turning off printer")
	# 			self._printer.disconnect()
	# 			self.auto_power_off = 0
	# 			self.power_ctrl.set_power_state(POWER_STATE_OFF)
	# 		else:
	# 			# Re-arm the timer
	# 			self.auto_power_off_timer = Timer(AUTO_POWER_OFF_INTERVAL, self.on_timer)
	# 			self.auto_power_off_timer.start()

	# 	self.notify_power_state()
	# 	self.auto_power_off_lock.release()

	# def get_auto_power_off_time_percent(self):
	# 	# Return the current auto-power-off timer state as percent
	# 	auto_power_off_time = self._settings.get_int(["auto_power_off", "interval"])
	# 	return self.auto_power_off*100/auto_power_off_time

	# def on_auto_connect_timer(self):
	# 	self._logger.info("Trying auto-connect")
		
	# 	# Extract settings
	# 	str_or_none = lambda s: None if s == "" else s
	# 	port = str_or_none(self._settings.get(["auto_connect", "port"]))
	# 	baud = str_or_none(self._settings.get(["auto_connect", "baud"]))
	# 	profile = str_or_none(self._settings.get(["auto_connect", "profile"]))

	# 	# Connect if not already connected
	# 	conn_state, _, _, _ = self._printer.get_current_connection()
	# 	if (conn_state == 'Closed'):
	# 		self._printer.connect(port = port, baudrate = baud, profile = profile)

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



