export type ContentPublishStatus = 'published' | 'draft'

export interface NoteItem {
  id: string
  title: string
  excerpt: string
  tag: string
  date: string
  topicId: string
  content: string
  /** 配图 URL 列表，最多 12 张 */
  images?: string[]
  /** 去重后的浏览次数 */
  viewCount?: number
  /** 是否置顶（全局仅一篇） */
  pinned?: boolean
  status?: ContentPublishStatus
  /** 为 true 时仅管理员可见 */
  ownerOnly?: boolean
  /** 蕾西亚根据正文生成的回复（后端字段 agentReply） */
  agentReply?: string | null
  /** none | pending | running | done | failed */
  agentReplyStatus?: string | null
}

export interface TopicItem {
  id: string
  title: string
  excerpt: string
  tag: string
  date: string
  noteCount?: number
}

export interface TimelineItem {
  id: string
  period: string
  title: string
  desc: string
}

export interface LifeItem {
  id: string
  title: string
  excerpt: string
  tag: string
  date: string
  content: string
  images?: string[]
  /** 去重后的浏览次数 */
  viewCount?: number
  /** 是否置顶（生活记录全局仅一篇） */
  pinned?: boolean
  status?: ContentPublishStatus
  /** 为 true 时仅管理员可见 */
  ownerOnly?: boolean
  /** 蕾西亚根据正文生成的回复（后端字段 agentReply） */
  agentReply?: string | null
}

export interface TagCountItem {
  tag: string
  count: number
}

export interface ArchiveMonthItem {
  month: string
  count: number
}

export interface SearchResult {
  notes: NoteItem[]
  life: LifeItem[]
  noteTotal: number
  lifeTotal: number
}

import { defaultAvatarUrl } from '@/utils/defaultAvatar'

export interface ProfileData {
  /** 资料所属用户 id（后端返回，便于后续多用户扩展） */
  userId?: number
  name: string
  subtitle: string
  bio: string
  focus: string[]
  avatarUrl: string
  /** 是否为站点公开展示的主人资料 */
  siteOwner?: boolean
}

export const defaultProfile: ProfileData = {
  name: '默认数据',
  subtitle: 'Personal Learning Blog',
  bio: '记录前端、工程化与日常学习心得。把零散的知识点整理成可回顾的笔记与专题，方便日后查阅与复盘。',
  focus: ['Vue / TypeScript', '工程化', 'CSS 与动效', '读书笔记'],
  avatarUrl: defaultAvatarUrl(),
}

export const mockTopics: TopicItem[] = [
  {
    id: 't1',
    title: '前端基础巩固',
    excerpt: 'HTML 语义化、CSS 布局、JS 异步与浏览器原理的专题索引。',
    tag: '专题',
    date: '2025-04-01',
  },
  {
    id: 't2',
    title: 'Vue 生态深入',
    excerpt: '组件设计、状态管理、路由与性能优化的系列学习路线。',
    tag: '专题',
    date: '2025-04-18',
  },
  {
    id: 't3',
    title: '学习方法与复盘',
    excerpt: '如何记录学习过程、做周复盘，把输入转化为可输出的笔记。',
    tag: '专题',
    date: '2025-05-01',
  },
]

export const mockNotes: NoteItem[] = [
  {
    id: 'n1',
    title: 'Vue 3 组合式 API 学习笔记',
    excerpt: 'ref、computed、watch 与生命周期在组件拆分中的实践总结。',
    tag: '前端',
    date: '2025-05-10',
    topicId: 't2',
    content: `## 核心 API

- **ref / reactive**：基本响应式状态
- **computed**：派生状态，带缓存
- **watch / watchEffect**：副作用与依赖收集

## 实践要点

组合式函数（composables）适合抽离可复用逻辑。注意 \`ref\` 在模板中自动解包，在 script 中需 \`.value\`。

## 常见踩坑

1. 解构 reactive 对象会丢失响应式，可用 \`toRefs\`
2. \`watch\` 监听 ref 时直接传 ref 即可
3. 生命周期钩子需在 \`setup\` 同步调用`,
  },
  {
    id: 'n2',
    title: 'Vite 构建与路径别名',
    excerpt: '从项目初始化到 alias、环境变量的配置流程。',
    tag: '工程化',
    date: '2025-05-15',
    topicId: 't3',
    content: `## 项目初始化

\`\`\`bash
npm create vite@latest my-app -- --template vue-ts
\`\`\`

## 路径别名

在 \`vite.config.ts\` 中配置 \`resolve.alias\`，配合 \`tsconfig\` 的 \`paths\` 字段。

## 环境变量

使用 \`.env\`、\`.env.development\`，变量需以 \`VITE_\` 前缀暴露给客户端。`,
  },
  {
    id: 'n3',
    title: 'CSS 滚动与分栏布局',
    excerpt: '固定侧栏 + 主内容区纵向滚动的实现思路。',
    tag: '布局',
    date: '2025-05-20',
    topicId: 't1',
    content: `## 布局结构

左侧 \`position: fixed\` 导航，右侧 \`margin-left\` 留出宽度，主区域 \`overflow-y: auto\`。

## 区块滚动

各 section 设置 \`scroll-margin-top\`，配合 \`scrollIntoView\` 实现侧栏锚点跳转。

## 参考

信息站风格：大卡片分块 + 整页纵向阅读节奏。`,
  },
  {
    id: 'n4',
    title: 'TypeScript 类型收窄',
    excerpt: 'typeof、in、判别联合在业务代码里的用法。',
    tag: 'TypeScript',
    date: '2025-05-21',
    topicId: 't2',
    content: `## 类型收窄方式

- \`typeof\`、\`instanceof\`
- \`in\` 操作符
- 判别联合（tag 字段）

## 收益

减少 \`as\` 断言，让编译器在分支内推断更窄的类型，降低运行时错误。`,
  },
]

export const mockLife: LifeItem[] = [
  {
    id: 'l1',
    title: '五月观影清单',
    excerpt: '记录本月看过的电影与简短观感。',
    tag: '生活',
    date: '2025-05-08',
    content: '《星际穿越》重看——配乐依然震撼。周末打算补《你想活出怎样的人生》。',
  },
  {
    id: 'l2',
    title: '厨房实验：戚风蛋糕',
    excerpt: '第一次尝试烘焙，记录配方与失败原因。',
    tag: '美食',
    date: '2025-05-12',
    content: '蛋白打发不够，蛋糕塌陷。下次降低烤箱温度、延长烘烤时间，模具不要刷油。',
  },
  {
    id: 'l3',
    title: '周末散步路线',
    excerpt: '家附近公园的固定环线，适合放空。',
    tag: '户外',
    date: '2025-05-18',
    content: '南门进 → 湖边栈道 → 梧桐大道 → 约 40 分钟。傍晚光线最好，记得带水。',
  },
]

export const mockTimeline: TimelineItem[] = [
  {
    id: 'tl1',
    period: '2025 Q1',
    title: 'Vue 3 系统学习',
    desc: '完成官方文档精读与小项目实战。',
  },
  {
    id: 'tl2',
    period: '2025 Q2',
    title: '个人博客搭建',
    desc: '实现登录、分栏布局与学习笔记展示。',
  },
  {
    id: 'tl3',
    period: '进行中',
    title: '工程化深化',
    desc: 'TypeScript 严格模式、CI 与部署流程。',
  },
]

export const navSections = [
  { id: 'about', label: '关于', en: 'ABOUT' },
  { id: 'notes', label: '学习笔记', en: 'NOTES' },
  { id: 'life', label: '生活记录', en: 'LIFE' },
  { id: 'timeline', label: '学习轨迹', en: 'TIMELINE' },
] as const

export type SectionId = (typeof navSections)[number]['id']

