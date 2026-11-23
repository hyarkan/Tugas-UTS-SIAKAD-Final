"""Demo HMAC webhook test: python demo_webhook.py BILLING_ID AMOUNT TRANSACTION_ID"""
import hashlib,hmac,json,os,sys,urllib.request,urllib.error

def main():
    if len(sys.argv)!=4:
        print('Usage: python demo_webhook.py BILLING_ID AMOUNT TRANSACTION_ID');return 2
    payload={'billing_id':int(sys.argv[1]),'transaction_id':sys.argv[3],'amount':sys.argv[2],'status':'success','method':'gateway'}
    raw=json.dumps(payload,separators=(',',':')).encode()
    secret=os.getenv('PAYMENT_WEBHOOK_SECRET','demo-webhook-secret-change-me')
    sig=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    url=os.getenv('FINANCE_API_URL','http://127.0.0.1:8000')+'/api/finance/webhook'
    req=urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json','X-Gateway-Signature':sig},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=10) as response:print(response.status,response.read().decode())
    except urllib.error.HTTPError as exc:print(exc.code,exc.read().decode());return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
