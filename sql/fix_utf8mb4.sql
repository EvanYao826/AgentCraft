-- ============================================
-- 修复管理端表字符集支持emoji
-- 将表字符集从utf8改为utf8mb4
-- ============================================

USE ai_knowledge_db;

-- 修改admin_conversation表字符集
ALTER TABLE `admin_conversation` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `admin_conversation` CHANGE COLUMN `title` `title` VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '新建会话' COMMENT '会话标题';

-- 修改admin_message表字符集
ALTER TABLE `admin_message` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `admin_message` CHANGE COLUMN `content` `content` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息内容';
ALTER TABLE `admin_message` CHANGE COLUMN `sources` `sources` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '参考来源（JSON格式）';
ALTER TABLE `admin_message` CHANGE COLUMN `task_type` `task_type` VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'unknown' COMMENT '任务类型';

-- 修改agent_run表字符集
ALTER TABLE `agent_run` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `agent_run` CHANGE COLUMN `input_text` `input_text` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '输入文本';
ALTER TABLE `agent_run` CHANGE COLUMN `output_text` `output_text` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '输出文本';
ALTER TABLE `agent_run` CHANGE COLUMN `error_message` `error_message` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '错误信息';

-- 修改agent_step表字符集
ALTER TABLE `agent_step` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `agent_step` CHANGE COLUMN `input_data` `input_data` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '输入数据（JSON格式）';
ALTER TABLE `agent_step` CHANGE COLUMN `output_data` `output_data` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '输出数据（JSON格式）';

-- 同时也检查用户端的表，确保它们也支持emoji
ALTER TABLE `conversation` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `message` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `qa_log` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `qa_unanswered` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT '✅ 字符集修复完成，现在支持emoji表情了！' AS message;
