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