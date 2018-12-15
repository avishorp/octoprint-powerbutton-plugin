import types
from octoprint_powerbutton.power_states import *

class StubPowerController:

    def __init__(self, logger = None, cb = None):
        assert(cb is None or callable(cb))
        self.cb = cb
        self.logger = logger
        self.set_power_state(POWER_STATE_OFF)

    def shutdown(self):
        if self.logger:
            self.logger.info("StubPowerController: shutdown")
        pass


    def get_power_state(self):
        if self.logger:
            self.logger.info("StubPowerController: get_power_state")
        return self.power_state

    def set_power_state(self, new_state):
        assert_power_state(new_state)

        if self.logger:
            self.logger.info("StubPowerController: set_power_state(%s)" % str_power_state(new_state))
        

        # Set the new power state
        self.power_state = new_state

        # If a callback is set, let it know
        if (self.cb is not None):
            self.cb(new_state)

