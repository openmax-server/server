class OnemeConfig:
    def __init__(self):
        pass

    # TODO: почистить вообще надо, и настройки потыкать
    SERVER_CONFIG = {
        "account-nickname-enabled": False,  # разрешены ли никнеймы аккаунтов
        "account-removal-enabled": False,  # разрешено ли удаление аккаунта

        "anr-config": {  # настройки ANR (Application Not Responding)
          "enabled": True,  # включён ли контроль зависаний
          "timeout": {  # пороги времени зависания
            "low": 5000,   # низкий порог (мс)
            "avg": 5000,   # средний порог (мс)
            "high": 5000   # высокий порог (мс)
          }
        },

        "appearance-multi-theme-screen-enabled": True,  # экран выбора нескольких тем
        "audio-transcription-locales": [],  # языки для расшифровки голосовых сообщений

        "available-complaints": [  # доступные типы жалоб
          "FAKE",       # фейковый аккаунт
          "SPAM",       # спам
          "PORNO",      # порнография
          "EXTREMISM",  # экстремизм
          "THREAT",     # угрозы
          "OTHER"       # другое
        ],

        "avatars-screen-enabled": True,  # экран выбора аватара

        "bad-networ-indicator-config": {  # индикатор плохой сети
          "signalingConfig": {
            "dcReportNetworkStatEnabled": False  # отправка статистики сети
          }
        },

        "bots-channel-adding": True,  # можно ли добавлять ботов в каналы
        "cache-msg-preprocess": True,  # кэширование предварительной обработки сообщений

        "call-incoming-ab": 2,  # вариант A/B теста входящих звонков
        "call-permissions-interval": 259200,  # интервал запроса разрешений для звонков (сек)

        "call-pinch-to-zoom": True,  # зум жестом в звонке

        "call-rate": {  # ограничения звонков
          "limit": 3,      # максимум звонков
          "sdk-limit": 2,  # ограничение SDK
          "duration": 10,  # длительность
          "delay": 86400   # задержка перед следующей попыткой
        },

        "callDontUseVpnForRtp": False,  # не использовать VPN для RTP
        "callEnableIceRenomination": False,  # ICE renegotiation для WebRTC

        "calls-endpoint": "https://calls.okcdn.ru/",  # сервер звонков

        "calls-sdk-am-speaker-fix": True,  # фикс громкой связи

        "calls-sdk-audio-dynamic-redundancy": {  # динамическая избыточность аудио
          "mab": 16,
          "dsb": 64,
          "nl": True,
          "df": True,
          "dlb": True
        },

        "calls-sdk-enable-nohost": True,  # отключение host кандидатов WebRTC
        "calls-sdk-incall-stat": False,  # статистика звонков
        "calls-sdk-linear-opus-bwe": True,  # линейное управление bitrate Opus

        "calls-sdk-mapping": {
          "off": True  # отключение mapping
        },

        "calls-sdk-remove-nonopus-audiocodecs": True,  # убрать не-Opus кодеки
        "calls-use-call-end-reason-fix": True,  # фикс причины завершения звонка
        "calls-use-ws-url-validation": True,  # проверка URL websocket

        "cfs": True,  # внутренний флаг функции

        "channels-complaint-enabled": True,  # жалобы на каналы
        "channels-enabled": True,  # включены ли каналы
        "channels-search-subscribers-visible": True,  # видимость подписчиков в поиске

        "chat-complaint-enabled": False,  # жалобы в чатах
        "chat-gif-autoplay-enabled": True,  # автозапуск GIF
        "chat-history-notif-msg-strategy": 1,  # стратегия уведомлений истории
        "chat-history-persist": False,  # сохранение истории
        "chat-history-warm-opts": 0,  # оптимизация прогрева истории

        "chat-invite-link-permissions-enabled": True,  # права на инвайт ссылки

        "chat-media-scrollable-caption-enabled": True,  # прокручиваемые подписи медиа
        "chat-video-autoplay-enabled": True,  # автозапуск видео
        "chat-video-call-button": True,  # кнопка видеозвонка

        "chatlist-subtitle-ver": 1,  # версия подзаголовков списка чатов
        "chats-folder-enabled": True,  # папки чатов

        "chats-page-size": 50,  # размер страницы списка чатов
        "chats-preload-period": 15,  # период предзагрузки

        "cis-enabled": True,  # внутренняя функция

        "contact-add-bottom-sheet": True,  # нижнее меню добавления контакта

        "creation-2fa-config": {  # настройки 2FA
          "pass_min_len": 6,   # минимальная длина пароля
          "pass_max_len": 64,  # максимальная длина
          "hint_max_len": 30,  # длина подсказки
          "enabled": True      # включено ли
        },

        "debug-profile-info": False,  # debug информация профиля

        "default-reactions-settings": {  # настройки реакций по умолчанию
          "isActive": True,
          "count": 8,
          "included": False,
          "reactionIds": []
        },

        "delete-msg-fys-large-chat-disabled": True,  # запрет удаления сообщений в больших чатах

        "devnull": {  # тестовые флаги
          "opcode": True,
          "upload_hang": True
        },

        "disconnect-timeout": 300,  # таймаут отключения

        "double-tap-reaction": "👍",  # реакция по двойному тапу
        "double-tap-reaction-enabled": True,  # включена ли

        "drafts-sync-enabled": False,  # синхронизация черновиков

        "edit-chat-type-screen-enabled": False,  # экран изменения типа чата
        "edit-timeout": 604800,  # время редактирования сообщения (сек)

        "enable-filters-for-folders": True,  # фильтры папок
        "enable-unknown-contact-bottom-sheet": 2,  # меню неизвестного контакта

        "fake-chats": True,  # тестовые фейковые чаты

        "family-protection-botid": 67804175,  # бот семейной защиты

        "february-23-26-theme": True,  # праздничная тема

        "file-preview": True,  # предпросмотр файлов
        "file-upload-enabled": True,  # загрузка файлов

        "file-upload-max-size": 4294967296,  # максимальный размер файла (~4GB)

        "file-upload-unsupported-types": [
          "exe"  # запрещённые типы файлов
        ],

        "force-play-embed": True,  # принудительное воспроизведение embed

        "gc-from-p2p": True,  # создание групп из p2p
        "gce": False,
        "group-call-part-limit": 100,  # лимит участников группового звонка
        "grse": False,
        "gsse": True,

        "hide-incoming-call-notif": True,  # скрыть уведомление входящего звонка

        "host-reachability": True,  # проверка доступности хоста

        "image-height": 1920,  # максимальная высота изображения
        "image-quality": 0.800000011920929,  # качество сжатия
        "image-size": 40000000,  # максимальный размер изображения
        "image-width": 1920,  # максимальная ширина

        "in-app-review-triggers": 255,  # триггеры оценки приложения
        "informer-enabled": True,  # информеры

        "inline-ev-player": True,  # встроенный видеоплеер

        "invalidate-db-msg-exception": True,  # сброс БД при ошибках сообщений

        "invite-friends-sheet-frequency": [
          2,
          7
        ],  # частота показа приглашения друзей

        "invite-link": "https://t.me/openmax_alerts",  # ссылка приглашения
        "invite-long": "Я пользуюсь OpenMAX. Присоединяйся! https://t.me/openmax_alerts",  # длинный текст
        "invite-short": "Я пользуюсь OpenMAX. Присоединяйся! https://t.me/openmax_alerts",  # короткий текст

        "join-requests": True,  # заявки на вступление

        "js-download-delegate": False,  # загрузка JS

        "keep-connection": 2,  # режим поддержания соединения

        "lebedev-theme-enabled": True,  # тема Лебедева

        "lgce": True,

        "markdown-enabled": True,  # markdown в сообщениях
        "markdown-menu": 0,  # меню markdown

        "max-audio-length": 3600,  # максимум аудио (сек)

        "max-description-length": 400,  # длина описания
        "max-favorite-chats": 5,  # максимум избранных чатов
        "max-favorite-sticker-sets": 100,
        "max-favorite-stickers": 100,

        "max-msg-length": 4000,  # длина сообщения

        "max-participants": 20000,  # максимум участников

        "max-readmarks": 100,  # максимум отметок прочтения

        "max-theme-length": 200,  # длина темы

        "max-video-duration-download": 1200,  # максимальная длительность видео
        "max-video-message-length": 60,  # видеосообщение

        "media-order": 1,  # порядок медиа
        "media-playlist-enabled": True,  # плейлист медиа

        "media-transform": {  # трансформация медиа
          "enabled": True,
          "hdr_enabled": False,
          "hevc_enabled": True,
          "max_enc_frames": {
            "low": 1,
            "avg": 1,
            "high": 2
          }
        },

        "media-viewer-rotation-enabled": True,  # поворот медиа
        "media-viewer-video-collage-enabled": True,  # коллаж видео

        "mentions-enabled": True,  # упоминания
        "mentions_entity_names_limit": 3,  # лимит имён

        "migrate-unsafe-warn": True,  # предупреждение небезопасной миграции

        "min-image-side-size": 64,  # минимальный размер стороны

        "miui-menu-enabled": True,  # меню MIUI

        "money-transfer-botid": 1134691,  # бот переводов

        "moscow-theme-enabled": True,  # московская тема

        "msg-get-reactions-page-size": 40,  # реакции на сообщение

        "music-files-enabled": False,  # поддержка музыкальных файлов

        "mytracker-enabled": False,  # аналитика MyTracker

        "net-client-dns-enabled": True,  # DNS клиент
        "net-session-suppress-bad-disconnected-state": True,  # подавление ошибки disconnect

        "net-stat-config": [
          64,
          48,
          128,
          135
        ],  # статистика сети

        "new-admin-permissions": True,  # новые права админов

        "new-logout-logic": False,  # новая логика выхода

        "new-media-upload-ui": True,  # новый UI загрузки медиа
        "new-media-viewer-enabled": True,  # новый просмотрщик

        "new-settings-storage-screen-enabled": False,  # экран хранилища

        "new-width-text-bubbles-mob": True,  # новая ширина сообщений

        "new-year-theme-2026": False,  # новогодняя тема 2026

        "nick-max-length": 60,  # макс длина ника
        "nick-min-length": 7,  # мин длина ника

        "official-org": True,  # официальный аккаунт организации

        "one-video-failover": True,  # fallback видео
        "one-video-player": True,  # единый видеоплеер
        "one-video-uploader": True,  # загрузчик видео
        "one-video-uploader-audio": True,  # аудио загрузка
        "one-video-uploader-progress-fix": True,  # фикс прогресса

        "perf-events": {  # события производительности
          "startup_report": 2,
          "web_app": 2
        },

        "player-load-control": {  # буферизация плеера
          "mp_autoplay_enabled": False,
          "time_over_size": False,
          "buffer_after_rebuffer_ms": 3000,
          "buffer_ms": 500,
          "max_buffer_ms": 13000,
          "min_buffer_ms": 5000,
          "use_min_size_lc": True,
          "min_size_lc_fmt_mis_sf": 4
        },

        "progress-diff-for-notify": 1,  # изменение прогресса уведомлений

        "push-delivery": True,  # push уведомления

        "qr-auth-enabled": True,  # авторизация по QR

        "quotes-enabled": True,  # цитирование

        "react-errors": [
          "error.comment.chat.access",
          "error.comment.invalid",
          "error.message.invalid",
          "error.message.chat.access",
          "error.message.like.unknown.like",
          "error.message.like.unknown.reaction",
          "error.too-many-unlikes-dialog",
          "error.too-many-unlikes-chat",
          "error.too-many-likes",
          "error.reactions.not.allowed"
        ],  # список ошибок реакций

        "react-permission": 2,  # уровень разрешения реакций

        "reactions-enabled": True,  # включены реакции
        "reactions-max": 8,  # максимум реакций

        "reactions-menu": [
          "👍",
          "❤️",
          "🤣",
          "🔥",
          "😭",
          "💯",
          "💩",
          "😡"
        ],  # меню реакций

        "reactions-settings-enabled": True,  # настройки реакций

        "reconnect-call-ringtone": True,  # звук переподключения

        "ringtone-am-mode": True,  # режим рингтона

        "saved-messages-aliases": [
          "избранное",
          "saved",
          "favourite",
          "favorite",
          "личное",
          "моё",
          "мои",
          "мой",
          "моя",
          "любимое",
          "сохраненные",
          "сохраненное",
          "заметки",
          "закладки"
        ],  # алиасы для "Избранного"

        "scheduled-messages-enabled": True,  # отложенные сообщения
        "scheduled-posts-enabled": True,  # отложенные посты

        "send-location-enabled": True,  # отправка геолокации

        "send-logs-interval-sec": 900,  # интервал отправки логов

        "server-side-complains-enabled": True,  # серверные жалобы

        "set-audio-device": False,  # выбор аудио устройства

        "set-unread-timeout": 31536000,  # время хранения непрочитанных

        "show-reactions-on-multiselect": True,  # реакции при мультивыборе

        "show-warning-links": True,  # предупреждение ссылок

        "speedy-upload": True,  # ускоренная загрузка
        "speedy-voice-messages": True,  # быстрые голосовые

        "sse": True,  # Server-Sent Events

        "stat-session-background-threshold": 60000,  # порог фоновой сессии

        "stickers-controller-suspend": True,  # приостановка контроллера стикеров
        "stickers-db-batch": True,  # пакетная запись БД

        "streamable-mp4": True,  # потоковое mp4

        "stub": "stub2",  # заглушка

        "suspend-video-converter": True,  # приостановка конвертера

        "system-default-ringtone-opt": True,  # системный рингтон

        "typing-enabled-FILE": True,  # индикатор набора при файлах

        "unique-favorites": True,  # уникальные избранные

        "unsafe-files-alert": True,  # предупреждение опасных файлов

        "upload-reusability": True,  # повторное использование загрузки
        "upload-rx-no-blocking": True,  # неблокирующая загрузка

        "video-msg-channels-enabled": True,  # видеосообщения в каналах

        "video-msg-config": {  # настройки видеосообщений
          "duration": 60,
          "quality": 480,
          "min_frame_rate": 30,
          "max_frame_rate": 30
        },

        "video-msg-enabled": True,  # включены видеосообщения

        "video-transcoding-class": [
          2,
          3
        ],  # классы транскодирования

        "views-count-enabled": True,  # счетчик просмотров

        "watchdog-config": {  # watchdog зависаний
          "enabled": True,
          "stuck": 10,
          "hang": 60
        },

        "webapp-exc": [
          63602953,
          8250447
        ],  # исключения webapp

        "webapp-push-open": True,  # открытие push webapp

        "webview-cache-enabled": False,  # кеш webview

        "white-list-links": [
          "max.ru",
          "vk.com",
          "vk.ru",
          "gosuslugi.ru",
          "mail.ru",
          "vk.ru",
          "vkvideo.ru"
        ],  # белый список ссылок

        "wm-analytics-enabled": True,  # аналитика
        "wm-workers-limit": 80,  # лимит воркеров

        "wud": False,  # внутренняя функция

        "y-map": {  # настройки Яндекс карт
          "tile": "34c7fd82-723d-4b23-8abb-33376729a893",
          "geocoder": "34c7fd82-723d-4b23-8abb-33376729a893",
          "static": "34c7fd82-723d-4b23-8abb-33376729a893",
          "logoLight": "https://st.max.ru/icons/ya_maps_logo_light.webp",
          "logoDark": "https://st.max.ru/icons/ya_maps_logo_dark.webp"
        },

        "has-phone": True  # аккаунт привязан к телефону
    }
