# EC2 자동 시작/종료 Terraform 설정
# AWS EC2 Auto Start/Stop Terraform Configuration

variable "instance_id" {
  description = "EC2 Instance ID to schedule"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ap-southeast-2"  # Sydney
}

provider "aws" {
  region = var.aws_region
}

# IAM Role for Lambda
resource "aws_iam_role" "ec2_scheduler_role" {
  name = "EC2SchedulerRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ec2_scheduler_policy" {
  name = "EC2SchedulerPolicy"
  role = aws_iam_role.ec2_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda: Start EC2
resource "aws_lambda_function" "start_ec2" {
  filename         = "lambda_start.zip"
  function_name    = "StartTradingEC2"
  role             = aws_iam_role.ec2_scheduler_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      INSTANCE_ID = var.instance_id
      REGION      = var.aws_region
    }
  }
}

# Lambda: Stop EC2
resource "aws_lambda_function" "stop_ec2" {
  filename         = "lambda_stop.zip"
  function_name    = "StopTradingEC2"
  role             = aws_iam_role.ec2_scheduler_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      INSTANCE_ID = var.instance_id
      REGION      = var.aws_region
    }
  }
}

# EventBridge: Start Schedule (KST 08:50 = UTC 23:50 previous day)
resource "aws_cloudwatch_event_rule" "start_schedule" {
  name                = "StartTradingEC2Schedule"
  description         = "Start trading EC2 at 08:50 KST on weekdays"
  schedule_expression = "cron(50 23 ? * SUN-THU *)"
}

resource "aws_cloudwatch_event_target" "start_target" {
  rule      = aws_cloudwatch_event_rule.start_schedule.name
  target_id = "StartTradingEC2"
  arn       = aws_lambda_function.start_ec2.arn
}

resource "aws_lambda_permission" "allow_start_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.start_ec2.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.start_schedule.arn
}

# EventBridge: Stop Schedule (KST 15:40 = UTC 06:40)
resource "aws_cloudwatch_event_rule" "stop_schedule" {
  name                = "StopTradingEC2Schedule"
  description         = "Stop trading EC2 at 15:40 KST on weekdays"
  schedule_expression = "cron(40 6 ? * MON-FRI *)"
}

resource "aws_cloudwatch_event_target" "stop_target" {
  rule      = aws_cloudwatch_event_rule.stop_schedule.name
  target_id = "StopTradingEC2"
  arn       = aws_lambda_function.stop_ec2.arn
}

resource "aws_lambda_permission" "allow_stop_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stop_ec2.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stop_schedule.arn
}

output "start_lambda_arn" {
  value = aws_lambda_function.start_ec2.arn
}

output "stop_lambda_arn" {
  value = aws_lambda_function.stop_ec2.arn
}
