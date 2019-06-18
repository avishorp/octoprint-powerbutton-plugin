
# Power states
POWER_STATE_OFF = 0
POWER_STATE_ON = 1
POWER_STATE_AUTOOFF = 2
POWER_STATE_LOCKED = 3
POWER_STATE_DROPPED = 4

def action_web_toggle(old_state, value):
    print(value)
    if value == 'on' and old_state["power_state"] == POWER_STATE_OFF:
        old_state["power_state"] = POWER_STATE_ON
    elif value == 'off' and (old_state["power_state"] == POWER_STATE_ON or old_state["power_state"] == POWER_STATE_AUTOOFF):
        old_state["power_state"] = POWER_STATE_OFF
    
    return old_state


class PowerbuttonState:

    def __init__(self, logger = None):
        self.logger = logger

        self.state = dict(
            power_state = POWER_STATE_OFF,
            auto_power_off_countdown = 0,
            auto_connect_countdown = 0
        )

        self.actions = {
            'web_toggle': action_web_toggle
        }

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
        return self.state

    def dispatch(self, action, *args):
        print("Dispatch: " + action)
        # Copy the old (current) state to a new variabel
        #old_state = self.state.copy()

        # Determine the action function to call
        faction = self.actions[action]

        # Invoke the action
        working_state = self.state.copy()
        old_state = self.state
        self.state = faction(working_state, *args)

        # Call all handlers
        for handler in self.subscribers:
            handler(self.state, old_state)


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



