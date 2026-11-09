{{- define "orders-service.name" -}}
orders-service
{{- end -}}

{{- define "orders-service.labels" -}}
app.kubernetes.io/name: {{ include "orders-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
