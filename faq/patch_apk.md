# Смена сервера в мобильном клиенте
> [!Caution]
> Инструкция может быть недостаточной, если вы используете самоподписанный сертификат или сертификат, которому система не доверяет. Вам, возможно, потребуется выполнить дополнительные действия в модификации клиента для успешного входа.

# MT Manager
1. Открываем apk файл клиента, который желаете пропатчить
2. Нажимаем на любой dex файл
3. Выбираем в качестве редактора "Редактор dex+"
4. Выбираем все dex файлы при появлении окна выбора "MultiDex"
5. В поиске выбираем тип Smali, а в поле поиска пишем "api.oneme.ru"
6. Проходимся по каждому результату и заменяем сервер на свой

# ApkTool M
1. Декомпилируем приложение, обязательно поставьте галочку у пункта "Декомпилировать classes*.dex"
2. В папке проекта нажимаем на "лупу"
3. Ставим поиск по содержимому с заменой
4. В поле поиска пишем "api.oneme.ru", а в поле замены ваш адрес сервера
5. После замены нажимаем на "Собрать проект"

# ApkTool
1. Помещаем apk в рабочую директорию
2. Открываем консоль в той же директории и производим декомпиляцию: `apktool d <имя apk> -o max`
3. Заходим в папку проекта и заменяем во всех классах "api.oneme.ru" на свой адрес сервера
4. Производим повторную сборку с помощью команды: `apktool b max -o max_modified.apk`

---

# Патчинг Firebase для push-уведомлений

> [!Important]
> Без замены Firebase-конфига пуши от вашего сервера не будут работать.

1. Создайте проект в [Firebase Console](https://console.firebase.google.com/) и добавьте Android-приложение с пакетом `ru.oneme.app`
2. Скачайте `google-services.json`
3. В декомпилированном APK откройте `res/values/strings.xml` и замените следующие строки на значения из вашего `google-services.json`:

| Строка | Оригинал | Откуда взять |
|---|---|---|
| `google_api_key` | `AIzaSyABuDYeeDXIOrKTXLkUj30Ii143ofPe63Q` | `client[0].api_key[0].current_key` |
| `google_app_id` | `1:659634599081:android:9605285443b661167225b8` | `client[0].client_info.mobilesdk_app_id` |
| `gcm_defaultSenderId` | `659634599081` | `project_info.project_number` |
| `project_id` | `max-messenger-app` | `project_info.project_id` |
| `google_crash_reporting_api_key` | `AIzaSyABuDYeeDXIOrKTXLkUj30Ii143ofPe63Q` | `client[0].api_key[0].current_key` |
| `google_storage_bucket` | `max-messenger-app.firebasestorage.app` | `project_info.storage_bucket` |

4. Соберите и подпишите APK
5. В настройках проекта Firebase создайте сервисный аккаунт и укажите путь в `.env`