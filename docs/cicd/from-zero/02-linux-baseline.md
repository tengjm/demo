# 2-Linux 基础环境标准化

本章在所有服务器上执行，包括 GitLab、Harbor、Jenkins、Kubernetes 节点。

## 2-1. 设置主机名

按实际角色设置：

```bash
hostnamectl set-hostname gitlab-harbor
# 或
hostnamectl set-hostname jenkins
# 或
hostnamectl set-hostname k8s-master
```

修改 `/etc/hosts`，示例：

```bash
cat >> /etc/hosts <<'EOF_HOSTS'
10.1.106.200 gitlab-harbor
10.1.106.201 jenkins
EOF_HOSTS
```

验证：

```bash
hostname
ping -c 2 k8s-master
```

## 2-2. 安装基础工具

Ubuntu / Debian：

```bash
apt-get update
apt-get install -y curl wget vim net-tools iproute2 telnet unzip tar gzip ca-certificates gnupg lsb-release chrony bash-completion
```

CentOS / Rocky / AlmaLinux / openEuler / 麒麟：

```bash
yum install -y curl wget vim net-tools iproute telnet unzip tar gzip ca-certificates chrony bash-completion yum-utils
# 如果系统使用 dnf，也可以使用：dnf install -y ...
```

## 2-3. 时间同步

```bash
systemctl enable --now chronyd || systemctl enable --now chrony
chronyc tracking || timedatectl status
```

时间不准会导致证书、Token、镜像仓库登录、Kubernetes 节点加入异常。

## 2-4. 关闭 Swap

Kubernetes 节点必须关闭 Swap。建议所有服务器都关闭，避免资源抖动。

```bash
swapoff -a
sed -ri 's/^([^#].*\sswap\s.*)$/#\1/' /etc/fstab
free -h
```

预期 `Swap` 为 `0B`。

## 2-5. 文件描述符优化

GitLab、Harbor、Jenkins、Kubernetes 都会打开较多文件和网络连接。

```bash
cat > /etc/security/limits.d/99-devops.conf <<'EOF_LIMITS'
* soft nofile 1048576
* hard nofile 1048576
* soft nproc  65535
* hard nproc  65535
root soft nofile 1048576
root hard nofile 1048576
root soft nproc  65535
root hard nproc  65535
EOF_LIMITS
```

systemd 默认限制：

```bash
mkdir -p /etc/systemd/system.conf.d /etc/systemd/user.conf.d
cat > /etc/systemd/system.conf.d/99-devops-limits.conf <<'EOF_SYSTEMD'
[Manager]
DefaultLimitNOFILE=1048576
DefaultLimitNPROC=65535
EOF_SYSTEMD
cat > /etc/systemd/user.conf.d/99-devops-limits.conf <<'EOF_USER'
[Manager]
DefaultLimitNOFILE=1048576
DefaultLimitNPROC=65535
EOF_USER
systemctl daemon-reexec
```

验证当前 shell：

```bash
ulimit -n
ulimit -u
```

重新登录后应该生效。

## 2-6. 内核参数优化

```bash
cat > /etc/sysctl.d/99-devops.conf <<'EOF_SYSCTL'
fs.file-max = 2097152
fs.inotify.max_user_instances = 8192
fs.inotify.max_user_watches = 1048576
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.ip_local_port_range = 1024 65000
vm.max_map_count = 262144
vm.swappiness = 0
EOF_SYSCTL

modprobe br_netfilter
modprobe overlay
cat > /etc/modules-load.d/k8s.conf <<'EOF_MODULES'
overlay
br_netfilter
EOF_MODULES

sysctl --system
```

验证：

```bash
sysctl net.ipv4.ip_forward
sysctl net.bridge.bridge-nf-call-iptables
sysctl vm.max_map_count
```

## 2-7. 防火墙和安全组

生产部署建议按端口最小放行；如果因排障临时关闭防火墙，完成后应恢复安全策略。

Ubuntu / Debian：

```bash
ufw status
ufw disable || true
```

CentOS / Rocky / AlmaLinux / openEuler / 麒麟：

```bash
systemctl disable --now firewalld || true
```

云服务器还需要在云控制台安全组放行端口，至少包括：

```text
22, 80, 443, 8080, 8088, 8929, 50000, 6443, 30000-32767
```

## 2-8. SELinux

CentOS/RHEL 系系统如因容器运行策略受限，可临时设置为 permissive，完成后应按安全规范加固：

```bash
getenforce || true
setenforce 0 || true
sed -ri 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config 2>/dev/null || true
```

## 2-9. 重启服务器

完成基础优化后建议重启一次：

```bash
reboot
```

重启后检查：

```bash
hostname
free -h
ulimit -n
sysctl net.ipv4.ip_forward
```

---

> 微信: wingsreops
