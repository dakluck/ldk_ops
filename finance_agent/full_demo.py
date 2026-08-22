import os
from datetime import datetime
from api.mercury_client import MercuryClient
from core.categorizer import TransactionCategorizer
from main import FinanceAgentOrchestrator

def run_full_lifecycle_demo():
    print("================================================================================")
    print("            🚀 FINANCE AGENT: FULL END-TO-END DEMO 🚀            ")
    print("================================================================================\n")
    
    orchestrator = FinanceAgentOrchestrator()
    
    print("STEP 1: Running Audit (Discovery Phase)...")
    orchestrator.run_safe_mode_audit()
    
    print("\n" + "-"*80)
    print("STEP 2: Running Apply (Action Phase)...")
    orchestrator.apply_proposals()
    
    print("\n" + "-"*80)
    print("STEP 3: Running Final Audit (Verification Phase)...")
    orchestrator.run_safe_mode_audit()
    
    print("\n================================================================================")
    print("                 ✅ DEMO COMPLETE: SYSTEM IS READY ✅                 ")
    print("================================================================================")

if __name__ == "__main__":
    # Set CWD to the finance_agent directory so imports work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_full_lifecycle_demo()
