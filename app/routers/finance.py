"""SPP demo endpoints. Admin access is a shared demo key, not production identity."""
import hashlib
import hmac
import json
import os
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.finance import Billing, PaymentMethod, Payment, FinanceNotification
from app.services.finance import FinanceError, generate_billing, apply_penalty, process_payment, dashboard, financial_report, reminders, serialize, dispatch_emails

router=APIRouter(prefix='/api/finance',tags=['Keuangan SPP - Minggu 11'])

def require_admin(x_demo_admin_key:str|None=Header(None)):
    secret=os.getenv('FINANCE_ADMIN_KEY','demo-admin-key-change-me')
    if not x_demo_admin_key or not hmac.compare_digest(x_demo_admin_key,secret):raise HTTPException(403,'Kunci admin demo tidak valid.')

def fail(exc):
    if isinstance(exc,FinanceError):raise HTTPException(exc.status_code,str(exc)) from exc
    raise exc

class GenerateRequest(BaseModel):
    semester:str=Field(pattern=r'^\d{4}[12]$')
    semester_start:date
class PaymentRequest(BaseModel):
    billing_id:int=Field(gt=0)
    amount:Decimal=Field(gt=0,max_digits=15,decimal_places=2)
    method:str='manual'
class WebhookPayload(BaseModel):
    billing_id:int
    transaction_id:str=Field(min_length=1,max_length=120)
    amount:Decimal=Field(gt=0,max_digits=15,decimal_places=2)
    status:str
    method:str='gateway'
class CsvReport(BaseModel):
    csv_text:str

@router.post('/methods/seed',dependencies=[Depends(require_admin)])
def seed_methods(db:Session=Depends(get_db)):
    created=[]
    for code,name in [('manual','Transfer Manual'),('gateway','Gateway Simulasi')]:
        if db.scalar(select(PaymentMethod).where(PaymentMethod.code==code)) is None:
            db.add(PaymentMethod(code=code,name=name));created.append(code)
    db.commit();return {'created':created}

@router.post('/billing/generate',dependencies=[Depends(require_admin)])
def generate(payload:GenerateRequest,db:Session=Depends(get_db)):
    try:return generate_billing(db,payload.semester,payload.semester_start)
    except Exception as exc:db.rollback();fail(exc)

@router.get('/billing',dependencies=[Depends(require_admin)])
def list_billing(db:Session=Depends(get_db)):
    return [serialize(b) for b in db.scalars(select(Billing).order_by(Billing.id)).all()]

@router.post('/billing/penalties',dependencies=[Depends(require_admin)])
def penalties(db:Session=Depends(get_db)):
    return apply_penalty(db)

@router.post('/payments/manual',dependencies=[Depends(require_admin)])
def manual(payload:PaymentRequest,db:Session=Depends(get_db)):
    try:
        p,_=process_payment(db,payload.billing_id,payload.amount,payload.method)
        return {'payment_id':p.id,'amount':str(p.amount),'status':db.get(Billing,p.billing_id).status}
    except Exception as exc:db.rollback();fail(exc)

@router.post('/webhook')
async def webhook(request:Request,db:Session=Depends(get_db),x_gateway_signature:str|None=Header(None)):
    secret=os.getenv('PAYMENT_WEBHOOK_SECRET','demo-webhook-secret-change-me')
    raw=await request.body()
    expected=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    if not x_gateway_signature or not hmac.compare_digest(x_gateway_signature,expected):raise HTTPException(401,'Signature webhook tidak valid.')
    try:
        payload=WebhookPayload.model_validate_json(raw)
        if payload.status.lower() not in ('paid','success','settlement'):
            return {'ok':True,'processed':False,'reason':'Transaksi belum sukses.'}
        p,created=process_payment(db,payload.billing_id,payload.amount,payload.method,payload.transaction_id,'webhook')
        return {'ok':True,'processed':created,'payment_id':p.id,'billing_status':db.get(Billing,p.billing_id).status}
    except Exception as exc:db.rollback();fail(exc)

@router.get('/dashboard',dependencies=[Depends(require_admin)])
def get_dashboard(db:Session=Depends(get_db)):
    return dashboard(db)

@router.get('/report',dependencies=[Depends(require_admin)])
def report(db:Session=Depends(get_db)):
    return financial_report(db)

@router.post('/report/csv',dependencies=[Depends(require_admin)])
def report_csv(payload:CsvReport,db:Session=Depends(get_db)):
    try:return financial_report(db,payload.csv_text)
    except Exception as exc:fail(exc)

@router.post('/reminders/run',dependencies=[Depends(require_admin)])
def run_reminders(db:Session=Depends(get_db)):
    return reminders(db)

@router.get('/notifications',dependencies=[Depends(require_admin)])
def notifications(db:Session=Depends(get_db)):
    return [{'kind':n.kind,'recipient':n.recipient,'subject':n.subject,'body':n.body,'sent_at':n.sent_at} for n in db.scalars(select(FinanceNotification)).all()]

@router.post('/notifications/send',dependencies=[Depends(require_admin)])
def send_notifications(db:Session=Depends(get_db)):
    try:return dispatch_emails(db)
    except Exception as exc:
        db.rollback()
        raise HTTPException(502,'Pengiriman SMTP gagal; notifikasi tetap di antrean.') from exc
