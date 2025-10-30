output "cur_bucket_name" {
  value       = aws_s3_bucket.cur_bucket.bucket
  description = "S3 bucket where CUR reports are delivered"
}

output "athena_results_bucket_name" {
  value       = aws_s3_bucket.athena_results_bucket.bucket
  description = "S3 bucket for Athena query results"
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.cost_intelligence.name
  description = "Glue catalog database name for CUR tables"
}

output "athena_workgroup_name" {
  value       = aws_athena_workgroup.cost_wg.name
  description = "Athena workgroup used for queries"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.cost_alerts.arn
  description = "SNS topic ARN for alerts/notifications"
}
