import asyncio
from tamtam.socket import TamTamMobile
from tamtam.websocket import TamTamWS
from classes.controllerbase import ControllerBase
from common.config import ServerConfig

class TTController(ControllerBase):
    def __init__(self):
        self.config = ServerConfig()

    def launch(self, api):
        async def _start_all():
            await asyncio.gather(
                TamTamMobile(
                    host=self.config.host,
                    port=self.config.tamtam_tcp_port,
                    ssl_context=api['ssl'],
                    db_pool=api['db'],
                    clients=api['clients'],
                    send_event=api['event']
                ).start(),
                TamTamWS(
                    host=self.config.host,
                    port=self.config.tamtam_ws_port,
                    ssl_context=api['ssl'],
                    db_pool=api['db'],
                    clients=api['clients'],
                    send_event=api['event']
                ).start()
            )

        return _start_all()