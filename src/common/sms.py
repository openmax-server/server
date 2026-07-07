import aiohttp
import ssl
import logging

logger = logging.getLogger(__name__)

async def send_sms_code(gateway_url: str, phone: str) -> str | None:
    url = f"{gateway_url}/sms/send"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.post(url, json={"phone_number": phone}) as resp:
                data = await resp.json()
        except Exception as e:
            logger.error(f"Ошибка подключения к SMS шлюзу: {e}")
            return None
    if not data.get("success"):
        logger.error(f"SMS шлюз вернул ошибку: {data.get('error')}")
        return None
    code = data.get("code")
    if not code:
        logger.error("SMS шлюз не вернул код")
        return None
    code = str(code)
    # Если шлюз вернул 5-значный код — повторяем последнюю цифру.
    # Пример: 26541 -> 265411, 26542 -> 265422
    # Пользователь получает SMS с 5 цифрами и дописывает последнюю (такую же).
    if len(code) == 5:
        code = code + code[-1]
        logger.debug(f"Код дополнен до 6 цифр: {code}")
    return code