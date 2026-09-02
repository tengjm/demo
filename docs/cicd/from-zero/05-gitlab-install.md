# 5-GitLab Docker Compose 部署

官方文档：https://docs.gitlab.com/install/docker/

本章使用 GitLab CE Docker Compose 部署，适合作为生产部署案例的代码仓库基础组件。GitLab 官方 Docker 文档同时提供 `docker run` 和 Docker Compose 示例，本文主线采用 Docker Compose，便于后续维护和重启。

## 5-1. 部署规划

| 配置项 | 示例值 |
|---|---|
| 服务器 IP | `10.1.106.200` |
| Web 端口 | `8929` |
| 镜像 | `gitlab/gitlab-ce:18.9.2-ce.0` |
| 数据目录 | `/app/gitlab` |
| root 初始密码 | `GitLab@123456` |

## 5-2. 创建目录

```bash
mkdir -p /app/gitlab/config /app/gitlab/logs /app/gitlab/data
cd /app/gitlab
```

## 5-3. 编写 docker-compose.yml

```bash
cat > /app/gitlab/docker-compose.yml <<'EOF_COMPOSE'
services:
  gitlab:
    image: gitlab/gitlab-ce:18.9.2-ce.0
    container_name: gitlab
    hostname: 10.1.106.200
    restart: unless-stopped
    shm_size: 256m
    ports:
      - "8929:8929"
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://10.1.106.200:8929'
        gitlab_rails['initial_root_password'] = 'GitLab@123456'
        nginx['listen_port'] = 8929
        nginx['listen_https'] = false
        letsencrypt['enable'] = false
        gitlab_rails['time_zone'] = 'Asia/Shanghai'
    volumes:
      - /app/gitlab/config:/etc/gitlab
      - /app/gitlab/logs:/var/log/gitlab
      - /app/gitlab/data:/var/opt/gitlab
EOF_COMPOSE
```

注意：

- `external_url` 必须和浏览器访问地址一致。
- `initial_root_password` 只在首次初始化时生效，后续修改 Compose 不会重置密码。
- 本文统一使用 HTTP 方式拉取和推送 Git 代码，不配置 Git SSH 克隆端口。

## 5-4. 启动 GitLab

```bash
cd /app/gitlab
docker compose up -d
```

首次启动可能需要 3 到 10 分钟。

## 5-5. docker run 可选方式

如果你只想快速验证，也可以使用官方 `docker run` 风格启动。长期维护仍推荐 Docker Compose。

```bash
docker run -d \
  --hostname 10.1.106.200 \
  --name gitlab \
  --restart unless-stopped \
  -p 8929:8929 \
  -v /app/gitlab/config:/etc/gitlab \
  -v /app/gitlab/logs:/var/log/gitlab \
  -v /app/gitlab/data:/var/opt/gitlab \
  -e GITLAB_OMNIBUS_CONFIG="external_url 'http://10.1.106.200:8929'; gitlab_rails['initial_root_password']='GitLab@123456'; nginx['listen_port']=8929; nginx['listen_https']=false; letsencrypt['enable']=false; gitlab_rails['time_zone']='Asia/Shanghai'" \
  gitlab/gitlab-ce:18.9.2-ce.0
```

## 5-6. 验证 GitLab

```bash
cd /app/gitlab
docker compose ps
docker ps | grep gitlab
docker logs -f gitlab
```

浏览器访问：

```text
http://10.1.106.200:8929
```

登录：

```text
账号：root
密码：GitLab@123456
```

## 5-7. 创建项目

在 GitLab 页面执行：

1. 点击 `New project`。
2. 选择 `Create blank project`。
3. Project name 填：`spring-cloud-ex`。
4. Visibility Level 可选 `Private`。
5. 创建完成后项目地址类似：

```text
http://10.1.106.200:8929/root/spring-cloud-ex.git
```

## 5-8. 推送当前项目代码

在开发机或项目所在机器执行：

```bash
git remote add gitlab http://10.1.106.200:8929/root/spring-cloud-ex.git || git remote set-url gitlab http://10.1.106.200:8929/root/spring-cloud-ex.git
git checkout main
git push gitlab main

# 如果本地已有 develop 分支会直接切换；没有则从 main 创建。
git checkout develop 2>/dev/null || git checkout -b develop main
git push gitlab develop
```

## 5-9. Git HTTP 克隆地址

本文统一使用 HTTP 地址克隆、推送代码，减少 SSH Key 分发和维护成本。

```bash
git clone http://10.1.106.200:8929/root/spring-cloud-ex.git
```

Jenkins 多分支流水线也使用 HTTP 地址和 `gitlab-root` 凭据拉取代码。

---

> 微信: wingsreops
