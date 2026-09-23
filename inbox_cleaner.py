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
    "embracepetinsurance.com", "ui.com", "southwest.com", "delta.com", "united.com",
    "alaskaair.com", "marriott.com", "hilton.com", "hyatt.com", "airbnb.com", "turo.com",
    "sdge.com", "att.com", "verizon.com", "t-mobile.com", "costco.com", "robinhood.com",
    "paypal.com", "venmo.com"
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
    "benefit", "clarification", "rsvp", "evite", "itinerary", "boarding pass", "check-in",
    "hotel", "car rental", "mortgage", "lease", "escrow", "deed", "contract", "warranty",
    "return", "claim", "prescription", "patient", "doctor"
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

def get_target_label_corporate(sender, subject):
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


def get_target_label_personal(sender, subject):
    s = sender.lower()
    sub = subject.lower()
    
    # Family
    if 'lmdobashi@' in s or 'lauren dobashi' in s:
        return 'Family/Lauren Dobashi'
    if 'nancy.kluck@' in s or 'nancy kluck' in s:
        return 'Family/Nancy Kluck'
    if 'sara lederhandler' in s or 'slederhandler@' in s:
        return 'Family/Sara Lederhandler'
    if any(k in s for k in ['dailey.kluck@gmail.com', 'dailey.kluck@fivetran.com']):
        return 'Family/Dailey Kluck'
    if 'leo@ldk-international.com' in s:
        return 'Non-Critical/Archived'
        
    # School & Childcare
    if any(k in s for k in ['mbm', 'mbmacademy', 'evite', 'procare']):
        return 'School/MBMA'
        
    # Financial & Banking
    if 'american express' in s or 'americanexpress' in s or 'amex' in s:
        return 'American Express'
    if 'usaa' in s:
        return 'USAA'
    if 'wellsfargo' in s or 'wells fargo' in s:
        return 'Wells Fargo'
    if 'chase' in s:
        return 'Chase'
    if 'vanguard' in s:
        return 'Vanguard'
    if 'fidelity' in s or 'your benefits center' in s:
        return 'Fidelity'
    if 'monarch' in s:
        return 'Monarch Money'
    if 'robinhood' in s:
        return 'Robinhood'
    if 'elevations' in s:
        return 'Elevations Credit Union'
    if 'paypal' in s:
        return 'Paypal'
    if 'venmo' in s:
        return 'Venmo'
    if 'alpaca' in s:
        return 'Tradestation'
        
    # Health & Medical & Pets
    if 'kaiser' in s or 'kp.org' in s:
        return 'Kaiser'
    if 'cigna' in s:
        return 'Cigna'
    if 'delta dental' in s or 'deltadental' in s or 'dental' in s:
        return 'Delta Dental'
    if any(k in s for k in ['west coast animal hospital', 'governor animal clinic', 'rapportmail3']):
        return 'West Coast Animal Hospital'
    if 'embrace' in s:
        return 'Embrace'
        
    # Government, Auto, Travel, Utilities
    if 'sdge' in s:
        return 'SDGE'
    if 'dmv' in s or 'etags' in s:
        return 'California/DMV'
    if 'fastrak' in s:
        return 'FasTrak'
    if 'docupet' in s or 'humane society' in s:
        return 'Brands/DocuPet'
    if 'turo' in s:
        return 'Turo'
    if 'porsche' in s:
        return 'Porsche San Diego'
    if 'marriott' in s or 'courtyard' in s:
        return 'Marriott'
    if 'disney' in s:
        return 'Disney+'
        
    # Tech, Hardware & Brands
    if any(k in s for k in ['google.com', 'googlestore', 'googlepixel', 'googleplay']):
        return 'Google'
    if any(k in s for k in ['apple.com', 'itunes', 'testflight', 'app store connect']):
        return 'Brands/Apple'
    if 'rei' in s:
        return 'Brands/REI'
    if 'nintendo' in s:
        return 'Brands/Nintendo'
    if 'discord' in s:
        return 'Discord'
    if 'facebook' in s:
        return 'Facebook'
    if 'docusign' in s:
        return 'Docusign'
    if 'rachio' in s:
        return 'Brands/Rachio'
    if 'nuphy' in s:
        return 'Brands/NuPhy'
    if 'hudson grace' in s:
        return 'Brands/Hudson Grace'
    if 'ubiquiti' in s or 'ui.com' in s:
        return 'Brands/Ubiquiti'
    if 'remarkable' in s:
        return 'reMarkable'
    if 'openai' in s or 'chatgpt' in s:
        return 'OpenAI'
    if 'fivetran' in s:
        return 'Fivetran'
    if 'cu.edu' in s or 'forever buffs' in s:
        return 'CU Email'
    if 'crkd' in s:
        return 'Branks/CRKD'
    if 'amazon' in s:
        return 'Amazon'
    if 'ups.com' in s or 'ups ' in s:
        return 'UPS'
    if 'fedex' in s:
        return 'FedEx'
    if 'cloudflare' in s:
        return 'Cloudflare'
    if 'spotify' in s:
        return 'Spotify'
    if 'microsoft' in s:
        return 'Microsoft'
    if 'nalpak' in s or 'pelican' in s:
        return 'Brands/Pelican'
    if 'waterhog' in s:
        return 'Brands/Front Runner Outfitters'
    if 'patagonia' in s:
        return 'Brands/Patagonia'
        
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
    
    is_personal = "gmail.com" in email_addr.lower()
    label_fn = get_target_label_personal if is_personal else get_target_label_corporate
    
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
                
                target_label = label_fn(sender, subject)
                if uid_val:
                    label_batches.setdefault(target_label, []).append(uid_val)
                    
        print(f"  Analyzed {min(i + chunk_size, total)}/{total} messages...")
        
    print("\nPlanned Categorization:")
    for lbl, b_uids in sorted(label_batches.items(), key=lambda x: -len(x[1])):
        print(f"  📁 {lbl:<32}: {len(b_uids)} messages")
        
    if not dry_run:
        print("\nExecuting label assignment and archiving out of INBOX...")
        for lbl, b_uids in label_batches.items():
            print(f"  Tagging and archiving {len(b_uids)} messages with '{lbl}'...")
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
        print("✅ All messages successfully labeled and archived out of INBOX (Inbox Zero)!")

    mail.logout()


def clean_archived_promotions(account_name, email_addr, password, dry_run=True, target_year=None, older_than="30d", batch_limit=None):
    print("=======================================================")
    print(f"  Archived Promotions Purge: {account_name} ({email_addr})")
    print(f"  Mode: {'DRY RUN (Preview Only)' if dry_run else 'LIVE EXECUTION (Moving to Trash)'}")
    if target_year:
        print(f"  Target Year: {target_year}")
    print(f"  Threshold: older_than:{older_than}")
    if batch_limit:
        print(f"  Limit: {batch_limit} messages max")
    print("=======================================================")

    if not password:
        print(f"Skipping {email_addr}: No password found.")
        return

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_addr, password)
    mail.select('"[Gmail]/All Mail"')

    years = [target_year] if target_year else [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

    search_exclusions = (
        "-{subject:order subject:receipt subject:invoice subject:confirmation "
        "subject:shipping subject:tracking subject:statement subject:tax "
        "subject:ticket subject:reservation subject:flight subject:booking "
        "subject:security subject:password subject:verify subject:pin "
        "subject:payout subject:deposit subject:bill subject:refund "
        "subject:w-2 subject:1099 subject:benefits subject:medical "
        "subject:insurance subject:appointment subject:itinerary}"
    )

    grand_total_found = 0
    grand_total_cleaned = 0
    grand_total_preserved = 0

    samples_cleaned = []
    samples_preserved = []

    for yr in years:
        if batch_limit and grand_total_cleaned >= batch_limit:
            print(f"\nBatch limit of {batch_limit} reached. Stopping.")
            break

        if yr < 2026:
            query = f'category:promotions -in:inbox after:{yr-1}/12/31 before:{yr+1}/01/01 {search_exclusions}'
        else:
            query = f'category:promotions -in:inbox after:2025/12/31 older_than:{older_than} {search_exclusions}'

        print(f"\n--- Processing Year {yr} ---")
        status, data = mail.uid('search', None, 'X-GM-RAW', f'"{query}"')
        if status != "OK" or not data[0]:
            print(f"  No promotional candidates found for {yr}.")
            continue

        uids = data[0].split()
        total_yr = len(uids)
        grand_total_found += total_yr
        print(f"  Found {total_yr} promotional candidate UIDs for {yr}.")

        yr_clean_uids = []
        yr_preserve_uids = []

        fetch_chunk_size = 500
        for i in range(0, total_yr, fetch_chunk_size):
            chunk = uids[i:i+fetch_chunk_size]
            chunk_str = b','.join(chunk).decode('ascii')
            status, fetch_data = mail.uid('fetch', chunk_str, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
            if status != 'OK' or not fetch_data:
                continue

            for item in fetch_data:
                if isinstance(item, tuple):
                    header_line = item[0].decode('ascii', errors='ignore')
                    uid_match = re.search(r'UID\s+(\d+)', header_line)
                    uid_val = uid_match.group(1).encode('ascii') if uid_match else None
                    if not uid_val:
                        continue

                    raw_header = item[1]
                    msg = email.message_from_bytes(raw_header)
                    sender = clean_header(msg.get('From', ''))
                    subject = clean_header(msg.get('Subject', ''))
                    date_str = msg.get('Date', '')

                    s_lower = sender.lower()
                    sub_lower = subject.lower()

                    is_family = any(fs in s_lower for fs in FAMILY_SENDERS)
                    is_protected_domain = any(d in s_lower for d in PROTECTED_DOMAINS)
                    is_transactional = any(k in sub_lower for k in PROTECTED_SUBJECT_KEYWORDS)

                    if is_family or is_protected_domain or is_transactional:
                        yr_preserve_uids.append(uid_val)
                        if len(samples_preserved) < 15:
                            samples_preserved.append((sender[:35], subject[:50], date_str[:25]))
                    else:
                        yr_clean_uids.append(uid_val)
                        if len(samples_cleaned) < 15:
                            samples_cleaned.append((sender[:35], subject[:50], date_str[:25]))

            print(f"  Verified {min(i + fetch_chunk_size, total_yr)}/{total_yr} headers in {yr}...", end="\r", flush=True)

        print(f"\n  Year {yr} Summary: {len(yr_clean_uids)} marketing blasts to trash, {len(yr_preserve_uids)} preserved.")
        grand_total_preserved += len(yr_preserve_uids)

        if not dry_run and yr_clean_uids:
            if batch_limit:
                remaining_quota = batch_limit - grand_total_cleaned
                if remaining_quota < len(yr_clean_uids):
                    yr_clean_uids = yr_clean_uids[:remaining_quota]

            print(f"  Moving {len(yr_clean_uids)} messages from {yr} to [Gmail]/Trash...")
            trash_batch_size = 500
            for b in range(0, len(yr_clean_uids), trash_batch_size):
                b_uids = yr_clean_uids[b:b+trash_batch_size]
                uid_set = b','.join(b_uids).decode('ascii')
                mail.uid('copy', uid_set, '[Gmail]/Trash')
                mail.uid('store', uid_set, '+FLAGS', r'(\Deleted)')
                print(f"    Moved {min(b + trash_batch_size, len(yr_clean_uids))}/{len(yr_clean_uids)}...", end="\r", flush=True)

            mail.expunge()
            print(f"\n  ✅ Successfully trashed and expunged {len(yr_clean_uids)} messages from {yr}.")
            grand_total_cleaned += len(yr_clean_uids)
        else:
            grand_total_cleaned += len(yr_clean_uids)

    print("\n=======================================================")
    print(f"  OVERALL CLEANUP SUMMARY ({'DRY RUN' if dry_run else 'COMPLETED'})")
    print(f"  Total Candidates Checked : {grand_total_found}")
    print(f"  🛡️ Preserved (Safe/Orders): {grand_total_preserved}")
    print(f"  🧹 Cleaned to Trash       : {grand_total_cleaned}")
    print("=======================================================")

    print("\nSample Preserved Messages (Receipts/Orders/Protected):")
    for s, sub, d in samples_preserved:
        print(f"  [KEEP]  {s:<35} | {sub:<45} | {d}")

    print("\nSample Cleaned Marketing Blasts:")
    for s, sub, d in samples_cleaned:
        print(f"  [CLEAN] {s:<35} | {sub:<45} | {d}")

    mail.logout()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="LDK Ops Inbox Triage & Cleaner")
    parser.add_argument("--apply", action="store_true", help="Apply cleanup actions (moves noise to Trash)")
    parser.add_argument("--organize", action="store_true", help="Organize remaining INBOX messages into custom labels and archive out of INBOX")
    parser.add_argument("--clean-promotions", action="store_true", help="Purge archived promotional marketing emails from [Gmail]/All Mail")
    parser.add_argument("--year", type=int, default=None, help="Target specific year for promotions cleanup (e.g. 2018)")
    parser.add_argument("--older-than", default="30d", help="Older than threshold for promotions cleanup (default: 30d)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of messages to process/trash")
    parser.add_argument("--account", choices=["dailey_ldk", "dailey_personal", "leo", "all"], default=None, help="Target specific account")
    args = parser.parse_args()

    dry_run = not args.apply
    creds = load_credentials()
    
    # If cleaning promotions, default account is dailey_personal
    if args.clean_promotions and not args.account:
        target_account = "dailey_personal"
    elif args.account:
        target_account = args.account
    else:
        target_account = "all"
    
    all_accounts = [
        ('dailey_ldk', 'Dailey LDK', creds['dailey_ldk']['email'], creds['dailey_ldk']['password']),
        ('dailey_personal', 'Dailey Personal', creds['dailey_personal']['email'], creds['dailey_personal']['password']),
        ('leo', 'Leo', creds['leo']['email'], creds['leo']['password'])
    ]
    
    for key, name, addr, pwd in all_accounts:
        if target_account != 'all' and target_account != key:
            continue
        if args.clean_promotions:
            clean_archived_promotions(name, addr, pwd, dry_run=dry_run, target_year=args.year, older_than=args.older_than, batch_limit=args.limit)
        elif args.organize:
            organize_inbox(name, addr, pwd, dry_run=dry_run)
        else:
            process_inbox(name, addr, pwd, dry_run=dry_run)

