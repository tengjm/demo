# 4-Kubernetes 基础环境安装

本章使用 kubeadm 部署 Kubernetes。官方文档：

- kubeadm 安装：https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
- containerd 运行时：https://kubernetes.io/docs/setup/production-environment/container-runtimes/
- Helm 安装：https://helm.sh/docs/intro/install/

## 4-0. 已有 Kubernetes 集群时可以跳过安装

如果你本地、公司内网或云上已经有可用 Kubernetes 集群，可以跳过本章的 `4-1` 到 `4-8` 安装步骤，直接做接入检查。

已有集群必须满足：

| 检查项 | 要求 |
|---|---|
| kubectl 可用 | 能在管理机执行 `kubectl get nodes` |
| 节点状态 | 至少 1 个 Ready 节点，推荐 2 个以上 |
| Namespace 权限 | Jenkins 使用的 kubeconfig 能创建 namespace、secret、deployment、service |
| 镜像拉取 | K8s 节点能拉取 Harbor 中的 HTTP 镜像，或 Harbor 已配置 HTTPS |
| NodePort | 集群允许使用 `30080`、`30081`、`30082` |
| Nacos | 可以在该集群中部署 Nacos，或已有 Nacos 可供访问 |
| Jenkins Agent | 集群能创建 Jenkins 动态 Agent Pod |

接入检查命令：

```bash
kubectl get nodes -o wide
kubectl auth can-i create namespace
kubectl auth can-i create secret -n dev
kubectl auth can-i create deployment -n dev
kubectl auth can-i create service -n dev
```

如果使用 HTTP Harbor，例如：

```text
10.1.106.200:8088
```

仍然必须在所有可能运行 Jenkins Agent Pod 和业务 Pod 的 K8s 节点上配置 containerd 不安全仓库，参考本章 `4-3. 配置 containerd 拉取 HTTP Harbor`。

如果已有集群只允许调度到部分节点，建议给已配置 HTTP Harbor 的节点打标签：

```bash
kubectl label node <node-name> harbor-insecure=true --overwrite
```

然后继续执行：

```text
4-9. 创建基础 Namespace
4-10. 给可拉取 HTTP Harbor 的节点打标签
```

如果你使用云厂商托管 Kubernetes，例如 ACK、TKE、CCE，也可以跳过 kubeadm 安装，但仍需要确认：

- Jenkins 能访问 Kubernetes API。
- Jenkins kubeconfig 权限足够。
- 云安全组或防火墙放行 NodePort。
- 节点运行时能拉取 Harbor 镜像。

## 4-1. 节点规划

| 节点 | 示例 IP | 角色 |
|---|---:|---|
| `k8s-master` | `10.1.106.71` | control-plane |
| `k8s-node1` | `10.1.106.65` | worker |
| `k8s-node2` | `10.1.106.68` | worker |

所有节点都先完成：

- `02-linux-baseline.md`
- 安装 containerd
- 关闭 swap
- 配置内核模块和 sysctl

## 4-2. 安装 containerd

如果已经通过 Docker 官方源安装了 `containerd.io`，可以直接配置：

```bash
containerd config default > /etc/containerd/config.toml
sed -ri 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
systemctl enable --now containerd
systemctl restart containerd
```

验证：

```bash
containerd --version
systemctl status containerd --no-pager
```

## 4-3. 配置 containerd 拉取 HTTP Harbor

Kubernetes 节点使用 containerd 拉镜像，Docker 的 `insecure-registries` 对 K8s 不生效，需要单独配置。

假设 Harbor 是 HTTP：

```text
10.1.106.200:8088
```

containerd 1.7 / 2.x 推荐使用 `certs.d`：

```bash
mkdir -p /etc/containerd/certs.d/10.1.106.200:8088
cat > /etc/containerd/certs.d/10.1.106.200:8088/hosts.toml <<'EOF_HOSTS'
server = "http://10.1.106.200:8088"

[host."http://10.1.106.200:8088"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
EOF_HOSTS
```

确认 `/etc/containerd/config.toml` 中 registry config path 存在：

```toml
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
```

或者 containerd 2.x 可能是：

```toml
[plugins.'io.containerd.cri.v1.images'.registry]
  config_path = '/etc/containerd/certs.d'
```

重启：

```bash
systemctl restart containerd
```

验证拉取镜像：

```bash
crictl info | head
# Harbor 中有镜像后再验证：
# crictl pull 10.1.106.200:8088/devops-demo/hello-service:某个tag
```

## 4-4. 安装 kubeadm/kubelet/kubectl

Ubuntu / Debian：

```bash
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gpg
mkdir -p /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' > /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl
systemctl enable --now kubelet
```

CentOS / Rocky / AlmaLinux / openEuler / 麒麟：

```bash
cat > /etc/yum.repos.d/kubernetes.repo <<'EOF_REPO'
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/repodata/repomd.xml.key
EOF_REPO

yum install -y kubelet kubeadm kubectl
systemctl enable --now kubelet
```

## 4-5. 初始化 control-plane

只在 `k8s-master` 执行：

```bash
kubeadm init \
  --apiserver-advertise-address=10.1.106.71 \
  --pod-network-cidr=172.16.0.0/16 \
  --service-cidr=192.168.0.0/16 \
  --cri-socket=unix:///run/containerd/containerd.sock
```

配置 kubectl：

```bash
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config
kubectl get nodes
```

## 4-6. 安装 CNI 网络插件

可以使用 Calico。官方文档以 Calico 当前版本为准。

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.2/manifests/tigera-operator.yaml
curl -fsSL https://raw.githubusercontent.com/projectcalico/calico/v3.28.2/manifests/custom-resources.yaml -o custom-resources.yaml
# 如果 kubeadm 使用 172.16.0.0/16，需要把 custom-resources.yaml 中 CIDR 改成 172.16.0.0/16
sed -ri 's#cidr: .*#cidr: 172.16.0.0/16#' custom-resources.yaml
kubectl create -f custom-resources.yaml
```

等待：

```bash
kubectl get pods -A
kubectl get nodes
```

## 4-7. Worker 节点加入集群

在 `kubeadm init` 输出中会有 join 命令，复制到 worker 节点执行，例如：

```bash
kubeadm join 10.1.106.71:6443 --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --cri-socket=unix:///run/containerd/containerd.sock
```

如果忘记命令，在 master 生成：

```bash
kubeadm token create --print-join-command
```

## 4-8. 安装 Helm

在 Jenkins Agent 镜像中会自带 Helm；K8s master 上也建议安装：

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

## 4-9. 创建基础 Namespace

```bash
kubectl create namespace nacos || true
kubectl create namespace jenkins-agent || true
kubectl create namespace dev || true
kubectl create namespace test || true
kubectl create namespace prod || true
```

## 4-10. 给可拉取 HTTP Harbor 的节点打标签

如果只有部分节点配置了 HTTP Harbor，需要给这些节点打标签，Jenkins Agent 和业务 Pod 只调度到这些节点：

```bash
kubectl label node k8s-master harbor-insecure=true --overwrite
kubectl label node k8s-node1 harbor-insecure=true --overwrite
```

验证：

```bash
kubectl get nodes --show-labels | grep harbor-insecure
```

---

> 微信: wingsreops
