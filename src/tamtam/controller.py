import asyncio
from tamtam.socket import TTMobileServer
from classes.controllerbase import ControllerBase
from common.config import ServerConfig

class TTMobileController(ControllerBase):
    def __init__(self):
        self.config = ServerConfig()

    def launch(self, api):
        async def _start_all():
            await asyncio.gather(
                TTMobileServer(
                    host=self.config.host,
                    port=self.config.tamtam_tcp_port,
                    ssl_context=api['ssl'],
                    db_pool=api['db'],
                    clients=api['clients'],
                    send_event=api['event']
                ).start()
            )

        return _start_all()