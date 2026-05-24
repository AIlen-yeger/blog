package com.personalblog.config;

import com.personalblog.entity.*;
import com.personalblog.mapper.*;
import com.personalblog.util.JsonUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 演示数据种子；默认关闭，避免每次启动向库中重复插入。
 * 首次需要演示账号/数据时：application.yml 设 app.seed.enabled=true 启动一次后改回 false。
 */
@Component
@ConditionalOnProperty(prefix = "app.seed", name = "enabled", havingValue = "true")
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserMapper userMapper;
    private final ProfileMapper profileMapper;
    private final TopicMapper topicMapper;
    private final NoteMapper noteMapper;
    private final LifeMapper lifeMapper;
    private final TimelineMapper timelineMapper;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        seedUsers();
        seedProfile();
        seedTopics();
        seedNotes();
        seedLife();
        seedTimeline();
    }

    private void seedUsers() {
        createUserIfAbsent("admin@qq.com", "admin123", UserRole.admin);
        createUserIfAbsent("reader@qq.com", "reader123", UserRole.user);
    }

    private void createUserIfAbsent(String email, String rawPassword, UserRole role) {
        if (userMapper.countByEmail(email) > 0) {
            return;
        }
        UserEntity user = new UserEntity();
        user.setEmail(email);
        user.setPasswordHash(passwordEncoder.encode(rawPassword));
        user.setRole(role);
        userMapper.insert(user);
    }

    private void seedProfile() {
        if (profileMapper.selectById(1L) != null) {
            return;
        }
        ProfileEntity profile = new ProfileEntity();
        profile.setId(1L);
        profile.setName("奥利奥");
        profile.setSubtitle("Personal Learning Blog");
        profile.setBio("记录前端、工程化与日常学习心得。把零散的知识点整理成可回顾的笔记与专题，方便日后查阅与复盘。");
        profile.setFocusJson(JsonUtil.toJson(List.of(
                "Vue / TypeScript", "工程化", "CSS 与动效", "读书笔记")));
        profile.setAvatarUrl("https://api.dicebear.com/7.x/avataaars/svg?seed=personal-blog");
        profileMapper.insert(profile);
    }

    private void seedTopics() {
        saveTopic("t1", "前端基础巩固",
                "HTML 语义化、CSS 布局、JS 异步与浏览器原理的专题索引。", "2025-04-01");
        saveTopic("t2", "Vue 生态深入",
                "组件设计、状态管理、路由与性能优化的系列学习路线。", "2025-04-18");
        saveTopic("t3", "学习方法与复盘",
                "如何记录学习过程、做周复盘，把输入转化为可输出的笔记。", "2025-05-01");
    }

    private void saveTopic(String id, String title, String excerpt, String date) {
        if (topicMapper.countById(id) > 0) {
            return;
        }
        TopicEntity topic = new TopicEntity();
        topic.setId(id);
        topic.setTitle(title);
        topic.setExcerpt(excerpt);
        topic.setTag("专题");
        topic.setDate(date);
        topicMapper.insert(topic);
    }

    private void seedNotes() {
        saveNote("n1", "Vue 3 组合式 API 学习笔记",
                "ref、computed、watch 与生命周期在组件拆分中的实践总结。",
                "前端", "t2", "2025-05-10", "## 核心 API\n\n- **ref / reactive**");
        saveNote("n2", "Vite 构建与路径别名",
                "从项目初始化到 alias、环境变量的配置流程。",
                "工程化", "t3", "2025-05-15", "## 项目初始化\n\n```bash\nnpm create vite@latest");
        saveNote("n3", "CSS 滚动与分栏布局",
                "固定侧栏 + 主内容区纵向滚动的实现思路。",
                "布局", "t1", "2025-05-20", "## 布局结构\n\n左侧 position: fixed");
        saveNote("n4", "TypeScript 类型收窄",
                "typeof、in、判别联合在业务代码里的用法。",
                "TypeScript", "t2", "2025-05-21", "## 类型收窄方式\n\n- typeof");
    }

    private void saveNote(String id, String title, String excerpt, String tag,
                          String topicId, String date, String content) {
        if (noteMapper.countById(id) > 0) {
            return;
        }
        NoteEntity note = new NoteEntity();
        note.setId(id);
        note.setTitle(title);
        note.setExcerpt(excerpt);
        note.setTag(tag);
        note.setTopicId(topicId);
        note.setContent(content);
        note.setDate(date);
        noteMapper.insert(note);
    }

    private void seedLife() {
        saveLife("l1", "五月观影清单", "记录本月看过的电影与简短观感。",
                "生活", "2025-05-08", "《星际穿越》重看——配乐依然震撼。");
        saveLife("l2", "厨房实验：戚风蛋糕", "第一次尝试烘焙，记录配方与失败原因。",
                "美食", "2025-05-12", "蛋白打发不够，蛋糕塌陷。");
        saveLife("l3", "周末散步路线", "家附近公园的固定环线，适合放空。",
                "户外", "2025-05-18", "南门进 → 湖边栈道 → 梧桐大道。");
    }

    private void saveLife(String id, String title, String excerpt, String tag, String date, String content) {
        if (lifeMapper.countById(id) > 0) {
            return;
        }
        LifeEntity life = new LifeEntity();
        life.setId(id);
        life.setTitle(title);
        life.setExcerpt(excerpt);
        life.setTag(tag);
        life.setContent(content);
        life.setDate(date);
        lifeMapper.insert(life);
    }

    private void seedTimeline() {
        saveTimeline("tl1", "2025 Q1", "Vue 3 系统学习", "完成官方文档精读与小项目实战。");
        saveTimeline("tl2", "2025 Q2", "个人博客搭建", "实现登录、分栏布局与学习笔记展示。");
        saveTimeline("tl3", "进行中", "工程化深化", "TypeScript 严格模式、CI 与部署流程。");
    }

    private void saveTimeline(String id, String period, String title, String desc) {
        if (timelineMapper.countById(id) > 0) {
            return;
        }
        TimelineEntity item = new TimelineEntity();
        item.setId(id);
        item.setPeriod(period);
        item.setTitle(title);
        item.setDesc(desc);
        timelineMapper.insert(item);
    }
}
