# 7-Jenkins 部署与 Kubernetes 动态 Agent 配置

官方文档：

- Jenkins Docker 安装：https://www.jenkins.io/doc/book/installing/docker/
- Jenkins Kubernetes 插件：https://plugins.jenkins.io/kubernetes/

本章主线使用 Docker Compose 部署 Jenkins Controller，方便持久化 `/var/jenkins_home`、维护端口映射和后续升级。

## 7-1. 部署规划

| 配置项 | 示例值 |
|---|---|
| 服务器 IP | `10.1.106.201` |
| Jenkins Web | `8080` |
| Agent 端口 | `50000` |
| 镜像 | `jenkins/jenkins:2.541.2-lts-jdk21` |
| 数据目录 | `/app/jenkins/home` |
| 管理员账号 | `admin` |
| 管理员密码 | `Jenkins@123456` |

## 7-2. 创建目录

```bash
mkdir -p /app/jenkins/home /app/jenkins/ref
chown -R 1000:1000 /app/jenkins/home /app/jenkins/ref
cd /app/jenkins
```

## 7-3. 编写 docker-compose.yml

```bash
cat > /app/jenkins/docker-compose.yml <<'EOF_COMPOSE'
services:
  jenkins:
    image: jenkins/jenkins:2.541.2-lts-jdk21
    container_name: jenkins
    restart: unless-stopped
    user: "0:0"
    ports:
      - "8080:8080"
      - "50000:50000"
    environment:
      TZ: Asia/Shanghai
      JAVA_OPTS: >-
        -Duser.timezone=Asia/Shanghai
      JENKINS_OPTS: --httpPort=8080
    volumes:
      - /app/jenkins/home:/var/jenkins_home
      - /app/jenkins/ref:/usr/share/jenkins/ref
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker:ro
EOF_COMPOSE
```

说明：

- 本实践主线使用 Kubernetes 动态 Agent + Kaniko 构建镜像，Jenkins Controller 不直接执行 `docker build`。
- `/var/run/docker.sock` 和 `/usr/bin/docker` 挂载是为了后续排查或扩展 Docker 类型任务，可按需保留。
- 如果你的系统 Docker 命令路径不是 `/usr/bin/docker`，先执行 `which docker`，并把 Compose 中的路径改成实际路径；不需要 Docker 任务时也可以删除这两行挂载。

启动：

```bash
cd /app/jenkins
docker compose up -d
```

查看日志：

```bash
docker logs -f jenkins
```

访问：

```text
http://10.1.106.201:8080
```

## 7-4. 初始化管理员账号

首次访问 Jenkins 时，按官方初始化向导完成管理员创建。先查看初始解锁密码：

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

页面解锁后选择安装推荐插件或跳过插件安装；本实践需要的插件在 `7-5` 单独安装。

建议创建：

```text
账号：admin
密码：Jenkins@123456
```

## 7-5. 安装插件

进入：`Manage Jenkins` -> `Plugins`，安装：

### 7-5-1. 本实践必需插件

| 插件 ID | 页面名称 | 用途 |
|---|---|---|
| `workflow-aggregator` | Pipeline | Jenkins Pipeline 基础能力 |
| `workflow-multibranch` | Pipeline: Multibranch | 多分支流水线，扫描 GitLab 分支 |
| `pipeline-model-definition` | Pipeline: Declarative | 支持声明式 `Jenkinsfile` |
| `git` | Git | 拉取 Git 仓库 |
| `git-client` | Git client | Git 插件底层客户端 |
| `gitlab-plugin` | GitLab | GitLab 集成、Webhook、构建状态 |
| `gitlab-branch-source` | GitLab Branch Source | GitLab 多分支/分支源能力，可选但推荐 |
| `credentials` | Credentials | Jenkins 凭据管理 |
| `credentials-binding` | Credentials Binding | `withCredentials` 在流水线中读取账号密码 |
| `plain-credentials` | Plain Credentials | Secret file 等凭据类型支持 |
| `ssh-credentials` | SSH Credentials | SSH 密钥凭据支持，当前实践使用 HTTP 拉 Git，可不依赖 |
| `ssh-agent` | SSH Agent | SSH Agent 凭据注入，当前实践使用 HTTP 拉 Git，可不依赖 |
| `kubernetes` | Kubernetes | 创建 Kubernetes 动态 Agent Pod |
| `kubernetes-credentials` | Kubernetes Credentials | Kubernetes kubeconfig 凭据支持 |
| `docker-workflow` | Docker Pipeline | Docker Pipeline 步骤支持，可选但推荐 |
| `docker-commons` | Docker Commons | Docker 相关插件基础依赖 |
| `timestamper` | Timestamper | 控制台日志显示时间戳 |
| `ws-cleanup` | Workspace Cleanup | 清理工作空间，可选 |
| `ansicolor` | ANSI Color | 彩色日志，可选 |

### 7-5-2. 当前参考服务器已安装的插件

参考环境 Jenkins 已安装的关键插件包括：

```text
ansicolor
build-timeout
cloudbees-folder
configuration-as-code
credentials
credentials-binding
docker-commons
docker-workflow
git
git-client
gitlab-api
gitlab-branch-source
gitlab-plugin
job-dsl
junit
kubernetes
kubernetes-client-api
kubernetes-credentials
matrix-auth
pipeline-build-step
pipeline-groovy-lib
pipeline-input-step
pipeline-model-definition
pipeline-stage-view
plain-credentials
publish-over-ssh
role-strategy
ssh-agent
ssh-credentials
timestamper
workflow-aggregator
workflow-api
workflow-basic-steps
workflow-cps
workflow-durable-task-step
workflow-job
workflow-multibranch
workflow-scm-step
workflow-step-api
workflow-support
ws-cleanup
```

你不需要手工逐个安装所有依赖插件。Jenkins 插件管理器或 `jenkins-plugin-cli` 会根据插件依赖自动下载依赖。

本文档已从参考 Jenkins 环境导出一份离线插件包，目录为：

```text
docs/cicd/from-zero/assets/jenkins-plugins/
```

该目录包含压缩包、校验文件和插件清单；压缩包解压后包含 `files/` 插件目录：

| 文件/目录 | 说明 |
|---|---|
| `.tgz` 解压后的 `files/` | 当前参考环境导出的 `.jpi` 插件文件 |
| `plugins.txt` | 插件 ID 清单 |
| `jenkins-plugins-2.541.2-lts-jdk21-current.tgz` | 离线安装压缩包 |
| `jenkins-plugins-2.541.2-lts-jdk21-current.tgz.sha256` | 校验文件 |
| `README.md` | 插件包使用说明 |

如果你的 Jenkins 镜像版本也是 `jenkins/jenkins:2.541.2-lts-jdk21`，可以优先使用该插件包，满足当前 CI/CD 实践需要。

注意：解压后的 `files/` 目录和 `.tgz` 压缩包内容重复。为了控制仓库体积，仓库中只保留 `.tgz`、`.sha256`、`plugins.txt` 和 `README.md`。

### 7-5-3. 在线安装方式

方式一：页面安装。

1. 进入 `Manage Jenkins` -> `Plugins`。
2. 点击 `Available plugins`。
3. 搜索插件名称，例如 `Kubernetes`、`GitLab`、`Pipeline`。
4. 勾选后点击 `Install`。
5. 安装完成后重启 Jenkins。

方式二：在 Jenkins 容器中使用官方 `jenkins-plugin-cli`。

先准备插件清单：

```bash
cat > /app/jenkins/plugins.txt <<'EOF_PLUGINS'
workflow-aggregator
workflow-multibranch
pipeline-model-definition
git
gitlab-plugin
gitlab-branch-source
credentials-binding
plain-credentials
ssh-agent
kubernetes
kubernetes-credentials
docker-workflow
timestamper
ws-cleanup
ansicolor
role-strategy
matrix-auth
configuration-as-code
job-dsl
publish-over-ssh
EOF_PLUGINS
```

执行安装：

```bash
docker cp /app/jenkins/plugins.txt jenkins:/tmp/plugins.txt
docker exec -u root jenkins jenkins-plugin-cli --plugin-file /tmp/plugins.txt
docker restart jenkins
```

官方说明：

- Jenkins 插件管理文档：https://www.jenkins.io/doc/book/managing/plugins/
- Jenkins Plugin Installation Manager：https://github.com/jenkinsci/plugin-installation-manager-tool
- Jenkins 插件下载站：https://plugins.jenkins.io/

### 7-5-4. 离线安装方式一：先在有网机器下载插件包

如果你使用本文档随附插件包，可以跳过本小节，直接看 `7-5-5`。

如果你想重新生成插件包，按下面步骤操作。

在一台可以访问互联网且已安装 Docker 的机器上执行：

```bash
mkdir -p /tmp/jenkins-plugins /tmp/jenkins-plugin-cache
cat > /tmp/jenkins-plugins/plugins.txt <<'EOF_PLUGINS'
workflow-aggregator
workflow-multibranch
pipeline-model-definition
git
gitlab-plugin
gitlab-branch-source
credentials-binding
plain-credentials
ssh-agent
kubernetes
kubernetes-credentials
docker-workflow
timestamper
ws-cleanup
ansicolor
role-strategy
matrix-auth
configuration-as-code
job-dsl
publish-over-ssh
EOF_PLUGINS

docker run --rm \
  -v /tmp/jenkins-plugins:/plugins \
  -v /tmp/jenkins-plugin-cache:/cache \
  jenkins/jenkins:2.541.2-lts-jdk21 \
  jenkins-plugin-cli \
  --plugin-file /plugins/plugins.txt \
  --plugin-download-directory /plugins/downloaded \
  --latest true
```

打包：

```bash
cd /tmp/jenkins-plugins
tar -zcvf jenkins-plugins-2.541.2-lts-jdk21.tgz downloaded plugins.txt
```

把 `jenkins-plugins-2.541.2-lts-jdk21.tgz` 上传到 Jenkins 服务器。

### 7-5-5. 离线安装方式二：拷贝到 Jenkins 插件目录

如果使用本文档随附插件包，先把下面两个文件上传到 Jenkins 服务器同一目录：

```text
docs/cicd/from-zero/assets/jenkins-plugins/jenkins-plugins-2.541.2-lts-jdk21-current.tgz
docs/cicd/from-zero/assets/jenkins-plugins/jenkins-plugins-2.541.2-lts-jdk21-current.tgz.sha256
```

上传示例：

```bash
scp docs/cicd/from-zero/assets/jenkins-plugins/jenkins-plugins-2.541.2-lts-jdk21-current.tgz root@<Jenkins服务器IP>:/root/
scp docs/cicd/from-zero/assets/jenkins-plugins/jenkins-plugins-2.541.2-lts-jdk21-current.tgz.sha256 root@<Jenkins服务器IP>:/root/
```

然后校验：

```bash
cd /root
sha256sum -c jenkins-plugins-2.541.2-lts-jdk21-current.tgz.sha256
```

如果服务器没有 `sha256sum`，也可以使用 `shasum -a 256 -c`，如确需跳过校验，需要由部署负责人确认文件来源可信。

在 Jenkins 服务器执行：

```bash
mkdir -p /tmp/jenkins-plugins
tar -zxvf jenkins-plugins-2.541.2-lts-jdk21-current.tgz -C /tmp/jenkins-plugins

docker cp /tmp/jenkins-plugins/files/. jenkins:/var/jenkins_home/plugins/
docker exec -u root jenkins sh -lc 'chown -R jenkins:jenkins /var/jenkins_home/plugins || true'
docker restart jenkins
```

如果你是按 `7-5-4` 自己重新下载的插件包，压缩包内目录可能叫 `downloaded`，则把 `files` 改成 `downloaded`：

```bash
docker cp /tmp/jenkins-plugins/downloaded/. jenkins:/var/jenkins_home/plugins/
```

重启后进入：`Manage Jenkins` -> `Plugins` -> `Installed plugins`，确认插件已安装。

离线插件路径核对：

| 项目 | 正确路径 |
|---|---|
| 文档内插件包 | `docs/cicd/from-zero/assets/jenkins-plugins/jenkins-plugins-2.541.2-lts-jdk21-current.tgz` |
| 文档内校验文件 | `docs/cicd/from-zero/assets/jenkins-plugins/jenkins-plugins-2.541.2-lts-jdk21-current.tgz.sha256` |
| 压缩包解压后的插件目录 | `/tmp/jenkins-plugins/files/` |
| Jenkins 容器插件目录 | `/var/jenkins_home/plugins/` |
| 宿主机 Jenkins 插件目录 | `/app/jenkins/home/plugins/` |

如果 Jenkins 容器名不是 `jenkins`，需要把命令中的 `jenkins` 替换成实际容器名。

### 7-5-6. 离线安装方式三：制作带插件的 Jenkins 镜像

如果要给多位同学分发统一 Jenkins 环境，推荐制作自定义镜像。

目录结构：

```text
jenkins-custom/
├── Dockerfile
└── plugins.txt
```

`plugins.txt` 内容同上。

`Dockerfile`：

```Dockerfile
FROM jenkins/jenkins:2.541.2-lts-jdk21
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
```

构建并推送到 Harbor：

```bash
docker build -t 10.1.106.200:8088/ci-tools/jenkins:2.541.2-lts-jdk21-cicd .
docker push 10.1.106.200:8088/ci-tools/jenkins:2.541.2-lts-jdk21-cicd
```

然后把 `/app/jenkins/docker-compose.yml` 中 Jenkins 镜像改为：

```yaml
image: 10.1.106.200:8088/ci-tools/jenkins:2.541.2-lts-jdk21-cicd
```

### 7-5-7. 手动下载插件的网址

如果只缺少少量插件，可以从 Jenkins 插件站手动下载：

插件下载页可以在 Jenkins 插件站中打开具体插件的 `releases` 页面。例如：

```text
https://plugins.jenkins.io/kubernetes/releases/
https://plugins.jenkins.io/git/releases/
https://plugins.jenkins.io/gitlab-plugin/releases/
https://plugins.jenkins.io/workflow-aggregator/releases/
```

下载 `.hpi` 或 `.jpi` 文件后，进入 `Manage Jenkins` -> `Plugins` -> `Advanced settings`，在 `Deploy Plugin` 上传插件文件。

注意手动下载单个插件时，还必须同时下载它的依赖插件；因此离线环境更推荐使用 `jenkins-plugin-cli` 在有网机器上统一解析并下载依赖。

## 7-6. 为 Jenkins 准备 K8s kubeconfig

在 K8s master 上执行：

```bash
kubectl create namespace jenkins-agent --dry-run=client -o yaml | kubectl apply -f -
```

确认 Namespace 已创建：

```bash
kubectl get namespace jenkins-agent
```

再查看 kubeconfig：

```bash
cat /root/.kube/config
```

复制内容，后续添加到 Jenkins Credentials。

流水线中的 `kubectl`/`helm` 步骤需要凭据类型选择 `Secret file`，ID 为：

```text
kubeconfig-main
```

Jenkins Kubernetes Cloud 也使用这个凭据。如果你的 Jenkins 页面里 Kubernetes Cloud 不显示 `Secret file` 类型凭据，可以额外创建一个同内容的 `Kubernetes configuration (kubeconfig)` 类型凭据，并在 Cloud 配置里选择它；流水线里仍保留 `Secret file` 类型的 `kubeconfig-main`。

生产部署应创建专用 ServiceAccount 并最小化权限；如果临时使用 admin kubeconfig，需限制使用范围并在部署完成后替换。

## 7-7. 配置 Jenkins Kubernetes Cloud

进入：`Manage Jenkins` -> `Clouds` -> `New cloud` -> `Kubernetes`。

填写：

| 配置项 | 示例值 |
|---|---|
| Name | `k8s-main` |
| Kubernetes URL | `https://10.1.106.71:6443` |
| Credentials | `kubeconfig-main` |
| Kubernetes Namespace | `jenkins-agent` |
| Jenkins URL | `http://10.1.106.201:8080` |
| Jenkins tunnel | `10.1.106.201:50000` |
| Container Cap | `10` |

点击 `Test Connection`，成功后保存。

![Jenkins Kubernetes Cloud 配置示例](./images/jenkins-kubernetes-cloud.jpeg)

## 7-8. 创建 Jenkins Credentials

进入：`Manage Jenkins` -> `Credentials` -> `System` -> `Global credentials`。

创建：

| ID | 类型 | 用户名 | 密码/内容 | 用途 |
|---|---|---|---|---|
| `gitlab-root` | Username with password | `root` | `GitLab@123456` | 拉取 GitLab 代码 |
| `harbor-admin` | Username with password | `admin` | `Harbor@123456` | 推送镜像到 Harbor |
| `kubeconfig-main` | Secret file | 无 | kubeconfig 文件 | 操作 K8s |
| `nacos-auth` | Username with password | `nacos` | `Nacos@123456` | 创建业务 Namespace 中的 Nacos Secret，需先在 Nacos 页面修改默认密码 |

![Jenkins Credentials 列表示例](./images/jenkins-credentials-list.png)

![GitLab 凭据配置示例](./images/jenkins-credential-gitlab.png)

![Harbor 凭据配置示例](./images/jenkins-credential-harbor.png)



![kubeconfig 凭据配置示例](./images/jenkins-credential-kubeconfig.png)



![Nacos 凭据配置示例](./images/jenkins-credential-nacos.png)

![Jenkins Credentials 创建完成示例](./images/jenkins-credentials-final.png)

## 7-9. 创建多分支流水线

1. 点击 `New Item`。
2. 名称：`spring-cloud-ex`。
3. 类型：`Multibranch Pipeline`。
4. Branch Sources 选择 `Git`。
5. Project Repository 填：

```text
http://10.1.106.200:8929/root/spring-cloud-ex.git
```

6. Credentials 选择：`gitlab-root`。
7. Behaviors 保留发现分支。
8. Build Configuration：`Jenkinsfile`。
9. Scan Multibranch Pipeline Triggers 勾选 `Periodically if not otherwise run`，例如 `H/2 * * * *`。
10. 保存后点击 `Scan Multibranch Pipeline Now`。

这样即使暂时没有配置 GitLab Webhook，Jenkins 也会定期扫描分支变化。后续也可以在 GitLab 项目中配置 Webhook，推送代码后立即触发 Jenkins。

![Jenkins 多分支扫描配置示例](./images/jenkins-multibranch-scan.jpeg)

---

> 微信: wingsreops
