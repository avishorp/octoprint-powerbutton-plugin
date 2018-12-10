import types
import os.path
from threading import Thread
import time

POWER_STATE_OFF = 0
POWER_STATE_ON = 1
POWER_STATE_LOCKED = 2

SYSFS_GPIO = '/sys/class/gpio'

LED_COLOR_OFF = 0
LED_COLOR_RED = 1
LED_COLOR_GREEN = 2
LED_COLOR_YELLOW = 3

BUTTON_RELEASE_VALUE = '1'
BUTTON_PRESS_VALUE = '0'

SHORT_PERIOD = 15
LONG_PERIOD = 50

class RaspiPowerController:

    def __init__(self, gpio_relay, gpio_button, gpio_red, gpio_green, cb = None):
        self.gpio_relay = gpio_relay
        self.gpio_button = gpio_button
        self.gpio_red = gpio_red
        self.gpio_green = gpio_green

        assert(cb is None or callable(cb))
        self.cb = cb

        # Setup all the assigned GPIO pons
        self.__setup_GPIO()

        # Set the initial power state to OFF
        self.set_power_state(POWER_STATE_OFF)

        # Start the button thread
        self.running = True
        self.button_thread = Thread(target = self.__button_thread)
        self.button_thread.start()

    def shutdown(self):
        self.running = False


    def get_power_state(self):
        return self.power_state

    def set_power_state(self, new_state):
        assert(new_state == POWER_STATE_ON or new_state == POWER_STATE_OFF or new_state == POWER_STATE_LOCKED)

        # Set the new power state
        self.power_state = new_state

        # Apply it
        if self.power_state == POWER_STATE_ON:
            self.__set_relay(True)
            self.__set_LED_color(LED_COLOR_GREEN)
        elif self.power_state == POWER_STATE_LOCKED:
            self.__set_relay(True)
            self.__set_LED_color(LED_COLOR_YELLOW)
        else:
            self.__set_relay(False)
            self.__set_LED_color(LED_COLOR_RED)

        # If a callback is set, let it know
        if (self.cb is not None):
            self.cb(new_state)

    # Export a GPIO pin
    def __export(self, pin):
        if os.path.exists(os.path.join(SYSFS_GPIO, 'gpio%d' % pin)):
            # Already exported
            return

        # Write to the export file. Will throw if no file exists (no GPIO
        # subsystem) or not writeable
        file(os.path.join(SYSFS_GPIO, "export"), 'w').write('%d\n' % pin)

        # Small delay to allow the change to settle, before trying to
        # make further modifications
        time.sleep(0.1)

    # Setup a GPIO pin as in (input = true) or outpu (input = false)
    def __set_direction(self, pin, input):
        s = "in" if input == True else "out"
        file(os.path.join(SYSFS_GPIO, "gpio%d/direction" % pin), 'w').write("%s\n" % s)

    # Set the value of an output pin
    def __set_value(self, pin, value):
        s = "1" if value == True else "0"
        file(os.path.join(SYSFS_GPIO, "gpio%d/value" % pin), 'w').write("%s\n" % s)

    def __setup_GPIO(self):
        if self.gpio_relay is not None:
            self.__export(self.gpio_relay)
            self.__set_direction(self.gpio_relay, False)
            self.__set_value(self.gpio_relay, False)

        if self.gpio_red is not None:
            self.__export(self.gpio_red)
            self.__set_direction(self.gpio_red, False)
            self.__set_value(self.gpio_red, False)

        if self.gpio_green is not None:
            self.__export(self.gpio_green)
            self.__set_direction(self.gpio_green, False)
            self.__set_value(self.gpio_green, False)

        if self.gpio_button is not None:
            self.__export(self.gpio_button)
            self.__set_direction(self.gpio_button, True)

    def __set_LED_color(self, color):
        if self.gpio_red is None or self.gpio_green is None:
            return

        red_value = (color == LED_COLOR_RED) or (color == LED_COLOR_YELLOW)
        green_value = (color == LED_COLOR_GREEN) or (color == LED_COLOR_YELLOW)

        self.__set_value(self.gpio_red, red_value)
        self.__set_value(self.gpio_green, green_value)

    def __set_relay(self, state):
        if self.gpio_relay is None:
            return

        self.__set_value(self.gpio_relay, state)

    def __button_thread(self):
        if self.gpio_button is None:
            return
        
        count = 0
        state = 0
        gpio_value_file = os.path.join(SYSFS_GPIO, "gpio%d/value" % self.gpio_button)
        
        while(self.running):
            # Read the button value
            v = file(gpio_value_file).read().startswith(BUTTON_PRESS_VALUE)
            
            if not v:
                # Button released
                if (count > 1 and count <= SHORT_PERIOD):
                    self.__notify_button_press(True)
            elif (count == LONG_PERIOD):
                self.__notify_button_press(False)

            if v:
                count += 1
            else:
                count = 0

            time.sleep(0.05)

    def __notify_button_press(self, short):
        if short:
            # Short press. If not locked, toggle between ON and OFF
            if self.get_power_state() == POWER_STATE_ON:
                self.set_power_state(POWER_STATE_OFF)
            elif self.get_power_state() == POWER_STATE_OFF:
                self.set_power_state(POWER_STATE_ON)

        else:
            # Long press. Force turn off
            self.set_power_state(POWER_STATE_OFF)
