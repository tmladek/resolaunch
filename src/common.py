from enum import Enum


class ClipState(Enum):
    NO_CLIP = 0,
    NOT_RUNNING = 1,
    MOVED = 2,
    RUNNING = 3
