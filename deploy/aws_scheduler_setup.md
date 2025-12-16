# AWS EC2 자동 시작/종료 설정 가이드

## 개요
- **시작**: 평일 08:50 KST (장 시작 10분 전)
- **종료**: 평일 15:40 KST (장 마감 10분 후)
- **비용 절감**: 하루 약 7시간만 실행 (24시간 대비 ~70% 절감)

## 1단계: EC2 인스턴스 ID 확인

AWS 콘솔 또는 CLI에서 확인:
```bash
# EC2 인스턴스 ID 확인 (52.62.241.70의 인스턴스)
aws ec2 describe-instances --filters "Name=ip-address,Values=52.62.241.70" --query "Reservations[].Instances[].InstanceId" --output text
```

## 2단계: IAM 역할 생성

### 2.1 Lambda 실행 역할 생성

AWS 콘솔 > IAM > 역할 > 역할 만들기:
1. 신뢰할 수 있는 엔터티: Lambda
2. 정책 연결: 아래 JSON으로 인라인 정책 생성

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:DescribeInstances"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
```

역할 이름: `EC2SchedulerRole`

## 3단계: Lambda 함수 생성

### 3.1 EC2 시작 함수

AWS 콘솔 > Lambda > 함수 생성:
- 함수 이름: `StartTradingEC2`
- 런타임: Python 3.12
- 실행 역할: EC2SchedulerRole

코드:
```python
import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='ap-southeast-2')  # Sydney
    instance_id = 'YOUR_INSTANCE_ID'  # 실제 인스턴스 ID로 변경
    
    ec2.start_instances(InstanceIds=[instance_id])
    
    return {
        'statusCode': 200,
        'body': f'Started instance {instance_id}'
    }
```

### 3.2 EC2 종료 함수

함수 이름: `StopTradingEC2`

코드:
```python
import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='ap-southeast-2')  # Sydney
    instance_id = 'YOUR_INSTANCE_ID'  # 실제 인스턴스 ID로 변경
    
    ec2.stop_instances(InstanceIds=[instance_id])
    
    return {
        'statusCode': 200,
        'body': f'Stopped instance {instance_id}'
    }
```

## 4단계: EventBridge 스케줄 생성

### 4.1 시작 스케줄

AWS 콘솔 > Amazon EventBridge > 스케줄 > 스케줄 생성:
- 스케줄 이름: `StartTradingEC2Schedule`
- 스케줄 유형: 반복 스케줄
- Cron 표현식: `50 23 ? * SUN-THU *`
  - (UTC 23:50 = KST 08:50, 일~목 = 한국 월~금)
- 대상: Lambda 함수 `StartTradingEC2`

### 4.2 종료 스케줄

- 스케줄 이름: `StopTradingEC2Schedule`
- Cron 표현식: `40 6 ? * MON-FRI *`
  - (UTC 06:40 = KST 15:40)
- 대상: Lambda 함수 `StopTradingEC2`

## 5단계: 테스트

Lambda 콘솔에서 각 함수 테스트:
1. `StartTradingEC2` 테스트 → EC2 시작 확인
2. `StopTradingEC2` 테스트 → EC2 종료 확인

## 주의사항

1. **공휴일 처리**: 한국 공휴일에는 수동으로 스케줄 비활성화 필요
2. **IP 변경**: EC2 재시작 시 Public IP가 변경됨
   - 해결책: Elastic IP 할당 (무료, 실행 중일 때만)
3. **서비스 자동 시작**: systemd 서비스가 `enabled` 상태면 EC2 시작 시 자동 실행됨

## Elastic IP 설정 (권장)

EC2 재시작 시 IP 유지를 위해:
1. AWS 콘솔 > EC2 > 탄력적 IP > 탄력적 IP 주소 할당
2. 할당된 IP를 인스턴스에 연결
3. 새 IP로 SSH 접속 설정 업데이트

## 비용 예상

| 항목 | 월 비용 (USD) |
|------|---------------|
| EC2 t3.micro (7시간/일 × 22일) | ~$3.50 |
| Lambda (60회/월) | 무료 |
| EventBridge | 무료 |
| Elastic IP (실행 중) | 무료 |
| **총계** | **~$3.50/월** |

(24시간 실행 시 ~$12/월 대비 약 70% 절감)
