# 8-Nacos 在 Kubernetes 中部署

官方文档：https://nacos.io/docs/latest/quickstart/quick-start-docker/

本案例先使用 Nacos standalone 模式部署到 Kubernetes，便于完成最小闭环。正式生产建议使用 Nacos 集群模式并接入外部数据库。

## 8-1. 部署规划

| 配置项 | 示例值 |
|---|---|
| Namespace | `nacos` |
| 镜像 | `nacos/nacos-server:v2.3.2` |
| 模式 | `standalone` |
| Web NodePort | `30848` |
| gRPC NodePort | `31848` / `31849` |
| 初始账号 | `nacos` |
| 初始密码 | `nacos` |
| 修改后示例密码 | `Nacos@123456` |
| K8s 内部地址 | `nacos.nacos.svc.cluster.local:8848` |

## 8-2. 创建 Namespace

```bash
kubectl create namespace nacos || true
```

## 8-3. 编写 Nacos YAML

```bash
cat > nacos.yaml <<'EOF_NACOS'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nacos
  namespace: nacos
  labels:
    app: nacos
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nacos
  template:
    metadata:
      labels:
        app: nacos
    spec:
      containers:
        - name: nacos
          image: nacos/nacos-server:v2.3.2
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8848
            - name: grpc-client
              containerPort: 9848
            - name: grpc-raft
              containerPort: 9849
          env:
            - name: MODE
              value: standalone
            - name: NACOS_AUTH_ENABLE
              value: "true"
            - name: NACOS_AUTH_IDENTITY_KEY
              value: serverIdentity
            - name: NACOS_AUTH_IDENTITY_VALUE
              value: security
            - name: NACOS_AUTH_TOKEN
              value: "VGhpc0lzTXlDdXN0b21TZWNyZXRLZXkwMTIzNDU2Nzg="
            - name: JVM_XMS
              value: 512m
            - name: JVM_XMX
              value: 512m
            - name: JVM_XMN
              value: 256m
          readinessProbe:
            httpGet:
              path: /nacos/actuator/health
              port: http
            initialDelaySeconds: 60
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /nacos/actuator/health
              port: http
            initialDelaySeconds: 90
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: nacos
  namespace: nacos
  labels:
    app: nacos
spec:
  type: NodePort
  selector:
    app: nacos
  ports:
    - name: http
      port: 8848
      targetPort: 8848
      nodePort: 30848
    - name: grpc-client
      port: 9848
      targetPort: 9848
      nodePort: 31848
    - name: grpc-raft
      port: 9849
      targetPort: 9849
      nodePort: 31849
EOF_NACOS
```

说明：`NACOS_AUTH_TOKEN` 按 Nacos 2.3 官方认证文档建议使用 Base64 编码后的密钥，原始密钥长度不少于 32 字符。上面示例值由 `ThisIsMyCustomSecretKey012345678` 编码得到，生产部署请自行生成并妥善保存。

生成示例：

```bash
echo -n 'ThisIsMyCustomSecretKey012345678' | base64
```

## 8-4. 部署 Nacos

```bash
kubectl apply -f nacos.yaml
kubectl -n nacos get pods,svc -o wide
```

等待 Ready：

```bash
kubectl -n nacos rollout status deployment/nacos --timeout=180s
```

## 8-5. 访问验证

浏览器访问：

```text
http://10.1.106.71:30848/nacos
```

登录：

```text
账号：nacos
初始密码：nacos
```

首次登录后，进入用户管理页面，把 `nacos` 用户密码修改为符合生产复杂度要求的密码，例如：

```text
Nacos@123456
```

后续 Jenkins Credentials 中的 `nacos-auth` 使用修改后的密码。

## 8-6. 创建业务命名空间

本项目流水线会把不同分支部署到不同环境，并通过 Nacos Namespace 隔离服务注册信息。

在 Nacos 页面进入 `命名空间`，创建：

| 命名空间名称 | 命名空间 ID | 用途 |
|---|---|---|
| `dev` | `dev` | 开发环境 |
| `test` | `test` | 测试环境 |
| `prod` | `prod` | 生产环境 |

![Nacos 创建命名空间示例](./images/nacos-namespace-create.png)



![Nacos 命名空间列表示例](./images/nacos-namespace-list.png)

注意必须把 `命名空间 ID` 明确填成 `dev`、`test`、`prod`，否则 Jenkinsfile 中设置的 `SPRING_CLOUD_NACOS_DISCOVERY_NAMESPACE` 对不上。

K8s 内部服务地址：

```text
nacos.nacos.svc.cluster.local:8848
```

业务服务会使用这个地址注册到 Nacos。

---

> 微信: wingsreops
