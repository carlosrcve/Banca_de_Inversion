# dcf_engine.py
from dcf_models import DCFInputs, DCFResults

class DCFEngine:
    @staticmethod
    def calculate(inputs: DCFInputs) -> DCFResults:
        num_years = len(inputs.growth_rates)
        revenues = []
        ebits = []
        nopats = []
        fcfs = []
        pv_fcfs = []

        current_rev = inputs.historical_revenue

        # 1. Proyección de Flujos de Caja Libres (FCFF)
        for i in range(num_years):
            current_rev *= (1 + inputs.growth_rates[i] / 100)
            ebit = current_rev * (inputs.ebit_margins[i] / 100)
            nopat = ebit * (1 - inputs.tax_rate / 100)
            
            da = current_rev * (inputs.da_percent / 100)
            capex = current_rev * (inputs.capex_percent / 100)
            delta_nwc = current_rev * (inputs.nwc_percent / 100)

            # FCF = NOPAT + D&A - CapEx - ΔNWC
            fcf = nopat + da - capex - delta_nwc
            
            # Valor Presente del FCF
            pv_fcf = fcf / ((1 + inputs.wacc / 100) ** (i + 1))

            revenues.append(round(current_rev, 2))
            ebits.append(round(ebit, 2))
            nopats.append(round(nopat, 2))
            fcfs.append(round(fcf, 2))
            pv_fcfs.append(round(pv_fcf, 2))

        # 2. Valor Terminal (Método de Crecimiento Perpetuo)
        last_fcf = fcfs[-1]
        wacc_dec = inputs.wacc / 100
        g_dec = inputs.terminal_growth_rate / 100
        
        terminal_value = (last_fcf * (1 + g_dec)) / (wacc_dec - g_dec)
        pv_terminal_value = terminal_value / ((1 + wacc_dec) ** num_years)

        # 3. Valor de la Empresa (EV) y Valor de Capital (Equity Value)
        enterprise_value = sum(pv_fcfs) + pv_terminal_value
        equity_value = enterprise_value - inputs.net_debt

        return DCFResults(
            projected_revenues=revenues,
            projected_ebit=ebits,
            projected_nopat=nopats,
            free_cash_flows=fcfs,
            pv_cash_flows=pv_fcfs,
            terminal_value=round(terminal_value, 2),
            pv_terminal_value=round(pv_terminal_value, 2),
            enterprise_value=round(enterprise_value, 2),
            equity_value=round(equity_value, 2)
        )