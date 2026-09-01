app.py
dcf_engine.py
dcf_models.py

┌─────────────────────────────────────────────────────────┐
│                     UI (app.py)                         │
└───────────┬─────────────────────────────────▲───────────┘
            │                                 │
            │ 1. Envía parámetros sin procesar│ 4. Recibe resultados
            │    (variables sueltas/inputs)   │    formatos para graficar
            ▼                                 │
┌─────────────────────────────────────────────┴───────────┐
│               Controller (dcf_controller.py)            │
└───────────┬─────────────────────────────────▲───────────┘
            │                                 │
            │ 2. Construye DCFInputs          │ 3. Retorna DCFResults
            ▼                                 │
┌─────────────────────────────────────────────┴───────────┐
│       dcf_models.py      │      dcf_engine.py           │
└──────────────────────────┴──────────────────────────────┘



# cd desktop
# streamlit run app.py



├── .streamlit/
│   └── secrets.toml        <-- (NO subir a GitHub pública)
├── .gitignore
├── app.py                  <-- Interfaz de Streamlit
├── dcf_controller.py      <-- Controlador y conexión TiDB Cloud
├── dcf_models.py          <-- Clases Dataclass (DCFInputs, DCFResults)
├── dcf_engine.py          <-- Lógica pura de cálculo DCF
└── requirements.txt        <-- Librerías requeridas


Paso 1: Abrir la terminal en la carpeta del proyecto
Abre la consola de comandos (PowerShell o Git Bash).

Ubícate dentro de tu carpeta ejecutando:

cd "C:\Users\Carlos Rodriguez\Desktop\Banca_de_Inversion"

# 1. Inicializar el repositorio Git
git init

# 2. Agregar todos los archivos al área de preparación
git add .

# 3. Guardar la primera captura (commit) del proyecto
git commit -m "Initial commit: Proyecto Banca de Inversion con Streamlit y TiDB Cloud"

# 4. Asegurarnos de que la rama principal se llame main
git branch -M main


# Vincular tu carpeta local con GitHub (reemplaza la URL con la tuya)
git remote add origin https://github.com/TU_USUARIO/Banca_de_Inversion.git

# Subir los archivos
git push -u origin main




1. Separación por Módulos y Capas
Módulo de M&A y Valoración de Empresas: Motores de valoración por Descuento de Flujos de Caja (DCF), Múltiples Comparables (EBITDA, EV/Sales) y LBO (Leveraged Buyout).

Módulo de Gestión de Portafolio y Riesgo: Análisis de varianza-covarianza, Optimización de Markowitz, cálculo de Sharpe Ratio, Beta y Value at Risk (VaR).

Módulo de Análisis Geoscatelital/Alternativo: Consultas automáticas a APIs de datos macro, commodities y seguimiento satelital de activos/inventarios.



https://bancadeinversion-axcln8mqbrzxadh5qq7ctf.streamlit.app/



cd "C:\Users\Carlos Rodriguez\Desktop\Banca_de_Inversion"

git add app.py
git commit -m "Fix: Ajuste de escala float para grafico"
git push origin main