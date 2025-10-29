variable "region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "cur_bucket_name" {
  description = "S3 bucket name to receive AWS CUR (must be globally unique)"
  type        = string
}

variable "athena_results_bucket_name" {
  description = "S3 bucket name for Athena query results (must be globally unique)"
  type        = string
}

variable "glue_database_name" {
  description = "Glue catalog database name for cost intelligence"
  type        = string
  default     = "cost_intelligence"
}

variable "cur_s3_prefix" {
  description = "S3 prefix (folder) under CUR bucket to store reports"
  type        = string
  default     = "cur/"
}

variable "enable_cur" {
  description = "Whether to create a CUR report definition (requires billing permissions in us-east-1)"
  type        = bool
  default     = false
}

variable "cur_report_name" {
  description = "Name of the CUR report definition"
  type        = string
  default     = "aws-cost-usage-report"
}

variable "cur_s3_region" {
  description = "Region of the CUR S3 bucket (CUR API requires explicit region)"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}
