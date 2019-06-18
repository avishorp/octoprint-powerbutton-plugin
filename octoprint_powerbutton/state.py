
# Power states
POWER_STATE_OFF = 0
POWER_STATE_ON = 1
POWER_STATE_AUTOOFF = 2
POWER_STATE_LOCKED = 3
POWER_STATE_DROPPED = 4

def assign(d, **mods):
    """
    Returns a new dictionary which comprises of a copy of a dictionary and modifications of additions
    """
    r = d.copy()
    r.update(**mods)
    return r

def action_web_toggle(old_state, value):
    if value == 'on' and old_state["power_state"] == POWER_STATE_OFF:
        old_state["power_state"] = POWER_STATE_ON
    elif value == 'off' and (old_state["power_state"] == POWER_STATE_ON or old_state["power_state"] == POWER_STATE_AUTOOFF):
        old_state["power_state"] = POWER_STATE_OFF
    
    return old_state

def action_button_short(old_state):
    p = old_state["power_state"]
    if p == POWER_STATE_OFF:
        # When off, turn the power on
        return assign(old_state, power_state=POWER_STATE_ON)
    elif p == POWER_STATE_ON:
        # When on, turn the power off
        return assign(old_state, power_state=POWER_STATE_OFF)
    elif p == POWER_STATE_AUTOOFF:
        # Canecl auto-off
        return assign(old_state, power_state=POWER_STATE_ON)
    else:
        return old_state

def action_button_long(old_state):
    p = old_state["power_state"]
    if p == POWER_STATE_OFF:
        return assign(old_state, power_state=POWER_STATE_ON)
    elif p == POWER_STATE_ON or p == POWER_STATE_LOCKED or p == POWER_STATE_AUTOOFF:
        return assign(old_state, power_state=POWER_STATE_OFF)
    else:
        return old_state

def action_drop(old_state):
    return assign(old_state, power_state=POWER_STATE_DROPPED)

class PowerbuttonState:

    def __init__(self, logger = None):
        self.logger = logger

        self.state = dict(
            power_state = POWER_STATE_OFF,
            auto_power_off_countdown = 0,
            auto_connect_countdown = 0
        )

        self.actions = {
            'web_toggle': action_web_toggle,
            'btn_short': action_button_short,
            'btn_long': action_button_long,
            'drop': action_drop
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



