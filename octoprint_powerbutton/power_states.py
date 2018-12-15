# Constants that defines the allowable power states

POWER_STATE_OFF = 0
POWER_STATE_ON = 1
POWER_STATE_LOCKED = 2

def str_power_state(s):
    assert_power_state(s)
    
    if s == POWER_STATE_OFF:
        return "off"
    elif s == POWER_STATE_ON:
        return "on"
    elif s == POWER_STATE_LOCKED:
        return "locked"

def assert_power_state(s):
    assert(s == POWER_STATE_OFF or s == POWER_STATE_ON or s == POWER_STATE_LOCKED)
