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
    "americanexpress.com", "fidelity.com", "vanguard.com", "elevationscu.com",
    "monarch.com", "monarchmoney.com", "stripe.com", "cloudflare.com", "vercel.com",
    "github.com", "sdsu.edu", "cu.edu", "mbmacademy.com", "bkscpa.com", "zenbusiness.com",
    "google.com", "apple.com", "gitguardian.com", "irs.gov", "sos.ca.gov", "ftb.ca.gov",
    "etags.com", "dmv.ca.gov", "kp.org", "cigna.com", "deltadental.com",
    "embracepetinsurance.com", "ui.com"
]

PROTECTED_SUBJECT_KEYWORDS = [
    "invoice", "receipt", "order", "shipping", "tracking", "delivered", "purchased",
    "confirmation", "ticket", "flight", "reservation", "payment", "statement",
    "security alert", "verification", "verify", "pin", "login", "password reset",
    "tax", "w-2", "1099", "p360", "coaching", "bank account", "deposit", "transfer",
    "payout", "dispute", "bill", "charge", "refund", "wire", "suspension", "suspended",
    "at risk", "action required", "action advised", "notice", "alert", "security",
    "warning", "critical", "storage limit", "storage pool", "data protection", "api key",
    "exposed", "breach", "incident", "billing", "balance", "credit balance", "credit score",
    "app review", "rejected", "approved", "compliance", "policy", "urgent", "quota",
    "limit exceeded", "registration", "insurance", "dental", "medical", "appointment",
    "benefit", "clarification", "rsvp", "evite"
]

MARKETING_PATTERNS = [
    "unsubscribe", "sale", "deal", "discount", "off your next", "limited time",
    "exclusive offer", "daily digest", "newsletter", "weekly update", "special offer",
    "clearance", "promo", "shop now", "free shipping on orders", "free shipping",
    "shipping is on us", "save up to", "word of the day", "word smarts", "word daily",
    "word genius", "trending", "summer collection", "new arrivals", "weekend deals",
    "flash sale", "referral", "ai coach", "simplifying payroll", "see fei-fei li",
    "standout sessions", "how did it go?", "tell us about your", "review your purchase",
    "review your order"
]

FAMILY_SENDERS = [
    "dailey.kluck@gmail.com", "dailey.kluck@fivetran.com",
    "lmdobashi@gmail.com", "ldobashi@sdsu.edu",
    "leo@ldk-international.com", "dailey@ldk-international.com"
]

def classify_message(sender, subject, list_unsub):
    s_lower = sender.lower()
    sub_lower = subject.lower()
    
    # 1. Always protect family senders
    if any(fs in s_lower for fs in FAMILY_SENDERS):
        return "KEEP"
    
    is_protected_sender = any(d in s_lower for d in PROTECTED_DOMAINS)
    is_explicit_marketing = any(p in sub_lower for p in MARKETING_PATTERNS)
    
    is_transactional = any(k in sub_lower for k in PROTECTED_SUBJECT_KEYWORDS)
    if "free shipping" in sub_lower or "shipping is on us" in sub_lower:
        is_transactional = False
        
    # If transactional and NOT explicit marketing, keep
    if is_transactional and not is_explicit_marketing:
        return "KEEP"
        
    # Known junk / retail marketing senders
    retail_junk_senders = [
        "wordsmarts", "worddaily", "wordgenius", "bandsintown", "etsy",
        "pelagic", "offerup", "huel", "roark", "tyr.com", "pelican.com",
        "newwestknifeworks", "complyfoam", "repfitness", "discover.offerup",
        "e.nike.com", "e.underarmour.com", "marketing.patagonia.com",
        "tiktok", "newsletters@", "promotions@", "jeffrandalldrumming",
        "hudsongracesf.com", "taggrading.com", "zwilling.com", "chompshop.com",
        "resy.com", "kingarthurbaking.com", "gatlindidier.com", "loox.io",
        "porsche.us", "thekeyrewards", "serviceprotectionadvantage"
    ]
    if any(j in s_lower for j in retail_junk_senders):
        return "CLEAN"
        
    # Protected infrastructure/business senders
    if is_protected_sender:
        if is_explicit_marketing:
            return "CLEAN"
        return "KEEP"
        
    if is_transactional:
        return "KEEP"

    # Default rules for unknown external senders
    if is_explicit_marketing or list_unsub:
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

def get_target_label(sender, subject):
    s = sender.lower()
    sub = subject.lower()
    
    if 'mercury.com' in s:
        return 'Banking/Mercury'
    if any(k in s for k in ['google.com', 'googleplay', 'googlepay', 'googleaistudio', 'admob', 'adsense', 'adwords', 'xwf.google.com']):
        return 'Google'
    if any(k in s for k in ['apple.com', 'itunes']):
        return 'Apple'
    if any(k in s for k in ['zenbusiness', 'avalara']):
        return 'ZenBusiness'
    if 'cloudflare.com' in s:
        return 'Cloudflare'
    if any(k in s for k in ['wyregisteredagent.net', 'buffaloregisteredagents']):
        return 'Wyoming Registered Agent'
    if any(k in s for k in ['1800accountant', 'bkscpa']):
        return 'Accounting'
    if any(k in s for k in ['link.com', 'stripe.com', 'payments']):
        return 'Payments'
    if any(k in s for k in ['itch.io', 'gitguardian', 'eia.gov']):
        return 'Software'
        
    return 'Non-Critical/Archived'


def organize_inbox(account_name, email_addr, password, dry_run=True):
    print("=======================================================")
    print(f"  Organizing: {account_name} ({email_addr}) | dry_run={dry_run}")
    print("=======================================================")
    
    if not password:
        print(f"Skipping {email_addr}: No password found.")
        return

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_addr, password)
    mail.select("INBOX")
    
    status, data = mail.uid('search', None, 'ALL')
    if status != "OK" or not data[0]:
        print("INBOX is already at Inbox Zero!")
        mail.logout()
        return

    uids = data[0].split()
    total = len(uids)
    print(f"Total messages in INBOX: {total}")
    
    label_batches = {}
    chunk_size = 50
    for i in range(0, total, chunk_size):
        chunk = uids[i:i+chunk_size]
        chunk_str = b','.join(chunk).decode('ascii')
        status, fetch_data = mail.uid('fetch', chunk_str, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])')
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
                
                target_label = get_target_label(sender, subject)
                if uid_val:
                    label_batches.setdefault(target_label, []).append(uid_val)
                    
        print(f"  Analyzed {min(i + chunk_size, total)}/{total} messages...")
        
    print("\nPlanned Categorization:")
    for lbl, b_uids in sorted(label_batches.items(), key=lambda x: -len(x[1])):
        print(f"  📁 {lbl:<30}: {len(b_uids)} messages")
        
    if not dry_run:
        print("\nExecuting label assignment and archiving out of INBOX...")
        for lbl, b_uids in label_batches.items():
            print(f"  Tagging {len(b_uids)} messages with '{lbl}'...")
            batch_size = 50
            for b in range(0, len(b_uids), batch_size):
                sub_batch = b_uids[b:b+batch_size]
                uid_set = b','.join(sub_batch).decode('ascii')
                # Add target label
                mail.uid('STORE', uid_set, '+X-GM-LABELS', f'("{lbl}")')
                # Mark \Deleted in INBOX to archive out of INBOX
                mail.uid('STORE', uid_set, '+FLAGS', '(\\Deleted)')
        print("  Expunging INBOX to finalize archive...")
        mail.expunge()
        print("✅ All messages successfully labeled and archived out of INBOX!")

    mail.logout()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="LDK Ops Inbox Triage & Cleaner")
    parser.add_argument("--apply", action="store_true", help="Apply cleanup actions (moves noise to Trash)")
    parser.add_argument("--organize", action="store_true", help="Organize remaining INBOX messages into custom labels and archive out of INBOX")
    parser.add_argument("--account", choices=["dailey_ldk", "dailey_personal", "leo", "all"], default="all", help="Target specific account")
    args = parser.parse_args()

    dry_run = not args.apply
    creds = load_credentials()
    
    all_accounts = [
        ('dailey_ldk', 'Dailey LDK', creds['dailey_ldk']['email'], creds['dailey_ldk']['password']),
        ('dailey_personal', 'Dailey Personal', creds['dailey_personal']['email'], creds['dailey_personal']['password']),
        ('leo', 'Leo', creds['leo']['email'], creds['leo']['password'])
    ]
    
    for key, name, addr, pwd in all_accounts:
        if args.account != 'all' and args.account != key:
            continue
        if args.organize:
            organize_inbox(name, addr, pwd, dry_run=dry_run)
        else:
            process_inbox(name, addr, pwd, dry_run=dry_run)
