from celery import shared_task
from celery.utils.log import get_task_logger
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from ..core.config import get_settings
from ..core.database import Database
from ..ads.analytics import AdAnalytics

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
ad_analytics = AdAnalytics(db)
logger = get_task_logger(__name__)

@shared_task(name='app.tasks.analytics.update_campaign_stats')
def update_campaign_stats() -> Dict[int, Dict]:
    """Update statistics for all active campaigns."""
    try:
        logger.info("Updating campaign statistics")
        results = {}
        
        # Get active campaigns
        campaigns = db.fetch_all(
            """
            SELECT id FROM ad_campaigns 
            WHERE status = 'active'
            """
        )
        
        for campaign in campaigns:
            campaign_id = campaign['id']
            try:
                # Get campaign metrics
                metrics = ad_analytics.get_campaign_metrics(campaign_id)
                
                # Store metrics in cache
                cache_key = f"campaign_metrics:{campaign_id}"
                metrics['timestamp'] = datetime.now().isoformat()
                
                # Update campaign stats in database
                db.update(
                    'ad_campaigns',
                    {
                        'last_metrics': json.dumps(metrics),
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    },
                    {'id': campaign_id}
                )
                
                results[campaign_id] = metrics
                
            except Exception as e:
                logger.error(f"Error updating stats for campaign {campaign_id}: {str(e)}")
                results[campaign_id] = {'error': str(e)}
        
        return results

    except Exception as e:
        logger.error(f"Error updating campaign stats: {str(e)}")
        raise

@shared_task(name='app.tasks.analytics.generate_daily_reports', bind=True)
def generate_daily_reports(self, send_email: bool = True) -> Dict[str, str]:
    """Generate daily analytics reports."""
    try:
        logger.info("Generating daily reports")
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        report_date = yesterday.strftime('%Y-%m-%d')
        
        # Create reports directory
        reports_dir = Path('reports') / report_date
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        reports = {}
        
        # Generate campaign performance report
        campaign_report = generate_campaign_report(yesterday)
        report_path = reports_dir / 'campaign_performance.pdf'
        campaign_report.savefig(report_path)
        plt.close()
        reports['campaign_performance'] = str(report_path)
        
        # Generate asset performance report
        asset_report = generate_asset_report(yesterday)
        report_path = reports_dir / 'asset_performance.pdf'
        asset_report.savefig(report_path)
        plt.close()
        reports['asset_performance'] = str(report_path)
        
        # Generate hourly distribution report
        hourly_report = generate_hourly_report(yesterday)
        report_path = reports_dir / 'hourly_distribution.pdf'
        hourly_report.savefig(report_path)
        plt.close()
        reports['hourly_distribution'] = str(report_path)
        
        # Send email if requested
        if send_email:
            send_daily_report_email(reports, report_date)
        
        return reports

    except Exception as e:
        logger.error(f"Error generating daily reports: {str(e)}")
        self.retry(exc=e, countdown=300)  # Retry after 5 minutes

def generate_campaign_report(date: datetime) -> plt.Figure:
    """Generate campaign performance visualization."""
    # Get campaign data
    campaigns = db.fetch_all(
        """
        SELECT 
            c.name,
            COUNT(l.id) as impressions,
            SUM(CASE WHEN l.completed = 1 THEN 1 ELSE 0 END) as completions
        FROM ad_campaigns c
        LEFT JOIN ad_logs l ON c.id = l.campaign_id
        WHERE DATE(l.timestamp) = DATE(?)
        GROUP BY c.id, c.name
        """,
        (date.strftime('%Y-%m-%d'),)
    )
    
    # Create DataFrame
    df = pd.DataFrame([dict(c) for c in campaigns])
    
    # Create visualization
    plt.figure(figsize=(12, 6))
    sns.barplot(data=df, x='name', y='impressions')
    plt.title('Campaign Performance')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return plt.gcf()

def generate_asset_report(date: datetime) -> plt.Figure:
    """Generate asset performance visualization."""
    # Get asset data
    assets = db.fetch_all(
        """
        SELECT 
            m.title,
            a.type,
            COUNT(l.id) as plays,
            SUM(CASE WHEN l.completed = 1 THEN 1 ELSE 0 END) as completions
        FROM ad_assets a
        JOIN media m ON a.media_id = m.id
        LEFT JOIN ad_logs l ON a.id = l.asset_id
        WHERE DATE(l.timestamp) = DATE(?)
        GROUP BY a.id, m.title, a.type
        """,
        (date.strftime('%Y-%m-%d'),)
    )
    
    # Create DataFrame
    df = pd.DataFrame([dict(a) for a in assets])
    
    # Create visualization
    plt.figure(figsize=(12, 6))
    sns.scatterplot(data=df, x='plays', y='completions', hue='type', size='plays')
    plt.title('Asset Performance')
    plt.tight_layout()
    
    return plt.gcf()

def generate_hourly_report(date: datetime) -> plt.Figure:
    """Generate hourly distribution visualization."""
    # Get hourly data
    hourly = db.fetch_all(
        """
        SELECT 
            strftime('%H', timestamp) as hour,
            COUNT(*) as impressions
        FROM ad_logs
        WHERE DATE(timestamp) = DATE(?)
        GROUP BY hour
        ORDER BY hour
        """,
        (date.strftime('%Y-%m-%d'),)
    )
    
    # Create DataFrame
    df = pd.DataFrame([dict(h) for h in hourly])
    
    # Create visualization
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df, x='hour', y='impressions')
    plt.title('Hourly Distribution')
    plt.xlabel('Hour of Day')
    plt.ylabel('Impressions')
    plt.tight_layout()
    
    return plt.gcf()

def send_daily_report_email(reports: Dict[str, str], report_date: str):
    """Send daily report email with attachments."""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f'Daily Analytics Report - {report_date}'
        msg['From'] = settings.app.email_sender
        msg['To'] = settings.app.email_recipient
        
        # Add body
        body = f"""
        Daily Analytics Report for {report_date}
        
        Please find attached the following reports:
        - Campaign Performance
        - Asset Performance
        - Hourly Distribution
        
        This is an automated message.
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachments
        for name, path in reports.items():
            with open(path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype='pdf')
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=f'{name}.pdf'
                )
                msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(settings.app.smtp_host, settings.app.smtp_port) as server:
            server.starttls()
            server.login(settings.app.smtp_user, settings.app.smtp_password)
            server.send_message(msg)
        
        logger.info(f"Daily report email sent for {report_date}")

    except Exception as e:
        logger.error(f"Error sending daily report email: {str(e)}")
        raise

@shared_task(name='app.tasks.analytics.generate_custom_report')
def generate_custom_report(
    start_date: str,
    end_date: str,
    metrics: List[str],
    group_by: Optional[str] = None
) -> str:
    """Generate custom analytics report."""
    try:
        logger.info(f"Generating custom report from {start_date} to {end_date}")
        
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Build query based on requested metrics
        select_clauses = []
        for metric in metrics:
            if metric == 'impressions':
                select_clauses.append('COUNT(*) as impressions')
            elif metric == 'completions':
                select_clauses.append(
                    'SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completions'
                )
            elif metric == 'completion_rate':
                select_clauses.append(
                    'AVG(CASE WHEN completed = 1 THEN 1 ELSE 0 END) * 100 as completion_rate'
                )
        
        # Add grouping if specified
        group_clause = ''
        if group_by:
            if group_by == 'campaign':
                select_clauses.insert(0, 'c.name as campaign')
                group_clause = 'GROUP BY c.id, c.name'
            elif group_by == 'asset':
                select_clauses.insert(0, 'm.title as asset')
                group_clause = 'GROUP BY a.id, m.title'
            elif group_by == 'date':
                select_clauses.insert(0, 'DATE(l.timestamp) as date')
                group_clause = 'GROUP BY date'
        
        # Build and execute query
        query = f"""
            SELECT {', '.join(select_clauses)}
            FROM ad_logs l
            JOIN ad_campaigns c ON l.campaign_id = c.id
            JOIN ad_assets a ON l.asset_id = a.id
            JOIN media m ON a.media_id = m.id
            WHERE DATE(l.timestamp) BETWEEN DATE(?) AND DATE(?)
            {group_clause}
        """
        
        results = db.fetch_all(query, (start_date, end_date))
        
        # Generate report file
        report_path = Path('reports') / 'custom' / f'report_{start_date}_{end_date}.pdf'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create visualization
        df = pd.DataFrame([dict(r) for r in results])
        
        plt.figure(figsize=(12, 6))
        if group_by == 'date':
            sns.lineplot(data=df, x='date', y=metrics[0])
        else:
            sns.barplot(data=df, x=group_by if group_by else 'metric', y=metrics[0])
        
        plt.title(f'Custom Report: {metrics[0].title()}')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(report_path)
        plt.close()
        
        return str(report_path)

    except Exception as e:
        logger.error(f"Error generating custom report: {str(e)}")
        raise
