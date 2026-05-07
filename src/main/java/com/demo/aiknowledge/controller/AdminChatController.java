package com.demo.aiknowledge.controller;

import com.demo.aiknowledge.common.Result;
import com.demo.aiknowledge.dto.FeedbackRequest;
import com.demo.aiknowledge.entity.AdminConversation;
import com.demo.aiknowledge.entity.AdminMessage;
import com.demo.aiknowledge.service.AdminChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin-chat")
@RequiredArgsConstructor
public class AdminChatController {

    private final AdminChatService adminChatService;

    @PostMapping("/conversations")
    public Result<AdminConversation> createConversation(
            @RequestParam Long adminId,
            @RequestParam(required = false) String title) {
        return Result.success(adminChatService.createConversation(adminId, title));
    }

    @GetMapping("/conversations")
    public Result<List<AdminConversation>> getHistory(@RequestParam Long adminId) {
        return Result.success(adminChatService.getHistory(adminId));
    }

    @PostMapping("/messages")
    public Result<AdminMessage> sendMessage(
            @RequestParam Long adminId,
            @RequestParam Long conversationId,
            @RequestBody Map<String, String> request) {
        String content = request.get("content");
        return Result.success(adminChatService.sendMessage(adminId, conversationId, content));
    }

    @GetMapping("/messages")
    public Result<List<AdminMessage>> getMessages(@RequestParam Long conversationId) {
        return Result.success(adminChatService.getMessages(conversationId));
    }

    @DeleteMapping("/conversations/{id}")
    public Result<String> deleteConversation(@PathVariable Long id) {
        adminChatService.deleteConversation(id);
        return Result.success("Conversation deleted");
    }

    @PutMapping("/conversations/{id}")
    public Result<AdminConversation> updateConversation(
            @PathVariable Long id,
            @RequestBody AdminConversation conversation) {
        return Result.success(adminChatService.updateConversation(id, conversation.getTitle(), conversation.getIsPinned()));
    }

    @PostMapping("/messages/feedback")
    public Result<AdminMessage> submitFeedback(@RequestBody FeedbackRequest request) {
        return Result.success(adminChatService.submitFeedback(request.getMessageId(), request.getFeedbackType()));
    }
}