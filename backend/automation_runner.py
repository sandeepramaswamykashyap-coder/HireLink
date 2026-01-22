from datetime import datetime
import streamlit as st
from backend.agents.auto_applier import AutoApplier

def run_pilot_mission(role, loc, sel_res_id, sel_portals, user_email, render_phases_callback, update_stats_callback, log_terminal):
    """
    Executes the Job Pilot automation mission.
    Extracted from app.py to avoid indentation errors and improve maintainability.
    """
    applier = AutoApplier()
    
    phase_map = {
        "Login Verification": 0, "Auto-Login": 0, "Login Success": 0,
        "Scraping Jobs": 1, "Enrichment": 1,
        "Matching Jobs": 2,
        "Applying": 3, "Finished": 4
    }
    
    full_log = []
    
    # Logging Setup
    from backend.database import SessionLocal, ActivityLog, AppUser
    db = SessionLocal()
    user = db.query(AppUser).filter(AppUser.email == user_email).first()
    uid = user.id if user else None
    
    # Log Start
    try:
        if uid:
            db.add(ActivityLog(user_id=uid, action="Mission Started", details=f"Role: {role}, Loc: {loc}"))
            db.commit()
    except Exception as e:
        print(f"Log Error: {e}")

    try:
        if not st.session_state.get('pilot_running', False):
            db.close()
            return

        for update in applier.run_hyper_automation(role, loc, sel_res_id, target_portals=sel_portals, user_email=user_email):
            step = update.get('step')
            status = update.get('status')
            
            # Update State
            print(f"DEBUG: Pilot Step: {step} - Status: {status}") # Trace
            st.session_state['m_step'] = step
            st.session_state['m_status'] = status
            st.session_state['m_phase_idx'] = phase_map.get(step, 0)
            
            # Parsing logic for stats
            if "Scraped" in status or "Found" in status:
                import re
                matches = re.findall(r'\d+', status)
                if matches: st.session_state['m_scanned'] = int(matches[0])
            
            if "matches" in status.lower() and step == "Matching Jobs":
                import re
                matches = re.findall(r'\d+', status)
                if matches: st.session_state['m_matches'] = int(matches[0])
            
            if status == "SUCCESS":
                st.session_state['m_sent'] += 1
                # Log Success
                if uid:
                    try:
                        db.add(ActivityLog(user_id=uid, action="Application Sent", details=f"Applied via {step}"))
                        db.commit()
                    except: pass
            
            # Refresh UI Components
            render_phases_callback(st.session_state['m_phase_idx'])
            update_stats_callback()
            
            full_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {step}: {status}")
            log_terminal.code("\n".join(full_log[-10:]))
            
            if step == "Finished":
                st.session_state['pilot_running'] = False
                st.balloons()
                st.success("Mission Concluded Successfully!")
                db.close()
                st.rerun()
    except Exception as e:
        db.close()

    except Exception as e:
        st.session_state['pilot_running'] = False
        st.error(f"Critical System Failure: {str(e)}")
        st.session_state['m_status'] = "FAILURE: " + str(e)
        update_stats_callback()
