import types

class RaspiPowerController:

    def __init__(self, gpio_relay, gpio_button, gpio_red, gpio_green, cb = None):
        self.gpio_relay = gpio_relay
        self.gpio_button = gpio_button
        self.gpio_red = gpio_red
        self.gpio_green = gpio_green

        assert(cb is None or callable(cb))
        self.cb = cb

        self.set_power_state(False)


    def get_power_state(self):
        return self.power_state

    def set_power_state(self, new_state):
        assert(type(new_state) is types.BooleanType)

        # Set the new power state
        self.power_state = new_state

        # Apply it
        if self.power_state:
            print "**** Turn on"
        else:
            print "**** Turn off"

        # If a callback is set, let it know
        if (self.cb is not None):
            self.cb(new_state)

