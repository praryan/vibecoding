terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# CUR must be created in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# S3 bucket to receive Cost & Usage Reports (CUR)
resource "aws_s3_bucket" "cur_bucket" {
  bucket = var.cur_bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_public_access_block" "cur_bucket" {
  bucket                  = aws_s3_bucket.cur_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "cur_bucket" {
  bucket = aws_s3_bucket.cur_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cur_bucket" {
  bucket = aws_s3_bucket.cur_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket for Athena query results
resource "aws_s3_bucket" "athena_results_bucket" {
  bucket = var.athena_results_bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_public_access_block" "athena_results_bucket" {
  bucket                  = aws_s3_bucket.athena_results_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "athena_results_bucket" {
  bucket = aws_s3_bucket.athena_results_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results_bucket" {
  bucket = aws_s3_bucket.athena_results_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Glue database to catalog CUR tables
resource "aws_glue_catalog_database" "cost_intelligence" {
  name = var.glue_database_name
}

# IAM role for Glue Crawler
resource "aws_iam_role" "glue_role" {
  name               = "cost-intel-glue-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "glue.amazonaws.com" },
      Action = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Limit S3 access to the specific buckets
resource "aws_iam_role_policy" "glue_s3_policy" {
  name = "cost-intel-glue-s3"
  role = aws_iam_role.glue_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = [
          aws_s3_bucket.cur_bucket.arn,
          aws_s3_bucket.athena_results_bucket.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        Resource = [
          "${aws_s3_bucket.cur_bucket.arn}/*",
          "${aws_s3_bucket.athena_results_bucket.arn}/*"
        ]
      }
    ]
  })
}

# Glue crawler to discover CUR schema in S3
resource "aws_glue_crawler" "cur_crawler" {
  name         = "cost-intel-cur-crawler"
  role         = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.cost_intelligence.name
  s3_target {
    path = "s3://${aws_s3_bucket.cur_bucket.bucket}/${trim(var.cur_s3_prefix, "/")}/"
  }
  schedule = "cron(0 2 * * ? *)" # daily at 02:00 UTC
  tags     = var.tags
}

# Athena workgroup configured with S3 results location
resource "aws_athena_workgroup" "cost_wg" {
  name = "cost-intel-wg"
  configuration {
    enforce_workgroup_configuration = true
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results_bucket.bucket}/athena-results/"
    }
  }
  state = "ENABLED"
}

# SNS topic for alerts/notifications
resource "aws_sns_topic" "cost_alerts" {
  name = "cost-intel-alerts"
  tags = var.tags
}

# Optional: Create a CUR report definition (must be us-east-1)
resource "aws_cur_report_definition" "cur" {
  count       = var.enable_cur ? 1 : 0
  provider    = aws.us_east_1
  report_name = var.cur_report_name

  time_unit                     = "DAILY"
  format                        = "Parquet"
  compression                   = "Parquet"
  additional_schema_elements    = ["RESOURCES"]
  additional_artifacts          = ["ATHENA"]
  refresh_closed_reports        = true
  report_versioning             = "OVERWRITE_REPORT"

  s3_bucket = aws_s3_bucket.cur_bucket.bucket
  s3_prefix = trim(var.cur_s3_prefix, "/")
  s3_region = var.cur_s3_region
}
