-- 1. Crear la Base de Datos
CREATE DATABASE IF NOT EXISTS valuations_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE valuations_db;

-- 2. Tabla de Clientes / Empresas a valorar
CREATE TABLE IF NOT EXISTS companies (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    tax_id VARCHAR(50) UNIQUE, -- RIF / NIT / Tax ID
    sector VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. Tabla Principal de Análisis DCF (Guarda inputs globales y resultados macro de dcf_models.py)
CREATE TABLE IF NOT EXISTS dcf_analyses (
    analysis_id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    scenario_name VARCHAR(100) DEFAULT 'Caso Base', -- Ej: Optimista, Pesimista, Base
    
    -- Supuestos Generales (Inputs de DCFInputs)
    historical_revenue DECIMAL(15, 2) NOT NULL,
    tax_rate DECIMAL(5, 2) NOT NULL,
    capex_percent DECIMAL(5, 2) NOT NULL,
    nwc_percent DECIMAL(5, 2) NOT NULL,
    da_percent DECIMAL(5, 2) NOT NULL,
    wacc DECIMAL(5, 2) NOT NULL,
    terminal_growth_rate DECIMAL(5, 2) NOT NULL,
    net_debt DECIMAL(15, 2) NOT NULL,

    -- Resultados del Cálculo (Outputs de DCFResults)
    terminal_value DECIMAL(15, 2) NOT NULL,
    pv_terminal_value DECIMAL(15, 2) NOT NULL,
    enterprise_value DECIMAL(15, 2) NOT NULL,
    equity_value DECIMAL(15, 2) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Tabla Detalle por Año (Guarda los arreglos/listas proyectadas año a año)
CREATE TABLE IF NOT EXISTS dcf_yearly_projections (
    projection_id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_id INT NOT NULL,
    year_number INT NOT NULL, -- Año 1, Año 2, etc.
    
    -- Supuestos específicos del año
    growth_rate DECIMAL(5, 2) NOT NULL,
    ebit_margin DECIMAL(5, 2) NOT NULL,
    
    -- Resultados del año (calculados por dcf_engine.py)
    projected_revenue DECIMAL(15, 2) NOT NULL,
    projected_ebit DECIMAL(15, 2) NOT NULL,
    projected_nopat DECIMAL(15, 2) NOT NULL,
    free_cash_flow DECIMAL(15, 2) NOT NULL,
    pv_cash_flow DECIMAL(15, 2) NOT NULL,

    FOREIGN KEY (analysis_id) REFERENCES dcf_analyses(analysis_id) ON DELETE CASCADE,
    UNIQUE KEY unique_analysis_year (analysis_id, year_number)
) ENGINE=InnoDB;





-- -----------------------------------------------------------------------------
-- ESTRUCTURA DE BASE DE DATOS PARA GYLFI SOFTWARE (MERCADOS Y PORTAFOLIOS)
-- -----------------------------------------------------------------------------
USE valuations_db;
-- 1. Tabla de Snapshots / Cotizaciones de Mercado Guardadas
CREATE TABLE IF NOT EXISTS market_quotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    asset_type ENUM('equity', 'commodity', 'index', 'forex', 'crypto') NOT NULL,
    price DECIMAL(15, 4) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    change_percent DECIMAL(8, 4),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_recorded_at (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Tabla de Portafolios de Inversión
CREATE TABLE IF NOT EXISTS portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Tabla de Posiciones / Activos dentro de cada Portafolio
CREATE TABLE IF NOT EXISTS portfolio_assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    asset_type ENUM('equity', 'commodity', 'index', 'bond') NOT NULL,
    quantity DECIMAL(15, 6) NOT NULL,
    purchase_price DECIMAL(15, 4) NOT NULL,
    purchase_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    INDEX idx_portfolio (portfolio_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



USE valuations_db;
CREATE TABLE financial_historicals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    fiscal_year INT NOT NULL,
    
    -- Estado de Resultados (P&L)
    revenue DECIMAL(15, 2) NOT NULL,
    ebit DECIMAL(15, 2) NOT NULL,
    depreciation_amortization DECIMAL(15, 2) NOT NULL,
    effective_tax_rate DECIMAL(5, 4) NOT NULL, -- Ej: 0.3400 para 34%
    
    -- Balance General & Flujo
    net_working_capital DECIMAL(15, 2) NOT NULL,
    capex DECIMAL(15, 2) NOT NULL,
    net_debt DECIMAL(15, 2) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_company_year (company_id, fiscal_year)
);



USE valuations_db;
CREATE TABLE dcf_assumptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    scenario_name VARCHAR(50) DEFAULT 'Base', -- Ej: Base, Optimista, Pesimista
    
    projection_years INT NOT NULL DEFAULT 5,   -- Período explícito (3 a 10 años)
    wacc DECIMAL(5, 4) NOT NULL,               -- Costo de capital (Ej: 0.0850 para 8.5%)
    perpetual_growth_rate DECIMAL(5, 4) NOT NULL, -- Tasa g (Ej: 0.0200 para 2.0%)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);




USE valuations_db;

DROP TABLE IF EXISTS excel_inputs_raw;
DROP TABLE IF EXISTS excel_projections_raw;

CREATE TABLE IF NOT EXISTS excel_inputs_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150),
    scenario_name VARCHAR(100),
    Parametro VARCHAR(255),
    Valor VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS excel_projections_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150),
    scenario_name VARCHAR(100),
    year INT,
    growth_rate DECIMAL(10, 4),
    ebit_margin DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



USE valuations_db;

-- 1. Crear tabla Padre
CREATE TABLE IF NOT EXISTS dcf_valuations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    historical_revenue DECIMAL(18,2) NOT NULL,
    wacc DECIMAL(10,4) NOT NULL,
    terminal_growth_rate DECIMAL(10,4) NOT NULL,
    net_debt DECIMAL(18,2) NOT NULL,
    enterprise_value DECIMAL(18,2) NOT NULL,
    equity_value DECIMAL(18,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Crear tabla Hija (Detalle FCFF)
CREATE TABLE IF NOT EXISTS dcf_projections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    valuation_id INT NOT NULL,
    year_index INT NOT NULL,
    year_label VARCHAR(20) NOT NULL,
    growth_rate DECIMAL(10,4),
    ebit_margin DECIMAL(10,4),
    projected_revenue DECIMAL(18,2) NOT NULL,
    ebit DECIMAL(18,2) NOT NULL,
    nopat DECIMAL(18,2) NOT NULL,
    da DECIMAL(18,2) NOT NULL,
    capex DECIMAL(18,2) NOT NULL,
    nwc_change DECIMAL(18,2) NOT NULL,
    fcf DECIMAL(18,2) NOT NULL,
    pv_fcf DECIMAL(18,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (valuation_id) REFERENCES dcf_valuations(id) ON DELETE CASCADE
);


USE valuations_db;
CREATE TABLE IF NOT EXISTS documentos_cloud (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_db VARCHAR(100) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo TEXT NOT NULL,
    fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;