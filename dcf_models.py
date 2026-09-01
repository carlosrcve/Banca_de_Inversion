# dcf_models.py
from dataclasses import dataclass
from typing import List

@dataclass
class DCFInputs:
    historical_revenue: float
    growth_rates: List[float]       # Tasa de crecimiento proyectada por año (%)
    ebit_margins: List[float]       # Margen EBIT proyectado (%)
    tax_rate: float                 # Tasa impositiva (%)
    capex_percent: float            # CapEx como % de ingresos
    nwc_percent: float              # Cambio en NWC como % de ingresos
    da_percent: float               # Depreciación y Amortización como % de ingresos
    wacc: float                     # Costo Promedio Ponderado de Capital (%)
    terminal_growth_rate: float     # Tasa de crecimiento perpetuo (g) (%)
    net_debt: float                 # Deuda Neta = Deuda Total - Efectivo

@dataclass
class DCFResults:
    projected_revenues: List[float]
    projected_ebit: List[float]
    projected_nopat: List[float]
    free_cash_flows: List[float]
    pv_cash_flows: List[float]
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    equity_value: float