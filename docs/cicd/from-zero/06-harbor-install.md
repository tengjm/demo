# 6-Harbor HTTP 镜像仓库部署

官方文档：https://goharbor.io/docs/2.14.0/install-config/

Harbor 官方支持在线安装包和离线安装包。生产部署建议使用离线安装包，部署更稳定、可重复。Harbor 官方安装包会根据 `harbor.yml` 自动生成并使用 Docker Compose 文件，因此 Harbor 的官方推荐安装流程本质上也是 Docker Compose 部署。

## 6-1. 部署规划

| 配置项 | 示例值 |
|---|---|
| 服务器 IP | `10.1.106.200` |
| HTTP 端口 | `8088` |
| Harbor 版本 | `v2.14.1` |
| 安装目录 | `/app/harbor/installer` |
| 数据目录 | `/app/harbor/data` |
| 管理员账号 | `admin` |
| 管理员密码 | `Harbor@123456` |

## 6-2. 下载 Harbor 安装包

到 GitHub Release 页面选择版本：

```text
https://github.com/goharbor/harbor/releases
```

示例：

```bash
mkdir -p /app/harbor
cd /app/harbor
wget https://github.com/goharbor/harbor/releases/download/v2.14.1/harbor-offline-installer-v2.14.1.tgz
tar -zxvf harbor-offline-installer-v2.14.1.tgz
mv harbor installer
cd /app/harbor/installer
```

如果服务器不能访问 GitHub，可以先在本地下载后上传到服务器。

## 6-3. 编写 harbor.yml

```bash
cp harbor.yml.tmpl harbor.yml
vim harbor.yml
```

核心配置如下：

```yaml
hostname: 10.1.106.200

http:
  port: 8088

# 如果当前案例暂不配置 https，注释 https 整段配置
# https:
#   port: 443
#   certificate: /your/certificate/path
#   private_key: /your/private/key/path

harbor_admin_password: Harbor@123456

data_volume: /app/harbor/data
```

注意：

- 使用 HTTP 时必须注释 `https:` 整段。
- 生产部署建议配置 HTTPS；如果当前阶段使用 HTTP，必须配置 Docker/containerd 不安全仓库并限制网络访问范围。
- 密码必须满足复杂度要求。

## 6-4. 安装 Harbor

```bash
cd /app/harbor/installer
./install.sh
```

`./install.sh` 会执行准备工作并生成 Docker Compose 配置，常见文件包括：

```text
/app/harbor/installer/docker-compose.yml
/app/harbor/installer/common/config/
```

后续启动、停止、查看状态都在该目录使用 Docker Compose：

```bash
cd /app/harbor/installer
docker compose ps
docker compose stop
docker compose start
docker compose restart
```

安装完成后验证：

```bash
docker compose ps
docker ps | grep harbor
```

浏览器访问：

```text
http://10.1.106.200:8088
```

登录：

```text
账号：admin
密码：Harbor@123456
```

## 6-5. 创建项目

在 Harbor 页面创建两个项目：

| 项目名 | 访问级别 | 用途 |
|---|---|---|
| `devops-demo` | 私有 | 保存业务镜像 |
| `ci-tools` | 私有或公开 | 保存 Jenkins Agent 使用的工具镜像 |

## 6-6. Docker 客户端登录 HTTP Harbor

所有需要 `docker login`、`docker pull`、`docker push` 的机器都需要配置 Docker 不安全仓库，见 `03-docker-and-compose.md`。

登录验证：

```bash
docker login 10.1.106.200:8088 -u admin -p 'Harbor@123456'
```

## 6-7. Kubernetes 节点拉取 HTTP Harbor

Kubernetes 使用 containerd 拉镜像，必须按 `04-kubernetes-install.md` 配置：

```text
/etc/containerd/certs.d/10.1.106.200:8088/hosts.toml
```

否则 Pod 可能报错：

```text
http: server gave HTTP response to HTTPS client
```

## 6-8. 准备 CI 工具镜像

Jenkinsfile 中的动态 Agent Pod 会用到这些官方或发布方镜像。建议先拉取官方镜像，再重新打 tag 推送到 Harbor 的 `ci-tools` 项目。

| 用途 | 官方/发布方镜像 | 推送到 Harbor 后的镜像 |
|---|---|---|
| Maven 构建 | `maven:3.9.9-eclipse-temurin-8` | `10.1.106.200:8088/ci-tools/maven:3.9.9-eclipse-temurin-8` |
| Java 运行时基础镜像 | `eclipse-temurin:8-jre` | `10.1.106.200:8088/ci-tools/eclipse-temurin:8-jre` |
| Jenkins inbound agent | `jenkins/inbound-agent:3355.v388858a_47b_33-3-jdk21` | `10.1.106.200:8088/ci-tools/jenkins-inbound-agent:3355.v388858a_47b_33-3-jdk21` |
| Kaniko 构建镜像 | `gcr.io/kaniko-project/executor:v1.23.2-debug` | `10.1.106.200:8088/ci-tools/kaniko-executor:v1.23.2-debug` |
| Helm + kubectl 工具 | `dtzar/helm-kubectl:3.16` | `10.1.106.200:8088/ci-tools/helm-kubectl:3.16.3` |

登录 Harbor：

```bash
docker login 10.1.106.200:8088 -u admin -p 'Harbor@123456'
```

同步 Maven 镜像：

```bash
docker pull maven:3.9.9-eclipse-temurin-8
docker tag maven:3.9.9-eclipse-temurin-8 10.1.106.200:8088/ci-tools/maven:3.9.9-eclipse-temurin-8
docker push 10.1.106.200:8088/ci-tools/maven:3.9.9-eclipse-temurin-8
```

同步 Java 运行时基础镜像：

```bash
docker pull eclipse-temurin:8-jre
docker tag eclipse-temurin:8-jre 10.1.106.200:8088/ci-tools/eclipse-temurin:8-jre
docker push 10.1.106.200:8088/ci-tools/eclipse-temurin:8-jre
```

同步 Jenkins inbound agent 镜像：

```bash
docker pull jenkins/inbound-agent:3355.v388858a_47b_33-3-jdk21
docker tag jenkins/inbound-agent:3355.v388858a_47b_33-3-jdk21 10.1.106.200:8088/ci-tools/jenkins-inbound-agent:3355.v388858a_47b_33-3-jdk21
docker push 10.1.106.200:8088/ci-tools/jenkins-inbound-agent:3355.v388858a_47b_33-3-jdk21
```

同步 Kaniko 镜像：

```bash
docker pull gcr.io/kaniko-project/executor:v1.23.2-debug
docker tag gcr.io/kaniko-project/executor:v1.23.2-debug 10.1.106.200:8088/ci-tools/kaniko-executor:v1.23.2-debug
docker push 10.1.106.200:8088/ci-tools/kaniko-executor:v1.23.2-debug
```

同步 Helm + kubectl 工具镜像：

```bash
docker pull dtzar/helm-kubectl:3.16
docker tag dtzar/helm-kubectl:3.16 10.1.106.200:8088/ci-tools/helm-kubectl:3.16.3
docker push 10.1.106.200:8088/ci-tools/helm-kubectl:3.16.3
```

若无法访问 `gcr.io` 或 Docker Hub，可以使用企业已有镜像代理，或在有网机器拉取后通过 `docker save` / `docker load` 手动导入。

不要使用 `eclipse-temurin:8-jre-alpine` 作为当前项目基础镜像，当前 Dockerfile 使用了 Debian/Ubuntu 风格的 `groupadd`、`useradd` 命令。

---

> 微信: wingsreops
