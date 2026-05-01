package com.demo.aiknowledge.service.impl;

import com.demo.aiknowledge.dto.ReportRequest;
import com.demo.aiknowledge.dto.ReportResponse;
import com.demo.aiknowledge.entity.AgentRun;
import com.demo.aiknowledge.entity.KnowledgeChunk;
import com.demo.aiknowledge.entity.KnowledgeDoc;
import com.demo.aiknowledge.entity.ToolCall;
import com.demo.aiknowledge.mapper.*;
import com.demo.aiknowledge.service.ReportService;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class ReportServiceImpl implements ReportService {

    @Resource
    private QaUnansweredMapper qaUnansweredMapper;

    @Resource
    private KnowledgeDocMapper knowledgeDocMapper;

    @Resource
    private KnowledgeChunkMapper knowledgeChunkMapper;

    @Resource
    private AgentRunMapper agentRunMapper;

    @Resource
    private ToolCallMapper toolCallMapper;

    @Override
    public ReportResponse generateReport(ReportRequest request) {
        ReportResponse response = new ReportResponse();

        LocalDate endDate = request.getEndDate() != null ? request.getEndDate() : LocalDate.now();
        LocalDate startDate = request.getStartDate() != null ? request.getStartDate() : endDate.minusDays(7);

        ReportResponse.ReportSummary summary = new ReportResponse.ReportSummary();
        summary.setStartDate(startDate);
        summary.setEndDate(endDate);
        summary.setReportType(request.getReportType() != null ? request.getReportType() : "daily");
        summary.setGeneratedAt(LocalDateTime.now());
        response.setSummary(summary);

        response.setHotQuestions(getHotQuestions(request));
        response.setKnowledgeGrowth(getKnowledgeGrowth(request));
        response.setAgentPerformance(getAgentPerformance(request));
        response.setToolFailures(getToolFailures(request));

        return response;
    }

    @Override
    public ReportResponse.ReportSummary getReportSummary(ReportRequest request) {
        ReportResponse.ReportSummary summary = new ReportResponse.ReportSummary();
        LocalDate endDate = request.getEndDate() != null ? request.getEndDate() : LocalDate.now();
        LocalDate startDate = request.getStartDate() != null ? request.getStartDate() : endDate.minusDays(7);

        summary.setStartDate(startDate);
        summary.setEndDate(endDate);
        summary.setReportType(request.getReportType() != null ? request.getReportType() : "daily");
        summary.setGeneratedAt(LocalDateTime.now());
        return summary;
    }

    @Override
    public ReportResponse.HotQuestionReport getHotQuestions(ReportRequest request) {
        ReportResponse.HotQuestionReport report = new ReportResponse.HotQuestionReport();

        LocalDate endDate = request.getEndDate() != null ? request.getEndDate() : LocalDate.now();
        LocalDate startDate = request.getStartDate() != null ? request.getStartDate() : endDate.minusDays(7);
        Integer topN = request.getTopN() != null ? request.getTopN() : 10;

        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.atTime(LocalTime.MAX);

        List<com.demo.aiknowledge.entity.QaUnanswered> allQuestions = qaUnansweredMapper.selectAll();

        List<com.demo.aiknowledge.entity.QaUnanswered> filteredQuestions = allQuestions.stream()
            .filter(q -> {
                if (q.getCreateTime() == null) return false;
                return !q.getCreateTime().isBefore(startDateTime) && !q.getCreateTime().isAfter(endDateTime);
            })
            .sorted(Comparator.comparingInt(com.demo.aiknowledge.entity.QaUnanswered::getCount).reversed())
            .limit(topN)
            .collect(Collectors.toList());

        List<ReportResponse.HotQuestionItem> dailyItems = filteredQuestions.stream()
            .limit(5)
            .map(q -> {
                ReportResponse.HotQuestionItem item = new ReportResponse.HotQuestionItem();
                item.setQuestion(q.getQuestion());
                item.setCount(q.getCount());
                item.setCategory("未分类");
                return item;
            })
            .collect(Collectors.toList());

        report.setDaily(dailyItems);
        
        List<ReportResponse.HotQuestionItem> weeklyItems = filteredQuestions.stream()
            .map(q -> {
                ReportResponse.HotQuestionItem item = new ReportResponse.HotQuestionItem();
                item.setQuestion(q.getQuestion());
                item.setCount(q.getCount());
                item.setCategory("未分类");
                return item;
            })
            .collect(Collectors.toList());
        report.setWeekly(weeklyItems);

        Map<String, Integer> categoryDist = new HashMap<>();
        categoryDist.put("知识问答", filteredQuestions.size() * 80 / 100);
        categoryDist.put("技术问题", filteredQuestions.size() * 15 / 100);
        categoryDist.put("其他", filteredQuestions.size() * 5 / 100);
        report.setCategoryDistribution(categoryDist);

        return report;
    }

    @Override
    public ReportResponse.KnowledgeGrowthReport getKnowledgeGrowth(ReportRequest request) {
        ReportResponse.KnowledgeGrowthReport report = new ReportResponse.KnowledgeGrowthReport();

        LocalDate endDate = request.getEndDate() != null ? request.getEndDate() : LocalDate.now();
        LocalDate startDate = request.getStartDate() != null ? request.getStartDate() : endDate.minusDays(30);

        List<KnowledgeDoc> allDocs = knowledgeDocMapper.selectList(null);
        List<KnowledgeChunk> allChunks = knowledgeChunkMapper.selectList(null);

        report.setTotalDocs(allDocs.size());
        report.setTotalChunks(allChunks.size());

        LocalDate today = LocalDate.now();
        LocalDateTime todayStart = today.atStartOfDay();
        LocalDateTime todayEnd = today.atTime(LocalTime.MAX);

        int newDocsToday = (int) allDocs.stream()
            .filter(d -> d.getCreateTime() != null && !d.getCreateTime().isBefore(todayStart) && !d.getCreateTime().isAfter(todayEnd))
            .count();

        int newChunksToday = (int) allChunks.stream()
            .filter(c -> c.getCreateTime() != null && !c.getCreateTime().isBefore(todayStart) && !c.getCreateTime().isAfter(todayEnd))
            .count();

        report.setNewDocsToday(newDocsToday);
        report.setNewChunksToday(newChunksToday);

        List<ReportResponse.GrowthDataPoint> docTrend = new ArrayList<>();
        List<ReportResponse.GrowthDataPoint> chunkTrend = new ArrayList<>();

        int docCount = 0;
        int chunkCount = 0;
        for (int i = 0; i <= ChronoUnit.DAYS.between(startDate, endDate); i++) {
            LocalDate date = startDate.plusDays(i);
            LocalDateTime dateEnd = date.atTime(LocalTime.MAX);

            int docsOnDate = (int) allDocs.stream()
                .filter(d -> d.getCreateTime() != null && !d.getCreateTime().isAfter(dateEnd))
                .count();

            int chunksOnDate = (int) allChunks.stream()
                .filter(c -> c.getCreateTime() != null && !c.getCreateTime().isAfter(dateEnd))
                .count();

            ReportResponse.GrowthDataPoint docPoint = new ReportResponse.GrowthDataPoint();
            docPoint.setDate(date);
            docPoint.setValue(docsOnDate);
            docTrend.add(docPoint);

            ReportResponse.GrowthDataPoint chunkPoint = new ReportResponse.GrowthDataPoint();
            chunkPoint.setDate(date);
            chunkPoint.setValue(chunksOnDate);
            chunkTrend.add(chunkPoint);
        }

        report.setDocCountTrend(docTrend);
        report.setChunkCountTrend(chunkTrend);

        return report;
    }

    @Override
    public ReportResponse.AgentPerformanceReport getAgentPerformance(ReportRequest request) {
        ReportResponse.AgentPerformanceReport report = new ReportResponse.AgentPerformanceReport();

        LocalDate endDate = request.getEndDate() != null ? request.getEndDate() : LocalDate.now();
        LocalDate startDate = request.getStartDate() != null ? request.getStartDate() : endDate.minusDays(30);

        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.atTime(LocalTime.MAX);

        List<AgentRun> allRuns = agentRunMapper.selectList(null);

        List<AgentRun> filteredRuns = allRuns.stream()
            .filter(r -> r.getStartTime() != null)
            .filter(r -> !r.getStartTime().isBefore(startDateTime) && !r.getStartTime().isAfter(endDateTime))
            .collect(Collectors.toList());

        int totalRuns = filteredRuns.size();
        int successCount = (int) filteredRuns.stream().filter(r -> "completed".equalsIgnoreCase(r.getStatus())).count();
        int failureCount = (int) filteredRuns.stream().filter(r -> "failed".equalsIgnoreCase(r.getStatus())).count();

        double successRate = totalRuns > 0 ? (double) successCount / totalRuns * 100 : 0;
        double failureRate = totalRuns > 0 ? (double) failureCount / totalRuns * 100 : 0;

        report.setTotalRuns(totalRuns);
        report.setSuccessCount(successCount);
        report.setFailureCount(failureCount);
        report.setSuccessRate(Math.round(successRate * 100.0) / 100.0);
        report.setFailureRate(Math.round(failureRate * 100.0) / 100.0);

        double avgDurationDouble = filteredRuns.stream()
            .filter(r -> r.getStartTime() != null && r.getEndTime() != null)
            .mapToLong(r -> ChronoUnit.MILLIS.between(r.getStartTime(), r.getEndTime()))
            .summaryStatistics()
            .getAverage();
        report.setAvgDurationMs(avgDurationDouble > 0 ? (int) avgDurationDouble : 0);

        List<ReportResponse.TrendDataPoint> successTrend = new ArrayList<>();
        List<ReportResponse.TrendDataPoint> failureTrend = new ArrayList<>();

        for (int i = 0; i <= ChronoUnit.DAYS.between(startDate, endDate); i++) {
            LocalDate date = startDate.plusDays(i);
            LocalDateTime dayStart = date.atStartOfDay();
            LocalDateTime dayEnd = date.atTime(LocalTime.MAX);

            List<AgentRun> dayRuns = filteredRuns.stream()
                .filter(r -> !r.getStartTime().isBefore(dayStart) && !r.getStartTime().isAfter(dayEnd))
                .collect(Collectors.toList());

            int dayTotal = dayRuns.size();
            int daySuccess = (int) dayRuns.stream().filter(r -> "completed".equalsIgnoreCase(r.getStatus())).count();
            int dayFailure = (int) dayRuns.stream().filter(r -> "failed".equalsIgnoreCase(r.getStatus())).count();

            ReportResponse.TrendDataPoint successPoint = new ReportResponse.TrendDataPoint();
            successPoint.setDate(date);
            successPoint.setValue(dayTotal > 0 ? Math.round((double) daySuccess / dayTotal * 100 * 100.0) / 100.0 : 0);
            successTrend.add(successPoint);

            ReportResponse.TrendDataPoint failurePoint = new ReportResponse.TrendDataPoint();
            failurePoint.setDate(date);
            failurePoint.setValue(dayTotal > 0 ? Math.round((double) dayFailure / dayTotal * 100 * 100.0) / 100.0 : 0);
            failureTrend.add(failurePoint);
        }

        report.setSuccessRateTrend(successTrend);
        report.setFailureRateTrend(failureTrend);

        return report;
    }

    @Override
    public ReportResponse.ToolFailureReport getToolFailures(ReportRequest request) {
        ReportResponse.ToolFailureReport report = new ReportResponse.ToolFailureReport();

        LocalDate endDate = request.getEndDate() != null ? request.getEndDate() : LocalDate.now();
        LocalDate startDate = request.getStartDate() != null ? request.getStartDate() : endDate.minusDays(30);
        Integer topN = request.getTopN() != null ? request.getTopN() : 10;

        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.atTime(LocalTime.MAX);

        List<ToolCall> allToolCalls = toolCallMapper.selectList(null);

        List<ToolCall> failedCalls = allToolCalls.stream()
            .filter(tc -> "failed".equalsIgnoreCase(tc.getStatus()))
            .filter(tc -> tc.getTimestamp() != null)
            .filter(tc -> !tc.getTimestamp().isBefore(startDateTime) && !tc.getTimestamp().isAfter(endDateTime))
            .collect(Collectors.toList());

        Map<String, List<ToolCall>> groupedByTool = failedCalls.stream()
            .collect(Collectors.groupingBy(tc -> tc.getToolName() != null ? tc.getToolName() : "unknown"));

        List<ReportResponse.ToolFailureItem> rankings = groupedByTool.entrySet().stream()
            .sorted((e1, e2) -> Integer.compare(e2.getValue().size(), e1.getValue().size()))
            .limit(topN)
            .map(entry -> {
                ReportResponse.ToolFailureItem item = new ReportResponse.ToolFailureItem();
                item.setToolName(entry.getKey());
                item.setFailureCount(entry.getValue().size());

                ToolCall lastFailure = entry.getValue().stream()
                    .max(Comparator.comparing(t -> t.getTimestamp() != null ? t.getTimestamp() : LocalDateTime.MIN))
                    .orElse(null);
                if (lastFailure != null) {
                    item.setLastFailureTime(lastFailure.getTimestamp());
                    item.setLastError(lastFailure.getErrorMessage());
                }

                int totalForTool = (int) allToolCalls.stream()
                    .filter(tc -> entry.getKey().equals(tc.getToolName()))
                    .count();
                double failureRate = totalForTool > 0 ? (double) entry.getValue().size() / totalForTool * 100 : 0;
                item.setFailureRate(Math.round(failureRate * 100.0) / 100.0);

                return item;
            })
            .collect(Collectors.toList());

        report.setRankings(rankings);
        report.setTotalFailures(failedCalls.size());

        if (!rankings.isEmpty()) {
            report.setMostFrequentFailure(rankings.get(0).getToolName());
        }

        return report;
    }
}
