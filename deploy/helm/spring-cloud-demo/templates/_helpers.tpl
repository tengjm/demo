{{- define "spring-cloud-demo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "spring-cloud-demo.fullname" -}}
{{- $name := include "spring-cloud-demo.name" . -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "spring-cloud-demo.labels" -}}
app.kubernetes.io/name: {{ include "spring-cloud-demo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "spring-cloud-demo.image" -}}
{{- printf "%s/%s/%s:%s" .root.Values.global.imageRegistry .root.Values.global.imageProject .repository .tag -}}
{{- end -}}
