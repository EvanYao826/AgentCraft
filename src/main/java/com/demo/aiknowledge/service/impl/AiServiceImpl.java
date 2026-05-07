package com.demo.aiknowledge.service.impl;


import com.demo.aiknowledge.dto.AiResponse;
import com.demo.aiknowledge.entity.Conversation;
import com.demo.aiknowledge.entity.KnowledgeDoc;
import com.demo.aiknowledge.entity.User;
import com.demo.aiknowledge.config.CacheConfig;
import com.demo.aiknowledge.mapper.ConversationMapper;
import com.demo.aiknowledge.mapper.KnowledgeDocMapper;
import com.demo.aiknowledge.service.AiService;
import com.demo.aiknowledge.service.CacheService;
import com.demo.aiknowledge.service.UserService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
@Slf4j
@RequiredArgsConstructor
public class AiServiceImpl implements AiService {

    private final KnowledgeDocMapper knowledgeDocMapper;
    private final ConversationMapper conversationMapper;
    private final RestTemplate restTemplate;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final UserService userService;
    private final CacheService cacheService;

    @Value("${ai.service.url}")
    private String aiServiceUrl;
    
    /**
     * 判断问题是否是一般性问题，不需要参考来源
     * @param question 用户问题
     * @return 是否是一般性问题
     */
    private boolean isGeneralQuestion(String question) {
        String lowerQuestion = question.toLowerCase();
        // 检查问题是否包含关于系统自身、身份、功能等关键词
        String[] generalKeywords = {
            "你是谁", "你是什么", "你的名字", "你是做什么的", 
            "你的功能", "你能做什么", "你的作用", "你是谁开发的",
            "你来自哪里", "你好", "hello", "hi", "你好吗",
            "how are you", "你叫什么", "你是什么东西", "你是机器人吗",
            "你是AI吗", "你是智能助手吗", "你能帮助我吗", "你的能力",
            "我是谁", "我叫什么", "我的名字", "我的身份"
        };
        
        for (String keyword : generalKeywords) {
            if (lowerQuestion.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 判断回答是否是错误响应
     * @param answer 回答内容
     * @return 是否是错误响应
     */
    private boolean isErrorResponse(String answer) {
        if (answer == null) {
            return true;
        }
        String[] errorKeywords = {
            "AI服务暂时不可用",
            "服务不可用",
            "系统错误",
            "无法连接",
            "网络错误",
            "暂时无法回答",
            "稍后再试"
        };
        for (String keyword : errorKeywords) {
            if (answer.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 获取友好的错误提示语
     * @param errorType 错误类型
     * @return 友好的错误提示
     */
    private String getFriendlyErrorMessage(String errorType) {
        String[] friendlyMessages = {
            "正在努力处理您的问题，请稍等片刻...",
            "系统正在维护中，很快就会恢复，请稍后再试",
            "服务暂时繁忙，请稍后重试",
            "我正在连接知识库，请耐心等待",
            "让我想想，马上为您解答"
        };
        int index = Math.abs(errorType.hashCode()) % friendlyMessages.length;
        return friendlyMessages[index];
    }

    @Override
    @Async
    public void parseDocument(String filePath, Long docId) {
        log.info("Start parsing document: {}, docId: {}", filePath, docId);
        
        // 更新文档状态为PROCESSING
        KnowledgeDoc doc = knowledgeDocMapper.selectById(docId);
        if (doc != null) {
            doc.setStatus("PROCESSING");
            doc.setErrorMessage(null); // 清除之前的错误信息
            knowledgeDocMapper.updateById(doc);
        }
        
        try {
            // 构建请求体
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("file_path", filePath);
            requestBody.put("doc_id", docId);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            // 调用 Python 服务
            String url = aiServiceUrl + "/parse";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            
            if (response.getStatusCode().is2xxSuccessful()) {
                // 更新文档状态为COMPLETED
                if (doc != null) {
                    doc.setStatus("COMPLETED");
                    doc.setErrorMessage(null);
                    knowledgeDocMapper.updateById(doc);
                }
                log.info("Document parsed successfully: {}", docId);
            } else {
                String errorMessage = "AI Service returned error: " + response.getStatusCode();
                throw new RuntimeException(errorMessage);
            }

        } catch (Exception e) {
            log.error("Document parsing failed", e);
            // 更新文档状态为FAILED并记录错误原因
            if (doc != null) {
                doc.setStatus("FAILED");
                doc.setErrorMessage(e.getMessage());
                knowledgeDocMapper.updateById(doc);
            }
            log.error("Document parsing failed: {}, error: {}", docId, e.getMessage());
        }
    }

    @Override
    public AiResponse ask(String question, String context, Long userId) {
        log.info("User question: {}, userId: {}", question, userId);
        AiResponse aiResponse = new AiResponse();

        // 生成缓存键（包含userId，避免不同用户共享缓存导致数据泄露）
        String cacheKey = "ai:answer:" + (userId != null ? userId : "anonymous") + ":" + question.trim().toLowerCase();

        try {
            // 1. 检查缓存（使用新的缓存服务）
            AiResponse cachedResponse = cacheService.get(
                CacheConfig.CacheConstants.CACHE_AI_ANSWER,
                cacheKey,
                AiResponse.class
            );
            if (cachedResponse != null) {
                // 如果缓存的是错误响应，不使用缓存，重新请求
                if (isErrorResponse(cachedResponse.getAnswer())) {
                    log.info("Cache hit but contains error response, refreshing");
                } else {
                    log.info("Cache hit for question: {}", question);
                    return cachedResponse;
                }
            }

            // 2. 构建请求（使用 /ask 接口，它内部已使用 RouterAgent）
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("question", question);
            requestBody.put("context", context);
            
            // 判断用户是否为管理员（userId == 1L 为管理员）
            boolean isAdmin = (userId != null && userId == 1L);
            String username = null;
            if (userId != null) {
                User user = userService.getById(userId);
                if (user != null) {
                    username = user.getUsername();
                    requestBody.put("username", username);
                    log.info("Added username to request: {}", username);
                }
            }
            requestBody.put("is_admin", isAdmin);
            log.info("User is admin: {}", isAdmin);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            // 使用原来的 /ask 接口（它内部已使用 RouterAgent）
            String url = aiServiceUrl + "/ask";
            log.info(">>> [AI Service] 正在调用 Python 服务: {}", url);
            log.info(">>> [AI Service] 请求体: {}", requestBody);

            // 4. 发起调用
            ResponseEntity<Map> response;
            try {
                response = restTemplate.postForEntity(url, entity, Map.class);
            } catch (Exception e) {
                // 捕获网络层面的异常（如 ConnectionRefused, Timeout, UnknownHost）
                log.error(">>> [AI Service] 网络调用失败！无法连接到 Python 服务。URL: {}", url, e);
                // 返回友好的错误响应，不暴露技术细节
                aiResponse.setAnswer(getFriendlyErrorMessage("network"));
                aiResponse.setSources(null);
                // 不要缓存错误响应
                return aiResponse;
            }

            log.info("<<< [AI Service] 响应状态码: {}", response.getStatusCode());
            log.info("<<< [AI Service] 响应体: {}", response.getBody());

            // 5. 处理响应
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Map<String, Object> body = response.getBody();

                // 检查 Python 服务是否返回了预期的 answer 字段
                if (!body.containsKey("answer")) {
                    log.error(">>> [AI Service] Python 服务返回数据格式错误，缺少 'answer' 字段。完整响应：{}", body);
                    // 返回友好的错误响应，不暴露技术细节
                    aiResponse.setAnswer(getFriendlyErrorMessage("format"));
                    aiResponse.setSources(null);
                    // 不要缓存错误响应
                    return aiResponse;
                }

                String answer = (String) body.get("answer");
                aiResponse.setAnswer(answer);

                // 获取任务类型
                if (body.containsKey("task_type")) {
                    String taskType = (String) body.get("task_type");
                    aiResponse.setTaskType(taskType);
                    log.info("Task type detected: {}", taskType);
                }

                // 检查是否有参考来源
                if (body.containsKey("sources")) {
                    List<Map<String, Object>> sources = (List<Map<String, Object>>) body.get("sources");
                    if (sources != null && !sources.isEmpty()) {
                        for (Map<String, Object> source : sources) {
                            if (!source.containsKey("doc") && source.containsKey("doc_name")) {
                                source.put("doc", source.get("doc_name"));
                            }
                        }
                        aiResponse.setSources(sources);
                    }
                }

                // 只缓存非错误响应
                if (!isErrorResponse(answer)) {
                    cacheService.set(
                        CacheConfig.CacheConstants.CACHE_AI_ANSWER,
                        cacheKey,
                        aiResponse
                    );
                }

                return aiResponse;
            } else {
                // 处理非 2xx 状态码（如 404, 500）
                log.error(">>> [AI Service] Python 服务返回错误状态码: {}, 响应体：{}", response.getStatusCode(), response.getBody());
                // 返回友好的错误响应，不暴露技术细节
                aiResponse.setAnswer(getFriendlyErrorMessage("status"));
                aiResponse.setSources(null);
                // 不要缓存错误响应
                return aiResponse;
            }

        } catch (RuntimeException e) {
            // 重新抛出我们上面包装过的运行时异常
            throw e;
        } catch (Exception e) {
            // 捕获其他未知异常
            log.error(">>> [AI Service] 发生未知异常", e);
            // 返回友好的错误响应，不暴露技术细节
            aiResponse.setAnswer(getFriendlyErrorMessage("unknown"));
            aiResponse.setSources(null);
            // 不要缓存错误响应
            return aiResponse;
        }
    }


    @Override
    @Async
    public void generateTitle(Long conversationId, String question) {
        log.info("Generating title for question: {}", question);
        try {
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("question", question);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            String url = aiServiceUrl + "/summary";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                String title = (String) response.getBody().get("title");
                if (title != null && !title.isEmpty()) {
                    Conversation conversation = conversationMapper.selectById(conversationId);
                    if (conversation != null) {
                        conversation.setTitle(title);
                        conversationMapper.updateById(conversation);
                        log.info("Conversation {} title updated to: {}", conversationId, title);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Generate title failed", e);
        }
    }

    @Override
    @Async
    public void deleteDoc(Long docId) {
        log.info("Deleting document vector index for docId: {}", docId);
        try {
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("doc_id", docId);
            // file_path 也是必需的参数，但删除逻辑不需要它，传空串
            requestBody.put("file_path", "");

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            String url = aiServiceUrl + "/delete";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Document vector index deleted successfully: {}", docId);
            } else {
                log.warn("Failed to delete document vector index: {}", response.getStatusCode());
            }
        } catch (Exception e) {
            log.error("Delete document vector index failed", e);
        }
    }

    @Override
    public Map<String, Object> askForAdmin(String question, String context, Long adminId) {
        log.info("[Admin AI] Admin question: {}, adminId: {}", question, adminId);
        Map<String, Object> response = new HashMap<>();

        try {
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("question", question);
            requestBody.put("context", context);
            requestBody.put("is_admin", true);
            requestBody.put("username", "admin_" + adminId);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            String url = aiServiceUrl + "/ask";
            log.info(">>> [Admin AI Service] Calling Python service: {}", url);

            ResponseEntity<Map> httpResponse = restTemplate.postForEntity(url, entity, Map.class);

            if (httpResponse.getStatusCode().is2xxSuccessful() && httpResponse.getBody() != null) {
                Map<String, Object> body = httpResponse.getBody();
                response.put("answer", body.getOrDefault("answer", "抱歉，服务暂时不可用。"));
                response.put("task_type", body.getOrDefault("task_type", "admin_copilot"));
                response.put("sources", body.getOrDefault("sources", null));
                log.info("[Admin AI] Response received, task_type: {}", response.get("task_type"));
            } else {
                response.put("answer", "抱歉，服务暂时不可用，请稍后再试。");
                response.put("task_type", "admin_copilot");
                response.put("sources", null);
            }
        } catch (Exception e) {
            log.error("[Admin AI] Failed to call admin agent", e);
            response.put("answer", "抱歉，服务暂时不可用，请稍后再试。");
            response.put("task_type", "admin_copilot");
            response.put("sources", null);
        }

        return response;
    }
}