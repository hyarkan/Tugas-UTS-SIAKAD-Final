"""Week 11 financial business rules; all amounts are Decimal and changes are atomic."""
import csv
import io
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import CalonMahasiswa, ProgramStudi
from app.models.finance import Billing, Payment, PaymentMethod, FinanceNotification

class FinanceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code=status_code

MONEY = Decimal('0.01')
def money(value):
    try:
        v=Decimal(str(value)).quantize(MONEY,rounding=ROUND_HALF_UP)
        if not v.is_finite(): raise ValueError()
        return v
    except (ValueError,ArithmeticError):
        raise FinanceError('Jumlah uang tidak valid.')

def serialize(b):
    return {'id':b.id,'nim':b.nim,'semester':b.semester,'total':str(b.total),'paid_amount':str(b.paid_amount),'penalty':str(b.penalty),'remaining':str(money(max(Decimal('0'),b.total+b.penalty-b.paid_amount))),'status':b.status,'due_date':b.due_date.isoformat()}

def tuition(prodi):
    label=f'{prodi.nama} {prodi.fakultas}'.lower()
    if 'ekonomi' in label: return Decimal('4000000.00')
    if 'teknik' in label or 'informatika' in label or 'sistem informasi' in label or 'fsti' in label: return Decimal('5000000.00')
    raise FinanceError(f'Tarif prodi {prodi.nama} belum dikonfigurasi.',422)

def generate_billing(db:Session,semester:str,semester_start:date):
    if len(semester)!=5 or not semester[:4].isdigit() or semester[-1] not in '12': raise FinanceError('Semester harus YYYY1 atau YYYY2.',422)
    students=db.execute(select(CalonMahasiswa,ProgramStudi).join(ProgramStudi,CalonMahasiswa.program_studi_id==ProgramStudi.id).where(CalonMahasiswa.nim.is_not(None))).all()
    count=0
    for student,prodi in students:
        if db.scalar(select(Billing.id).where(Billing.nim==student.nim,Billing.semester==semester)) is not None: continue
        db.add(Billing(nim=student.nim,semester=semester,total=tuition(prodi),paid_amount=Decimal('0'),penalty=Decimal('0'),status='unpaid',due_date=semester_start+timedelta(days=14)))
        count+=1
    db.commit()
    return {'semester':semester,'created':count,'active_students':len(students)}

def refresh_billing(b:Billing,today=None):
    today=today or date.today()
    due=money(b.total)+money(b.penalty)
    paid=money(b.paid_amount)
    b.status='paid' if paid>=due else 'partial' if paid>0 else 'overdue' if today>b.due_date else 'unpaid'

def apply_penalty(db:Session,today=None,rate=Decimal('0.01')):
    """Configurable flat 1% overdue penalty, assessed once per bill (demo policy)."""
    today=today or date.today();changed=0
    for b in db.scalars(select(Billing).where(Billing.due_date<today)).all():
        if b.status=='paid': continue
        if b.penalty==0:
            b.penalty=money(b.total*rate)
            changed+=1
        refresh_billing(b,today)
    db.commit();return {'penalties_assessed':changed}

def process_payment(db:Session,billing_id:int,amount,method:str,transaction_id=None,source='manual'):
    amount=money(amount)
    if amount<=0: raise FinanceError('Pembayaran harus lebih besar dari nol.',422)
    if db.get_bind().dialect.name=='sqlite' and not db.in_transaction():
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    if transaction_id:
        existing=db.scalar(select(Payment).where(Payment.transaction_id==transaction_id))
        if existing:
            if existing.billing_id==billing_id and existing.amount==amount: return existing,False
            raise FinanceError('transaction_id sudah digunakan untuk pembayaran berbeda.',409)
    b=db.get(Billing,billing_id,with_for_update=True)
    if b is None: raise FinanceError('Tagihan tidak ditemukan.',404)
    m=db.scalar(select(PaymentMethod).where(PaymentMethod.code==method))
    if m is None: raise FinanceError('Metode pembayaran tidak tersedia.',422)
    outstanding=money(b.total+b.penalty-b.paid_amount)
    if outstanding<=0: raise FinanceError('Tagihan sudah lunas.',409)
    if amount>outstanding: raise FinanceError('Pembayaran melebihi sisa tagihan.',422)
    payment=Payment(billing_id=b.id,method_id=m.id,amount=amount,transaction_id=transaction_id,source=source)
    db.add(payment);b.paid_amount=money(b.paid_amount+amount);refresh_billing(b)
    student=db.scalar(select(CalonMahasiswa).where(CalonMahasiswa.nim==b.nim))
    db.add(FinanceNotification(billing_id=b.id,kind='receipt',recipient=student.email,subject='Bukti pembayaran SPP (simulasi)',body=f'Pembayaran Rp {amount} diterima untuk NIM {b.nim}, semester {b.semester}.'))
    db.commit();db.refresh(payment)
    return payment,True

def has_arrears(db:Session,nim:str,semester:str):
    # Any overdue unpaid billing blocks KRS; the current semester must also be paid if already billed.
    bills=db.scalars(select(Billing).where(Billing.nim==nim)).all()
    return any(money(b.total+b.penalty-b.paid_amount)>0 and (b.due_date<date.today() or b.semester==semester) for b in bills)

def reminders(db:Session,today=None):
    today=today or date.today();count=0
    for b in db.scalars(select(Billing).where(Billing.due_date<today)).all():
        refresh_billing(b,today)
        if b.status=='paid':continue
        student=db.scalar(select(CalonMahasiswa).where(CalonMahasiswa.nim==b.nim))
        exists=db.scalar(select(FinanceNotification.id).where(FinanceNotification.billing_id==b.id,FinanceNotification.kind=='reminder',func.date(FinanceNotification.created_at)==today.isoformat()))
        if not exists:
            db.add(FinanceNotification(billing_id=b.id,kind='reminder',recipient=student.email,subject='Pengingat tunggakan SPP',body=f'Tagihan semester {b.semester} belum lunas. Sisa Rp {b.total+b.penalty-b.paid_amount}.'))
            count+=1
    db.commit();return {'reminders_queued':count}

def dashboard(db:Session):
    bills=db.scalars(select(Billing)).all();payments=db.scalars(select(Payment)).all()
    students={s.nim:s for s in db.scalars(select(CalonMahasiswa).where(CalonMahasiswa.nim.is_not(None))).all()}
    prodis={p.id:p.nama for p in db.scalars(select(ProgramStudi)).all()}
    per_student={};per_prodi={};monthly={}
    for b in bills:
        refresh_billing(b)
        s=per_student.setdefault(b.nim,{'nim':b.nim,'total':Decimal('0.00'),'paid':Decimal('0.00'),'remaining':Decimal('0.00')})
        s['total']+=b.total+b.penalty;s['paid']+=b.paid_amount;s['remaining']+=max(Decimal(0),b.total+b.penalty-b.paid_amount)
        st=students.get(b.nim)
        if st:
            p=per_prodi.setdefault(prodis.get(st.program_studi_id,'Tidak diketahui'),{'bills':0,'paid_bills':0})
            p['bills']+=1;p['paid_bills']+=int(b.status=='paid')
    for p in payments:
        month=p.created_at.strftime('%Y-%m');monthly[month]=monthly.get(month,Decimal(0))+p.amount
    return {'students':[{k:str(v) if isinstance(v,Decimal) else v for k,v in s.items()} for s in per_student.values()], 'programs':[{'program_studi':k,**v,'collection_rate_percent':round(100*v['paid_bills']/v['bills'],2) if v['bills'] else 0} for k,v in per_prodi.items()], 'monthly_payments':[{'month':k,'amount':str(v)} for k,v in sorted(monthly.items())]}

def financial_report(db:Session,csv_text:str|None=None,today=None):
    today=today or date.today()
    dash=dashboard(db)
    month=today.strftime('%Y-%m')
    revenue=sum((money(x['amount']) for x in dash['monthly_payments'] if x['month']==month),Decimal(0))
    if csv_text is not None:
        reader=csv.DictReader(io.StringIO(csv_text))
        if not {'nim','jumlah','tanggal','status'}.issubset(reader.fieldnames or []):raise FinanceError('CSV wajib berisi nim,jumlah,tanggal,status.',422)
        revenue=Decimal(0)
        for row in reader:
            try: d=date.fromisoformat(row['tanggal'])
            except ValueError:raise FinanceError('Tanggal CSV harus YYYY-MM-DD.',422)
            if d.strftime('%Y-%m')==month and row['status'].lower() in ('paid','success','settlement'):
                revenue+=money(row['jumlah'])
    all_bills=db.scalars(select(Billing)).all();paid=sum(b.status=='paid' for b in all_bills)
    delinquent=[s for s in dash['students'] if money(s['remaining'])>0]
    top=sorted(delinquent,key=lambda s:money(s['remaining']),reverse=True)[:10]
    older_nims={b.nim for b in all_bills if money(b.total+b.penalty-b.paid_amount)>0 and b.due_date<today-timedelta(days=60)}
    return {'month':month,'total_revenue':str(revenue),'collection_rate_percent':round(paid*100/len(all_bills),2) if all_bills else 0,'top_10_arrears':top,'recommendation':f'Kirim reminder ke {len(older_nims)} mahasiswa dengan tunggakan >2 bulan.','method':'rule-based analytics (simulasi AI; tanpa layanan model eksternal)'}

def dispatch_emails(db:Session):
    """Deliver queued receipts/reminders via SMTP when configured; otherwise retain in outbox.

    Required: SMTP_HOST, SMTP_FROM. Optional SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SMTP_STARTTLS (default 1). Sending is at-least-once; production needs a durable worker.
    """
    import os, smtplib
    from email.message import EmailMessage
    host=os.getenv('SMTP_HOST')
    sender=os.getenv('SMTP_FROM')
    if not host or not sender:
        return {'sent':0,'pending':len(db.scalars(select(FinanceNotification).where(FinanceNotification.sent_at.is_(None))).all()),'configured':False}
    pending=db.scalars(select(FinanceNotification).where(FinanceNotification.sent_at.is_(None)).order_by(FinanceNotification.id)).all()
    sent=0
    for n in pending:
        msg=EmailMessage();msg['From']=sender;msg['To']=n.recipient;msg['Subject']=n.subject;msg.set_content(n.body)
        with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
            if os.getenv('SMTP_STARTTLS','1')=='1':smtp.starttls()
            if os.getenv('SMTP_USER'):smtp.login(os.getenv('SMTP_USER'),os.getenv('SMTP_PASSWORD',''))
            smtp.send_message(msg)
        n.sent_at=datetime.now(timezone.utc)
        db.commit();sent+=1
    return {'sent':sent,'pending':0,'configured':True}
