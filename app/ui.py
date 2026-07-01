# app/ui.py
import streamlit as st
import json
import os
import importlib

# Force reload helper modules to bypass Streamlit's import cache
import app.schema
import app.agent
import app.supabase_client
importlib.reload(app.schema)
importlib.reload(app.agent)
importlib.reload(app.supabase_client)

from app.agent import HOAAuditorLivePipeline
from app.supabase_client import save_audit_report

# Set up clean, modern page layout
st.set_page_config(page_title="HOA Document Auditor", page_icon="🏢", layout="wide")

# Custom CSS styling to make the cards look gorgeous and professional
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #6c757d;
        margin-bottom: 15px;
    }
    .risk-high { background-color: #fff5f5; border-left-color: #dc3545; }
    .risk-medium { background-color: #fffdf0; border-left-color: #ffc107; }
    .risk-low { background-color: #f4fff5; border-left-color: #28a745; }
    </style>
""", unsafe_allow_html=True)

st.title("🏢 HOA Document Risk Auditor")
st.markdown("### Turning 300+ Pages of Legal Noise into Simple, Actionable Clarity")
st.write("---")

# Split layout: Raw Document Scale vs. AI Processing Dashboard
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📁 Unstructured Document Ingestion Pipeline")
    st.markdown("This system ingests messy, overwhelming document dumps provided by a seller and matches them instantly against Washington State regulations.")
    
    # Track workspace folder counts dynamically
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mock_data')
    all_files = [f for f in os.listdir(data_dir) if f.endswith(".txt")] if os.path.exists(data_dir) else []
    
    # Processing metrics
    m1, m2 = st.columns(2)
    m1.metric(label="Raw Package Scale", value="~300 Pages")
    m2.metric(label="Detected Source Components", value=f"{len(all_files)} Files")
    
    st.write("---")
    st.markdown("🔍 **Detected Source Files:**")
    if all_files:
        for filename in sorted(all_files):
            with st.expander(f"📄 {filename}", expanded=False):
                try:
                    with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                        st.code(f.read(), language="text")
                except Exception as e:
                    st.error(f"Error reading file: {e}")
    else:
        st.warning("No .txt files detected in mock_data folder.")

with col2:
    st.subheader("📋 Executive Audit Summary")
    st.write("Click below to run a state-compliant risk analysis on your document package.")
    
    # Trigger the full token-cached live pipeline on click!
    if st.button("🚀 Run Live Audit Analysis", type="primary", use_container_width=True):
        with st.spinner("Processing data package layers safely..."):
            try:
                # 1. Fire your cached multi-agent execution pipeline logic
                pipeline = HOAAuditorLivePipeline()
                pipeline_response = pipeline.run_agent_analysis()
                
                # 2. BULLETPROOF UNPACKING SAFEGUARD:
                # Check if the pipeline returned a tuple (data, was_cached) or just a single data object
                if isinstance(pipeline_response, tuple) and len(pipeline_response) == 2:
                    result_data, was_cached = pipeline_response
                else:
                    result_data = pipeline_response
                    was_cached = False  # Default fallback if no tuple was returned
                
                # 3. BULLETPROOF PARSING: Convert raw string to dictionary safely if needed
                if isinstance(result_data, str):
                    report_data = json.loads(result_data)
                else:
                    report_data = result_data
                
                # Check if the response contains an error message from the backend
                if "error" in report_data:
                    st.error(f"Pipeline Error: {report_data['error']}")
                else:
                    # 4. Handle Token-Saving Notification UI banners cleanly
                    if was_cached:
                        st.success("🎯 **Token Blocker Active:** Document fingerprint matched database records perfectly! Retrieved instant analysis summary from Supabase cache at 0 token expense.")
                    else:
                        # Only show the fresh ingestion info and save to the database on a true cache miss
                        st.info("💸 **New Content Ingested:** Dynamic file changes detected. Live model loop triggered.")
                        save_audit_report(report_data)
                        st.success("🎉 Live analysis complete! New report successfully synced to cloud storage.")
                    
                    st.write("---")
                    
                    # 5. RENDER VERDICT METRIC WARNING BOX
                    verdict_info = report_data.get("overall_verdict", {})
                    verdict_val = verdict_info.get('verdict', 'CAUTION ADVISED').upper()
                    
                    if "APPROVED" in verdict_val or "PASS" in verdict_val:
                        st.success(f"### 🎉 Overall Verdict: {verdict_val}")
                    elif "WARNING" in verdict_val or "CAUTION" in verdict_val:
                        st.warning(f"### ⚠️ Overall Verdict: {verdict_val}")
                    else:
                        st.error(f"### 🚨 Overall Verdict: {verdict_val}")
                        
                    st.markdown(f"**Simple English Analysis:** {verdict_info.get('verdict_reason', '')}")
                    st.write("---")
                    
                    # 6. LAY OUT THE THREE INTERACTIVE TABS FOR USER DIGESTION
                    tab1, tab2, tab3 = st.tabs(["🚨 Identified Risks", "✅ Buyer Action Items", "🔍 Missing Documents"])
                    
                    with tab1:
                        st.markdown("### Clear Breakdown of Discovered Liabilities")
                        st.caption("We translated dense legalese statements into clear, plain English definitions.")
                        
                        findings = report_data.get("risks", {}).get("findings", [])
                        if findings:
                            for risk in findings:
                                urgency_level = risk.get("urgency", "Low").lower()
                                card_class = f"risk-{urgency_level}"
                                
                                st.markdown(f"""
                                    <div class="metric-card {card_class}">
                                        <h4>🏷️ {risk.get('label', 'Disclosed Issue')} (<span style='text-transform: uppercase;'>{risk.get('urgency', 'LOW')} Urgency</span>)</h4>
                                        <p><b>What the documents say:</b> {risk.get('finding', '')}</p>
                                        <p style='color: #1a1a1a;'><b>💡 Why this matters to you:</b> {risk.get('buyer_note', '')}</p>
                                        <small style='color: #6c757d;'>📍 Verified Reference: {risk.get('source_document', '')} ({risk.get('source_section', '')})</small>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                if risk.get("lender_flag"):
                                    st.warning("⚠️ **Lender Flag Warning:** Banks frequently reject loans for this issue. This may halt your mortgage approval timeline!")
                                st.write("")
                        else:
                            st.info("No explicit risk findings flagged in this package.")

                    with tab2:
                        st.markdown("### 📋 Your Before-You-Sign Checklist")
                        st.markdown("Take these exact negotiation steps to protect yourself before signing any paperwork:")
                        
                        action_items = report_data.get("action_items", [])
                        if action_items:
                            for item in action_items:
                                priority_color = "🔴" if item.get("priority") == "High" else "🟡" if item.get("priority") == "Medium" else "🟢"
                                st.markdown(f"**{priority_color} {item.get('priority', 'Low')} Priority:** {item.get('action', '')}")
                                st.caption(f"Linked reference element: `{item.get('risk_id', 'N/A')}`")
                                st.write("---")
                        else:
                            st.info("No critical immediate action items recommended.")

                    with tab3:
                        st.markdown("### ❌ Missing Critical Items")
                        st.markdown("The state requires these items be disclosed, but **they were completely absent** from the package provided by the seller:")
                        
                        absences = report_data.get("risks", {}).get("notable_absences", [])
                        if absences:
                            for absence in absences:
                                st.markdown(f"• 🚨 **Missing Component:** {absence}")
                        else:
                            st.info("No major statutory document absences observed.")

            except Exception as e:
                st.error(f"Dashboard execution anomaly observed: {e}")
# End of file - triggers hot reload v11