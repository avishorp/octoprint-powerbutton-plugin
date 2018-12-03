# coding=utf-8
from __future__ import absolute_import
import flask
import raspi_power
import time

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin

class PowerbuttonPlugin(octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.AssetPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.StartupPlugin,
                        octoprint.plugin.SimpleApiPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
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
	    # Create a RaspiPower instance
	    self.power_ctrl = raspi_power.RaspiPowerController(0, 0, 0, 0, self.on_power_state) 

    ## SimpleApiPlugin
        
	def get_api_commands(self):
		return dict(
				power = ['newState'],
				refresh_state = []
				)

	def on_api_command(self, command, data):
		if command == "power":
			if data["newState"] == "on":
				new_state = True
			elif data["newState"] == "off":
				new_state = False
			else:
				return flask.make_response("Illegal power state parameter", 400)

			time.sleep(5)  # For testing
			self._logger.info("Setting power to %s", "On" if new_state else "Off")
			self.power_ctrl.set_power_state(new_state)
		
		elif command == "refresh_state":
			self.notify_power_state()

	##

	def on_power_state(self, new_state):
		self._logger.info("Power state changed")
		self.notify_power_state()

	def notify_power_state(self):
		if (hasattr(self, 'power_ctrl')):
			self._plugin_manager.send_plugin_message("powerbutton", 
				{ "newState": self.power_ctrl.get_power_state() })



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



