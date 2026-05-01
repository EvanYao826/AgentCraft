package com.demo.aiknowledge.dto;

import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
public class ReportResponse {
    private ReportSummary summary;
    private HotQuestionReport hotQuestions;
    private KnowledgeGrowthReport knowledgeGrowth;
    private AgentPerformanceReport agentPerformance;
    private ToolFailureReport toolFailures;

    @Data
    public static class ReportSummary {
        private LocalDate startDate;
        private LocalDate endDate;
        private String reportType;
        private LocalDateTime generatedAt;
    }

    @Data
    public static class HotQuestionReport {
        private List<HotQuestionItem> daily;
        private List<HotQuestionItem> weekly;
        private Map<String, Integer> categoryDistribution;
    }

    @Data
    public static class HotQuestionItem {
        private String question;
        private Integer count;
        private String category;
        private Double percentage;
    }

    @Data
    public static class KnowledgeGrowthReport {
        private List<GrowthDataPoint> docCountTrend;
        private List<GrowthDataPoint> chunkCountTrend;
        private Integer totalDocs;
        private Integer totalChunks;
        private Integer newDocsToday;
        private Integer newChunksToday;
    }

    @Data
    public static class GrowthDataPoint {
        private LocalDate date;
        private Integer value;
    }

    @Data
    public static class AgentPerformanceReport {
        private Double successRate;
        private Double failureRate;
        private Integer totalRuns;
        private Integer successCount;
        private Integer failureCount;
        private List<TrendDataPoint> successRateTrend;
        private List<TrendDataPoint> failureRateTrend;
        private Integer avgDurationMs;
    }

    @Data
    public static class TrendDataPoint {
        private LocalDate date;
        private Double value;
    }

    @Data
    public static class ToolFailureReport {
        private List<ToolFailureItem> rankings;
        private Integer totalFailures;
        private String mostFrequentFailure;
    }

    @Data
    public static class ToolFailureItem {
        private String toolName;
        private Integer failureCount;
        private String lastError;
        private LocalDateTime lastFailureTime;
        private Double failureRate;
    }
}
