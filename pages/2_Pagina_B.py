import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
from scipy.optimize import minimize
import gdown
import matplotlib.pyplot as plt

# ----------------------------
# Configuración ZIP de Drive
# ----------------------------
ZIP_FILE_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"
ZIP_NAME = "acciones.zip"
CARPETA_DATOS = "acciones"

# ----------------------------
# Funciones auxiliares
# ----------------------------
def download_and_extract_zip(file_id, zip_name, folder_name):
    if not os.path.exists(zip_name):
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, zip_name, quiet=False)
    if not os.path.exists(folder_name):
        os.makedirs(folder_name, exist_ok=True)
        with zipfile.ZipFile(zip_name, "r") as z:
            z.extractall(folder_name)

def read_user_csv(uploaded):
    try:
        df = pd.read_csv(uploaded)
        # Normalizar columnas
        cols_lower = [c.strip().lower() for c in df.columns]
        col_ticker = next((c for c, l in zip(df.columns, cols_lower) if "tick" in l), None)
        col_weight = next((c for c, l in zip(df.columns, cols_lower) if "%" in l or "por" in l or "peso" in l), None)
        if col_ticker is None or col_weight is None:
            st.error("El CSV debe tener columnas con Ticker y % del Portafolio")
            return None
        df[col_weight] = pd.to_numeric(df[col_weight], errors="coerce")
        if df[col_weight].isnull().any():
            st.error("Algunos pesos no son numéricos")
            return None
        df[col_weight] = df[col_weight] / df[col_weight].sum()
        df[col_ticker] = df[col_ticker].astype(str).str.strip().str.upper()
        return df[[col_ticker, col_weight]]
    except Exception as e:
        st.error(f"Error leyendo CSV: {e}")
        return None

def load_historical_data(tickers):
    series_list = []
    missing = []
    for t in tickers:
        path = os.path.join(CARPETA_DATOS, f"{t}.csv")
        if not os.path.exists(path):
            missing.append(t)
            continue
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        date_col = next((c for c in df.columns if c.lower() in ["date", "fecha"]), None)
        adj_col = next((c for c in df.columns if "adj" in c.lower() and "close" in c.lower()), None)
        if adj_col is None and "close" in df.columns:
            adj_col = "Close"
        if date_col is None or adj_col is None:
            missing.append(t)
            continue
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col, adj_col])
        df = df.sort_values(date_col)
        s = df.set_index(date_col)[adj_col].pct_change().dropna()
        s.name = t
        series_list.append(s)
    if missing:
        st.warning(f"No se encontraron históricos para: {missing}")
    return pd.concat(series_list, axis=1, join="inner").dropna() if series_list else None

def markowitz_analysis(returns_df):
    n_assets = returns_df.shape[1]
    mean_returns = returns_df.mean()
    cov_matrix = returns_df.cov()
    
    def portfolio_return(weights):
        return np.sum(mean_returns * weights)
    
    def portfolio_volatility(weights):
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    
    # GMVP
    w0 = np.ones(n_assets)/n_assets
    bounds = [(0,1)]*n_assets
    cons = [{'type':'eq','fun': lambda w: np.sum(w)-1}]
    gmv_res = minimize(portfolio_volatility, w0, method="SLSQP", bounds=bounds, constraints=cons)
    
    # Max Sharpe
    risk_free = 0.0
    def negative_sharpe(weights):
        ret = portfolio_return(weights)
        vol = portfolio_volatility(weights)
        return -(ret - risk_free)/vol
    ms_res = minimize(negative_sharpe, w0, method="SLSQP", bounds=bounds, constraints=cons)
    
    # Anualizar
    def anualizar(ret, vol):
        return ret*252, vol*np.sqrt(252)
    
    gmv_ret, gmv_vol = anualizar(portfolio_return(gmv_res.x), portfolio_volatility(gmv_res.x))
    ms_ret, ms_vol = anualizar(portfolio_return(ms_res.x), portfolio_volatility(ms_res.x))
    
    gmv_weights = pd.Series(gmv_res.x, index=returns_df.columns)
    ms_weights = pd.Series(ms_res.x, index=returns_df.columns)
    
    return {
        "GMVP": {"ret": gmv_ret, "vol": gmv_vol, "weights": gmv_weights},
        "MaxSharpe": {"ret": ms_ret, "vol": ms_vol, "weights": ms_weights}
    }

# ----------------------------
# Interfaz Streamlit
# ----------------------------
st.title("📈 Simulación Markowitz — App")

st.write("Sube un CSV con columnas `Ticker` y `% del Portafolio` para comparar con GMVP y Max Sharpe.")

# Botón para ejemplo
ejemplo = pd.DataFrame({"Ticker":["AAPL","MSFT","GOOGL"], "% del Portafolio":[40,30,30]})
st.download_button("📂 Descargar ejemplo CSV", ejemplo.to_csv(index=False), file_name="ejemplo_portafolio.csv")

# Subir CSV
uploaded = st.file_uploader("Sube tu CSV", type=["csv"])
if uploaded:
    df_user = read_user_csv(uploaded)
    if df_user is not None:
        st.success("CSV cargado correctamente")
        st.dataframe(df_user)
        
        # Descargar y extraer ZIP
        download_and_extract_zip(ZIP_FILE_ID, ZIP_NAME, CARPETA_DATOS)
        
        tickers = df_user["Ticker"].tolist()
        weights = df_user.iloc[:,1].values
        
        returns_df = load_historical_data(tickers)
        if returns_df is None or returns_df.shape[1]==0:
            st.error("No se pudieron cargar series válidas.")
        else:
            # Portafolio usuario
            mean_returns = returns_df.mean()
            cov_matrix = returns_df.cov()
            port_ret = float(np.dot(weights, mean_returns)*252)
            port_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix*252, weights))))
            
            # Markowitz
            marko_res = markowitz_analysis(returns_df)
            
            # Mostrar resultados
            st.subheader("📊 Resultados de Simulación")
            st.write(f"**Portafolio Usuario**: Retorno anual {port_ret:.2%}, Volatilidad anual {port_vol:.2%}")
            st.write(f"**GMVP**: Retorno anual {marko_res['GMVP']['ret']:.2%}, Volatilidad anual {marko_res['GMVP']['vol']:.2%}")
            st.write(f"**Max Sharpe**: Retorno anual {marko_res['MaxSharpe']['ret']:.2%}, Volatilidad anual {marko_res['MaxSharpe']['vol']:.2%}")
            
            # Mostrar distribución pesos
            st.subheader("Distribución de Pesos")
            distrib = pd.DataFrame({
                "Ticker": tickers,
                "% Portafolio Usuario": (weights*100).round(2)
            })
            distrib["GMVP"] = marko_res['GMVP']['weights'].reindex(tickers).fillna(0).round(4)*100
            distrib["Max Sharpe"] = marko_res['MaxSharpe']['weights'].reindex(tickers).fillna(0).round(4)*100
            st.dataframe(distrib)
            
            # Botón guardar resultados
            if st.button("💾 Finalizar y Guardar Resultados"):
                distrib.to_csv("resultado_comparacion.csv", index=False, encoding="utf-8-sig")
                st.success("✅ Resultados guardados en resultado_comparacion.csv")
