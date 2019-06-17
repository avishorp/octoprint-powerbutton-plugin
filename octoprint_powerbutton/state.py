
# Power states
POWER_STATE_OFF = 0
POWER_STATE_ON = 1
POWER_STATE_AUTOOFF = 2
POWER_STATE_LOCKED = 3
POWER_STATE_DROPPED = 4


class PowerbuttonState:

    def __init__(self, logger = None):
        self.logger = logger

        self.power_state = POWER_STATE_OFF
        self.auto_power_off_countdown = 0
        self.auto_connect_countdown = 0

        self.subscribers = []

    def subscribe(self, handler):
        # Add the handler function to the subscriber list
        self.subscribers.append(handler)

        # Send the initial state to the new handler
        handler(self.get_state(), None)

    def get_state(self):
        return dict(
            power_state = self.power_state,
            auto_power_off_countdown = self.auto_power_off_countdown,
            auto_connect_countdown = self.auto_connect_countdown
        )


    def action_button_press(self, long_press):
        pass

    def action_web_toggle(self, value):
        pass

    def action_web_cancel_auto_off(self):
        pass

    def action_print_started(self):
        pass

    def action_print_failed(self):
        pass

    def action_print_done(self):
        pass



