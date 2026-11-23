from datetime import date, timedelta
from decimal import Decimal
import hashlib,hmac,json
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import CalonMahasiswa, ProgramStudi, JalurMasuk, StatusPMB, MataKuliah
from app.models.finance import Billing,Payment,PaymentMethod,FinanceNotification
from app.services.finance import generate_billing,process_payment,FinanceError,apply_penalty,reminders,financial_report
from app.services.krs_service import KRSManager,KRSForbidden
import pytest

@pytest.fixture
def student(db_session):
    prodi=db_session.scalar(select(ProgramStudi).where(ProgramStudi.kode=='001'))
    jalur=db_session.scalar(select(JalurMasuk).where(JalurMasuk.nama=='SNBP'))
    s=CalonMahasiswa(nama_lengkap='Demo SPP',email='demo.spp@example.test',phone='081234567890',tanggal_lahir=date(2002,1,1),alamat='Test',program_studi_id=prodi.id,jalur_masuk_id=jalur.id,status=StatusPMB.approve,nim='20240001')
    db_session.add_all([s,PaymentMethod(code='manual',name='Manual'),PaymentMethod(code='gateway',name='Gateway')]);db_session.commit()
    return s

def test_generate_idempotent_and_payment_partial_paid(db_session,student):
    assert generate_billing(db_session,'20261',date.today())['created']==1
    assert generate_billing(db_session,'20261',date.today())['created']==0
    b=db_session.scalar(select(Billing));assert b.total==5000000 and b.status=='unpaid' and b.due_date==date.today()+timedelta(days=14)
    p,_=process_payment(db_session,b.id,Decimal('1000000'),'manual');assert p.amount==1000000
    db_session.refresh(b);assert b.status=='partial'
    p,_=process_payment(db_session,b.id,Decimal('4000000'),'gateway','trx-1','webhook')
    db_session.refresh(b);assert b.status=='paid'
    same,created=process_payment(db_session,b.id,Decimal('4000000'),'gateway','trx-1','webhook');assert not created and same.id==p.id
    assert db_session.scalar(select(Payment).where(Payment.billing_id==b.id)) is not None
    assert len(db_session.scalars(select(FinanceNotification)).all())==2

def test_penalty_reminder_and_krs_block(db_session,student):
    generate_billing(db_session,'20261',date.today()-timedelta(days=30))
    b=db_session.scalar(select(Billing));assert apply_penalty(db_session)['penalties_assessed']==1
    db_session.refresh(b);assert b.penalty==50000 and b.status=='overdue'
    assert apply_penalty(db_session)['penalties_assessed']==0
    assert reminders(db_session)['reminders_queued']==1
    assert reminders(db_session)['reminders_queued']==0
    with pytest.raises(KRSForbidden):KRSManager(db_session,'20261').add_course(student.nim,'ANY')
    db_session.rollback()
    process_payment(db_session,b.id,Decimal('5050000'),'manual')
    db_session.refresh(b);assert b.status=='paid'

def test_webhook_signature_and_dashboard(db_session,student):
    generate_billing(db_session,'20261',date.today())
    b=db_session.scalar(select(Billing))
    app.dependency_overrides[get_db]=lambda:db_session
    try:
        client=TestClient(app)
        body={'billing_id':b.id,'transaction_id':'unique-webhook-1','amount':'5000000','status':'success','method':'gateway'}
        raw=json.dumps(body,separators=(',',':')).encode()
        assert client.post('/api/finance/webhook',content=raw).status_code==401
        signature=hmac.new(b'demo-webhook-secret-change-me',raw,hashlib.sha256).hexdigest()
        r=client.post('/api/finance/webhook',content=raw,headers={'X-Gateway-Signature':signature})
        assert r.status_code==200,r.text
        assert r.json()['billing_status']=='paid'
        r=client.post('/api/finance/webhook',content=raw,headers={'X-Gateway-Signature':signature})
        assert r.status_code==200 and not r.json()['processed']
        assert client.get('/api/finance/dashboard').status_code==403
        data=client.get('/api/finance/dashboard',headers={'X-Demo-Admin-Key':'demo-admin-key-change-me'}).json()
        assert data['students'][0]['remaining']=='0.00'
        assert data['programs'][0]['collection_rate_percent']==100
    finally:app.dependency_overrides.clear()

def test_financial_report_csv(db_session,student):
    generate_billing(db_session,'20261',date.today())
    csv_text=f'nim,jumlah,tanggal,status\n20240001,12345,{date.today().isoformat()},paid\n'
    result=financial_report(db_session,csv_text)
    assert result['total_revenue']=='12345.00'
    assert result['collection_rate_percent']==0
