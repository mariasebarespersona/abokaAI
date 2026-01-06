# Reporte de Análisis: Estudio Económico - Cristobal Bordiú

## 1. Resumen Ejecutivo
El documento "Estudio Económico-Pv2 Cristobal Bordiú" es un modelo financiero de viabilidad para una operación de inversión inmobiliaria (estrategia *Value Add* o *Fix & Flip*). El proyecto consiste en la adquisición de un activo, su reforma integral y posterior venta, generando ingresos adicionales por alquiler durante el periodo de comercialización.

*   **Activo:** Cristobal Bordiú.
*   **Estrategia:** Compra $\rightarrow$ Reforma $\rightarrow$ Venta (con explotación temporal).
*   **Rentabilidad Bruta (ROE):** **19,97%** (Celda C63).
*   **Beneficio Neto Inversor:** **91.005 €** (Celda D65).
*   **Horizonte Temporal:** 12 meses estimados (Celda C46).

---

## 2. Estructura y Lógica del Modelo (Hoja "ESTUDIO ECONOMICO")

La hoja actúa como un cuadro de mando que agrega inputs de otras pestañas (como 'DATOS GENERALES' y 'RENTABILIDADES') y desglosa el flujo de caja del proyecto en cuatro bloques principales.

### A. Adquisición del Activo (Filas 3-12)
Este bloque calcula el coste "duro" de entrada.

*   **Precio de Compra (C4):** **1.000.000 €**. Es el input principal que detona el resto de cálculos.
*   **Impuestos de Compra (C11):** **20.000 €**.
    *   *Análisis:* Se aplica un **ITP del 2%**. Esto indica una optimización fiscal, asumiendo que el comprador es una empresa o profesional inmobiliario que se acoge a la bonificación por reventa (art. 42 RIS) o renuncia a la exención del IVA. Si no se cumplieran estos requisitos, este coste subiría al 6% (60.000 €) en Madrid.
*   **Gastos de Gestión (C9):** 1% (**10.000 €**).
*   **Notaría y Registro (C8):** **2.250 €**.
*   **Total Coste Adquisición (C12):** **1.033.270 €**.

### B. CAPEX: Reforma y Adecuación (Filas 13-26)
Desglose detallado de la inversión en mejora del activo.

*   **Obra Civil (C15):** 54.600 €.
*   **Materiales y Acabados:** Incluye partidas específicas como Carpintería (12.620 €), Cocina (11.800 €) y Climatización (4.100 €).
*   **Amueblamiento y Menaje (C25):** **15.200 €**. Esta partida es clave para el *Home Staging*, esencial para vender al precio objetivo de 1.35M €.
*   **Total Reforma (C26):** **118.070 €**.
    *   *Ratio:* Supone un ~11,8% sobre el precio de compra. Es una reforma contenida, enfocada en "lavado de cara" y acabados visibles más que en cambios estructurales profundos.

### C. Gastos Financieros y Operativos (Filas 27-49)
Costes de tenencia (*Holding Costs*) y estructura de deuda.

*   **Periodo de Tenencia:** 12 meses.
*   **Gastos Fijos:** Comunidad (3.600 €) e IBI (1.020 €).
*   **Comisión de Venta (C33):** **27.000 €** (2% sobre venta).
    *   *Nota:* Un 2% es una comisión de agencia baja (estándar de mercado 3-5%).
*   **Estructura de Deuda:**
    *   **Hipoteca (D35):** **600.000 €**.
    *   **LTV (Loan to Value):** 60%.
    *   **Intereses (C45):** **22.800 €**. Calculados al **3,8%** fijo el primer año.
*   **Total Gastos Financieros y Varios (C49):** 40.205 €.

### D. Ingresos y Resultados (Filas 51-65)
El "Bottom Line" del negocio.

*   **Precio de Venta (D53):** **1.350.000 €**.
    *   *Plusvalía:* Se proyecta una revalorización del **35%** sobre el precio de compra.
*   **Ingresos por Alquiler (C60):** **12.300 €**.
    *   *Estrategia:* Se asume alquiler temporal/vacacional durante los meses de primavera-verano (Mayo-Septiembre) mientras se comercializa el activo.
*   **Total Ingresos (D60):** **1.362.300 €**.

---

## 3. Análisis de Rentabilidad y Fórmulas Clave

### Beneficio Bruto
*   **Celda D63:** **126.865 €**
*   **Fórmula Implícita:** `Total Ingresos (D60) - Total Gastos (C50)`
*   `1.362.300 € - 1.235.435 € = 126.865 €`

### Rentabilidad sobre Capital (ROE)
*   **Celda C63:** **19,97%**
*   **Origen:** La fórmula es `=+RENTABILIDADES!D11`, lo que indica que el cálculo detallado se realiza en la hoja "RENTABILIDADES".
*   **Desglose del Cálculo en Hoja "RENTABILIDADES":**
    *   El modelo consolida aquí el retorno sobre el *Equity* (Capital propio).
    *   *Capital Invertido (Equity):* **635.435 €**.
        *   Obtenido de: Total Inversión (1.235.435 €) - Hipoteca (600.000 €).
    *   *Beneficio Antes de Impuestos:* **126.865 €**.
    *   *Ratio:* `126.865 / 635.435 = 19,965...` $\rightarrow$ **19,97%**.
    *   Esta métrica confirma que por cada 1 € aportado por el inversor, se generan casi 20 céntimos de beneficio bruto en un año.

### Reparto de Beneficios (Waterfall)
*   **Honorarios de Éxito (ABOKA) (C64):** **35.860 €**.
    *   Representa un ~28% del beneficio bruto. Es un *Success Fee* significativo para el gestor/promotor.
*   **Beneficio Neto Inversor (D65):** **91.005 €**.
*   **Rentabilidad Neta Inversor (C65):** **14,32%**.

---

## 4. Conclusiones y Riesgos Detectados

1.  **Sensibilidad al Precio de Venta:** El margen de beneficio neto (91k) es estrecho (~6,7% sobre el precio de venta). Una desviación del 7% en el precio de venta eliminaría el beneficio del inversor.
2.  **Riesgo Fiscal:** El modelo asume un ITP reducido del 2% (Celda C11). Si no se cumplen los requisitos fiscales y se aplica el 6%, el coste aumentaría en 40.000 €, reduciendo el beneficio neto casi a la mitad.
3.  **Dependencia de la Financiación:** La rentabilidad de dos dígitos depende totalmente del apalancamiento (Hipoteca 600k). Sin financiación, el ROI del proyecto caería al ~10%.
4.  **Ingresos Atípicos:** El modelo cuenta con 12.300 € de alquileres temporales. Si la venta se retrasa o no se logran estos alquileres, la rentabilidad se verá erosionada por los costes financieros mensuales (~1.900 €/mes).
