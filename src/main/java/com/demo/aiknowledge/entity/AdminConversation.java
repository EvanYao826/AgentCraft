package com.demo.aiknowledge.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("admin_conversation")
public class AdminConversation {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long adminId;
    private String title;
    private Boolean isPinned;
    private LocalDateTime createTime;
}