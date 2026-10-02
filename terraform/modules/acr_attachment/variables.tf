variable "acr_id" {
  type        = string
  description = "Resource ID of the Container Registry."
}

variable "kubelet_identity_object_id" {
  type        = string
  description = "Object ID of the AKS kubelet managed identity."
}

variable "enable_acr_pull" {
  type        = bool
  default     = true
  description = "Flag to enable AcrPull role assignment."
}
