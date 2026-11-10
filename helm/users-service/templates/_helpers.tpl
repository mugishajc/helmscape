{{- define "users-service.name" -}}
users-service
{{- end -}}

{{- define "users-service.labels" -}}
app.kubernetes.io/name: {{ include "users-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
