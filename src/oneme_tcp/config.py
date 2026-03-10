class OnemeConfig:
    def __init__(self):
        pass

    # TODO: почистить вообще надо, и настройки потыкать
    SERVER_CONFIG = {
        "account-nickname-enabled": False,
        "account-removal-enabled": False,
        "anr-config": {
          "enabled": True,
          "timeout": {
            "low": 5000,
            "avg": 5000,
            "high": 5000
          }
        },
        "appearance-multi-theme-screen-enabled": True,
        "audio-transcription-locales": [],
        "available-complaints": [
          "FAKE",
          "SPAM",
          "PORNO",
          "EXTREMISM",
          "THREAT",
          "OTHER"
        ],
        "avatars-screen-enabled": True,
        "bad-networ-indicator-config": {
          "signalingConfig": {
            "dcReportNetworkStatEnabled": False
          }
        },
        "bots-channel-adding": True,
        "cache-msg-preprocess": True,
        "call-incoming-ab": 2,
        "call-permissions-interval": 259200,
        "call-pinch-to-zoom": True,
        "call-rate": {
          "limit": 3,
          "sdk-limit": 2,
          "duration": 10,
          "delay": 86400
        },
        "callDontUseVpnForRtp": False,
        "callEnableIceRenomination": False,
        "calls-endpoint": "https://calls.okcdn.ru/",
        "calls-sdk-am-speaker-fix": True,
        "calls-sdk-audio-dynamic-redundancy": {
          "mab": 16,
          "dsb": 64,
          "nl": True,
          "df": True,
          "dlb": True
        },
        "calls-sdk-enable-nohost": True,
        "calls-sdk-incall-stat": False,
        "calls-sdk-linear-opus-bwe": True,
        "calls-sdk-mapping": {
          "off": True
        },
        "calls-sdk-remove-nonopus-audiocodecs": True,
        "calls-use-call-end-reason-fix": True,
        "calls-use-ws-url-validation": True,
        "cfs": True,
        "channels-complaint-enabled": True,
        "channels-enabled": True,
        "channels-search-subscribers-visible": True,
        "chat-complaint-enabled": False,
        "chat-gif-autoplay-enabled": True,
        "chat-history-notif-msg-strategy": 1,
        "chat-history-persist": False,
        "chat-history-warm-opts": 0,
        "chat-invite-link-permissions-enabled": True,
        "chat-media-scrollable-caption-enabled": True,
        "chat-video-autoplay-enabled": True,
        "chat-video-call-button": True,
        "chatlist-subtitle-ver": 1,
        "chats-folder-enabled": True,
        "chats-page-size": 50,
        "chats-preload-period": 15,
        "cis-enabled": True,
        "contact-add-bottom-sheet": True,
        "creation-2fa-config": {
          "pass_min_len": 6,
          "pass_max_len": 64,
          "hint_max_len": 30,
          "enabled": True
        },
        "debug-profile-info": False,
        "default-reactions-settings": {
          "isActive": True,
          "count": 8,
          "included": False,
          "reactionIds": []
        },
        "delete-msg-fys-large-chat-disabled": True,
        "devnull": {
          "opcode": True,
          "upload_hang": True
        },
        "disconnect-timeout": 300,
        "double-tap-reaction": "👍",
        "double-tap-reaction-enabled": True,
        "drafts-sync-enabled": False,
        "edit-chat-type-screen-enabled": False,
        "edit-timeout": 604800,
        "enable-filters-for-folders": True,
        "enable-unknown-contact-bottom-sheet": 2,
        "fake-chats": True,
        "family-protection-botid": 67804175,
        "february-23-26-theme": True,
        "file-preview": True,
        "file-upload-enabled": True,
        "file-upload-max-size": 4294967296,
        "file-upload-unsupported-types": [
          "exe"
        ],
        "force-play-embed": True,
        "gc-from-p2p": True,
        "gce": False,
        "group-call-part-limit": 100,
        "grse": False,
        "gsse": True,
        "hide-incoming-call-notif": True,
        "host-reachability": True,
        "image-height": 1920,
        "image-quality": 0.800000011920929,
        "image-size": 40000000,
        "image-width": 1920,
        "in-app-review-triggers": 255,
        "informer-enabled": True,
        "inline-ev-player": True,
        "invalidate-db-msg-exception": True,
        "invite-friends-sheet-frequency": [
          2,
          7
        ],
        "invite-link": "https://t.me/openmax_alerts",
        "invite-long": "Я пользуюсь OpenMAX. Присоединяйся! https://t.me/openmax_alerts",
        "invite-short": "Я пользуюсь OpenMAX. Присоединяйся! https://t.me/openmax_alerts",
        "join-requests": True,
        "js-download-delegate": False,
        "keep-connection": 2,
        "lebedev-theme-enabled": True,
        "lgce": True,
        "markdown-enabled": True,
        "markdown-menu": 0,
        "max-audio-length": 3600,
        "max-description-length": 400,
        "max-favorite-chats": 5,
        "max-favorite-sticker-sets": 100,
        "max-favorite-stickers": 100,
        "max-msg-length": 4000,
        "max-participants": 20000,
        "max-readmarks": 100,
        "max-theme-length": 200,
        "max-video-duration-download": 1200,
        "max-video-message-length": 60,
        "media-order": 1,
        "media-playlist-enabled": True,
        "media-transform": {
          "enabled": True,
          "hdr_enabled": False,
          "hevc_enabled": True,
          "max_enc_frames": {
            "low": 1,
            "avg": 1,
            "high": 2
          }
        },
        "media-viewer-rotation-enabled": True,
        "media-viewer-video-collage-enabled": True,
        "mentions-enabled": True,
        "mentions_entity_names_limit": 3,
        "migrate-unsafe-warn": True,
        "min-image-side-size": 64,
        "miui-menu-enabled": True,
        "money-transfer-botid": 1134691,
        "moscow-theme-enabled": True,
        "msg-get-reactions-page-size": 40,
        "music-files-enabled": False,
        "mytracker-enabled": False,
        "net-client-dns-enabled": True,
        "net-session-suppress-bad-disconnected-state": True,
        "net-stat-config": [
          64,
          48,
          128,
          135
        ],
        "new-admin-permissions": True,
        "new-logout-logic": False,
        "new-media-upload-ui": True,
        "new-media-viewer-enabled": True,
        "new-settings-storage-screen-enabled": False,
        "new-width-text-bubbles-mob": True,
        "new-year-theme-2026": False,
        "nick-max-length": 60,
        "nick-min-length": 7,
        "official-org": True,
        "one-video-failover": True,
        "one-video-player": True,
        "one-video-uploader": True,
        "one-video-uploader-audio": True,
        "one-video-uploader-progress-fix": True,
        "perf-events": {
          "startup_report": 2,
          "web_app": 2
        },
        "player-load-control": {
          "mp_autoplay_enabled": False,
          "time_over_size": False,
          "buffer_after_rebuffer_ms": 3000,
          "buffer_ms": 500,
          "max_buffer_ms": 13000,
          "min_buffer_ms": 5000,
          "use_min_size_lc": True,
          "min_size_lc_fmt_mis_sf": 4
        },
        "progress-diff-for-notify": 1,
        "push-delivery": True,
        "qr-auth-enabled": True,
        "quotes-enabled": True,
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
        ],
        "react-permission": 2,
        "reactions-enabled": True,
        "reactions-max": 8,
        "reactions-menu": [
          "👍",
          "❤️",
          "🤣",
          "🔥",
          "😭",
          "💯",
          "💩",
          "😡"
        ],
        "reactions-settings-enabled": True,
        "reconnect-call-ringtone": True,
        "ringtone-am-mode": True,
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
        ],
        "scheduled-messages-enabled": True,
        "scheduled-posts-enabled": True,
        "search-webapps-showcase": {
          "items": [
            {
              "id": 4479862,
              "icon": "https://st.max.ru/icons/icon_channel_square.webp",
              "title": "Каналы"
            }
          ]
        },
        "send-location-enabled": True,
        "send-logs-interval-sec": 900,
        "server-side-complains-enabled": True,
        "set-audio-device": False,
        "set-unread-timeout": 31536000,
        "settings-entry-banners": [
          {
            "id": 1,
            "logo": "https://st.max.ru/icons/epgu_white_111125.png",
            "align": 2,
            "items": [
              {
                "icon": "https://st.max.ru/icons/digital_id_new_40_3x.png",
                "title": "Цифровой ID",
                "appid": 8250447
              }
            ]
          },
          {
            "id": 2,
            "items": [
              {
                "icon": "https://st.max.ru/icons/sferum_with_padding_120.png",
                "title": "Войти в Cферум",
                "appid": 2340831
              }
            ]
          }
        ],
        "show-reactions-on-multiselect": True,
        "show-warning-links": True,
        "speedy-upload": True,
        "speedy-voice-messages": True,
        "sse": True,
        "stat-session-background-threshold": 60000,
        "sticker-suggestion": [
          "RECENT",
          "NEW",
          "TOP"
        ],
        "stickers-controller-suspend": True,
        "stickers-db-batch": True,
        "streamable-mp4": True,
        "stub": "stub2",
        "suspend-video-converter": True,
        "system-default-ringtone-opt": True,
        "transfer-botid": 1134691,
        "typing-enabled-FILE": True,
        "unique-favorites": True,
        "unsafe-files-alert": True,
        "upload-reusability": True,
        "upload-rx-no-blocking": True,
        "user-debug-report": 2340932,
        "video-msg-channels-enabled": True,
        "video-msg-config": {
          "duration": 60,
          "quality": 480,
          "min_frame_rate": 30,
          "max_frame_rate": 30
        },
        "video-msg-enabled": True,
        "video-transcoding-class": [
          2,
          3
        ],
        "views-count-enabled": True,
        "watchdog-config": {
          "enabled": True,
          "stuck": 10,
          "hang": 60
        },
        "webapp-exc": [
          63602953,
          8250447
        ],
        "webapp-push-open": True,
        "webview-cache-enabled": False,
        "welcome-sticker-ids": [
          272821,
          295349,
          13571,
          546741,
          476341
        ],
        "white-list-links": [
          "max.ru",
          "vk.com",
          "vk.ru",
          "gosuslugi.ru",
          "mail.ru",
          "vk.ru",
          "vkvideo.ru"
        ],
        "wm-analytics-enabled": True,
        "wm-workers-limit": 80,
        "wud": False,
        "y-map": {
          "tile": "34c7fd82-723d-4b23-8abb-33376729a893",
          "geocoder": "34c7fd82-723d-4b23-8abb-33376729a893",
          "static": "34c7fd82-723d-4b23-8abb-33376729a893",
          "logoLight": "https://st.max.ru/icons/ya_maps_logo_light.webp",
          "logoDark": "https://st.max.ru/icons/ya_maps_logo_dark.webp"
        },
        "has-phone": True
    }
