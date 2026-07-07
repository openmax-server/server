import json

class WebProto:
    def pack_packet(self, ver=10, cmd=1, seq=0, opcode=1, payload=None):
        # а разве не надо в жсон запаковывать ещё
        # о всё
        return json.dumps({
            "ver": ver,
            "cmd": cmd,
            "seq": seq,
            "opcode": opcode,
            "payload": payload
        })

    MAX_PACKET_SIZE = 65536 # 64 KB, заглушка, нужно узнать реальные лимиты и поменять, хотя кто будет это делать...

    def unpack_packet(self, packet):
        # try catch чтобы не сыпалось всё при неверных пакетах
        if isinstance(packet, (str, bytes)) and len(packet) > self.MAX_PACKET_SIZE:
            return {}

        try:
            parsed_packet = json.loads(packet)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

        return parsed_packet
        # мне кажется долго вручную всё писать
        # а как еще
        # ну вставить сюда целиком и потом через multiline cursor удалить лишнее
        # ну ты удалишь тогда. я на тачпаде
        # ладно щас другим способом удалю
        # всё нахуй
        # TAMTAM SOURCE LEAK 2026
        # так ну че делать будем 
        # так ну

        # 19 опкод сделан?
        # нет сэр пошли библиотеку тамы смотреть
        # мб найдем че. она без обфускации
        # а ты ее видишь?
        # пошли

    ### Констаты протокола
    CMD_OK = 1
    CMD_NOF = 2
    CMD_ERR = 3
    PROTO_VER = 10
