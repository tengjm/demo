# Spring Cloud Demo — 全链路 CI/CD 实践项目

> 基于 Spring Cloud + Nacos 微服务，配合 GitLab + Jenkins + Harbor + Kubernetes + Helm 实现从代码提交到多环境部署的完整 DevOps 流水线。

## 项目亮点

- **微服务架构**：Spring Cloud + Nacos 服务注册发现 + OpenFeign 声明式远程调用
- **多分支流水线**：基于 Git Flow 的分支策略，自动映射 dev / test / prod 三套环境
- **云原生构建**：Kaniko 在 Kubernetes 集群内完成镜像构建，无需 Docker-in-Docker
- **Helm 包管理**：通过 Helm Chart 实现多环境配置分离与一键部署/回滚
- **完整探针体系**：startup / readiness / liveness 三类探针 + Helm `--atomic` 自动回滚
- **生产审批门控**：生产环境部署前需人工确认，防止误发布

---

## 架构总览

### 微服务调用架构

```
                    ┌─────────────────────┐
                    │   Nacos 注册中心      │
                    │   nacos:8848         │
                    └──────────┬──────────┘
                               │ 服务注册 / 发现
              ┌────────────────┼────────────────┐
              │                                 │
              ▼                                 ▼
    ┌──────────────────┐   OpenFeign    ┌──────────────────┐
    │   date-service   │◄──────────────│  hello-service   │
    │   端口: 8001     │   远程调用     │   端口: 8002     │
    │                  │                │                  │
    │  GET /api/date   │                │  GET /           │
    │  返回当前日期     │                │  返回渲染页面     │
    └──────────────────┘                └──────────────────┘
              │                                 │
              └─────────── K8s Namespace ───────┘
```

### CI/CD 全链路架构

```
┌──────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐    ┌────────────────────┐
│  开发者   │───▶│  GitLab   │───▶│ Jenkins │───▶│  Harbor  │───▶│  Kubernetes 集群   │
│  Push     │    │  仓库     │    │ Pipeline│    │ 镜像仓库  │    │  (dev/test/prod)   │
└──────────┘    └───────────┘    └─────────┘    └──────────┘    └────────────────────┘
                                       │                              │
                                       │  ┌──────────────┐            │
                                       ├─▶│  Maven 构建  │            │
                                       │  └──────────────┘            │
                                       │  ┌──────────────┐            │
                                       ├─▶│  Kaniko 打包 │────────────┘
                                       │  │  容器镜像     │  推送镜像 → 拉取部署
                                       │  └──────────────┘            │
                                       │  ┌──────────────┐            │
                                       └─▶│  Helm 部署   │────────────┘
                                          └──────────────┘
```

---

## 技术栈

| 层级 | 技术选型 | 版本 |
|---|---|---|
| **微服务** | Spring Boot | 2.3.12.RELEASE |
| **微服务** | Spring Cloud | Hoxton.SR12 |
| **注册中心** | Nacos | 2.x |
| **服务调用** | OpenFeign | Spring Cloud 内置 |
| **模板引擎** | Thymeleaf | Spring Boot 内置 |
| **CI/CD** | Jenkins (Multibranch Pipeline) | LTS |
| **代码托管** | GitLab | — |
| **镜像仓库** | Harbor | — |
| **容器构建** | Kaniko | v1.23.2 |
| **容器编排** | Kubernetes | — |
| **包管理** | Helm | 3.16.3 |
| **监控暴露** | Actuator + Prometheus | — |

---

## CI/CD 流水线详解

### Pipeline 阶段流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Jenkins Multibranch Pipeline                       │
│                                                                             │
│  GitLab Push/Branch/Tag 触发 → 自动 checkout 代码到 Jenkins Agent Pod      │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ 1. Resolve Env   │  根据分支名解析目标环境(dev/test/prod)、镜像Tag等     │
│  └────────┬────────┘                                                        │
│           ▼                                                                 │
│  ┌─────────────────┐                                                        │
│  │ 2. Maven Build   │  mvn clean package（含单元测试）                       │
│  └────────┬────────┘                                                        │
│           ▼                                                                 │
│  ┌─────────────────┐                                                        │
│  │ 3. Prepare Auth  │  配置 Kaniko 访问 Harbor 的认证信息                    │
│  └────────┬────────┘                                                        │
│           ▼                                                                 │
│  ┌─────────────────┐                                                        │
│  │ 4. Build Images  │  Kaniko 构建 date-service + hello-service 镜像并推送   │
│  └────────┬────────┘                                                        │
│           ▼                                                                 │
│  ┌─────────────────┐  仅 prod 环境触发                                      │
│  │ 5. Approval      │  人工审批门控(input step)                              │
│  └────────┬────────┘                                                        │
│           ▼                                                                 │
│  ┌─────────────────┐  helm upgrade --install --atomic --timeout 10m         │
│  │ 6. Helm Deploy   │  注入 Nacos 认证、镜像Tag等参数，部署到 K8s           │
│  └────────┬────────┘                                                        │
│           ▼                                                                 │
│  ┌─────────────────┐                                                        │
│  │ 7. Verify        │  kubectl rollout status + 业务冒烟测试(dev/test)     │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Git Flow 分支策略

```
                    Git Flow 合并路径

  feature/* ──────▶ develop ──────▶ release/* ──────▶ main ──────▶ tag v*
                        │                              │
                        │                              │
                     部署 dev                       部署 prod
                     (自动)                       (人工审批后)

  热修复路径:
  hotfix/* ──────────────────▶ release/* ──▶ main ──▶ tag v*
```

| 分支 / Tag | 部署环境 | Namespace | NodePort | 是否需要审批 |
|---|---|---|---:|---|
| `feature/*` / `dev` / `develop` | dev | `dev` | 30083 | 否 |
| `release/*` | test | `test` | 30081 | 否 |
| `main` / `v*` tag | prod | `prod` | 30082 | 是 |

### 镜像 Tag 规则

| 触发方式 | 镜像 Tag 示例 |
|---|---|
| dev 分支 | `dev-a1b2c3d4` |
| release/v1.2 分支 | `release-v1-2-a1b2c3d4` |
| main 分支 | `main-a1b2c3d4` |
| v1.0.0 tag | `v1.0.0` |

---

## 部署与回滚机制

### Helm 部署与自动回滚

```
helm upgrade --install spring-cloud-demo ./deploy/helm/spring-cloud-demo \
  -n $NAMESPACE \
  -f values-$ENV.yaml \
  --set global.imageRegistry=$HARBOR_REGISTRY \
  --set dateService.image.tag=$IMAGE_TAG \
  --set helloService.image.tag=$IMAGE_TAG \
  --atomic \          ← 部署失败自动回滚到上一版本
  --timeout 10m       ← 10 分钟内未就绪判定为失败
```

### 三层健康保障体系

```
┌────────────────────────────────────────────────────────────────────┐
│  第 1 层：Kubernetes 探针                                          │
│                                                                    │
│  startupProbe    → 应用启动是否完成（容忍 3 分钟慢启动）            │
│  readinessProbe  → 是否可以接收流量（决定 Pod Ready 状态）          │
│  livenessProbe   → 进程是否卡死（触发容器自动重启）                 │
│                                                                    │
│  探针端点:                                                          │
│  ├── /actuator/health/liveness   (startup + liveness)             │
│  └── /actuator/health/readiness   (readiness)                     │
├────────────────────────────────────────────────────────────────────┤
│  第 2 层：Helm --atomic                                            │
│                                                                    │
│  部署期间 Pod 未就绪 → 超时 → 自动回滚到上一个 Release Revision     │
├────────────────────────────────────────────────────────────────────┤
│  第 3 层：Verify 阶段                                               │
│                                                                    │
│  kubectl rollout status   → 等待滚动更新完成                       │
│  wget + grep "你好"        → 业务冒烟测试(dev/test)                 │
│  kubectl get pods -o wide → 留下排障现场快照                       │
└────────────────────────────────────────────────────────────────────┘
```

### 生产环境手动回滚

```bash
# 查看发布历史
helm history spring-cloud-demo -n prod

# 回滚到指定版本
helm rollback spring-cloud-demo <REVISION> -n prod --wait
```

---

## Helm Chart 结构

```
deploy/helm/spring-cloud-demo/
├── Chart.yaml              # Chart 元数据 (v2, appVersion: 1.0.0)
├── values.yaml             # 默认配置（基线）
├── values-dev.yaml          # dev 环境覆盖配置
├── values-test.yaml         # test 环境覆盖配置
├── values-prod.yaml         # prod 环境覆盖配置（含资源限制）
└── templates/
    ├── _helpers.tpl         # 自定义模板函数（镜像地址拼接、标签生成）
    ├── date-service-deployment.yaml   # Deployment + 探针 + 资源限制
    ├── date-service-service.yaml       # ClusterIP Service
    ├── hello-service-deployment.yaml   # Deployment + 探针 + 资源限制
    └── hello-service-service.yaml     # NodePort Service
```

### 关键配置：多环境差异化

| 配置项 | dev | test | prod |
|---|---|---|---|
| 副本数 | 1 | 1 | 1 |
| CPU 限制 | 无 | 无 | 500m - 1000m |
| 内存限制 | 无 | 无 | 512Mi - 1Gi |
| Nacos 命名空间 | dev | test | prod |
| 部署审批 | 否 | 否 | 是 |
| 冒烟测试 | 是 | 是 | 否（避免生产副作用） |

---

## 项目结构

```
spring-cloud-ex/
├── date-service/                  # 日期服务（服务提供者）
│   ├── src/main/java/.../controller/DateController.java
│   ├── src/main/resources/application.yml
│   ├── Dockerfile                 # 基于 eclipse-temurin:8-jre，非 root 运行
│   └── pom.xml
├── hello-service/                 # Hello 服务（服务消费者）
│   ├── src/main/java/.../
│   │   ├── controller/HelloController.java
│   │   └── feign/DateClient.java  # OpenFeign 声明式调用 date-service
│   ├── src/main/resources/
│   │   ├── templates/hello.html   # Thymeleaf 页面
│   │   └── application.yml
│   ├── Dockerfile
│   └── pom.xml
├── deploy/
│   ├── helm/spring-cloud-demo/    # Helm Chart（多环境 values）
│   └── k8s/                       # 原生 K8s YAML（备用）
├── docs/cicd/                     # 从零搭建 CI/CD 的完整文档
│   ├── from-zero/                 # 10 章保姆级教程
│   ├── git-flow.md                # 分支策略
│   └── jenkins-prerequisites.md   # Jenkins 前置条件
├── scripts/                       # 辅助脚本
├── Jenkinsfile                    # 多分支流水线定义
├── pom.xml                        # 父 POM（多模块管理）
└── README.md
```

---

## 服务说明

### date-service（服务提供者）

| 属性 | 值 |
|---|---|
| 端口 | 8001 |
| 接口 | `GET /api/date` |
| 返回 | 当前日期，格式 `yyyy年MM月dd日` |
| 注册名 | date-service |

### hello-service（服务消费者）

| 属性 | 值 |
|---|---|
| 端口 | 8002 |
| 接口 | `GET /` |
| 功能 | 通过 OpenFeign 调用 date-service 获取日期，渲染 Thymeleaf 页面 |
| 页面输出 | `xxxx年xx月xx日，你好` |

### 调用链路

```
用户浏览器
    │
    ▼  GET /
hello-service (Thymeleaf 渲染)
    │
    ▼  OpenFeign → GET /api/date
date-service (返回日期)
    │
    ▼
页面: "2026年08月23日，你好"
```