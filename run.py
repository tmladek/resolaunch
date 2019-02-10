import logging

from src.controller import Controller
from src.resolume import Resolume

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.DEBUG)

controller = Controller()
resolume = Resolume()

controller.set_resolume(resolume)
resolume.set_controller(controller)

resolume.start()
controller.run()
