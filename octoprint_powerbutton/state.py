
from threading import Timer

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
        return assign(old_state, power_state=POWER_STATE_ON, auto_power_off_countdown=0)
    else:
        return old_state

def action_button_long(old_state):
    p = old_state["power_state"]
    if p == POWER_STATE_OFF:
        return assign(old_state, power_state=POWER_STATE_ON)
    elif p == POWER_STATE_ON or p == POWER_STATE_LOCKED or p == POWER_STATE_AUTOOFF:
        return assign(old_state, power_state=POWER_STATE_OFF, auto_power_off_countdown=0)
    else:
        return old_state

def action_drop(old_state):
    return assign(old_state, power_state=POWER_STATE_DROPPED)

def action_print_started(old_state):
    return assign(old_state, power_state=POWER_STATE_LOCKED)

def action_print_failed(old_state):
    return assign(old_state, power_state=POWER_STATE_ON)

def action_print_done(old_state, auto_power_off_countdown, auto_power_off_enabled):
    if auto_power_off_enabled:
        return assign(old_state, 
            power_state=POWER_STATE_AUTOOFF, 
            auto_power_off_countdown=auto_power_off_countdown)
    else:
        return assign(old_state, power_state=POWER_STATE_ON)

def action_update_auto_off(old_state, value):
    if value == 0:
        # Countdown done - turn off
        return assign(old_state, power_state=POWER_STATE_OFF, auto_power_off_countdown=0)
    else:
        return assign(old_state, auto_power_off_countdown=value)

def action_cancel_auto_off(old_state):
    if old_state["power_state"] == POWER_STATE_AUTOOFF:
        return assign(old_state, power_state=POWER_STATE_ON, auto_power_off_countdown=0)
    else:
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
            'web_toggle': action_web_toggle,
            'btn_short': action_button_short,
            'btn_long': action_button_long,
            'drop': action_drop,
            'print_started': action_print_started,
            'print_failed': action_print_failed,
            'print_done': action_print_done,
            'update_auto_off': action_update_auto_off,
            'cancel_auto_off': action_cancel_auto_off
        }

        self.power_state = POWER_STATE_OFF
        self.auto_power_off_countdown = 0
        self.auto_connect_countdown = 0

        self.subscribers = []

        # Start a thread to handle time-based actions
        self.time_action_timer = Timer(1, self.time_action_timer_func)
        self.time_action_timer.start()

    def stop(self):
        self.time_action_timer.cancel()


    def subscribe(self, handler):
        # Add the handler function to the subscriber list
        self.subscribers.append(handler)

        # Send the initial state to the new handler
        handler(self.get_state(), None)

    def get_state(self):
        return self.state

    def dispatch(self, action, *args):
        print "Dispatch: " + action

        # Determine the action function to call
        faction = self.actions[action]

        # Invoke the action
        working_state = self.state.copy()
        old_state = self.state
        self.state = faction(working_state, *args)

        # Call all handlers
        for handler in self.subscribers:
            handler(self.state, old_state)

    def time_action_timer_func(self):
        if self.state["auto_power_off_countdown"] > 0:
            self.dispatch("update_auto_off", self.state["auto_power_off_countdown"] - 1)

        # Re-arm
        self.time_action_timer = Timer(1, self.time_action_timer_func)
        self.time_action_timer.start()



