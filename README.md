# 🪑 Nesting Topográfico Multi-Lámina — eFe-Design

Aplicación web desarrollada en **Python** y **Streamlit** para la optimización de corte y anidamiento geométrico (*nesting*) de piezas paramétricas curvas para corte láser y fresado CNC, diseñada específicamente para la producción del proyecto **Banco Tronco**.

🌐 **Aplicación en vivo:** [nestingefe.streamlit.app](https://nestingefe.streamlit.app/)  
🏢 **Laboratorio:** [eFe-Design Lab](https://efe-design.web.app/)

---

## 📌 Contexto del Proyecto

En el flujo de diseño paramétrico del **Banco Tronco**, el modelo 3D genera entre 192 y 377 costillas onduladas únicas. Cuando se exportan en formato vectorial plano (.SVG), las geometrías quedan dispersas linealmente a lo largo de más de 12 metros, lo que provocaría un desperdicio masivo de material si se procesan sin empaquetamiento o mediante cajas contenedoras rectangulares convencionales.

Esta herramienta resuelve el problema mediante un algoritmo determinista de **Horizonte Dinámico de Perfil Real (True Profile Skyline)**, logrando el encastre interconectado de crestas y valles (*interlocking*) con holgura controlada.

---

## 🚀 Flujo de Trabajo

1. **Diseño 3D:** Modela y configura el banco paramétrico en el [Configurador Banco Tronco 3D](https://efe-design.web.app/apps/banco-tronco).
2. **Extracción Vectorial:** Exporta el despiece de costillas desde el [Panel de Taller](https://efe-design.web.app/apps/taller) en formato `.svg`.
3. **Optimización con Python:** Carga el archivo `.svg` en esta aplicación web.
4. **Descarga de Planos de Corte:** Obtén el archivo `.svg` final optimizado y separado por capas para fabricación en **LightBurn** o **RDWorks**.

---

## ⚙️ Características Técnicas del Algoritmo

* **Parser SVG Vectorial:** Filtra contornos cerrados de corte exterior (trazo negro) y descarta automáticamente vectores auxiliares o de ensamble.
* **Mapeo y Transformación Solidaria de Rótulos:** Identifica los códigos de ensamble (ej. `C1-P1`) mediante proximidad euclidiana al centroide de cada pieza, manteniéndolos vinculados tras la rotación y traslación.
* **Optimización Angular:** Muestrea la rotación grado a grado (de $1^\circ$ a $180^\circ$) buscando la orientación de mínima altura transversal, evaluando variantes directas e invertidas ($180^\circ$).
* **Horizonte Dinámico (Skyline):** Desciende las piezas sobre la cota acumulada de la mesa considerando un *kerf* de seguridad (separación mínima configurable).
* **Gestión Multi-Lámina:** Sella la lámina actual y abre un nuevo tablero cuando la cota vertical supera el límite configurado ($Y > 800\text{ mm}$).
* **Separación por Capas para Corte Láser Industrial:**
  * **Capa Azul (`#0000FF`):** Grabado/marcado superficial de códigos de ensamble.
  * **Capa Negra (`#000000`):** Corte perimetral de costillas.
  * **Capa Roja (`#FF0000`):** Delimitación y formato de la mesa de trabajo.

---

## 🛠️ Estructuras de Control Computacional Implementadas

El desarrollo de este algoritmo en **Python** ilustra la resolución de problemas lógicos y espaciales mediante estructuras fundamentales:

| Estructura | Función / Ámbito en el Código | Propósito |
| :--- | :--- | :--- |
| `for` | Recorrido del árbol XML / SVG | Iterar sobre los nodos vectoriales y catálogo de costillas. |
| `while` | Búsqueda angular grado a grado | Muestrear de $1^\circ$ en $1^\circ$ hasta $180^\circ$ para hallar la mínima altura. |
| `while` | Barrido horizontal en $X$ | Desplazar la pieza sobre los 1200 mm de la mesa evaluando apoyo. |
| `if` / `elif` | Filtrado geométrico | Discriminar contornos cerrados de corte frente a rótulos de texto. |
| `if` / `else` | Validación de altura en $Y$ | Asentar pieza si $Y \le 800\text{ mm}$; de lo contrario, abrir nueva lámina. |

---

## 📦 Instalación y Ejecución Local

Para ejecutar esta aplicación en tu entorno local:

```bash
# 1. Clonar el repositorio
git clone [https://github.com/lpqlp1/nesting.git](https://github.com/lpqlp1/nesting.git)
cd nesting

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar Streamlit
streamlit run app.pygit add README.md