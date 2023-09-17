variable "vpc_id" {
  type        = string
  description = "The VPC id"
}

variable "zone_id" {
  type        = string
  description = "Cloudflare zone ID for domain bianxm.dev"
}

variable "cert_arn" {
  type        = string
  description = "Amazon-issued TLS certificate ARN"
}