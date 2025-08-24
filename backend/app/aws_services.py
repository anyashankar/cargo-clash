"""AWS services integration for Cargo Clash."""

import json
import logging
from typing import Dict, List, Any, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .config import settings

logger = logging.getLogger(__name__)


class SQSService:
    """Amazon SQS service for handling game events."""
    
    def __init__(self):
        try:
            self.sqs = boto3.client(
                'sqs',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self.queue_url = settings.sqs_queue_url
            self._test_connection()
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"SQS initialization failed: {e}. Using local fallback.")
            self.sqs = None
            self.queue_url = None
    
    def _test_connection(self):
        """Test SQS connection."""
        if self.sqs and self.queue_url:
            try:
                self.sqs.get_queue_attributes(
                    QueueUrl=self.queue_url,
                    AttributeNames=['QueueArn']
                )
                logger.info("SQS connection established successfully")
            except ClientError as e:
                logger.warning(f"SQS connection test failed: {e}")
                self.sqs = None
    
    async def send_game_event(self, event_type: str, event_data: Dict[str, Any], delay_seconds: int = 0) -> bool:
        """Send a game event to SQS queue."""
        if not self.sqs or not self.queue_url:
            logger.warning("SQS not available, processing event locally")
            return await self._process_event_locally(event_type, event_data)
        
        try:
            message_body = {
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "cargo-clash-backend"
            }
            
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                DelaySeconds=delay_seconds,
                MessageAttributes={
                    'EventType': {
                        'StringValue': event_type,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Game event sent to SQS: {event_type}, MessageId: {response['MessageId']}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to send message to SQS: {e}")
            return await self._process_event_locally(event_type, event_data)
    
    async def receive_game_events(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Receive game events from SQS queue."""
        if not self.sqs or not self.queue_url:
            return []
        
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=1,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            events = []
            
            for message in messages:
                try:
                    body = json.loads(message['Body'])
                    events.append({
                        'receipt_handle': message['ReceiptHandle'],
                        'event_type': body['event_type'],
                        'event_data': body['event_data'],
                        'timestamp': body['timestamp']
                    })
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse SQS message: {e}")
            
            return events
            
        except ClientError as e:
            logger.error(f"Failed to receive messages from SQS: {e}")
            return []
    
    async def delete_message(self, receipt_handle: str) -> bool:
        """Delete a processed message from SQS queue."""
        if not self.sqs or not self.queue_url:
            return True
        
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete SQS message: {e}")
            return False
    
    async def _process_event_locally(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Fallback to process events locally when SQS is unavailable."""
        logger.info(f"Processing event locally: {event_type}")
        # This would integrate with the local event processing system
        return True


class S3Service:
    """Amazon S3 service for storing game assets and logs."""
    
    def __init__(self):
        try:
            self.s3 = boto3.client(
                's3',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self.bucket_name = f"cargo-clash-{settings.aws_region}"
            logger.info("S3 service initialized")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"S3 initialization failed: {e}")
            self.s3 = None
    
    async def upload_game_log(self, log_data: Dict[str, Any], log_type: str) -> Optional[str]:
        """Upload game logs to S3."""
        if not self.s3:
            return None
        
        try:
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H")
            key = f"game-logs/{log_type}/{timestamp}/{log_data.get('id', 'unknown')}.json"
            
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(log_data),
                ContentType='application/json'
            )
            
            return f"s3://{self.bucket_name}/{key}"
            
        except ClientError as e:
            logger.error(f"Failed to upload log to S3: {e}")
            return None
    
    async def upload_player_data_backup(self, player_id: int, backup_data: Dict[str, Any]) -> Optional[str]:
        """Upload player data backup to S3."""
        if not self.s3:
            return None
        
        try:
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            key = f"player-backups/{player_id}/backup_{timestamp}.json"
            
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(backup_data),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            return f"s3://{self.bucket_name}/{key}"
            
        except ClientError as e:
            logger.error(f"Failed to upload player backup to S3: {e}")
            return None


class CloudWatchService:
    """Amazon CloudWatch service for monitoring and metrics."""
    
    def __init__(self):
        try:
            self.cloudwatch = boto3.client(
                'cloudwatch',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self.namespace = 'CargoClash/Game'
            logger.info("CloudWatch service initialized")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"CloudWatch initialization failed: {e}")
            self.cloudwatch = None
    
    async def put_metric(self, metric_name: str, value: float, unit: str = 'Count', dimensions: Dict[str, str] = None):
        """Send custom metric to CloudWatch."""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': key, 'Value': value} 
                    for key, value in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
        except ClientError as e:
            logger.error(f"Failed to send metric to CloudWatch: {e}")
    
    async def put_game_metrics(self, metrics: Dict[str, float]):
        """Send multiple game metrics to CloudWatch."""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = []
            for metric_name, value in metrics.items():
                metric_data.append({
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': 'Count'
                })
            
            # Send in batches of 20 (CloudWatch limit)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
        except ClientError as e:
            logger.error(f"Failed to send game metrics to CloudWatch: {e}")


class SecretsManagerService:
    """AWS Secrets Manager for handling sensitive configuration."""
    
    def __init__(self):
        try:
            self.secrets_client = boto3.client(
                'secretsmanager',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            logger.info("Secrets Manager service initialized")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"Secrets Manager initialization failed: {e}")
            self.secrets_client = None
    
    async def get_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a secret from AWS Secrets Manager."""
        if not self.secrets_client:
            return None
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
            
        except ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            return None
    
    async def update_secret(self, secret_name: str, secret_data: Dict[str, Any]) -> bool:
        """Update a secret in AWS Secrets Manager."""
        if not self.secrets_client:
            return False
        
        try:
            self.secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_data)
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update secret {secret_name}: {e}")
            return False


class AWSServiceManager:
    """Manager for all AWS services."""
    
    def __init__(self):
        self.sqs = SQSService()
        self.s3 = S3Service()
        self.cloudwatch = CloudWatchService()
        self.secrets_manager = SecretsManagerService()
        
        logger.info("AWS Service Manager initialized")
    
    async def send_player_action_event(self, player_id: int, action_type: str, action_data: Dict[str, Any]):
        """Send player action event to SQS for processing."""
        event_data = {
            "player_id": player_id,
            "action_type": action_type,
            "action_data": action_data
        }
        
        await self.sqs.send_game_event("player_action", event_data)
    
    async def send_game_state_change(self, change_type: str, change_data: Dict[str, Any]):
        """Send game state change event to SQS."""
        await self.sqs.send_game_event("game_state_change", {
            "change_type": change_type,
            "change_data": change_data
        })
    
    async def log_combat_event(self, combat_data: Dict[str, Any]):
        """Log combat event to S3 and send metrics to CloudWatch."""
        # Upload detailed log to S3
        await self.s3.upload_game_log(combat_data, "combat")
        
        # Send metrics to CloudWatch
        await self.cloudwatch.put_metric("CombatEvents", 1.0)
        
        if combat_data.get("winner_id"):
            await self.cloudwatch.put_metric("CombatWins", 1.0, dimensions={
                "PlayerId": str(combat_data["winner_id"])
            })
    
    async def log_mission_completion(self, mission_data: Dict[str, Any]):
        """Log mission completion event."""
        await self.s3.upload_game_log(mission_data, "missions")
        await self.cloudwatch.put_metric("MissionsCompleted", 1.0)
        
        if mission_data.get("reward_credits"):
            await self.cloudwatch.put_metric("CreditsAwarded", mission_data["reward_credits"])
    
    async def backup_player_data(self, player_id: int, player_data: Dict[str, Any]):
        """Backup player data to S3."""
        backup_url = await self.s3.upload_player_data_backup(player_id, player_data)
        if backup_url:
            logger.info(f"Player {player_id} data backed up to {backup_url}")
    
    async def send_daily_metrics(self, metrics: Dict[str, float]):
        """Send daily game metrics to CloudWatch."""
        await self.cloudwatch.put_game_metrics(metrics)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all AWS services."""
        return {
            "sqs": self.sqs.sqs is not None,
            "s3": self.s3.s3 is not None,
            "cloudwatch": self.cloudwatch.cloudwatch is not None,
            "secrets_manager": self.secrets_manager.secrets_client is not None
        }


# Global AWS service manager instance
aws_services = AWSServiceManager()

# Import datetime for timestamp generation
from datetime import datetime
