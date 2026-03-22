# 淘宝营销分析系统 (Taobao Marketing Analytics)

专业的淘宝电商营销数据分析与投放优化工具系统。

## 功能模块

### 1. 人群分析 (Crowd Analysis)
- 消费者画像分析（年龄、性别、地域、消费层级）
- 人群标签管理与自定义人群包
- AIPL人群流转分析（认知-兴趣-购买-忠诚）
- 人群价值评估与潜客挖掘

### 2. 收藏加购分析 (Favorites & Cart Analysis)
- 收藏/加购趋势追踪
- 收藏加购转化漏斗
- 商品维度收藏加购排行
- 收藏加购人群画像交叉分析

### 3. 广告投放计划 (Ad Campaign Planning)
- 直通车/引力魔方/万相台投放计划管理
- 关键词出价策略建议
- 预算分配优化
- 投放时段与地域策略

### 4. ROI 优化 (ROI Optimization)
- 多维度ROI追踪（计划/单元/关键词/人群）
- 转化归因分析
- 智能出价建议
- 投产比预测模型

## 技术栈

- **后端**: Python 3.10+
- **数据处理**: pandas, numpy
- **可视化**: matplotlib, plotly
- **报表**: 终端表格 + HTML报告

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

## 项目结构

```
├── main.py                    # 主入口
├── config.py                  # 系统配置
├── requirements.txt           # 依赖
├── models/                    # 数据模型
│   ├── crowd.py              # 人群模型
│   ├── product.py            # 商品模型
│   └── campaign.py           # 投放计划模型
├── analyzers/                 # 分析引擎
│   ├── crowd_analyzer.py     # 人群分析
│   ├── cart_fav_analyzer.py  # 收藏加购分析
│   ├── campaign_analyzer.py  # 投放分析
│   └── roi_optimizer.py      # ROI优化
├── dashboard/                 # 数据面板
│   └── reporter.py           # 报表生成
├── data/                      # 示例数据
│   └── sample_generator.py   # 模拟数据生成
└── utils/                     # 工具函数
    └── helpers.py            # 通用工具
```
