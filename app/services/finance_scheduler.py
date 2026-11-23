"""Optional APScheduler jobs, enabled with FINANCE_SCHEDULER_ENABLED=1."""
import os
from datetime import date
from app.database import SessionLocal
from app.services.finance import generate_billing, apply_penalty, reminders, dispatch_emails

def run_daily():
    with SessionLocal() as db:
        apply_penalty(db)
        reminders(db)
        dispatch_emails(db)

def run_semester(semester:str,start:date):
    with SessionLocal() as db:
        return generate_billing(db,semester,start)

def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler=BackgroundScheduler(timezone='Asia/Jakarta')
    scheduler.add_job(run_daily,'cron',hour=8,minute=0,id='daily_finance',replace_existing=True)
    # Default calendar example: semester 1 starts September 1; semester 2 starts February 1.
    # Adapt actual academic calendar before production use.
    def kickoff(month):
        now=date.today();semester=f'{now.year}{"1" if month==9 else "2"}'
        run_semester(semester,date(now.year,month,1))
    scheduler.add_job(lambda:kickoff(9),'cron',month=9,day=1,hour=0,minute=5,id='semester_ganjil',replace_existing=True)
    scheduler.add_job(lambda:kickoff(2),'cron',month=2,day=1,hour=0,minute=5,id='semester_genap',replace_existing=True)
    scheduler.start()
    return scheduler
