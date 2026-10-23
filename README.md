# Análisis de pérdidas y transiciones

Primera pieza de un proyecto personal para presentar una candidatura de prácticas de Ingeniería Informática al Real Racing Club de Santander. No está afiliado al club.

El programa importa un partido en formato de eventos StatsBomb y busca pérdidas de balón seguidas de una posesión rival y un remate. Genera un informe HTML que se abre en el navegador, un JSON de resultados y un registro de procedencia con hash del archivo original. No requiere servicios de pago ni paquetes Python externos.

La demo utiliza datos reales de **España–Inglaterra, final de la Eurocopa del 14 de julio de 2024**, identificador `3943043`. No son datos del Racing. La primera versión es un análisis descriptivo basado en reglas; no contiene un modelo de IA ni extrae datos de vídeo.

## Ejecutar

En Windows, haz **doble clic en `iniciar_app.cmd`**. Busca Python 3.10 o superior (incluido el runtime de Codex si está disponible), genera el informe y lo abre en el navegador. Si hay un error, deja la ventana abierta para que puedas leerlo. No cambia la configuración de PowerShell.

La versión actual abre la demo España–Inglaterra de 2024. El análisis del Racing de la temporada actual sigue pendiente de una fuente de acciones detalladas o de un módulo de vídeo validado.

El archivo `ejecutar_demo.ps1` es un script de PowerShell: si al abrirlo ves su código, se ha abierto en un editor. Puedes usar `iniciar_app.cmd` o ejecutar el `.ps1` desde una terminal PowerShell.

También puedes arrancar el programa desde una terminal con Python 3.10 o superior:

```powershell
python -m racing_analysis demo
```

El primer uso descarga un partido y las condiciones de uso del repositorio oficial de StatsBomb. Con los archivos ya descargados:

```powershell
python -m racing_analysis demo --offline
```

Abre `output/informe.html`. El archivo es autónomo y funciona sin conexión. También puedes ejecutar `./ejecutar_demo.ps1`, que genera el informe y lo abre. El script busca Python y, como alternativa, el runtime de esta instalación de Codex.

Para analizar otro archivo de **un solo partido** en el mismo formato:

```powershell
python -m racing_analysis analyze ruta/al/partido.json --window 10 --output output/otro-partido.html
```

No concatenes partidos: los contadores de posesión y los relojes son locales a cada encuentro. La adaptación a otros proveedores necesita un importador que respete su esquema y sus definiciones.

## Qué mide y qué no mide

- Candidatos observables: pase incompleto en juego abierto, mal control, desposesión o regate fallido.
- Se confirma una pérdida solo cuando la siguiente posesión identificada pertenece al rival, empieza en el mismo periodo dentro de un máximo de 5 segundos y no aparece una interrupción antes. Los candidatos de una misma posesión se deduplican. Esto es una definición conservadora y no pretende recuperar todas las pérdidas posibles.
- Una pérdida se marca como peligrosa si el rival remata durante esa posesión, dentro de la ventana elegida y antes de una interrupción o recuperación. No mide goles evitables ni el valor de todos los ataques rivales.
- Las ventanas de 5, 10 y 15 segundos se calculan por separado para comprobar sensibilidad. Los porcentajes usan como denominador las pérdidas detectadas de cada equipo o zona, nunca todas sus acciones.
- Las nueve zonas dividen las coordenadas del proveedor en tercios: x 0–120 e y 0–80. Se usan etiquetas neutrales para evitar confundir banda del equipo con parte superior/inferior de la visualización.
- Cada resultado conserva identificadores y una secuencia de acciones para auditarlo. No hay reproducción de vídeo asociada.

Un partido es una muestra pequeña. No permite concluir un estilo estable, asignar responsabilidades individuales ni demostrar que un cambio táctico mejoraría resultados. Los eventos no proporcionan posiciones continuas de todos los jugadores. La siguiente validación es contrastar manualmente pérdidas incluidas y excluidas en varios partidos y, si existe acceso, con vídeo.

## Datos y atribución

Fuente: [StatsBomb Open Data](https://github.com/hudl/open-data). Consulta su [README](https://github.com/hudl/open-data/blob/master/README.md) y [licencia](https://github.com/hudl/open-data/blob/master/LICENSE.pdf), que se descargan también en `data/raw/`.

El conjunto se ofrece para investigación y análisis. La licencia incluye restricciones de redistribución y explotación comercial, y exige el logo StatsBomb al publicar análisis. La disponibilidad pública no equivale a permiso para usar estos datos como servicio operativo de un club. Antes de publicar el portfolio, incorpora la atribución visual oficial; para una implantación real utiliza datos con permisos adecuados. Los archivos brutos y los informes generados están excluidos de Git.

## Estructura

```text
racing_analysis/analysis.py  Reglas de detección y agregaciones
racing_analysis/report.py    Informe HTML autónomo
racing_analysis/cli.py       Descarga, entrada/salida y procedencia
tests/                      Casos sintéticos de validación de las reglas
data/raw/                   Datos originales locales (no versionados)
output/                     Informe, resultados y procedencia (no versionados)
```

Pruebas:

```powershell
python -m unittest discover -s tests -v
```

## Siguientes hitos

1. Revisar manualmente una muestra de pérdidas incluidas y excluidas; documentar desacuerdos.
2. Añadir varios partidos, contexto de marcador y denominadores de exposición antes de comparar equipos.
3. Escalar el almacenamiento a tablas por partido en Parquet/SQL y medir rendimiento. Este prototipo carga un partido en memoria; no se ha probado con millones de eventos.
4. Entrenar un modelo de riesgo solo con variables disponibles al producirse la pérdida. Separar entrenamiento y evaluación por partidos y fecha; comparar con una referencia simple.
5. Probar vídeo en un fragmento corto: detección de jugadores y balón, seguimiento, calibración del campo, posesión y eventos. Medir cada etapa contra anotaciones manuales antes de generar recomendaciones.

Para vídeo, una retransmisión contiene cortes, repeticiones y jugadores fuera de plano. Una cámara elevada, estable y con plano amplio ayuda a seguir el juego; aun así, obtener eventos fiables requiere validación. Referencia técnica: [SoccerNet Game State Reconstruction](https://github.com/SoccerNet/sn-gamestate).
