package com.demo.aiknowledge.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class LibraryInspectionResponse {
    private LibraryInspectionStats stats;
    private List<DuplicateDocGroup> duplicateDocs;
    private List<LowQualityChunk> lowQualityChunks;
    private List<OutdatedDoc> outdatedDocs;
    private List<UnaccessedDoc> unaccessedDocs;
    private List<InspectionExport> exportData;

    @Data
    public static class LibraryInspectionStats {
        private Integer totalDocs;
        private Integer totalChunks;
        private Integer duplicateDocGroups;
        private Integer duplicateDocCount;
        private Integer lowQualityChunkCount;
        private Integer outdatedDocCount;
        private Integer unaccessedDocCount;
        private LocalDateTime lastInspectionTime;
    }

    @Data
    public static class DuplicateDocGroup {
        private Long groupId;
        private List<DuplicateDoc> documents;
        private Double similarity;
        private String reason;
    }

    @Data
    public static class DuplicateDoc {
        private Long id;
        private String docName;
        private Long categoryId;
        private String categoryName;
        private LocalDateTime createTime;
    }

    @Data
    public static class LowQualityChunk {
        private Long id;
        private Long docId;
        private String docName;
        private String chunkText;
        private Integer chunkIndex;
        private String issueType;
        private String issueDescription;
    }

    @Data
    public static class OutdatedDoc {
        private Long id;
        private String docName;
        private String categoryName;
        private LocalDateTime createTime;
        private LocalDateTime updateTime;
        private Integer daySinceUpdate;
    }

    @Data
    public static class UnaccessedDoc {
        private Long id;
        private String docName;
        private String categoryName;
        private LocalDateTime createTime;
        private LocalDateTime lastAccessTime;
        private Integer accessCount;
        private Integer daySinceAccess;
    }

    @Data
    public static class InspectionExport {
        private String type;
        private String name;
        private String issue;
        private String detail;
    }
}
