package com.demo.aiknowledge.service;

import com.demo.aiknowledge.dto.AiResponse;

public interface AiService {
    void parseDocument(String filePath, Long docId);

    /**
     * 根据上下文回答问题
     * @param question 用户问题
     * @param context 相关文档上下文
     * @param userId 用户ID
     * @return AI回答对象
     */
    AiResponse ask(String question, String context, Long userId);

    /**
     * 生成会话标题并更新数据库
     * @param conversationId 会话ID
     * @param question 用户问题
     */
    void generateTitle(Long conversationId, String question);

    /**
     * 删除文档向量索引
     */
    void deleteDoc(Long docId);

    /**
     * 管理端AI助手问答
     * @param question 用户问题
     * @param context 对话上下文
     * @param adminId 管理员ID
     * @return AI回答对象
     */
    java.util.Map<String, Object> askForAdmin(String question, String context, Long adminId);
}
