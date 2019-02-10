import math
from enum import Enum, auto
from logging import getLogger
from time import sleep

import launchpad_py as launchpad


class ControlButtons(Enum):
    UP_ARROW = (0, 0)
    DOWN_ARROW = (1, 0)
    LEFT_ARROW = (2, 0)
    RIGHT_ARROW = (3, 0)

    LAUNCH_BUTTON = (4, 0)
    MIXER_BUTTON = (7, 0)


class Mode(Enum):
    LAUNCH = auto()
    MIXER = auto()


class Controller:
    POLLING_DELAY = 0.1

    mode = None
    launch_x_offset = 0
    launch_deck = 0
    layers_bypassed = [False for _ in range(8)]

    resolume = None

    def __init__(self):
        self.lp = launchpad.Launchpad()
        self.lp.Open()
        self.lp.Check()
        self.lp.Reset()

    def set_resolume(self, resolume):
        self.resolume = resolume

    def run(self):
        self._switch_mode(Mode.LAUNCH)

        while True:
            while True:
                event = self.lp.ButtonStateXY()
                if len(event) > 0:
                    x, y, down = event
                    getLogger('controller').debug("EV: {}, {} {}".format(x, y, "DOWN" if down else "UP"))
                    self._handle(x, y, down)
                else:
                    break
            sleep(self.POLLING_DELAY)

    def stop(self):
        self.lp.Reset()
        self.lp.Close()

    def unset_clip(self, layer, clip):
        if self.mode == Mode.LAUNCH and self.launch_x_offset < clip <= self.launch_x_offset + 8:
            self.lp.LedCtrlXY(clip - 1 - self.launch_x_offset, 8 - (layer - 1), 0, 0)

    def reset_clip(self, layer, clip):
        if self.mode == Mode.LAUNCH and self.launch_x_offset < clip <= self.launch_x_offset + 8:
            self.lp.LedCtrlXY(clip - 1 - self.launch_x_offset, 8 - (layer - 1), 0, 3)

    def arm_clip(self, layer, clip):
        if self.mode == Mode.LAUNCH and self.launch_x_offset < clip <= self.launch_x_offset + 8:
            self.lp.LedCtrlXY(clip - 1 - self.launch_x_offset, 8 - (layer - 1), 3, 3)

    def set_layer_clear(self, layer, state):
        if self.mode == Mode.LAUNCH:
            self.lp.LedCtrlXY(8, 8 - (layer - 1), *((1, 0) if state else (3, 0)))

    def set_layer_opacity(self, layer, opacity):
        if self.mode == Mode.MIXER:
            level = math.floor(8 * opacity)
            for x in range(0, level):
                self.lp.LedCtrlXY(x, 8 - (layer - 1), 0, 3)
            for x in range(level, 8):
                self.lp.LedCtrlXY(x, 8 - (layer - 1), 0, 0)

    def set_layer_bypass(self, layer, state):
        self.layers_bypassed[layer - 1] = state
        if self.mode == Mode.MIXER:
            self.lp.LedCtrlXY(8, 8 - (layer - 1), *((3, 0) if state else (1, 0)))

    def _switch_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self._reset()
        if self.mode == Mode.LAUNCH:
            self.resolume.poll_for_launch_state(self.launch_x_offset)
        elif self.mode == Mode.MIXER:
            self.resolume.poll_for_mixer_state()

    def _reset(self):
        self.lp.Reset()
        for button in [ControlButtons.LAUNCH_BUTTON, ControlButtons.MIXER_BUTTON]:
            self.lp.LedCtrlXY(*button.value, 0, 3)
        if self.mode == Mode.LAUNCH:
            self.lp.LedCtrlXY(*ControlButtons.LAUNCH_BUTTON.value, 3, 3)
            self._update_launch_arrows()
        elif self.mode == Mode.MIXER:
            self.lp.LedCtrlXY(*ControlButtons.MIXER_BUTTON.value, 3, 3)

    def _handle(self, x, y, down):
        if (x, y) == ControlButtons.LAUNCH_BUTTON.value and down:
            self._switch_mode(Mode.LAUNCH)
        elif (x, y) == ControlButtons.MIXER_BUTTON.value and down:
            self._switch_mode(Mode.MIXER)
        elif self.mode == Mode.LAUNCH:
            self._handle_launch(x, y, down)
        elif self.mode == Mode.MIXER:
            self._handle_mixer(x, y, down)

    def _handle_launch(self, x, y, down):
        if y == 0:
            if not down:
                return
            if (x, y) == ControlButtons.LEFT_ARROW.value:
                if self.launch_x_offset > 0:
                    self.launch_x_offset -= 1
                    self.resolume.poll_for_launch_state(self.launch_x_offset)
            elif (x, y) == ControlButtons.RIGHT_ARROW.value:
                self.launch_x_offset += 1
                self.resolume.poll_for_launch_state(self.launch_x_offset)
            # elif (x, y) == ControlButtons.DOWN_ARROW.value:
            #     if self.launch_deck > 0:
            #         self.launch_deck -= 1
            #     self._reset()
            #     self.resolume.select_deck(self.launch_deck + 1)
            # elif (x, y) == ControlButtons.UP_ARROW.value:
            #     self.launch_deck += 1
            #     self._reset()
            #     self.resolume.select_deck(self.launch_deck + 1)

            self._update_launch_arrows()
        else:
            if x < 8:
                if not down:
                    return
                layer, column = 8 - (y - 1), x + 1 + self.launch_x_offset
                self.resolume.launch_clip(layer, column)
            else:
                self.resolume.clear_layer(8 - (y - 1), down)

    def _update_launch_arrows(self):
        # self.lp.LedCtrlXY(*ControlButtons.UP_ARROW.value, 0, 3)
        # if self.launch_deck > 0:
        #     self.lp.LedCtrlXY(*ControlButtons.DOWN_ARROW.value, 0, 3)
        # else:
        #     self.lp.LedCtrlXY(*ControlButtons.DOWN_ARROW.value, 0, 1)

        self.lp.LedCtrlXY(*ControlButtons.RIGHT_ARROW.value, 0, 3)
        if self.launch_x_offset > 0:
            self.lp.LedCtrlXY(*ControlButtons.LEFT_ARROW.value, 0, 3)
        else:
            self.lp.LedCtrlXY(*ControlButtons.LEFT_ARROW.value, 0, 1)

    def _handle_mixer(self, x, y, down):
        if not down:
            return
        if x == 8:
            layer = 8 - (y - 1)
            self.resolume.set_layer_bypassed(layer, not self.layers_bypassed[layer - 1])
        else:
            level = (x + 1) / 8
            self.resolume.set_layer_opacity(8 - (y - 1), level)
