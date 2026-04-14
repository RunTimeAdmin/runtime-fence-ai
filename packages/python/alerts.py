"""
Runtime Fence - Alert System
Email and SMS notifications for security events.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fence_alerts")


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    KILL_SWITCH = "kill_switch"


@dataclass
class AlertConfig:
    """Configuration for alert notifications."""
    enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    
    # Email settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    from_email: str = os.getenv("ALERT_FROM_EMAIL", "alerts@runtimefence.com")
    to_emails: List[str] = None
    
    # SMS settings (Twilio)
    twilio_sid: str = os.getenv("TWILIO_SID", "")
    twilio_token: str = os.getenv("TWILIO_TOKEN", "")
    twilio_from: str = os.getenv("TWILIO_FROM", "")
    sms_numbers: List[str] = None
    
    # Alert thresholds
    min_level: AlertLevel = AlertLevel.WARNING
    
    def __post_init__(self):
        if self.to_emails is None:
            env_emails = os.getenv("ALERT_TO_EMAILS", "")
            self.to_emails = [e.strip() for e in env_emails.split(",") if e.strip()]
        if self.sms_numbers is None:
            env_numbers = os.getenv("ALERT_SMS_NUMBERS", "")
            self.sms_numbers = [n.strip() for n in env_numbers.split(",") if n.strip()]


class AlertManager:
    """Manages sending alerts via email and SMS."""
    
    def __init__(self, config: AlertConfig = None):
        self.config = config or AlertConfig()
        self.alert_history: List[dict] = []
    
    def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        agent_id: str = None,
        action: str = None,
        target: str = None,
        risk_score: int = 0
    ) -> bool:
        """Send an alert notification."""
        if not self.config.enabled:
            return False
        
        # Check if level meets threshold
        level_priority = {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.CRITICAL: 2,
            AlertLevel.KILL_SWITCH: 3
        }
        
        if level_priority[level] < level_priority[self.config.min_level]:
            logger.debug(f"Alert level {level} below threshold {self.config.min_level}")
            return False
        
        # Build alert data
        alert_data = {
            "level": level.value,
            "title": title,
            "message": message,
            "agent_id": agent_id,
            "action": action,
            "target": target,
            "risk_score": risk_score,
            "timestamp": __import__("time").time()
        }
        
        self.alert_history.append(alert_data)
        
        # Send notifications
        email_sent = False
        sms_sent = False
        
        if self.config.email_enabled:
            email_sent = self._send_email(level, title, message, alert_data)
        
        if self.config.sms_enabled:
            sms_sent = self._send_sms(level, title, message)
        
        logger.info(f"Alert sent: {title} (email={email_sent}, sms={sms_sent})")
        return email_sent or sms_sent
    
    def _send_email(self, level: AlertLevel, title: str, message: str, data: dict) -> bool:
        """Send email alert."""
        if not self.config.smtp_user or not self.config.to_emails:
            logger.warning("Email not configured - skipping email alert")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[Runtime Fence {level.value.upper()}] {title}"
            msg["From"] = self.config.from_email
            msg["To"] = ", ".join(self.config.to_emails)
            
            # Plain text version
            text_body = f"""
Runtime Fence Alert
====================

Level: {level.value.upper()}
Title: {title}

{message}

Details:
- Agent ID: {data.get('agent_id', 'N/A')}
- Action: {data.get('action', 'N/A')}
- Target: {data.get('target', 'N/A')}
- Risk Score: {data.get('risk_score', 0)}%

---
This is an automated alert from Runtime Fence.
"""
            
            # HTML version
            color = {
                AlertLevel.INFO: "#3b82f6",
                AlertLevel.WARNING: "#f59e0b",
                AlertLevel.CRITICAL: "#ef4444",
                AlertLevel.KILL_SWITCH: "#dc2626"
            }.get(level, "#666")
            
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 24px;">Runtime Fence Alert</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">{level.value.upper()}</p>
    </div>
    <div style="padding: 20px; background: #f9fafb; border: 1px solid #e5e7eb; border-top: none;">
        <h2 style="margin-top: 0;">{title}</h2>
        <p>{message}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <tr style="background: #fff;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Agent ID</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{data.get('agent_id', 'N/A')}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Action</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{data.get('action', 'N/A')}</td>
            </tr>
            <tr style="background: #fff;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Target</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{data.get('target', 'N/A')}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Risk Score</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{data.get('risk_score', 0)}%</td>
            </tr>
        </table>
    </div>
    <div style="padding: 15px; background: #e5e7eb; border-radius: 0 0 8px 8px; text-align: center; color: #666; font-size: 12px;">
        Automated alert from Runtime Fence
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_sms(self, level: AlertLevel, title: str, message: str) -> bool:
        """Send SMS alert via Twilio."""
        if not self.config.twilio_sid or not self.config.sms_numbers:
            logger.warning("SMS not configured - skipping SMS alert")
            return False
        
        try:
            from twilio.rest import Client
            
            client = Client(self.config.twilio_sid, self.config.twilio_token)
            sms_body = f"[{level.value.upper()}] {title}: {message[:100]}"
            
            for number in self.config.sms_numbers:
                client.messages.create(
                    body=sms_body,
                    from_=self.config.twilio_from,
                    to=number
                )
            
            return True
            
        except ImportError:
            logger.warning("Twilio not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
    
    def alert_blocked_action(self, agent_id: str, action: str, target: str, risk_score: int, reasons: List[str]):
        """Send alert for blocked action."""
        self.send_alert(
            level=AlertLevel.WARNING if risk_score < 90 else AlertLevel.CRITICAL,
            title=f"Action Blocked: {action}",
            message=f"Agent '{agent_id}' attempted blocked action. Reasons: {', '.join(reasons)}",
            agent_id=agent_id,
            action=action,
            target=target,
            risk_score=risk_score
        )
    
    def alert_kill_switch(self, agent_id: str, reason: str):
        """Send alert for kill switch activation."""
        self.send_alert(
            level=AlertLevel.KILL_SWITCH,
            title="KILL SWITCH ACTIVATED",
            message=f"Agent '{agent_id or 'ALL'}' has been terminated. Reason: {reason}",
            agent_id=agent_id,
            risk_score=100
        )
    
    def alert_new_agent_detected(self, agent_name: str, risk_level: str, pid: int):
        """Send alert for new agent detection."""
        self.send_alert(
            level=AlertLevel.INFO if risk_level == "low" else AlertLevel.WARNING,
            title=f"New Agent Detected: {agent_name}",
            message=f"A new AI agent has been detected running on your system (PID: {pid}, Risk: {risk_level})",
            agent_id=agent_name,
            risk_score={"low": 25, "medium": 50, "high": 75}.get(risk_level, 50)
        )


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None

def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager

def configure_alerts(config: AlertConfig):
    """Configure the global alert manager."""
    global _alert_manager
    _alert_manager = AlertManager(config)


# Convenience functions
def alert_blocked(agent_id: str, action: str, target: str, risk_score: int, reasons: List[str]):
    get_alert_manager().alert_blocked_action(agent_id, action, target, risk_score, reasons)

def alert_kill(agent_id: str, reason: str):
    get_alert_manager().alert_kill_switch(agent_id, reason)

def alert_detected(agent_name: str, risk_level: str, pid: int):
    get_alert_manager().alert_new_agent_detected(agent_name, risk_level, pid)
