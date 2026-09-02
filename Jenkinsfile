pipeline {
  agent {
    kubernetes {
      defaultContainer 'maven'
      yaml '''
apiVersion: v1
kind: Pod
spec:
  nodeSelector:
    harbor-insecure: "true"
  containers:
    - name: maven
      image: 172.24.76.66:8088/ci-tools/maven:3.9.9-eclipse-temurin-8
      command: ['cat']
      tty: true
      volumeMounts:
        - name: maven-cache
          mountPath: /root/.m2
    - name: kaniko
      image: 172.24.76.66:8088/ci-tools/kaniko-executor:v1.23.2-debug
      command: ['/busybox/cat']
      tty: true
      volumeMounts:
        - name: docker-config
          mountPath: /kaniko/.docker
    - name: helm
      image: 172.24.76.66:8088/ci-tools/helm-kubectl:3.16.3
      command: ['cat']
      tty: true
    - name: jnlp
      image: 172.24.76.66:8088/ci-tools/jenkins-inbound-agent:3355.v388858a_47b_33-3-jdk21
      resources:
        requests:
          cpu: "100m"
          memory: "256Mi"
  volumes:
    - name: maven-cache
      hostPath:
        path: /var/lib/jenkins-agent/m2-cache
        type: DirectoryOrCreate
    - name: docker-config
      emptyDir: {}
'''
    }
  }

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    HARBOR_REGISTRY = '172.24.76.66:8088'
    CI_TOOLS_PROJECT = 'ci-tools'
    HARBOR_PROJECT = 'devops-demo'
    HELM_RELEASE = 'spring-cloud-demo'
    CHART_DIR = 'deploy/helm/spring-cloud-demo'
    NACOS_ADDR = 'nacos.nacos.svc.cluster.local:8848'
    NACOS_AUTH_SECRET = 'nacos-auth'
  }

  stages {
    stage('Resolve Environment') {
      steps {
        script {
          def branch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: 'main'
          branch = branch.replaceFirst(/^origin\\//, '')
          env.SOURCE_BRANCH = branch
          sh 'git config --global --add safe.directory "$WORKSPACE"'
          env.SHORT_COMMIT = sh(script: 'git rev-parse --short=8 HEAD', returnStdout: true).trim()

          if (env.TAG_NAME || branch ==~ /^v\\d+.*/) {
            env.DEPLOY_ENV = 'prod'
            env.NAMESPACE = 'prod'
            env.NACOS_NAMESPACE = 'prod'
            env.VALUES_FILE = 'values-prod.yaml'
            env.IMAGE_TAG = env.TAG_NAME ?: branch
            env.REQUIRE_APPROVAL = 'true'
          } else if (branch ==~ /^release\\/.*/) {
            env.DEPLOY_ENV = 'test'
            env.NAMESPACE = 'test'
            env.NACOS_NAMESPACE = 'test'
            env.VALUES_FILE = 'values-test.yaml'
            env.IMAGE_TAG = branch.replaceAll('[^A-Za-z0-9_.-]', '-') + '-' + env.SHORT_COMMIT
            env.REQUIRE_APPROVAL = 'false'
          } else if (branch == 'dev' || branch == 'develop' || branch ==~ /^feature\\/.*/) {
            env.DEPLOY_ENV = 'dev'
            env.NAMESPACE = 'dev'
            env.NACOS_NAMESPACE = 'dev'
            env.VALUES_FILE = 'values-dev.yaml'
            env.IMAGE_TAG = branch.replaceAll('[^A-Za-z0-9_.-]', '-') + '-' + env.SHORT_COMMIT
            env.REQUIRE_APPROVAL = 'false'
          } else if (branch == 'main') {
            env.DEPLOY_ENV = 'prod'
            env.NAMESPACE = 'prod'
            env.NACOS_NAMESPACE = 'prod'
            env.VALUES_FILE = 'values-prod.yaml'
            env.IMAGE_TAG = 'main-' + env.SHORT_COMMIT
            env.REQUIRE_APPROVAL = 'true'
          } else {
            env.DEPLOY_ENV = 'none'
            env.NAMESPACE = ''
            env.NACOS_NAMESPACE = ''
            env.VALUES_FILE = ''
            env.IMAGE_TAG = branch.replaceAll('[^A-Za-z0-9_.-]', '-') + '-' + env.SHORT_COMMIT
            env.REQUIRE_APPROVAL = 'false'
          }

          echo "branch=${env.SOURCE_BRANCH}, imageTag=${env.IMAGE_TAG}, deployEnv=${env.DEPLOY_ENV}"
        }
      }
    }

    stage('Maven Build') {
      steps {
        container('maven') {
          script {
            writeFile file: 'settings.xml', text: '''<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 https://maven.apache.org/xsd/settings-1.0.0.xsd">
              <mirrors>
                <mirror>
                  <id>aliyunmaven</id>
                  <name>aliyun maven</name>
                  <url>https://maven.aliyun.com/repository/public</url>
                  <mirrorOf>*</mirrorOf>
                </mirror>
              </mirrors>
            </settings>
'''
          }
          sh 'mvn -s "$WORKSPACE/settings.xml" -B -DskipTests=false clean package'
        }
      }
    }

    stage('Prepare Kaniko Auth') {
      steps {
        container('kaniko') {
          withCredentials([usernamePassword(credentialsId: 'harbor-admin', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASSWORD')]) {
            sh '''
              AUTH="$(printf '%s:%s' "$HARBOR_USER" "$HARBOR_PASSWORD" | base64 | tr -d '\\n')"
              cat > /kaniko/.docker/config.json <<EOF
{"auths":{"${HARBOR_REGISTRY}":{"auth":"${AUTH}"}}}
EOF
            '''
          }
        }
      }
    }

    stage('Build and Push Images') {
      steps {
        container('kaniko') {
          sh '''
            /kaniko/executor \
              --context "${WORKSPACE}/date-service" \
              --dockerfile "${WORKSPACE}/date-service/Dockerfile" \
              --destination "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/date-service:${IMAGE_TAG}" \
              --insecure \
              --skip-tls-verify
          '''
          sh '''
            /kaniko/executor \
              --context "${WORKSPACE}/hello-service" \
              --dockerfile "${WORKSPACE}/hello-service/Dockerfile" \
              --destination "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/hello-service:${IMAGE_TAG}" \
              --insecure \
              --skip-tls-verify
          '''
        }
      }
    }

    stage('Approval') {
      when {
        expression { env.REQUIRE_APPROVAL == 'true' }
      }
      steps {
        input message: "Deploy ${env.IMAGE_TAG} to ${env.DEPLOY_ENV}?", ok: 'Deploy'
      }
    }

    stage('Helm Deploy') {
      when {
        expression { env.DEPLOY_ENV != 'none' }
      }
      steps {
        container('helm') {
          withCredentials([
            file(credentialsId: 'kubeconfig-main', variable: 'KUBECONFIG_FILE'),
            usernamePassword(credentialsId: 'nacos-auth', usernameVariable: 'NACOS_USER', passwordVariable: 'NACOS_PASSWORD')
          ]) {
            sh '''
              export KUBECONFIG="$KUBECONFIG_FILE"
              kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"
              kubectl delete secret "$NACOS_AUTH_SECRET" -n "$NAMESPACE" --ignore-not-found
              kubectl create secret generic "$NACOS_AUTH_SECRET" \
                -n "$NAMESPACE" \
                --from-literal=username="$NACOS_USER" \
                --from-literal=password="$NACOS_PASSWORD"
              helm lint "$CHART_DIR" -f "$CHART_DIR/$VALUES_FILE"
              helm upgrade --install "$HELM_RELEASE" "$CHART_DIR" \
                -n "$NAMESPACE" \
                -f "$CHART_DIR/$VALUES_FILE" \
                --set global.imageRegistry="$HARBOR_REGISTRY" \
                --set global.imageProject="$HARBOR_PROJECT" \
                --set global.nacosAddr="$NACOS_ADDR" \
                --set global.nacosNamespace="$NACOS_NAMESPACE" \
                --set global.nacosAuth.enabled=true \
                --set global.nacosAuth.secretName="$NACOS_AUTH_SECRET" \
                --set dateService.image.tag="$IMAGE_TAG" \
                --set helloService.image.tag="$IMAGE_TAG" \
                --atomic \
                --timeout 10m
            '''
          }
        }
      }
    }

    stage('Verify Deployment') {
      when {
        expression { env.DEPLOY_ENV != 'none' }
      }
      steps {
        container('helm') {
          withCredentials([file(credentialsId: 'kubeconfig-main', variable: 'KUBECONFIG_FILE')]) {
            sh '''
              export KUBECONFIG="$KUBECONFIG_FILE"
              kubectl rollout status deployment/date-service -n "$NAMESPACE" --timeout=120s
              kubectl rollout status deployment/hello-service -n "$NAMESPACE" --timeout=120s
              kubectl get pods,svc -n "$NAMESPACE" -l app.kubernetes.io/instance="$HELM_RELEASE" -o wide

              if [ "$NAMESPACE" = "dev" ] || [ "$NAMESPACE" = "test" ]; then
                NODE_PORT="$(kubectl get svc hello-service -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')"
                NODE_IP="$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')"
                wget -qO- "http://${NODE_IP}:${NODE_PORT}/" | grep -q "你好"
              fi
            '''
          }
        }
      }
    }
  }

  post {
    failure {
      echo 'Pipeline failed. Helm --atomic will roll back failed deployments automatically.'
    }
  }
}
