import re
from logging import getLogger
from threading import Thread

from pythonosc import osc_server, dispatcher, udp_client


class Resolume:
    controller = None

    def __init__(self, host="127.0.0.1", port_out=7000, port_in=7001, debug=False):
        self._dispatcher = dispatcher.Dispatcher()
        if debug:
            self._dispatcher.map("/composition/*", print)
        else:
            self._dispatcher.map("/composition/layers/*/clips/*/connected", self._handle_connected)
            self._dispatcher.map("/composition/layers/*/clear", self._handle_clear)
            self._dispatcher.map("/composition/layers/*/video/opacity", self._handle_opacity)
            self._dispatcher.map("/composition/layers/*/bypassed", self._handle_bypassed)
        self.server = osc_server.ThreadingOSCUDPServer((host, port_in), self._dispatcher)
        self.client = udp_client.SimpleUDPClient(host, port_out)

    # batch_lock = threading.Lock()
    # batch_done = threading.Event()
    # batch_timer = None
    # batch_result = []

    def start(self):
        thread = Thread(target=self.server.serve_forever)
        thread.start()
        getLogger('resolume').info("Started OSC server @ {}:{}".format(*self.server.server_address))

    def set_controller(self, controller):
        self.controller = controller

    def set_layer_opacity(self, layer, opacity):
        self._osc_send(f"/composition/layers/{layer}/video/opacity", opacity)

    def set_layer_bypassed(self, layer, state):
        self._osc_send(f"/composition/layers/{layer}/bypassed", 1 if state else 0)

    def launch_clip(self, layer, column):
        self._osc_send(f"/composition/layers/{layer}/clips/{column}/connect", 1)

    def clear_layer(self, layer, state):
        self._osc_send(f"/composition/layers/{layer}/clear", 1 if state else 0)

    def select_deck(self, deck):
        self._osc_send(f"/composition/decks/{deck}/select", 1)

    def poll_for_launch_state(self, column_start, width=8):
        for layer in range(1, 8):
            self._osc_send(f"/composition/layers/{layer}/clear", "?")
            for column in range(column_start, column_start + width + 1):
                self._osc_send(f"/composition/layers/{layer}/clips/{column}/connected", "?")

    def poll_for_mixer_state(self):
        for layer in range(1, 8):
            self._osc_send(f"/composition/layers/{layer}/bypassed", "?")
            self._osc_send(f"/composition/layers/{layer}/video/opacity", "?")

    def _handle_connected(self, address, value):
        getLogger('resolume').debug("OSC RECV: %s: '%s'", address, value)
        layer, clip = [int(number) for _, number in re.findall(r'(layers|clips)/([0-9]+)', address)]
        if value == 0 or value == 2:
            self.controller.unset_clip(layer, clip)
        elif value == 1:
            self.controller.reset_clip(layer, clip)
        elif value == 3:
            self.controller.arm_clip(layer, clip)

    def _handle_clear(self, address, value):
        getLogger('resolume').debug("OSC RECV: %s: '%s'", address, value)
        layer = int(re.search(r'layers/([0-9]+)', address).group(1))
        self.controller.set_layer_clear(layer, bool(value))

    def _handle_opacity(self, address, value):
        getLogger('resolume').debug("OSC RECV: %s: '%s'", address, value)
        layer = int(re.search(r'layers/([0-9]+)', address).group(1))
        self.controller.set_layer_opacity(layer, value)

    def _handle_bypassed(self, address, value):
        getLogger('resolume').debug("OSC RECV: %s: '%s'", address, value)
        layer = int(re.search(r'layers/([0-9]+)', address).group(1))
        self.controller.set_layer_bypass(layer, bool(value))

    def _osc_send(self, address, value):
        getLogger('resolume').debug("OSC SEND: %s: '%s'", address, value)
        self.client.send_message(address, value)

    def debug(self):
        for layer in range(1, 4):
            self._osc_send(f"/composition/layers/{layer}/playmode", "?")

#
# resolume = Resolume(debug=True)
# resolume.start()
#
# while True:
#     resolume.debug()
#     sleep(30)
