import asyncio
from classes.controllerbase import ControllerBase
from common.config import ServerConfig
from tamtam_ws.server import TTWSServer

class TTWSController(ControllerBase):
    def __init__(self):
        self.config = ServerConfig()

    def launch(self, api):
        async def _start_all():
            await asyncio.gather(
                TTWSServer(
                    host=self.config.host,
                    port=self.config.tamtam_ws_port,
                    db_pool=api['db'],
                    clients=api['clients'],
                    send_event=api['event']
                ).start()
            )

        return _start_all()