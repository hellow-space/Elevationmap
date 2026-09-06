# AGENTS.md


## 项目目标

当前项目只研究：

Elevation Map
→ 2.5D terrain geometric features
→ traversability / terrain cost
→ MPPI local planning

目标场景：
1. 普通障碍物
2. 斜坡
3. 楼梯

当前阶段不要扩展到完整 3D planner、全局规划、拓扑规划或学习式 traversability。

## 当前环境

ROS 2 Humble。

已有主要模块：
- elevation_mapping_cupy
- elevation_nav2_bridge
- terrain_test


开始任何任务前，先阅读：
1. PROJECT_STATUS.md
2. EXPERIENCES.md 中与当前任务相关的条目
3. 当前任务涉及 package 的源码、配置和 README
4. 当前相关 package 的 README / launch / config

不要根据包名猜实现，必须读源码确认。

## 工作规则

修改代码前：
1. 先定位当前数据流和相关源码。
2. 说明准备修改什么以及为什么。
3. 尽量最小修改，不做无关重构。

修改代码后：
1. build。
2. 运行对应测试。
3. 实际查看 topic / GridMap layer / RViz 或日志结果。
4. 未实际运行的测试不得写成“已通过”。

## 当前研究原则

Elevation Map 的几何特征优先使用确定性几何算法。

重点检查：
- elevation
- slope
- roughness
- step / height difference
- surface normal
- variance

不要因为代码使用 CuPy / CUDA 就认为它属于神经网络。

当前阶段不要自行引入新的神经网络。

## MPPI 原则

当前不要直接修改 MPPI。

先验证：
Elevation Map 的几何指标能否有效区分：
- 平地
- 斜坡
- 楼梯
- 普通障碍物
- 粗糙地面

在这些指标验证完成之前，不实现 terrain critic。

最终目标接口是：

terrain evaluator:
    input: (x, y, yaw) + elevation map
    output: feasible + terrain_cost

然后才接入 MPPI rollout evaluation。

## 禁止事项

- 不替换现有导航框架
- 不重写 elevation_mapping_cupy
- 不自行更换 ROS 版本
- 不引入无关 package
- 不为了“看起来能跑”而使用假数据
- 不在未验证几何特征之前开始调 MPPI
- 不把未运行的实验描述成成功

## EXPERIENCES.md 更新规则

`EXPERIENCES.md` 用于记录可复用的工程经验、失败教训、调试结论和已验证的实现规律。

它不是任务日志，也不是 PROJECT_STATUS.md 的替代品。

### 什么时候必须更新

完成任务后，如果出现以下任意情况，必须更新 `EXPERIENCES.md`：

1. 发现了一个以后很可能再次遇到的问题。
2. 找到了一个不明显但有效的解决方法。
3. 某种实现方案实际验证失败，并且失败原因具有复用价值。
4. 某个参数、配置、TF、topic、frame、launch 或依赖存在容易踩坑的约束。
5. 发现源码行为与文档、预期或包名含义不同。
6. 经过实际测试确认了一条重要技术结论。
7. 找到明显提高调试、编译、测试或运行效率的方法。
8. 修复了一个花费较长时间定位的问题。

### 什么时候不要更新

以下内容不要写入 `EXPERIENCES.md`：

- 普通文件修改记录
- 单次任务进度
- 尚未验证的猜测
- 临时 debug 输出
- 很快会失效的中间状态
- PROJECT_STATUS.md 已经足够记录的内容
- 仅对一次性实验有效的细节

这些内容应写入 `PROJECT_STATUS.md`，而不是 `EXPERIENCES.md`。

### 更新时机

任务开始前：

1. 阅读与当前任务相关的 `EXPERIENCES.md` 条目。
2. 避免重复已经验证失败的方法。
3. 优先复用已经验证有效的解决方案。

任务完成后：

1. 判断本次工作是否产生了可复用经验。
2. 如果有，更新 `EXPERIENCES.md`。
3. 如果没有，不要为了形式而添加内容。

### 每条经验的格式

每条经验尽量使用：

## [简短标题]

**日期：** YYYY-MM-DD
**相关模块：** package / node / subsystem

**现象：**
发生了什么。

**原因：**
最终确认的原因是什么。

**解决方法：**
实际有效的解决方式。

**验证：**
使用什么命令、测试或现象确认解决有效。

**适用范围：**
这个经验在哪些情况下适用。

**避免：**
以后不要重复做什么。

### 重要规则

- 只记录经过实际验证的结论。
- 如果只是推测，必须明确标记为“未验证”，原则上不要加入长期经验库。
- 如果已有条目描述同一问题，优先更新原条目，不重复新增。
- 如果后续实验推翻旧结论，必须修改旧条目，并注明原结论已失效。
- 保持条目简短，优先记录“原因 + 解决方法 + 验证方式”。
## 状态记录

每完成一个实际阶段，更新 PROJECT_STATUS.md：

- 修改文件
- 做了什么
- 实际运行命令
- 实际结果
- 当前问题
- 下一步
