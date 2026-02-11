"""
Scheduled Mood Analysis Job

Runs nightly (or on-demand) to analyze mood patterns for all patients
and trigger alerts as needed.

This script should be scheduled via cron or Windows Task Scheduler.
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from lifelens.qdrant.client import get_qdrant_client
from lifelens.agents.mood_agent import run_mood_analysis
from lifelens.auth.users import get_all_patients

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mood_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run_scheduled_mood_analysis():
    """
    Runs mood analysis for all patients in the system.
    
    This should be called by a scheduler (cron/Task Scheduler) nightly.
    """
    logger.info("=" * 60)
    logger.info(f"Starting scheduled mood analysis at {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        # Get Qdrant client
        client = get_qdrant_client()
        logger.info("Connected to Qdrant")
        
        # Get all patients
        patients = get_all_patients()
        logger.info(f"Found {len(patients)} patients in system")
        
        if not patients:
            logger.warning("No patients found. Exiting.")
            return
        
        # Analyze each patient
        results = []
        for patient in patients:
            patient_id = patient.get("patient_id")
            patient_name = patient.get("full_name", "Unknown")
            
            logger.info(f"\nAnalyzing patient: {patient_name} ({patient_id})")
            logger.info("-" * 40)
            
            try:
                # Run mood analysis with alerts enabled
                result = run_mood_analysis(
                    patient_id=patient_id,
                    qdrant_client=client,
                    trigger_alerts=True
                )
                
                if result:
                    risk = result.get("risk_score", 0)
                    verdict = result.get("verdict", "UNKNOWN")
                    notified = result.get("notified", False)
                    
                    logger.info(f"  Risk Score: {risk:.2%}")
                    logger.info(f"  Verdict: {verdict}")
                    logger.info(f"  Notified: {notified}")
                    
                    if result.get("insufficient_data"):
                        logger.info(f"  Insufficient mood data for {patient_id}")
                    
                    results.append({
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        "risk_score": risk,
                        "verdict": verdict,
                        "notified": notified,
                        "success": True
                    })
                else:
                    logger.warning(f"  No result returned for {patient_id}")
                    results.append({
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        "success": False
                    })
                    
            except Exception as e:
                logger.error(f"  Error analyzing {patient_id}: {e}")
                results.append({
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "error": str(e),
                    "success": False
                })
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("MOOD ANALYSIS SUMMARY")
        logger.info("=" * 60)
        
        successful = sum(1 for r in results if r.get("success"))
        alerts_sent = sum(1 for r in results if r.get("notified"))
        high_risk = sum(1 for r in results if r.get("risk_score", 0) >= 0.7)
        
        logger.info(f"Patients Analyzed: {len(results)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Alerts Sent: {alerts_sent}")
        logger.info(f"High Risk Patients: {high_risk}")
        
        # List high-risk patients
        if high_risk > 0:
            logger.info("\nHigh Risk Patients:")
            for r in results:
                if r.get("risk_score", 0) >= 0.7:
                    logger.info(f"  • {r['patient_name']} ({r['patient_id']}): {r['risk_score']:.2%} - {r.get('verdict', 'N/A')}")
        
        logger.info("\nScheduled mood analysis completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Scheduled mood analysis failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    logger.info("Mood Analysis Scheduler - LifeLens")
    logger.info(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = run_scheduled_mood_analysis()
    
    if results is None:
        sys.exit(1)
    else:
        sys.exit(0)
