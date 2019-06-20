
import os.path
import time
from threading import Thread

SYSFS_GPIO = "/sys/class/gpio"

# Hardware GPIO definitions
GPIO_RELAY = 14
GPIO_BUTTON = 15
GPIO_DROP = 17
GPIO_LED_R = 3
GPIO_LED_G = 22
GPIO_LED_B = 27

# LED Patterns
PATT_LED_NONE = 0        # LED turned off
PATT_LED_RED = 1         # Solid Red
PATT_LED_GREEN = 2       # Solid Green
PATT_LED_YELLOW = 3      # Solid Yellow
PATT_LED_RED_BLINK = 4   # Blinking Red
PATT_LED_GREEN_BLINK = 5 # Green, with short red blinks

# Button press period
SHORT_PERIOD = 15  # Short press
LONG_PERIOD = 50   # Long press

class OctoboxHardware:
    """
    Low level hardware interface to OctoBox hardware.

    This class includes functions that map low level primitives (GPIOs)
    to board functions (LED, relay, drop feedback)
    """


    def __init__(self):
        self.__gpio_output(GPIO_RELAY, False)
        self.__gpio_output(GPIO_LED_R, True)
        self.__gpio_output(GPIO_LED_G, True)
        self.__gpio_output(GPIO_LED_B, True)

        self.__gpio_input(GPIO_BUTTON)
        self.__gpio_input(GPIO_DROP)

    def set_led(self, r, g, b):
        """
        Control the LED

        r, g, b - When True, the color is turned on
        """
        self.__set_value(GPIO_LED_R, not r)
        self.__set_value(GPIO_LED_G, not g)
        self.__set_value(GPIO_LED_B, not b)

    def set_relay(self, value):
        """
        Control the power relay
        """
        self.__set_value(GPIO_RELAY, value)

    def get_button(self):
        """
        Get the value of the button

        Return True when the button is pressed, False when depressed
        """
        raw = self.__get_value(GPIO_BUTTON)
        if raw == '0':
            return True
        else:
            return False

    def get_drop(self):
        """
        Get the value of the power drop indication signal
        """
        raw = self.__get_value(GPIO_DROP)
        if raw == '0':
            return False
        else:
            return True

    def __gpio_input(self, gpio_number):
	self.__export(gpio_number)
	self.__set_direction(gpio_number, True)


    def __gpio_output(self, gpio_number, init_value):
  	self.__export(gpio_number)
	self.__set_direction(gpio_number, False)
	self.__set_value(gpio_number, init_value)


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

    def __get_value(self, pin):
        return file(os.path.join(SYSFS_GPIO, "gpio%d/value" % pin)).read().split('\n')[0]


class Octobox:
    """
    A high-level interface to Octobox hardware functions.
    """
    def __init__(self):
        self.hw = OctoboxHardware()
        self.button_press_callback = None
        self.drop_callback = None
        self.drop_indicated = False

        self.set_led_pattern(PATT_LED_NONE)

        self.running = True
        self.bg = Thread(target = self.__button_thread)
        self.bg.daemon = True
        self.bg.start()

    def stop(self):
        """
        Stop the thread contained in this instance and
        reset the hardware state.
        """
        self.running = False
        self.bg.join()

        self.hw.set_led(False, False, False)
        self.hw.set_relay(False)


    def subscribe_button_press(self, handler = None):
        """
        Subscribe to button press event.

        The handler argument is a callable that will be called when the
        button is pressed. It receives an argument that is either False in
        case of a "short press" or True in the case of "Long press".
        """
        self.button_press_callback = handler

    def subscribe_drop(self, handler = None):
        """
        Subscribe to power drop event.

        The handler argument is a callable that will be called when
        a power drop event has occured.
        """
        self.drop_callback = handler
        self.drop_indicated = False

    def set_relay(self, value):
        """
        Sets the state of the power relay.
        """
        self.hw.set_relay(value)

    def set_led_pattern(self, pat):
        """
        Sets the LED color or pattern.

        The pat argument is any of the PATT_LED_* constants
        """
        self.led_pattern = pat

        # Apply constant patterns
        if pat == PATT_LED_NONE:
            self.hw.set_led(False, False, False)
        elif pat == PATT_LED_RED:
            self.hw.set_led(True, False, False)
        elif pat == PATT_LED_GREEN:
            self.hw.set_led(False, True, False)
        elif pat == PATT_LED_YELLOW:
            self.hw.set_led(True, True, False)


    def __button_thread(self):
        count = 0
        state = 0
        led_count = 0
         
        while(self.running):
            # Handle button press detection
            v = self.hw.get_button()
            if not v:
                # Button released
                if (count > 1 and count <= SHORT_PERIOD):
                    if self.button_press_callback is not None:
                        self.button_press_callback(False)
            elif (count == LONG_PERIOD):
                if self.button_press_callback is not None:
                    self.button_press_callback(True)

            if v:
                count += 1
            else:
                count = 0

            # Handle LED blinking
            led_count += 1

            if self.led_pattern == PATT_LED_RED_BLINK:
                if led_count % 10 < 5:
                    self.hw.set_led(False, False, False)
                else:
                    self.hw.set_led(True, False, False)

            elif self.led_pattern == PATT_LED_GREEN_BLINK:
                if led_count % 10 < 5:
                    self.hw.set_led(False, False, False)
                else:
                    self.hw.set_led(False, True, False)

            # Drop indication
            if (self.drop_callback is not None) and (not self.drop_indicated) and (self.hw.get_drop()):
                self.drop_indicated = True
                self.drop_callback()

            time.sleep(0.05)


def handle_btn(v):
    print "Button " + ("long" if v else "short")

def handle_drop():
    print "drop"

# ob = Octobox()
# ob.subscribe_button_press(handle_btn)
# ob.subscribe_drop(handle_drop)

# ob.set_led_pattern(PATT_LED_NONE)
# time.sleep(5)
# ob.set_led_pattern(PATT_LED_RED)
# time.sleep(3)
# ob.set_led_pattern(PATT_LED_GREEN)
# time.sleep(3)
# ob.set_led_pattern(PATT_LED_YELLOW)
# time.sleep(3)
# ob.set_led_pattern(PATT_LED_RED_BLINK)
# time.sleep(3)
# ob.stop()


