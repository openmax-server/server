CREATE TABLE `users` (
    `id` INT PRIMARY KEY,
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
    `username` VARCHAR(60) UNIQUE
);

CREATE TABLE `tokens` (
    `phone` VARCHAR(20) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL,
    `device_type` VARCHAR(256) NOT NULL,
    `device_name` VARCHAR(256) NOT NULL,
    `location` VARCHAR(256) NOT NULL,
    `time` VARCHAR(16) NOT NULL
);

CREATE TABLE `auth_tokens` (
    `phone` VARCHAR(20) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL,
    `code_hash` VARCHAR(64) NOT NULL,
    `expires` VARCHAR(16) NOT NULL,
    `state` VARCHAR(16)
);

CREATE TABLE `user_data` (
    `phone` VARCHAR(20) NOT NULL UNIQUE PRIMARY KEY,
    `contacts` JSON NOT NULL,
    `folders` JSON NOT NULL,
    `user_config` JSON NOT NULL,
    `chat_config` JSON NOT NULL
);

CREATE TABLE `chats` (
    `id` INT NOT NULL PRIMARY KEY,
    `owner` INT NOT NULL,
    `type` VARCHAR(16) NOT NULL
);

CREATE TABLE `messages` (
    `id` INT NOT NULL PRIMARY KEY,
    `chat_id` INT NOT NULL,
    `sender` INT NOT NULL,
    `time` VARCHAR(32) NOT NULL,
    `text` VARCHAR(4000) NOT NULL,
    `attaches` JSON NOT NULL,
    `cid` VARCHAR(32) NOT NULL,
    `elements` JSON NOT NULL,
    `type` VARCHAR(16) NOT NULL
);

CREATE TABLE `chat_participants` (
    `chat_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `joined_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`chat_id`, `user_id`)
);
