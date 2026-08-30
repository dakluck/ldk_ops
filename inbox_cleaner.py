import imaplib
import email
from email.header import decode_header
import re
import sys
from email_sender import load_credentials

def clean_header(header_val):
    if not header_val:
        return ""
    decoded_parts = decode_header(header_val)
    result = []
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(enc or 'utf-8', errors='ignore'))
            except Exception:
                result.append(part.decode('latin1', errors='ignore'))
        else:
            result.append(str(part))
    return " ".join(result)

PROTECTED_DOMAINS = [
    "ldk-international.com", "mercury.com", "usaa.com", "chase.com", "wellsfargo.com",
    "stripe.com", "cloudflare.com", "vercel.com", "github.com", "sdsu.edu",
    "mbmacademy.com", "bkscpa.com", "zenbusiness.com"
]

PROTECTED_SUBJECT_KEYWORDS = [
    "invoice", "receipt", "order", "shipping", "tracking", "delivered", "purchased",
    "confirmation", "ticket", "flight", "reservation", "payment", "statement",
    "security alert", "verification", "verify", "pin", "login", "password reset",
    "tax", "w-2", "1099", "p360", "coaching", "bank account", "deposit", "transfer",
    "payout", "dispute", "bill", "charge", "refund", "wire"
]

MARKETING_PATTERNS = [
    "unsubscribe", "sale", "deal", "discount", "off your next", "limited time",
    "exclusive offer", "daily digest", "newsletter", "weekly update", "special offer",
    "clearance", "promo", "shop now", "free shipping on orders", "save up to",
    "word of the day", "word smarts", "word daily", "word genius", "trending",
    "summer collection", "new arrivals", "weekend deals", "flash sale", "referral"
]

def classify_message(sender, subject, list_unsub):
    s_lower = sender.lower()
    sub_lower = subject.lower()
    
    is_transactional = any(k in sub_lower for k in PROTECTED_SUBJECT_KEYWORDS)
    is_protected_sender = any(d in s_lower for d in PROTECTED_DOMAINS)
    
    is_marketing = False
    if any(p in sub_lower for p in MARKETING_PATTERNS):
        is_marketing = True
    if list_unsub and not is_transactional:
        is_marketing = True
        
    junk_senders = [
        "wordsmarts", "worddaily", "wordgenius", "bandsintown", "etsy",
        "pelagic", "offerup", "huel", "roark", "tyr.com", "pelican.com",
        "newwestknifeworks", "complyfoam", "repfitness", "discover.offerup",
        "no-reply@", "noreply@", "newsletters@", "marketing@", "promotions@",
        "e.nike.com", "e.underarmour.com", "marketing.patagonia.com"
    ]
    if any(j in s_lower for j in junk_senders) and not is_transactional:
        is_marketing = True

    if is_transactional or (is_protected_sender and not is_marketing):
        return "KEEP"
    elif is_marketing:
        return "CLEAN"
    else:
        if list_unsub:
            return "CLEAN"
        return "KEEP"

def process_inbox(account_name, email_addr, password, dry_run=True):
    print("=======================================================")
    print(f"  Account: {account_name} ({email_addr}) | dry_run={dry_run}")
    print("=======================================================")
    
    if not password:
        print(f"Skipping {email_addr}: No password found in .env or himalaya config.")
        return

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_addr, password)
    mail.select("INBOX")
    
    status, data = mail.uid('search', None, 'ALL')
    if status != "OK" or not data[0]:
        print("No messages found in INBOX.")
        mail.logout()
        return

    uids = data[0].split()
    total = len(uids)
    print(f"Total messages in INBOX: {total}")
    
    clean_uids = []
    keep_count = 0
    clean_count = 0
    
    samples_cleaned = []
    samples_kept = []
    
    # Batch fetch headers in chunks of 100
    chunk_size = 100
    for i in range(0, total, chunk_size):
        chunk = uids[i:i+chunk_size]
        chunk_str = b','.join(chunk).decode('ascii')
        status, fetch_data = mail.uid('fetch', chunk_str, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE LIST-UNSUBSCRIBE)])')
        if status != 'OK' or not fetch_data:
            continue
            
        for item in fetch_data:
            if isinstance(item, tuple):
                header_line = item[0].decode('ascii', errors='ignore')
                uid_match = re.search(r'UID\s+(\d+)', header_line)
                uid_val = uid_match.group(1).encode('ascii') if uid_match else None
                
                raw_header = item[1]
                msg = email.message_from_bytes(raw_header)
                sender = clean_header(msg.get('From', ''))
                subject = clean_header(msg.get('Subject', ''))
                list_unsub = msg.get('List-Unsubscribe', '')
                
                action = classify_message(sender, subject, list_unsub)
                
                if action == 'CLEAN' and uid_val:
                    clean_uids.append(uid_val)
                    clean_count += 1
                    if len(samples_cleaned) < 15:
                        samples_cleaned.append((sender[:35], subject[:50]))
                else:
                    keep_count += 1
                    if len(samples_kept) < 12:
                        samples_kept.append((sender[:35], subject[:50]))
                        
        print(f"  Fetched & analyzed {min(i + chunk_size, total)}/{total} messages...")
            
    print(f"\nResults for {email_addr}:")
    print(f"  🛡️ Preserved in INBOX: {keep_count}")
    print(f"  🧹 Cleaned to Trash   : {clean_count}")
    
    print("\nSample Noise / Cleaned:")
    for s, sub in samples_cleaned:
        print(f"  [CLEAN] From: {s:<35} | Sub: {sub}")
        
    print("\nSample Kept:")
    for s, sub in samples_kept:
        print(f"  [KEEP]  From: {s:<35} | Sub: {sub}")
        
    if not dry_run and clean_uids:
        print(f"\nApplying cleanup: Moving {len(clean_uids)} messages to Trash...")
        batch_size = 50
        for b in range(0, len(clean_uids), batch_size):
            b_uids = clean_uids[b:b+batch_size]
            uid_set = b','.join(b_uids).decode('ascii')
            mail.uid('copy', uid_set, '[Gmail]/Trash')
            mail.uid('store', uid_set, '+FLAGS', '(\\Deleted)')
        mail.expunge()
        print(f"Done! {len(clean_uids)} messages moved to Trash.")

    mail.logout()

if __name__ == '__main__':
    dry_run = '--apply' not in sys.argv
    creds = load_credentials()
    accounts = [
        ('Dailey LDK', creds['dailey_ldk']['email'], creds['dailey_ldk']['password']),
        ('Dailey Personal', creds['dailey_personal']['email'], creds['dailey_personal']['password'])
    ]
    for name, addr, pwd in accounts:
        process_inbox(name, addr, pwd, dry_run=dry_run)
