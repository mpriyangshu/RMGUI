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

st.set_page_config(page_title="Relative Permeability & Fraction Flow", layout="wide")

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

st.sidebar.title("User Inputs")
mu_w = st.sidebar.number_input("Water viscosity (cP)", 0.1, 1000.0, 0.5)
mu_o = st.sidebar.number_input("Oil viscosity (cP)", 0.1, 1000.0, 5.0)
Swc = st.sidebar.slider("Irreducible water saturation (Swc)", 0.0, 0.5, 0.2)
Sor = st.sidebar.slider("Residual oil saturation (Sor)", 0.0, 0.5, 0.2)
krw0 = st.sidebar.number_input("End-point krw0", 0.0, 1.0, 0.3)
kro0 = st.sidebar.number_input("End-point kro0", 0.0, 1.0, 0.9)
model = st.sidebar.selectbox("Select model", list(MODEL_FUNCS.keys()))

if model == 'Corey':
    nw = st.sidebar.number_input("Corey exponent nw", 0.1, 10.0, 3.0)
    no = st.sidebar.number_input("Corey exponent no", 0.1, 10.0, 2.0)
else:
    nw = 3.0
    no = 2.0

st.sidebar.markdown("---")
compute = st.sidebar.button("Compute & Plot")

# ------------------ Main Layout ------------------

st.title("💧 Relative Permeability & Fraction Flow Calculator")
st.write("This tool calculates and plots relative permeability (krw, kro) and fractional flow (fw) as functions of water saturation Sw.")

if compute:
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

    st.subheader("Numerical Results")
    st.dataframe(df.round(5))

    # Plot krw/kro
    fig1, ax1 = plt.subplots()
    ax1.plot(Sw, krw, label='krw')
    ax1.plot(Sw, kro, label='kro')
    ax1.set_xlabel('Water Saturation (Sw)')
    ax1.set_ylabel('Relative Permeability')
    ax1.legend()
    st.pyplot(fig1)

    # Plot fw
    fig2, ax2 = plt.subplots()
    ax2.plot(Sw, fw, 'g--', label='fw')
    ax2.set_xlabel('Water Saturation (Sw)')
    ax2.set_ylabel('Fractional Flow (fw)')
    ax2.legend()
    st.pyplot(fig2)

    # Export buttons
    st.subheader("📤 Export Results")

    # Excel export
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Results')
    st.download_button(
        label="Download Excel (.xlsx)",
        data=excel_buffer.getvalue(),
        file_name="relperm_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # PDF export
    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        fig1.tight_layout()
        pdf.savefig(fig1)
        fig2.tight_layout()
        pdf.savefig(fig2)
    st.download_button(
        label="Download PDF (.pdf)",
        data=pdf_buffer.getvalue(),
        file_name="relperm_results.pdf",
        mime="application/pdf"
    )

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
        mime="application/json"
    )
