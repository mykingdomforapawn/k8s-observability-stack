{{/*
Defines a standard helper template to generate a unique and safe name for Kubernetes resources.
This name is used in the Deployment, Service, and labels.
*/}}
{{- define "app-chart.fullname" -}}
{{/*
Takes the 'appName' from values.yaml, truncates it to 63 characters (the K8s name limit),
and removes any trailing hyphen to ensure a valid DNS-compatible name.
*/}}
{{- .Values.appName | trunc 63 | trimSuffix "-" -}}
{{- end -}}
