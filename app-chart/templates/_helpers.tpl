{{/* services/app-chart/templates/_helpers.tpl */}}

{{/*
Define the full name of the app.
*/}}
{{- define "app-chart.fullname" -}}
{{- .Values.appName | trunc 63 | trimSuffix "-" -}}
{{- end -}}
