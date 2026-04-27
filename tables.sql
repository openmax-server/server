CREATE TABLE `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `phone` VARCHAR(20) UNIQUE,
    `telegram_id` VARCHAR(64) UNIQUE,
    `firstname` VARCHAR(59) NOT NULL,
    `lastname` VARCHAR(59),
    `description` VARCHAR(400),
    `avatar_id` VARCHAR(16),
    `updatetime` VARCHAR(24),
    `lastseen` VARCHAR(24),
    `profileoptions` JSON NOT NULL,
    `options` JSON NOT NULL,
    `accountstatus` VARCHAR(16) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `username` VARCHAR(60) UNIQUE,
    PRIMARY KEY (`id`)
);

CREATE TABLE `tokens` (
    `phone` VARCHAR(20) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL,
    `device_type` VARCHAR(256) NOT NULL,
    `device_name` VARCHAR(256) NOT NULL,
    `location` VARCHAR(256) NOT NULL,
    `time` VARCHAR(16) NOT NULL,
    `push_token` VARCHAR(512) DEFAULT NULL,
    PRIMARY KEY (`phone`, `token_hash`)
);

CREATE TABLE `auth_tokens` (
    `phone` VARCHAR(20) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL,
    `code_hash` VARCHAR(64) NOT NULL,
    `expires` VARCHAR(16) NOT NULL,
    `state` VARCHAR(16),
    PRIMARY KEY (`phone`, `token_hash`)
);

CREATE TABLE `user_data` (
    `phone` VARCHAR(20) NOT NULL UNIQUE,
    `user_config` JSON NOT NULL,
    `chat_config` JSON NOT NULL,
    PRIMARY KEY (`phone`)
);

CREATE TABLE `chats` (
    `id` INT NOT NULL,
    `owner` INT NOT NULL,
    `type` VARCHAR(16) NOT NULL,
    PRIMARY KEY (`id`)
);

CREATE TABLE `messages` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `chat_id` INT NOT NULL,
    `sender` INT NOT NULL,
    `time` VARCHAR(32) NOT NULL,
    `text` VARCHAR(4000) NOT NULL,
    `attaches` JSON NOT NULL,
    `cid` VARCHAR(32) NOT NULL,
    `elements` JSON NOT NULL,
    `type` VARCHAR(16) NOT NULL,
    PRIMARY KEY (`id`)
);

CREATE TABLE `chat_participants` (
    `chat_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `joined_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`chat_id`, `user_id`)
);

CREATE TABLE `contacts` (
    `owner_id` INT NOT NULL,
    `contact_id` INT NOT NULL,
    `custom_firstname` VARCHAR(64),
    `custom_lastname` VARCHAR(64),
    `is_blocked` BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (`owner_id`, `contact_id`)
);

CREATE TABLE `banners` (
    `id` VARCHAR(64) NOT NULL,
    `title` VARCHAR(256) NOT NULL,
    `description` VARCHAR(512) NOT NULL,
    `url` VARCHAR(512) NOT NULL,
    `type` INT NOT NULL DEFAULT 1,
    `priority` INT NOT NULL DEFAULT 0,
    `animoji_id` INT NOT NULL DEFAULT 0,
    `repeat` INT NOT NULL DEFAULT 1,
    `rerun` BIGINT NOT NULL DEFAULT 0,
    `hide_close_button` BOOLEAN NOT NULL DEFAULT FALSE,
    `hide_on_click` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_title_animated` BOOLEAN NOT NULL DEFAULT FALSE,
    `enabled` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);

CREATE TABLE `user_folders` (
    `id` VARCHAR(64) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `title` VARCHAR(128) NOT NULL,
    `filters` JSON NOT NULL DEFAULT ('[]'),
    `include` JSON NOT NULL DEFAULT ('[]'),
    `options` JSON NOT NULL DEFAULT ('[]'),
    `source_id` INT NOT NULL DEFAULT 1,
    `update_time` BIGINT NOT NULL DEFAULT 0,
    `sort_order` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`, `phone`)
);
