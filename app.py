"""
Relative Permeability & Fraction Flow Calculator
Author: Priyangshu Malakar
Repo: https://github.com/mpriyangshu/RMGUI
This app computes and plots relative permeability and fractional flow curves during water flooding.
It supports Corey, Pirson, and Wyllie-Gardner models, with options to export results to .xlsx and .pdf.
"""

import streamlit as st
import numpy as np
import pandas as pd
import io
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Set page config with white background
st.set_page_config(
    page_title="Relative Permeability & Fraction Flow", 
    layout="wide",
    page_icon="📊"
)

# Apply custom CSS for white background and premium styling
st.markdown("""
<style>
    .main {
        background-color: #ffffff;
    }
    .stApp {
        background-color: #ffffff;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .css-1d391kg, .css-12oz5g7 {
        background-color: #ffffff;
    }
    .block-container {
        padding-top: 2rem;
        background-color: #ffffff;
    }
    .header-style {
        color: #1f77b4;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 10px;
    }
    .card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ Relative permeability models ------------------

def effective_saturation(Sw, Swc, Sor):
    denom = 1.0 - Swc - Sor
    denom = np.where(denom == 0, 1e-12, denom)
    Sstar = (Sw - Swc) / denom
    Sstar = np.clip(Sstar, 0.0, 1.0)
    return Sstar

def corey_kr(Sw, Swc, Sor, krw0, kro0, nw=3.0, no=2.0):
    Sstar = effective_saturation(Sw, Swc, Sor)
    krw = krw0 * (Sstar ** nw)
    kro = kro0 * ((1.0 - Sstar) ** no)
    return krw, kro

def pirson_kr(Sw, Swc, Sor, krw0, kro0):
    Sstar = effective_saturation(Sw, Swc, Sor)
    krw = krw0 * (Sstar ** 2)
    kro = kro0 * ((1.0 - Sstar) ** 2)
    return krw, kro

def wyllie_gardner_kr(Sw, Swc, Sor, krw0, kro0):
    Sstar = effective_saturation(Sw, Swc, Sor)
    krw = krw0 * (Sstar ** 1.5)
    kro = kro0 * ((1.0 - Sstar) ** 1.5)
    return krw, kro

MODEL_FUNCS = {
    'Corey': corey_kr,
    'Pirson': pirson_kr,
    'Wyllie-Gardner': wyllie_gardner_kr,
}

# ------------------ Fraction flow ------------------

def fraction_flow(krw, kro, mu_w, mu_o):
    lambda_w = krw / mu_w
    lambda_o = kro / mu_o
    fw = lambda_w / (lambda_w + lambda_o)
    fw = np.nan_to_num(fw, nan=0.0, posinf=0.0, neginf=0.0)
    return fw

# ------------------ Sidebar Inputs ------------------

st.sidebar.markdown('<div class="header-style">🔧 User Inputs</div>', unsafe_allow_html=True)

st.sidebar.markdown("### Fluid Properties")
mu_w = st.sidebar.number_input("**Water viscosity (cP)**", 0.1, 1000.0, 0.5, help="Viscosity of water phase")
mu_o = st.sidebar.number_input("**Oil viscosity (cP)**", 0.1, 1000.0, 5.0, help="Viscosity of oil phase")

st.sidebar.markdown("### Saturation Parameters")
Swc = st.sidebar.slider("**Irreducible water saturation (Swc)**", 0.0, 0.5, 0.2, 0.01, help="Minimum water saturation that cannot be reduced")
Sor = st.sidebar.slider("**Residual oil saturation (Sor)**", 0.0, 0.5, 0.2, 0.01, help="Minimum oil saturation that cannot be reduced")

st.sidebar.markdown("### End-point Relative Permeabilities")
krw0 = st.sidebar.number_input("**End-point krw0**", 0.0, 1.0, 0.3, 0.01, help="Relative permeability to water at residual oil saturation")
kro0 = st.sidebar.number_input("**End-point kro0**", 0.0, 1.0, 0.9, 0.01, help="Relative permeability to oil at irreducible water saturation")

st.sidebar.markdown("### Model Selection")
model = st.sidebar.selectbox("**Select relative permeability model**", list(MODEL_FUNCS.keys()), help="Choose the correlation model for calculations")

if model == 'Corey':
    st.sidebar.markdown("### Corey Exponents")
    nw = st.sidebar.number_input("**Corey exponent nw**", 0.1, 10.0, 3.0, 0.1, help="Exponent for water relative permeability curve")
    no = st.sidebar.number_input("**Corey exponent no**", 0.1, 10.0, 2.0, 0.1, help="Exponent for oil relative permeability curve")
else:
    nw = 3.0
    no = 2.0

st.sidebar.markdown("---")
compute = st.sidebar.button("🚀 Compute & Plot", type="primary", use_container_width=True)

# ------------------ Main Layout ------------------

st.markdown('<div class="header-style">📊 Relative Permeability & Fraction Flow Calculator</div>', unsafe_allow_html=True)

st.markdown("""
<div class="card">
    <h3>📖 Introduction</h3>
    <p>This tool calculates and plots relative permeability (krw, kro) and fractional flow (fw) as functions of water saturation Sw during water flooding operations.</p>
    <p><strong>Group Members:</strong> Priyangshu Malakar, Aishwarya</p>
    <p><strong>Features:</strong></p>
    <ul>
        <li>Multiple relative permeability models (Corey, Pirson, Wyllie-Gardner)</li>
        <li>Real-time calculations and visualization</li>
        <li>Export results to Excel and PDF formats</li>
        <li>Save and load project configurations</li>
    </ul>
</div>
""", unsafe_allow_html=True)

if compute:
    # Add progress indicator
    with st.spinner('Calculating relative permeability and fractional flow...'):
        Sw = np.linspace(0, 1, 201)
        func = MODEL_FUNCS.get(model)
        if model == 'Corey':
            krw, kro = func(Sw, Swc, Sor, krw0, kro0, nw, no)
        else:
            krw, kro = func(Sw, Swc, Sor, krw0, kro0)

        fw = fraction_flow(krw, kro, mu_w, mu_o)

        df = pd.DataFrame({
            'Sw': Sw,
            'krw': krw,
            'kro': kro,
            'fw': fw
        })

    # Display input summary
    st.markdown("### 📋 Input Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Water Viscosity", f"{mu_w} cP")
        st.metric("Swc", f"{Swc}")
    with col2:
        st.metric("Oil Viscosity", f"{mu_o} cP")
        st.metric("Sor", f"{Sor}")
    with col3:
        st.metric("krw0", f"{krw0}")
        st.metric("Model", model)
    with col4:
        st.metric("kro0", f"{kro0}")
        if model == 'Corey':
            st.metric("Exponents", f"nw={nw}, no={no}")

    st.markdown("### 📈 Numerical Results")
    st.dataframe(df.round(5), use_container_width=True)

    # Create plots with white background
    fig1, ax1 = plt.subplots(figsize=(10, 6), facecolor='white')
    ax1.set_facecolor('white')
    ax1.plot(Sw, krw, 'b-', linewidth=2, label='krw (Water)')
    ax1.plot(Sw, kro, 'r-', linewidth=2, label='kro (Oil)')
    ax1.set_xlabel('Water Saturation (Sw)', fontsize=12)
    ax1.set_ylabel('Relative Permeability', fontsize=12)
    ax1.set_title('Relative Permeability vs Water Saturation', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=12)
    ax1.set_xlim(0, 1)
    st.pyplot(fig1)

    # Plot fw
    fig2, ax2 = plt.subplots(figsize=(10, 6), facecolor='white')
    ax2.set_facecolor('white')
    ax2.plot(Sw, fw, 'g-', linewidth=2, label='fw')
    ax2.set_xlabel('Water Saturation (Sw)', fontsize=12)
    ax2.set_ylabel('Fractional Flow (fw)', fontsize=12)
    ax2.set_title('Fractional Flow vs Water Saturation', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=12)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    st.pyplot(fig2)

    # Export section
    st.markdown("### 📤 Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Excel export
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')
            # Add summary sheet
            summary_df = pd.DataFrame({
                'Parameter': ['Water Viscosity (cP)', 'Oil Viscosity (cP)', 'Swc', 'Sor', 
                            'krw0', 'kro0', 'Model', 'nw', 'no'],
                'Value': [mu_w, mu_o, Swc, Sor, krw0, kro0, model, nw, no]
            })
            summary_df.to_excel(writer, index=False, sheet_name='Input_Summary')
        
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=excel_buffer.getvalue(),
            file_name="relperm_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col2:
        # PDF export
        pdf_buffer = io.BytesIO()
        with PdfPages(pdf_buffer) as pdf:
            fig1.tight_layout()
            pdf.savefig(fig1, bbox_inches='tight', facecolor='white')
            fig2.tight_layout()
            pdf.savefig(fig2, bbox_inches='tight', facecolor='white')
        
        st.download_button(
            label="📥 Download PDF (.pdf)",
            data=pdf_buffer.getvalue(),
            file_name="relperm_results.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with col3:
        # Save project JSON
        project_data = {
            'params': {
                'mu_w': mu_w, 'mu_o': mu_o, 'Swc': Swc, 'Sor': Sor,
                'krw0': krw0, 'kro0': kro0, 'model': model, 'nw': nw, 'no': no
            },
            'results': df.to_dict(orient='list')
        }
        st.download_button(
            label="💾 Save Project (.json)",
            data=json.dumps(project_data, indent=2),
            file_name="project_relperm.json",
            mime="application/json",
            use_container_width=True
        )

else:
    st.info("👈 Configure your parameters in the sidebar and click 'Compute & Plot' to see the results!")

# Add footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Developed by Priyangshu Malakar | "
    "<a href='https://github.com/mpriyangshu/RMGUI' target='_blank'>GitHub Repository</a>"
    "</div>", 
    unsafe_allow_html=True
)
