import os
from typing import Optional


class Settings:
    """Application settings sourced from environment variables with safe defaults.

    These defaults are suitable for local development and should be overridden in production.
    """

    def __init__(self) -> None:
        # AWS/Athena configuration
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")
        self.athena_workgroup: str = os.getenv("ATHENA_WORKGROUP", "cost-intel-wg")
        self.athena_database: str = os.getenv("ATHENA_DATABASE", "cost_intelligence")
        self.cur_table_name: str = os.getenv("CUR_TABLE_NAME", "aws_cur")
        self.athena_results_s3: Optional[str] = os.getenv("ATHENA_RESULTS_S3")

        # Optional: SNS for alert testing
        self.sns_topic_arn: Optional[str] = os.getenv("SNS_TOPIC_ARN")

        # Query behavior
        self.athena_query_timeout_seconds: int = int(
            os.getenv("ATHENA_QUERY_TIMEOUT_SECONDS", "120")
        )


settings = Settings()
