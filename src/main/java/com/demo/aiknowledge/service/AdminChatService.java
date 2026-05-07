package com.demo.aiknowledge.service;

import com.demo.aiknowledge.entity.AdminConversation;
import com.demo.aiknowledge.entity.AdminMessage;
import java.util.List;

public interface AdminChatService {
    AdminConversation createConversation(Long adminId, String title);
    List<AdminConversation> getHistory(Long adminId);
    AdminMessage sendMessage(Long adminId, Long conversationId, String content);
    List<AdminMessage> getMessages(Long conversationId);
    void deleteConversation(Long conversationId);
    AdminConversation updateConversation(Long conversationId, String title, Boolean isPinned);
    AdminMessage submitFeedback(Long messageId, String feedbackType);
}