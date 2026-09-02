# 3-Docker Engine 与 Docker Compose 安装

GitLab、Harbor、Jenkins 推荐使用 Docker 或 Docker Compose 部署。本章在 GitLab/Harbor 机器、Jenkins 机器上执行。Kubernetes 节点也可以安装 Docker 客户端用于调试，但 K8s 运行时推荐使用 containerd。

官方文档：

- Docker Engine：https://docs.docker.com/engine/install/
- Docker Compose：https://docs.docker.com/compose/install/linux/
- Docker 二进制包：https://download.docker.com/linux/static/stable/
- Docker Compose Release：https://github.com/docker/compose/releases

## 3-1. 安装方式选择

| 场景 | 推荐方式 | 说明 |
|---|---|---|
| 服务器可访问 Docker 官方源 | 官方源安装 | 最标准，版本新，依赖自动处理 |
| 国内服务器访问官方源慢 | 国内镜像源安装 | 可用阿里云、清华、华为云等镜像源 |
| 云厂商系统已有软件源 | 系统源安装 | 版本可能较旧，但最省事 |
| 离线环境 | RPM/DEB 离线包 | 适合 CentOS/Ubuntu，依赖需要一起下载 |
| 极简离线环境 | 二进制安装 | 不依赖包管理器，适合多发行版兜底 |

建议优先级：

```text
国内镜像源安装 > 官方源安装 > 系统源安装 > RPM/DEB 离线包 > 二进制安装
```

## 3-2. Ubuntu / Debian 使用国内源安装 Docker

### 3-2-1. 阿里云 Docker 源

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/${ID} ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

如果是 Debian，`${ID}` 通常是 `debian`；如果是 Ubuntu，`${ID}` 通常是 `ubuntu`。

### 3-2-2. 清华 Docker 源

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/${ID} ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3-2-3. 华为云 Docker 源

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://repo.huaweicloud.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://repo.huaweicloud.com/docker-ce/linux/${ID} ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

注意：部分国产系统虽然基于 Debian/Ubuntu，但 `${VERSION_CODENAME}` 可能不是 Docker 源支持的发行版代号。遇到 `Release file not found` 时，可以改成对应 Ubuntu LTS 代号，例如：

```bash
# Ubuntu 22.04
VERSION_CODENAME=jammy
# Ubuntu 20.04
VERSION_CODENAME=focal
```

## 3-3. CentOS / Rocky / AlmaLinux / openEuler / 麒麟使用国内源安装 Docker

### 3-3-1. 阿里云 Docker 源

```bash
yum install -y yum-utils
yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
yum makecache
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

如果系统使用 `dnf`：

```bash
dnf install -y dnf-plugins-core
dnf config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
dnf makecache
dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3-3-2. 清华 Docker 源

```bash
yum install -y yum-utils
yum-config-manager --add-repo https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/docker-ce.repo
yum makecache
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3-3-3. 华为云 Docker 源

```bash
yum install -y yum-utils
yum-config-manager --add-repo https://repo.huaweicloud.com/docker-ce/linux/centos/docker-ce.repo
yum makecache
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

openEuler、麒麟、Anolis、TencentOS 等系统如果不能直接使用 CentOS Docker CE 仓库，建议优先使用对应系统官方源中的 Docker 包，或使用本文后面的二进制安装方式。

如果系统兼容 RHEL/CentOS 但 `$releasever` 解析异常，可以手动把 repo 文件里的 `$releasever` 改成 `7`、`8` 或 `9` 后再执行 `yum makecache`。

## 3-4. 官方源安装方式

如果服务器能稳定访问 Docker 官方源，可按官方文档安装。

Ubuntu / Debian：

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

CentOS / Rocky / AlmaLinux：

```bash
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

## 3-5. 使用系统源快速安装

如果需要快速完成基础部署，也可以使用系统自带源安装。

Ubuntu / Debian：

```bash
apt-get update
apt-get install -y docker.io docker-compose-plugin || apt-get install -y docker.io docker-compose
```

CentOS / Rocky / AlmaLinux / openEuler / 麒麟：

```bash
yum install -y docker docker-compose-plugin || yum install -y docker docker-compose
```

注意：系统源版本可能较旧，如果 Harbor、Jenkins、GitLab 部署遇到兼容问题，建议改用 Docker CE 源或二进制安装方式。

## 3-6. 启动 Docker

```bash
systemctl enable --now docker
systemctl status docker --no-pager
```

验证：

```bash
docker version
docker compose version || docker-compose version
docker run --rm hello-world
```

## 3-7. Docker 数据目录规划

默认 Docker 数据目录是 `/var/lib/docker`。如果磁盘较小，建议迁移到独立数据盘，例如 `/data/docker` 或 `/app/docker/data`。

```bash
mkdir -p /app/docker/data /etc/docker
cat > /etc/docker/daemon.json <<'EOF_DOCKER'
{
  "data-root": "/app/docker/data",
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF_DOCKER
systemctl restart docker
```

验证：

```bash
docker info | grep -E 'Docker Root Dir|Cgroup Driver'
```

## 3-8. 配置 HTTP Harbor 不安全仓库

当前生产部署案例可能暂未准备 HTTPS 证书，Harbor 可以先使用 HTTP。Docker 默认要求 HTTPS，所以必须配置 `insecure-registries`，并在后续安全加固阶段切换到 HTTPS。

假设 Harbor 地址是：

```text
10.1.106.200:8088
```

编辑 `/etc/docker/daemon.json`：

```bash
mkdir -p /etc/docker /app/docker/data
cat > /etc/docker/daemon.json <<'EOF_DOCKER'
{
  "data-root": "/app/docker/data",
  "exec-opts": ["native.cgroupdriver=systemd"],
  "insecure-registries": ["10.1.106.200:8088"],
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF_DOCKER
systemctl restart docker
```

说明：

- `insecure-registries` 用于 HTTP Harbor。
- `registry-mirrors` 用于加速拉取 Docker Hub 镜像，可按实际情况替换为企业内网镜像加速地址。
- 云厂商镜像加速地址通常需要在控制台开通后获得专属地址。

验证：

```bash
docker info | grep -A8 'Insecure Registries'
docker info | grep -A8 'Registry Mirrors'
```

## 3-9. Docker Compose 使用方式

新版本 Docker Compose 是 Docker CLI 插件，命令是：

```bash
docker compose version
```

不是旧命令：

```bash
docker-compose version
```

如果第三方脚本仍需要 `docker-compose`，可以创建兼容软链接：

```bash
ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose 2>/dev/null || true
ln -sf /usr/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose 2>/dev/null || true
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose 2>/dev/null || true
docker-compose version || true
```

## 3-10. Docker 二进制安装方式

当系统包管理器不可用，或国产系统无法直接使用 Docker CE 源时，可以使用二进制安装。

### 3-10-1. 准备二进制包

在有网机器下载：

```bash
mkdir -p /tmp/docker-binary
cd /tmp/docker-binary
wget https://download.docker.com/linux/static/stable/x86_64/docker-27.5.1.tgz
wget https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-x86_64 -O docker-compose
```

上传到目标服务器，例如：

```text
/root/offline/docker-27.5.1.tgz
/root/offline/docker-compose
```

### 3-10-2. 安装 Docker 二进制

```bash
mkdir -p /root/offline
cd /root/offline

tar -zxvf docker-27.5.1.tgz
cp docker/* /usr/local/bin/
chmod +x /usr/local/bin/docker* /usr/local/bin/containerd* /usr/local/bin/ctr /usr/local/bin/runc || true
```

创建 systemd 文件：

```bash
cat > /etc/systemd/system/containerd.service <<'EOF_CONTAINERD'
[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target local-fs.target

[Service]
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/containerd
Type=notify
Delegate=yes
KillMode=process
Restart=always
RestartSec=5
LimitNPROC=infinity
LimitCORE=infinity
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF_CONTAINERD

cat > /etc/systemd/system/docker.service <<'EOF_DOCKER_SERVICE'
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target containerd.service
Wants=network-online.target
Requires=containerd.service

[Service]
Type=notify
ExecStart=/usr/local/bin/dockerd --containerd=/run/containerd/containerd.sock
ExecReload=/bin/kill -s HUP $MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
Delegate=yes
KillMode=process
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity

[Install]
WantedBy=multi-user.target
EOF_DOCKER_SERVICE
```

安装 Compose 插件：

```bash
mkdir -p /usr/local/lib/docker/cli-plugins
cp /root/offline/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
```

启动：

```bash
systemctl daemon-reload
systemctl enable --now containerd
systemctl enable --now docker

docker version
docker compose version
```

## 3-11. 离线 RPM/DEB 安装思路

如果希望保持系统包管理器管理 Docker，可以使用 RPM/DEB 离线包。

### 3-11-1. RPM 离线包

在同版本有网机器下载：

```bash
mkdir -p /tmp/docker-rpms
cd /tmp/docker-rpms
yum install -y yum-utils
yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
yumdownloader --resolve docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

上传到离线服务器后安装：

```bash
cd /root/offline/docker-rpms
yum localinstall -y *.rpm
systemctl enable --now docker
```

### 3-11-2. DEB 离线包

在同版本 Ubuntu/Debian 有网机器下载：

```bash
mkdir -p /tmp/docker-debs
cd /tmp/docker-debs
apt-get update
apt-get install -y --download-only docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
cp /var/cache/apt/archives/*.deb /tmp/docker-debs/
```

上传到离线服务器后安装：

```bash
cd /root/offline/docker-debs
dpkg -i *.deb || apt-get install -f -y
systemctl enable --now docker
```

## 3-12. 离线二进制安装脚本

下面脚本适合“目标服务器没有外网，但已经上传 Docker 二进制包和 Compose 二进制”的场景。

文件规划：

```text
/root/offline/docker/docker-27.5.1.tgz
/root/offline/docker/docker-compose-linux-x86_64
```

创建脚本：

```bash
cat > install-docker-binary-offline.sh <<'EOF_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

DOCKER_TGZ=${DOCKER_TGZ:-/root/offline/docker/docker-27.5.1.tgz}
COMPOSE_BIN=${COMPOSE_BIN:-/root/offline/docker/docker-compose-linux-x86_64}
DOCKER_DATA_ROOT=${DOCKER_DATA_ROOT:-/app/docker/data}
HARBOR_INSECURE=${HARBOR_INSECURE:-10.1.106.200:8088}

if [ "$(id -u)" != "0" ]; then
  echo "请使用 root 执行"
  exit 1
fi

if [ ! -f "$DOCKER_TGZ" ]; then
  echo "未找到 Docker 二进制包: $DOCKER_TGZ"
  exit 1
fi

if [ ! -f "$COMPOSE_BIN" ]; then
  echo "未找到 Docker Compose 二进制: $COMPOSE_BIN"
  exit 1
fi

mkdir -p /tmp/docker-install
rm -rf /tmp/docker-install/*
tar -zxf "$DOCKER_TGZ" -C /tmp/docker-install
cp /tmp/docker-install/docker/* /usr/local/bin/
chmod +x /usr/local/bin/docker* /usr/local/bin/containerd* /usr/local/bin/ctr /usr/local/bin/runc || true

mkdir -p /usr/local/lib/docker/cli-plugins
cp "$COMPOSE_BIN" /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

mkdir -p /etc/docker "$DOCKER_DATA_ROOT"
cat > /etc/docker/daemon.json <<EOF_DAEMON
{
  "data-root": "$DOCKER_DATA_ROOT",
  "exec-opts": ["native.cgroupdriver=systemd"],
  "insecure-registries": ["$HARBOR_INSECURE"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF_DAEMON

cat > /etc/systemd/system/containerd.service <<'EOF_CONTAINERD'
[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target local-fs.target

[Service]
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/containerd
Type=notify
Delegate=yes
KillMode=process
Restart=always
RestartSec=5
LimitNPROC=infinity
LimitCORE=infinity
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF_CONTAINERD

cat > /etc/systemd/system/docker.service <<'EOF_DOCKER_SERVICE'
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target containerd.service
Wants=network-online.target
Requires=containerd.service

[Service]
Type=notify
ExecStart=/usr/local/bin/dockerd --containerd=/run/containerd/containerd.sock
ExecReload=/bin/kill -s HUP $MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
Delegate=yes
KillMode=process
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity

[Install]
WantedBy=multi-user.target
EOF_DOCKER_SERVICE

systemctl daemon-reload
systemctl enable --now containerd
systemctl enable --now docker

docker version
docker compose version || docker-compose version

echo "Docker 离线二进制安装完成"
EOF_SCRIPT

chmod +x install-docker-binary-offline.sh
```

执行：

```bash
HARBOR_INSECURE=10.1.106.200:8088 \
DOCKER_DATA_ROOT=/app/docker/data \
bash install-docker-binary-offline.sh
```

验证：

```bash
docker info | grep -E 'Docker Root Dir|Cgroup Driver'
docker info | grep -A8 'Insecure Registries'
docker compose version || docker-compose version
```

---

> 微信: wingsreops
