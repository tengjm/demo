# 10-验证、排错、回滚与清理

## 10-1. 总体验证清单

| 检查项 | 命令 |
|---|---|
| Docker 状态 | `systemctl status docker --no-pager` |
| Docker Compose | `docker compose version` |
| GitLab 容器 | `docker ps | grep gitlab` |
| Harbor 容器 | `cd /app/harbor/installer && docker compose ps` |
| Jenkins 容器 | `docker ps | grep jenkins` |
| K8s 节点 | `kubectl get nodes -o wide` |
| Nacos | `kubectl -n nacos get pods,svc -o wide` |
| Jenkins Agent Namespace | `kubectl get ns jenkins-agent` |
| dev 应用 | `kubectl -n dev get pods,svc -o wide` |
| Helm 发布 | `helm list -A` |
| 业务访问 | `curl http://10.1.106.71:30080` |

## 10-2. 部署前关键项复核

如果流水线没有跑通，先不要直接改 Jenkinsfile，优先复核下面四类前置项。

### 10-2-1. 端口与安全组

在对应机器上验证端口监听：

```bash
ss -lntp | grep -E '8929|8088|8080|50000|6443|30080|30081|30082|30848|31848|31849'
```

在访问端机器上验证连通性：

```bash
nc -zv 10.1.106.200 8929
nc -zv 10.1.106.200 8088
nc -zv 10.1.106.201 8080
nc -zv 10.1.106.201 50000
nc -zv 10.1.106.71 6443
nc -zv 10.1.106.71 30080
nc -zv 10.1.106.71 30848
```

如果是云服务器，同时检查云安全组和系统防火墙。

### 10-2-2. HTTP Harbor

Docker 侧：

```bash
docker info | grep -A5 'Insecure Registries'
docker login 10.1.106.200:8088 -u admin -p 'Harbor@123456'
```

Kubernetes 节点 containerd 侧：

```bash
cat /etc/containerd/certs.d/10.1.106.200:8088/hosts.toml
systemctl status containerd --no-pager
crictl pull 10.1.106.200:8088/ci-tools/helm-kubectl:3.16.3
```

如果 `crictl pull` 失败，业务 Pod 和 Jenkins Agent Pod 都可能无法启动。

### 10-2-3. Nacos Namespace 与密码

检查 Nacos 页面是否已经创建 `dev`、`test`、`prod` 三个 Namespace，且 Namespace ID 不是随机值。

检查 Jenkins Credentials：

```text
ID: nacos-auth
类型: Username with password
用户名: nacos
密码: Nacos 页面中 nacos 用户修改后的密码
```

业务 Namespace 中的 Secret 由 Jenkinsfile 自动创建，可以在流水线跑过后检查：

```bash
kubectl -n dev get secret nacos-auth
```

### 10-2-4. 离线镜像与插件

检查 Harbor 中是否已经存在 CI 工具镜像：

```bash
docker pull 10.1.106.200:8088/ci-tools/maven:3.9.9-eclipse-temurin-8
docker pull 10.1.106.200:8088/ci-tools/kaniko-executor:v1.23.2-debug
docker pull 10.1.106.200:8088/ci-tools/helm-kubectl:3.16.3
docker pull 10.1.106.200:8088/ci-tools/jenkins-inbound-agent:3355.v388858a_47b_33-3-jdk21
```

检查 Jenkins 插件是否安装：

```text
Manage Jenkins -> Plugins -> Installed plugins
```

重点确认 `Pipeline`、`Git`、`GitLab`、`Kubernetes`、`Credentials Binding` 已安装。

## 10-3. Harbor HTTP 拉取失败

现象：

```text
http: server gave HTTP response to HTTPS client
```

原因：Docker 或 containerd 没有把 Harbor 配成不安全仓库。

Docker 修复：

```bash
cat /etc/docker/daemon.json
systemctl restart docker
docker info | grep -A5 'Insecure Registries'
```

containerd 修复：

```bash
cat /etc/containerd/certs.d/10.1.106.200:8088/hosts.toml
systemctl restart containerd
```

确认 Pod 调度到了已配置节点：

```bash
kubectl get nodes --show-labels | grep harbor-insecure
kubectl -n dev get pod -o wide
```

## 10-4. Jenkins Agent Pod 起不来

查看 Pod：

```bash
kubectl -n jenkins-agent get pods -o wide
kubectl -n jenkins-agent describe pod <pod-name>
kubectl -n jenkins-agent logs <pod-name> -c jnlp
```

常见原因：

| 现象 | 处理 |
|---|---|
| 拉取 Agent 镜像失败 | 同步 CI 工具镜像到 Harbor，并配置 containerd HTTP Harbor |
| `jnlp` 连不上 Jenkins | 检查 `Jenkins URL` 和 `Jenkins tunnel`，放行 `50000` |
| Namespace 不存在 | `kubectl create namespace jenkins-agent` |
| kubeconfig 无权限 | 重新创建 `kubeconfig-main` 凭据 |

## 10-5. Jenkins 拉 GitLab 代码失败

检查：

```bash
curl -I http://10.1.106.200:8929
```

Jenkins Credentials：

```text
ID: gitlab-root
类型: Username with password
账号: root
密码: GitLab@123456
```

如果 GitLab 项目是私有项目，必须配置凭据。

## 10-6. Kaniko 推送 Harbor 失败

常见日志：

```text
UNAUTHORIZED: unauthorized to access repository
```

处理：

1. Jenkins Credentials `harbor-admin` 是否正确。
2. Harbor 是否存在项目 `devops-demo`。
3. Jenkinsfile 中 `HARBOR_REGISTRY` 是否等于 `10.1.106.200:8088`。
4. Kaniko 命令是否包含：

```bash
--insecure --skip-tls-verify
```

## 10-7. Nacos 注册失败

检查业务 Pod 环境变量：

```bash
kubectl -n dev describe pod <hello-pod-name> | grep -A20 SPRING_CLOUD_NACOS
```

检查 Secret：

```bash
kubectl -n dev get secret nacos-auth
```

检查 Nacos：

```bash
kubectl -n nacos get pods,svc
curl http://10.1.106.71:30848/nacos
```

常见原因：

| 原因 | 处理 |
|---|---|
| Nacos 密码错误 | 更新 Jenkins `nacos-auth` 凭据后重跑流水线 |
| Nacos Namespace 不存在 | 在 Nacos 页面创建 `dev/test/prod` 命名空间 |
| 服务地址错误 | 确认 `nacos.nacos.svc.cluster.local:8848` 可解析 |

## 10-8. Helm 部署失败

查看历史：

```bash
helm history spring-cloud-demo -n dev
helm status spring-cloud-demo -n dev
```

查看事件：

```bash
kubectl -n dev get events --sort-by=.lastTimestamp | tail -50
```

因为 Jenkinsfile 使用 `--atomic`，部署失败会自动回滚到上一个可用版本。

## 10-9. 手动回滚

查看版本：

```bash
helm history spring-cloud-demo -n dev
```

回滚：

```bash
helm rollback spring-cloud-demo <REVISION> -n dev
kubectl -n dev rollout status deployment/date-service --timeout=120s
kubectl -n dev rollout status deployment/hello-service --timeout=120s
```

验证：

```bash
curl http://10.1.106.71:30080
```

## 10-10. 清理 dev 环境

```bash
helm uninstall spring-cloud-demo -n dev
kubectl delete namespace dev
kubectl create namespace dev
```

## 10-11. 清理基础组件

谨慎执行，清理会删除数据。

GitLab：

```bash
docker rm -f gitlab
# rm -rf /app/gitlab
```

Harbor：

```bash
cd /app/harbor/installer
docker compose down
# rm -rf /app/harbor/data
```

Jenkins：

```bash
cd /app/jenkins
docker compose down
# rm -rf /app/jenkins/home
```

Nacos：

```bash
kubectl delete namespace nacos
```

---

> 微信: wingsreops
