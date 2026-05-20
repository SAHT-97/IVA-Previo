# 🧾 Cálculo de IVA - App Streamlit

App para calcular el IVA / Impuesto a pagar a partir de los resúmenes de Compras y Ventas del SII (Chile).

## 📦 Instalación

```bash
# 1. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
```

## ▶️ Ejecutar

```bash
streamlit run app.py
```

Se abrirá en el navegador en `http://localhost:8501`.

## 📋 Cómo usarla

1. En la barra lateral, ingresa:
   - **Nombre del contribuyente** (ej: "Com. Ruben Rivas")
   - **PPM (%)** — se aplica sobre el Neto de ventas
   - Marca **Retención de Honorarios** si aplica e ingresa el monto
   - **Remanente mes anterior** si corresponde

2. Sube los dos CSV del SII:
   - **Resumen de Ventas**
   - **Resumen de Compras**

3. Se generará automáticamente el cuadro "DETALLE DE IMPUESTO" con el mismo formato del cliente.

4. Toma una captura de pantalla del recuadro y envíala al cliente.

## 🧮 Lógica de cálculo

- **IVA Ventas** = IVA Facturas + IVA Boletas + IVA CPE − IVA Notas de Crédito
- **IVA Compras** = IVA Facturas − IVA NC + Remanente anterior
- **Impuesto Determinado** = IVA Ventas − IVA Compras
  - Si es negativo → se muestra 0 y el resto pasa a "Remanente próximo mes"
- **PPM** = Neto Ventas × (PPM%)
- **TOTAL A PAGAR** = Impuesto Determinado + PPM + Retención
