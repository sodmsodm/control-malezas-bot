import os
import logging
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- CONFIGURACION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- BASE DE CONOCIMIENTO ---
KNOWLEDGE_BASE = """
Eres un asistente técnico especializado en control de malezas en cultivos extensivos de Argentina.
Tu conocimiento está basado EXCLUSIVAMENTE en la información técnica contenida en esta base de datos, proveniente de INTA Pergamino, Lares SRL, Ojos del Salado y otras fuentes especializadas.

REGLA FUNDAMENTAL: Respondés ÚNICAMENTE con información que esté explícitamente contenida en esta base de conocimiento. NO uses conocimiento externo de tu entrenamiento bajo ninguna circunstancia. Si la consulta no está cubierta por la información de esta base, respondé exactamente: "No tengo información suficiente en mi base para responder esto con certeza."

REGLA DE SEGURIDAD CRÍTICA — MOMENTOS DE APLICACIÓN:
Los encabezados de cada sección indican DOS cosas separadas:
1. El estado de LA MALEZA al momento de aplicar (POE maleza = maleza ya nacida / PEE maleza = maleza aún no emergida)
2. El momento respecto AL CULTIVO (PSI = antes de sembrar el cultivo / PEE = cultivo aún no emergido / POE = cultivo ya emergido)
NUNCA confundas el momento de la maleza con el momento del cultivo. Son independientes.

REGLA DE COINCIDENCIA EXACTA: Si el estadio, momento de aplicación, o condición específica mencionada por el usuario NO coincide exactamente con lo que figura en la base, SIEMPRE aclararlo con un ⚠️ antes de responder.

REGLA DE FENOLOGÍA: Para consultas sobre estadios fenológicos, respondé únicamente con las descripciones que figuran en la base. No agregues datos como días después de siembra, temperaturas, duraciones, ni ninguna otra información que no esté explícitamente escrita en la base de conocimiento.

REGLA DE BIOTIPOS: Cuando el usuario pregunta sobre control de malezas en soja, trigo, maíz o cualquier cultivo sin especificar el biotipo o tecnología, SIEMPRE presentar las opciones organizadas por biotipo disponible en la base.

REGLA DE MARCAS COMERCIALES: Cada vez que menciones un principio activo que tenga una marca comercial asociada en esta base, SIEMPRE incluí la marca junto al principio activo en tu respuesta. Formato obligatorio: "Principio activo dosis (Marca)".

Respondés en español, de forma clara, técnica y organizada.

REGLA DE FORMATO — MUY IMPORTANTE:
NUNCA uses tablas Markdown (con | y ---) en tus respuestas. Las tablas no se renderizan bien en Telegram y quedan ilegibles.
En su lugar, usá SIEMPRE este formato de lista con viñetas:

Para listar opciones de herbicidas, usá este formato:
✅ Principio activo dosis (Marca) — observación breve

Para separar momentos de aplicación o secciones, usá encabezados con *negrita*:
*📌 BARBECHO — Sobre maleza nacida:*

Para advertencias usá:
⚠️ Texto de la advertencia

Para doble golpe usá:
🔁 1° Glifosato + Cletodim 24% (0,7-1l) (Select) → 2° DG Paraquat 27,6% (1,5-2,5l) (Gramoxone) ~7 días después

Para situaciones o estrategias escalonadas usá:
*🌱 SITUACIÓN 1 — Raigrás 1-2 hojas, baja densidad:*

Cada opción va en su propia línea. Nunca juntes múltiples opciones en una sola celda o línea separadas por guiones.
Siempre aclarás el momento de aplicación (barbecho, PEE, PSI-PEE, POE) y el biotipo de cultivo cuando es relevante.

=== ACEITES Y COADYUVANTES ===
REGLA DE COADYUVANTES: Siempre que recomendés un herbicida de los grupos indicados abajo, incluí la recomendación de aceite o coadyuvante correspondiente.

ACCasa — GRAMINICIDAS (cletodim/Select, haloxyfop/Galant Max, quizalofop/Assure, fluazifop/Super Onecide, pinoxaden/Axial, propaquizafop/Agil):
→ SIEMPRE incluir aceite vegetal o metilado de soja 0,5-1% v/v. Sin aceite la eficacia cae significativamente.

PPO — CONTACTO (carfentrazone/Shark, piraflufen/Stagger, epirefenacil/Empera, flumioxazin/Sumisoya, trifludimoxazin+saflufenacil/Voraxor):
→ SIEMPRE incluir aceite metilado de soja o mineral 0,5-1% v/v.
⚠️ EXCEPCIÓN CRÍTICA: Saflufenacil (Heat) en POE de trigo estado de hojas (Z1.2-Z1.3) — SIN aceite ni coadyuvante.

SAFLUFENACIL (Heat) — según contexto:
→ En barbecho (POE maleza): con aceite metilado de soja 0,5% v/v
→ En trigo POE estado de hojas (Z1.2-Z1.3): SIN aceite
→ En maíz POE: con aceite según marbete BASF

GLUFOSINATO DE AMONIO:
→ SIEMPRE incluir surfactante no iónico 0,1-0,5% v/v o aceite metilado de soja. Agregar Sulfato de Amonio 1,5-2 l/ha.

HPPD — MAÍZ POE (mesotrione/Callisto, topramezone/Convey, tembotrione/Laudis, tolpyralate/Brucia):
→ Incluir aceite mineral o metilado de soja según marbete.

ALS / SULFONILUREAS (metsulfurón/Errasin WP/Ally, imazetapir/Pivot, clorimurón/Classic, diclosulam/Spider, halosulfurón/Sempra, etc.):
→ Surfactante no iónico 0,1-0,2% v/v (200cc/100L). NO aceite mineral.

HORMONALES (2,4D, MCPA, dicamba, fluroxipir/Starane, picloram/Tordón):
→ En general no es obligatorio. En condiciones adversas agregar surfactante no iónico o aceite metilado de soja.

GLIFOSATO SOLO:
→ NO usar aceite vegetal. Usar Sulfato de Amonio 1-2% v/v para mejorar absorción.

TRIAZINAS / RESIDUALES DE SUELO (atrazina, metribuzin, terbutilazina, sulfentrazone, pyroxasulfone, etc.):
→ No requieren coadyuvante foliar. Son residuales de suelo, se activan con humedad.

REGLA CRÍTICA — MEZCLAS CON GLIFOSATO: El aceite se recomienda por el herbicida principal de la mezcla. La presencia de glifosato en la mezcla NO cancela la necesidad de aceite.

=== RESIDUALIDAD DE HERBICIDAS ===
Fuente: Dto. Técnico DOW AgroSciences Argentina S.A. y otros.
Valores orientativos. Intervalo mínimo en días desde la aplicación hasta la siembra del cultivo siguiente.
s/d = sin dato disponible.

Herbicida: Spider | P.activo: Diclosulam 35g | Trigo:200 Maíz:325 Sorgo:355 Soja:0 Girasol:540
Herbicida: Starane Xtra | P.activo: Fluroxipir 210-450 | Trigo:0 Maíz:0 Sorgo:0 Soja:1 Girasol:1 Alfalfa:1 Tréboles:1 Colza:1
Herbicida: 2,4D | P.activo: 2,4D 300-500 | Trigo:3-5 Maíz:3-5 Sorgo:3-5 Soja:7-15 Girasol:7-15
Herbicida: Banvel | P.activo: Dicamba 120-150 | Trigo:0 Maíz:0 Sorgo:0 Soja:15-20 Girasol:15-20
Herbicida: Lontrel | P.activo: Clopyralid 150 | Trigo:0 Maíz:0 Sorgo:0 Soja:20 Girasol:45 Alfalfa:45 Tréboles:45 Colza:0
Herbicida: Tordon 24K | P.activo: Picloram 80-100 | Trigo:0 Maíz:0 Sorgo:0 Soja:45 Girasol:80 Alfalfa:80 Tréboles:80 Colza:15-20
Herbicida: Koltar | P.activo: Oxifluorfén 300 | Trigo:10 Maíz:10 Sorgo:10 Soja:80 Girasol:0
Herbicida: Brodal | P.activo: Diflufenicán 250 | Trigo:15 Maíz:20 Soja:20 Girasol:0
Herbicida: Ally/Metsulfurón | P.activo: Metsulfurón 8-10 | Trigo:0 Maíz:60 Soja:90 Girasol:120 Alfalfa:90 Tréboles:90
Herbicida: Classic | P.activo: Clorimurón 30-40 | Trigo:40 Maíz:40 Soja:0 Girasol:120 Alfalfa:120 Tréboles:120 Colza:40
Herbicida: Gesaprim/Atrazina | P.activo: Atrazina 90% 1,5 kg/ha | Trigo:120 Maíz:0 Sorgo:0 Soja:60 Girasol:90 Tréboles:90
Herbicida: Authority/Capaz | P.activo: Sulfentrazone | Trigo:180 Maíz:180 Sorgo:180 Soja:0 Girasol:0
Herbicida: Flex | P.activo: Fomesafén | Trigo:180 Maíz:180 Sorgo:270 Soja:0 Girasol:180 Alfalfa:180 Tréboles:180 Colza:270
Herbicida: Select | P.activo: Cletodim 800-(500) | Trigo:15(?) Maíz:15(?) Sorgo:15(?) Soja:0 Girasol:0 Alfalfa:0 Tréboles:0 Colza:0
Herbicida: Shark | P.activo: Carfentrazone 75 | Trigo:0 Maíz:0 Sorgo:0 Soja:0 Girasol:0 Alfalfa:0 Tréboles:0 Colza:0
Herbicida: Sempra | P.activo: Halosulfurón 100-150g | Trigo:s/d Maíz:0 Sorgo:s/d Soja:0 Girasol:s/d Alfalfa:s/d Tréboles:s/d Colza:s/d
Herbicida: Pivot | P.activo: Imazapic 240g/L 1L/ha | Trigo:s/d Maíz:0 CL Sorgo:s/d Soja:90 Girasol:s/d Alfalfa:0 Tréboles:s/d Colza:s/d

NOTAS IMPORTANTES:
- Spider (diclosulam): residualidad en girasol luego de un año en suelos con 2% MO. Sin efecto en girasoles CL.
- Cletodim: valores con "?" indican incertidumbre. Aplicar solo con buena MO, sin lluvias y dosis ≤600 g e.a./ha.
- Tordon/Picloram: residualidad muy prolongada en suelos con pH alto o bajo contenido de MO.
- Residualidad de las AUXINAS en orden de mayor a menor: Picloram (Tordón) > Clopyralid (Lontrel) > Dicamba (Banvel) > 2,4D > Fluroxipir (Starane)
- Pivot (imazapic): carencia 90 días en soja. En Maíz CL y alfalfa: uso posicionado sin restricción práctica. Precaución en rotación con cultivos sensibles a imidazolinonas.
- Sempra (halosulfurón): período de carencia exento por uso posicionado en soja y maíz. Carencia tomate: 51 días.

=== FENOLOGÍA DE CULTIVOS ===

--- FENOLOGÍA TRIGO Y CEBADA — Escala Zadoks ---
Z10: Primera hoja a través del coleoptile
Z11: Primera hoja expandida — 1 hoja
Z12: Dos hojas expandidas
Z13: Tres hojas expandidas
Z14: Cuatro hojas expandidas
Z21: Primer macollo
Z22: Dos macollos
Z31: Primer nudo detectable
Z32: Segundo nudo detectable
Z37: Punta de hoja bandera visible
Z39: Hoja bandera expandida
Z41: Vaina de hoja bandera comenzando a ensancharse
Z49: Primeras aristas visibles
Z51: Primeras espiguillas visibles
Z55: 1/2 espiga emergida
Z59: Emergencia completa
Z65: 50% antesis
Z71: Grano acuoso
Z85: Grano pastoso suave
Z92: Grano maduro para cosecha
Una hoja está expandida cuando se observa la lígula en la base de la lámina.
El primer macollo aparece generalmente junto con la cuarta hoja.
CEBADA: usa la misma escala Zadoks. Macollaje más corto en variedades de 2 carreras.

--- FENOLOGÍA MAÍZ — Escala Ritchie & Hanway ---
VE: Emergencia
V1: Collar de 1ª hoja — hoja inferior completamente desplegada, collar y lígula visible
V2-V10: Collar de la hoja correspondiente completamente desplegado
VT: Antesis — aparición de la panoja con liberación de polen
R1: Silking — emergencia de los estigmas
R2: Ampolla — granos de color blanco asemejándose a una ampolla
R3: Grano lechoso — granos amarillos, interior líquido blanco lechoso
R4: Grano pastoso — humedad ~70%
R5: Grano dentado — inicio de secado, humedad ~55%
R5.5: 1/2 línea de leche — humedad ~40-45%
R6: Madurez fisiológica — capa negra formada, humedad del grano 30-35%

--- FENOLOGÍA SORGO — Escala Vanderlip & Reeves ---
Estado 0: Emergencia
Estado 1: Lígula de la 3ª hoja visible
Estado 2: Lígula de la 5ª hoja visible
Estado 3: Diferenciación de meristemas
Estado 4: Inicio de panoja visible
Estado 5: Floración (antesis)
Estado 6: Grano lechoso
Estado 7: Grano pastoso
Estado 8: Madurez fisiológica — capa negra formada
Estado 9: Madurez de cosecha

--- FENOLOGÍA SOJA — Escala Fehr & Caviness ---
VE: Planta emergida — cotiledones por encima de la superficie
VC: Estado cotiledonar — primer par de hojas unifoliadas separadas y visibles
V1: Primer nudo verdadero desarrollado
V2: Segunda hoja trifoliada totalmente desarrollada
Vn: n-ésima hoja trifoliada totalmente desarrollada
Una hoja está totalmente desarrollada cuando la siguiente ya separó los bordes de sus folíolos.
R1: Inicio floración — una flor abierta en cualquier nudo
R2: Plena floración — una flor abierta en los dos nudos superiores
R3: Inicio fructificación — una vaina de al menos 0,5 cm
R4: Plena fructificación — una vaina de al menos 2 cm
R5: Inicio llenado de semilla — semilla de al menos 3 mm de diámetro
R6: Pleno llenado — semilla que ocupó toda su cavidad
R7: Inicio madurez — UNA vaina normal llega a color marrón o gris
R8: Plena madurez — 95% de vainas con color marrón o gris
Luego de R7 un desecante NO incide en el rendimiento.

--- FENOLOGÍA GIRASOL — Escala Schneiter & Miller ---
VE: Emergencia — hipocótilo y cotiledones emergidos
Vn: n hojas verdaderas (más de 4 cm de largo)
R1: Inflorescencia rodeada de brácteas inmaduras visible (parece estrella desde arriba)
R2: Entrenudo debajo de la inflorescencia se elonga 0,5 a 2 cm
R4: Inflorescencia comienza a abrirse
R5: Antesis de flores tubuladas
R5.1: 10% del capítulo en antesis
R5.5: 50% del capítulo en antesis
R6: Antesis completa
R7: Receptáculo comienza a cambiar de color (amarillo claro)
R8: Receptáculo completamente amarillo, brácteas aún verdes
R9: Brácteas cambian a color marrón — madurez fisiológica

--- FENOLOGÍA COLZA/CANOLA — Escala BBCH ---
BBCH 10: Cotiledones emergidos
BBCH 11: Primera hoja verdadera
BBCH 12: Segunda hoja verdadera
BBCH 15-19: Estado de roseta (5 a 9+ hojas)
Ventana óptima herbicidas POE: BBCH 12-15 (roseta temprana)
BBCH 30: Inicio elongación del tallo
BBCH 60: Primeras flores abiertas
BBCH 65: Plena floración
BBCH 89: Madurez fisiológica
BBCH 99: Madurez cosecha

--- FENOLOGÍA ARVEJA — Escala BBCH ---
BBCH 09: Emergencia
BBCH 11: Primera hoja verdadera expandida (1 par de folíolos)
BBCH 12: Segunda hoja verdadera
BBCH 13: Tercera hoja verdadera
BBCH 14: Cuarta hoja verdadera
BBCH 15: Quinta hoja verdadera — inicio de zarcillos
Ventana POE herbicidas: BBCH 11 a BBCH 14 (antes de zarcillos)
BBCH 60: Primeras flores abiertas
BBCH 89: Madurez fisiológica
BBCH 92: Madurez cosecha

--- FENOLOGÍA CAMELINA — Escala BBCH ---
BBCH 10: Cotiledones emergidos
BBCH 13-15: Estado de roseta (3 a 5 hojas)
BBCH 60: Primeras flores abiertas
BBCH 89: Madurez fisiológica
Opciones herbicidas muy limitadas — ver sección Camelina en base de conocimiento.

=== CONSIDERACIONES GENERALES DE MANEJO ===

--- GIRASOL: ESTRATEGIA Y MALEZAS PROBLEMA ---
Fuente: REM Aapresid / Jorgelina Montoya INTA Anguil. Campaña 2025.

BIOLOGÍA Y VENTANA CRÍTICA:
- Baja densidad (5 pl/m²) + crecimiento inicial lento → el cultivo tarda ~5 semanas en cerrar canopeo
- Los primeros 30-35 días desde emergencia son la ventana crítica de competencia de malezas
- Después del cierre de canopeo el cultivo gana ventaja por sombreo

MALEZAS PROBLEMA CLAVE EN GIRASOL (2025):
- Rama negra (Conyza): biotipos con resistencia múltiple → control anticipado obligatorio
- Crucíferas: biotipos resistentes a ALS, glifosato, 2,4D y RECIENTEMENTE A FLUROCLORIDONA
- Morenita: resistencia a ALS y glifosato confirmada en oeste de Buenos Aires
- Yuyo colorado: biotipos resistentes a glifosato, 2,4D, ALS, PREOCUPACION CRECIENTE por resistencia a PPO
- Gramíneas estivales: muchas con resistencia a glifosato, ALS y graminicidas
- Raigrás: avanzando del sur al centro del país

CARRY-OVER — RIESGO FITOTOXICIDAD EN CULTIVO ANTECESOR:
El girasol es MUY sensible a residuos de herbicidas de cultivos anteriores. Verificar siempre:
- Fomesafen (Flex) en soja antecesora + <300mm acumulados antes de siembra → RIESGO en girasol
- Diclosulam (Spider) en soja antecesora → RESTRINGE directamente la posibilidad de sembrar girasol
- Topramezone (Convey) en maíz + campaña seca + lote de baja productividad → daños residuales posibles
- Sulfonilureas en barbecho o cultivo invernal + ambiente seco → riesgo de carry-over para girasol
- HERRAMIENTA: bioensayo con muestras de suelo en macetas

ESTRATEGIA POR MOMENTO:
- BARBECHO: clave para malezas otoño-invernales. Hormonales (2,4D, dicamba, fluroxipir, halauxifén), PPO (piraflufen, carfentrazone, flumioxazin).
- PEE: momento más importante. Dosis ajustar por MO, arena, pH y humedad de suelo.
- POE: opciones muy limitadas. La clave NO es el rescate en POE sino llegar limpio desde barbecho+PEE.


--- BRASICÁCEAS / CRUCÍFERAS: BIOLOGÍA, RESISTENCIAS Y ESTRATEGIA TRANSVERSAL ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Junio 2024.

IDENTIFICACIÓN:
- Brassica rapa Nabo/nabolza: flor AMARILLA, silicua dehiscente, hojas amplexicaules.
- Raphanus sativus Nabón: flor VIOLÁCEA/ROSADA/BLANCA, silicua INDEHISCENTE y corchosa, hojas pecioladas.
- Hirschfeldia incana Nabillo/mostacilla: flor AMARILLO PÁLIDO, silicua adpresa al raquis.
- Rapistrum rugosum Mostacilla: fruto SILÍCULA indehiscente globosa.

FLUJOS DE EMERGENCIA:
- Brassica rapa: todo el año, picos en OTOÑO y primavera.
- Raphanus sativus: concentrado en OTOÑO y primavera.
- Rapistrum rugosum: principalmente OTOÑO.

RESISTENCIAS CONFIRMADAS EN ARGENTINA (REM Aapresid 2024):
- Hirschfeldia incana: ALS / ALS+2,4D / Glifosato+2,4D
- Brassica napus (colza feral): Glifosato (transgén GT73)
- Brassica rapa: ALS+Glifosato / ALS+Glifosato+2,4D (triple)
- Rapistrum rugosum: ALS (desde 2018 Entre Ríos, expandiéndose)
- Raphanus sativus: ALS (mutación W574L)

ESTRATEGIA QUÍMICA EN BARBECHO:
ROSETA CHICA menor a 10 cm — Base: Glifosato + Hormonal (2,4D o MCPA) + acompañante:
- PPO: carfentrazone 40% (Shark), piraflufen 2,5% (Stagger), saflufenacil 70% (Heat), flumioxazin 48% (Sumisoya)
- Fotosistema II: atrazina 90%, metribuzin 48% (Sencorex), amicarbazone 70% (Dinamic), terbutilazina 75% (Terbine)
- HPPD/PDS: biciclopirona 20%, mesotrione 48% (Callisto), diflufenicán 50% (Brodal)

ROSETA GRANDE mayor a 10 cm — Doble Golpe:
- 1 Aplicación sistémica: Glifosato + 2,4D o MCPA + PPO/Triazina/HPPD
- 2 Aplicación desecante: Paraquat 27,6% (Gramoxone) / Diquat 40% (Reglone) / Glufosinato 28%

REGLA CRÍTICA POR TIPO DE RESISTENCIA:
- Con resistencia a ALS: NO usar sulfonilureas ni imidazolinonas. Cambiar a PPO/Triazinas/HPPD.
- Con resistencia a glifosato: agregar PPO quemante (Heat, Shark) a la mezcla base.
- Con TRIPLE resistencia: Glifosato+PPO/Triazina en 1° app + desecante DG.


--- COMMELINA ERECTA: BIOLOGÍA Y ESTRATEGIA DE CONTROL ---
Fuente: Panigo E., Cortés E., Vernier F. — REM Aapresid. Mayo 2025.

NOMBRE VULGAR: Flor de Santa Lucía
TIPO: Monocotiledónea herbácea PERENNE (familia Commelináceas)

CARACTERÍSTICAS BIOLÓGICAS CLAVE:
- Ciclo PERENNE: rebrote de rizomas en septiembre, plántulas de semilla desde octubre.
- Rizomas: fragmentos cortos engrosados en base de tallos. La tolerancia al glifosato SOLO se observa en plantas con rizomas desarrollados (>5 hojas).
- Banco de yemas latentes: ~50% de nudos del tallo conservan yemas vivas incluso tras aplicación de glifosato.
- Dos tipos de semillas: alargadas (baja dormición) y ovoides (alta dormición). Producción: ~750 semillas/planta/temporada.
- Ceras epicuticulares: plantas adultas tienen mayor cantidad de ceras → menor absorción foliar de herbicidas.

TOLERANCIA AL GLIFOSATO:
- Plantas <5 hojas de semilla: buen manejo posible con herbicidas
- Plantas >5 hojas o de rebrote de rizoma: TOLERANTES — glifosato solo alcanza <30% de control

DOS ÉPOCAS CLAVE DE INTERVENCIÓN QUÍMICA:

>> OTOÑO — POST-COSECHA de cultivos estivales:
- Base: Glifosato + 2,4D
- Opción para rizomas: Imazapir 200 cc/ha (formulado al 48%) — aplicar ANTES de heladas.

>> PRIMAVERA — 2-3 momentos escalonados desde fines de septiembre:
OBJETIVO: intervenir con plantas ≤10-15 cm de diámetro.
Base obligatoria: Glifosato + 2,4D
Priorizar acompañante con efecto RESIDUAL.

Acompañantes según eficacia (REM Aapresid 2025):
HPPD — promedio 72%: Biciclopirona 20% 1000 cc/ha MEJOR / Mesotrione 48% / Tembotrione 42%
ALS — promedio 64%: Diclosulam 84% 30-40 g/ha MEJOR / Imazetapir 10% / Nicosulfuron
PPO — promedio 63%: Flumioxazin 48% 150 cc/ha MEJOR / Saflufenacil 70% / Carfentrazone 40%
TRIAZINAS — promedio 59%: Metribuzin 48% 0,8-1 l/ha / Amicarbazone 70% / Atrazina 90%

DOBLE GOLPE (DG) — mayor eficacia:
- 1° aplicación sistémica + 2° aplicación desecante con intervalo acotado.
- 2° aplicación: Paraquat 27,6% (Gramoxone) o Glufosinato de amonio 28% 2500-3000 cc/ha

ESTRATEGIA POR BIOTIPO DE CULTIVO:
SOJA RR: glifosato solo <30% de control. Control pre-siembra obligatorio.
SOJA ENLIST: POE — Glufosinato + Glifosato + 2,4D → >80% de control.
MAÍZ ENLIST: muy buenos niveles de control en POE.
MAÍZ SIN ENLIST: HPPD + Triazina como aplicación secuencial POE.


--- TRÉBOL BLANCO (Trifolium repens): ESTRATEGIA DE CONTROL EN BARBECHO ---
Fuente: Corteva Agriscience, Manual Barbecho Quimico / Ensayos EEA INTA Oliveros / Marbete Starane Xtra SENASA No.35.712.

BIOLOGÍA: Perenne por stolones — el control foliar no elimina la planta si no se transloca a stolones.
Momento óptimo: follaje joven, receptivo, en activo crecimiento (NO en estrés hídrico ni frío intenso).

OPCIÓN PRINCIPAL:
- Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha
  Carencia: soja 3 DAS, girasol/algodon 10 DAS, maiz/trigo sin restriccion.

OPCIÓN CON PPO:
- Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha + Saflufenacil 70% (Heat) 25-35g/ha

OPCIÓN MARBETE:
- Glifosato 48% (3 l/ha) + Fluroxipir 33% (Starane Xtra) 360 cc/ha


--- CYPERUS ROTUNDUS (CEBOLLÍN): BIOLOGÍA Y ESTRATEGIA TRANSVERSAL ---
Fuente: Uso interno / Marbete Summit-Agro SEMPRA (halosulfurón metil 75%) SENASA Nº35.981 / Marbete BASF Pivot (imazapic 240g/L) SENASA Nº33.606.

BIOLOGÍA:
- Maleza ESTIVAL PERENNE — rebrota de tubérculos en primavera cuando las condiciones son favorables.
- La presencia de un cultivo invernal como trigo puede RETRASAR la emergencia pero no la bloquea al 100%.
- Durante el ciclo del cultivo invernal no hay opciones de control químico efectivas.
- Dispersión: principalmente por tubérculos arrastrados por maquinaria o agua.

SENSIBILIDAD A HERBICIDAS:
- Glifosato: sensible a dosis altas (≥2000 g.e.a./ha). Requiere cebollin en activo crecimiento, idealmente 6-8 hojas.
- Halosulfurón metil (Sempra): muy eficaz. Aplicar con cebollin a ~15 cm de altura.
- Imazapic (Pivot): control PARCIAL, no total. Tiene acción residual que limita rebrotes posteriores.
- Imazetapir 10%: buenos resultados en mezcla con glifosato. Aporta residualidad.
- Clorimurón (Classic): buenos resultados en mezcla con glifosato.
CONTROL NUNCA ES 100% TOTAL — requiere estrategia de largo plazo para agotamiento de tubérculos.

MEZCLAS CON BUENOS RESULTADOS (uso antes de siembra):
- Glifosato 3 L/ha + Clorimurón 25% (60-80 g/ha) (Classic) — control de cebollin nacido
- Glifosato 3,5 L/ha + Imazetapir 10% (800 cc/ha) + humectante — control + residualidad
  Con imazetapir: NO sembrar alfalfa pura en rotación (residualidad en suelo).

CONDICIONES PARA MEJOR RESULTADO:
- Cebollin en activo crecimiento — no aplicar sobre plantas en estrés o dormición.
- Temperaturas cálidas favorecen absorción y translocación sistémica.
- Aplicar siempre con coadyuvante (surfactante no iónico 0,1-0,2% v/v).

=== SOJA ===

--- SOJA: MALEZA GENERAL (No GMO) ---

BARBECHO INTERMEDIO (45-60 DAS):
- Flumioxazin 48% (150cc) (Sumisoya)
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) hasta 15 DAS
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (1kg) (Terbine/Gesatop) hasta 45 DAS
- Metribuzin 48% (1l) (Sencorex)
- Terbutilazina 50%/Flumioxazin 3,8% (1,25l) (Terbyne Max Sipcam) hasta 30 DAS
- Sulfometurón 15% + Clorimurón 20% (0,1kg) (Ligate) SOJAS STS

PEE / PSI-PEE:
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Sulfentrazone 50% (0,5l) (Authority/Capaz) + Piroxasulfone 48% (0,355l)
- Sulfentrazone 50% (0,5l) (Authority/Capaz) + Imazetapir 10% (0,8-1l) (Pivot)
- Sulfentrazone 50% (0,5l) (Authority/Capaz) + Diclosulam 84% (0,03kg) (Spider)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) + Metribuzin 48% (0,8-1l) (Sencorex)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) + Clomazone 36% (1,75-2l) (Command)
- Flumioxazin 15%/Piroxasulfone 34,5% (0,5l) (Fierce FMC) 7 DAS
- Flumioxazin 4,2%/S-metolacloro 84% (1,75l) (Apresa ADAMA) 7 DAS
- Flumioxazin 5%/S-metolacloro 57,6%/Imazetapir 5% (1,5l) (Zethamaxx Sumitomo) 7 DAS
- Flumioxazin 14,5%/Diclosulam 6,5%/Imazetapir 20% (0,5l) (Predecessor DVA) 7 DAS
- Flumioxazin 28,8%/Diclosulam 8,4% (0,25l) + S-metolacloro 96% (1,1-1,3l) (Dual Gold) 7 DAS
- Flumioxazin 4,2%/Acetoclor 90% (1,5l) (Harness) 7 DAS
- Metribuzin 14,9%/S-metolacloro 62,8% (2,5l) (Boundary Syngenta)
- Fomesafén 50% (0,4-0,5l) + Metribuzin 48% (0,8-1l) (Sencorex) + Acetoclor 90% (1,5l) (Harness)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)

POST-EMERGENCIA CULTIVO (V4-V6):
- Fomesafén 25% (1-1,5l) (Flex)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Cletodim 24% (0,7-1l) (Select); Cletodim 36% (0,5-0,7 l/ha) (Select 36)
- Piroxasulfone 85% (0,16-0,2 kg/ha) (Yamato) hasta V4 o V8
- Fomesafén 25% (1-1,5l) (Flex) + Benazolín 50% (0,8l) (Dasen)
- Fomesafén 25% (1-1,5l) (Flex) + 2,4DB 97% e.a. (0,04l)
- Fomesafén 25% (1-1,5l) (Flex) + Clorimurón 25% (0,03kg) (Classic)
- Clorimurón 25% (0,04-0,05kg) (Classic)
- Cloransulam 84% (0,04-0,05kg) (Pacto)
- Imazetapir 10% (0,5-0,8l) (Pivot)
- 2,4DB 97% e.a. (0,04l) + Bentazón 60% (0,8-1l) (Basagran)
- Benazolín 50% (0,6l) (Dasen) + Clorimurón 25% (0,03g) (Classic)
- Benazolín 50% (0,6l) (Dasen) + Diclosulam 84% (0,015g) (Spider)

--- SOJA: CEBOLLÍN (Cyperus rotundus) ---
Fuente: Uso interno / Marbete Summit-Agro SEMPRA SENASA Nº35.981 / Marbete BASF Pivot SENASA Nº33.606.
Ver también sección CONSIDERACIONES GENERALES — CYPERUS ROTUNDUS para biología y estrategia completa.
Control nunca es 100% total — requiere estrategia de largo plazo.

PRE-SIEMBRA — Aplicar sobre cebollin nacido (POE maleza) / Cultivo aún no sembrado:
Aplicar con cebollin a ~15 cm de altura (estado activo de crecimiento). Mínimo 10 días antes de siembra.
- Halosulfurón metil 75% (100-150 g/ha) (Sempra) — ALS, muy eficaz.
- Halosulfurón metil 75% (30-50 g/ha) (Sempra) + Glifosato 48% (2,5 L/ha) — dosis reducida + glifosato
- Glifosato 48% (3 L/ha) + Clorimurón 25% (60-80 g/ha) (Classic) — buenos resultados de campo
- Glifosato 48% (3,5 L/ha) + Imazetapir 10% (800 cc/ha) + humectante — control + residualidad
  ATENCION con imazetapir: NO sembrar alfalfa pura en rotación
- Glifosato (≥2000 g.e.a./ha) solo — solo con cebollin de 6-8 hojas en activo crecimiento. Control parcial.

POE CULTIVO — Aplicar sobre soja emergida:
- Imazapic 240 g/L (1 L/ha) (Pivot) — desde emergencia del cebollin hasta 4ª hoja verdadera. Control parcial con acción residual.
  ATENCION: Carencia Pivot 90 días desde aplicación a cosecha de soja.
  ATENCION: Verificar tolerancia de la variedad de soja antes de aplicar.

COADYUVANTE: Surfactante no iónico 0,1-0,2% v/v en todas las aplicaciones de ALS (Sempra, Pivot, Classic). NO aceite mineral.

--- SOJA: COMMELINA ERECTA ---
Ver también sección CONSIDERACIONES GENERALES DE MANEJO — COMMELINA ERECTA para biología y estrategia completa.

ANTES DE SIEMBRA DEL CULTIVO — POE maleza / PSI cultivo:
CON GLIFOSATO:
- Glifosato 1260 g.e.a. + 2,4D (1-1,5l éster ethyl hexyl) + Saflufenacil 70% (40g) (Heat)
- Glifosato + 2,4D + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D + Flumioxazin 48% (150cc) (Sumisoya)
- Glifosato + 2,4D + (Iodosulfurón/Thiencarbazone) (30-45g) 30-45 DAS
- Glifosato + 2,4D + Imazetapir 10% (0,8-1l) (Pivot)
- Glifosato + 2,4D + (Trifludimoxazin/Saflufenacil) (0,1-0,2l) (Voraxor)
- Glifosato + 2,4D + Metribuzin 48% (0,8-1l) (Sencorex)
- Glifosato + 2,4D + Amicarbazone 70% (0,4g) (Dinamic) — hasta 45 DAS

CON GLUFOSINATO:
- Glufosinato de amonio 28% (2,5l) + 2,4D
- Glufosinato de amonio 28% + 2,4D + Metribuzin 48% (0,8-1l) (Sencorex)
- Glufosinato de amonio 28% + 2,4D + Amicarbazone 70% (0,4g) (Dinamic) — hasta 45 DAS
- Glufosinato de amonio 28% + 2,4D + Saflufenacil 70% (Heat)
- Glufosinato de amonio 28% + 2,4D + Carfentrazone 40% (Shark)
- Glufosinato de amonio 28% + 2,4D + Epirefenacil 5,5% (Empera)
- Glufosinato de amonio 28% + 2,4D + Flumioxazin 48% (Sumisoya)
- Glufosinato de amonio 28% + 2,4D + (Trifludimoxazin/Saflufenacil) (Voraxor)

DOBLE GOLPE — 1° aplicación sistémica + 2° desecante ~7 días después:
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (Gramoxone)
- 1° Glifosato + 2,4D // 2° DG Glufosinato de amonio 28%
- 1° Glifosato + 2,4D // 2° DG (Paraquat 27,6% + Atrazina 90%) — hasta 40 DAS
- 1° Glifosato + 2,4D // 2° DG (Glufosinato 28% 2-3l + Saflufenacil 70% 35-40g) (Heat)
- 1° Glifosato + 2,4D // 2° DG (Glufosinato 28% 2-3l + Carfentrazone 40% 70-80cc) (Shark)

SOJAS ENLIST:
- Glifosato 1260 g.e.a. + Glufosinato de amonio 28% + 2,4D 30% e.a. (1,5-2l) — hasta V4-V6
- Glufosinato de amonio 28% (2-2,5l) + 2,4D 30% e.a. (1,5-2l) — hasta V4-V6

--- SOJA: CRUCIFERAS ---

ANTES DE SIEMBRA DEL CULTIVO — POE maleza / PSI cultivo:
- Glifosato + 2,4D (carencia v.s.f.)
- Glifosato + MCPA 28% (1,5-2,5l)
- Glifosato + 2,4D + Dicamba — 25 DAS
- Glifosato + 2,4D o MCPA + Saflufenacil 70% (35-40g) (Heat)
- Glifosato + 2,4D o MCPA + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D o MCPA + Piraflufén 2,5% (200cc) (Stagger)
- Glifosato + 2,4D o MCPA + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D o MCPA + (Trifludimoxazin/Saflufenacil) (0,1-0,15l) (Voraxor)
- Glufosinato de amonio 28% (1-2,5l) + 2,4D
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)

MALEZA PEE BARBECHO LARGO — PEE maleza:
- Atrazina 90% (1kg) hasta 30 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Flurocloridona 25% (1,5l) (Rainbow) hasta 45 DAS
- Diflufenicán 50% (0,3l) (Brodal)
- Flumioxazin 48% (0,1-0,15l) (Sumisoya)

PEE / PSI-PEE:
- Metribuzin 48% (0,8-1kg) (Sencorex)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz)
- Flumioxazin 48% (0,1-0,15l) (Sumisoya) 7 DAS
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) 15 DAS
- Trifludimoxazin 12,5%/Saflufenacil 25% (Voraxor) (0,1-0,2l) 7 DAS

POST-EMERGENCIA CULTIVO — Soja RR o No GMO:
CONDICIÓN CLAVE: Maleza en ROSETA PEQUEÑA (5-8 cm).
- Fomesafén 25% (1-1,5l) (Flex)
- Acifluorfén 24% (1-1,5l) (Blazer)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Bentazón 60% (1,5l) (Basagran)
- Imazetapir 10% (0,5-0,8l) (Pivot) + Clorimurón 25% (0,04kg) (Classic)
ADVERTENCIA: En biotipos con resistencia a ALS no usar sulfonilureas ni imidazolinonas.

SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) + 2,4D 30% e.a. (1,5-2l) hasta V4-V6

--- SOJA: PARIETARIA ---

BARBECHO LARGO:
- Atrazina 90% (1-1,5kg) hasta 60 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (0,8-1kg) (Terbine/Gesatop) hasta 45 DAS
- Metsulfurón 60% (6-8g) hasta 60 DAS
- Flumioxazin 48% (0,1-0,15l) (Sumisoya)

PEE / PSI-PEE:
- Atrazina 90% (0,5kg) hasta 30 DAS
- Metribuzin 48% (0,8-1l) (Sencorex)
- Prometrina 48% (1,5-2l) (Gesagard)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) + Metribuzin 48% (0,8-1l) (Sencorex)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) 7 DAS
- Glifosato 1260 g.e.a. + Epirefenacil 5,5% (600cc) (Empera)

POST-EMERGENCIA CULTIVO: Sin opciones efectivas.

--- SOJA: AMARANTHUS SPP. (Yuyo Colorado) ---

ANTES DE SIEMBRA DEL CULTIVO — POE maleza / PSI cultivo:
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Epirefenacil 5,5% (600cc) (Empera)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor)
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 2,4D + Saflufenacil 70% (40g) (Heat)
- 2,4D + Carfentrazone 40% (70-80cc) (Shark)
- 2,4D + Epirefenacil 5,5% (600cc) (Empera)

MALEZA PEE BARBECHO INTERMEDIO (45-60 DAS):
- Flumioxazin 48% (150cc) (Sumisoya)
- Piroxasulfone 85% (160-200g) (Yamato)
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Metribuzin 48% (1l) (Sencorex)

PEE / PSI-PEE:
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Flumioxazin 15%/Piroxasulfone 34,5% (0,5l) (Fierce FMC) 7 DAS
- Flumioxazin 4,2%/S-metolacloro 84% (1,75l) (Apresa ADAMA) 7 DAS
- Fomesafén 11,9% / S-metolacloro 51,8% (2,5l)
- (Trifludimoxazin/Saflufenacil) (Voraxor) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)

POST-EMERGENCIA CULTIVO — Sojas Resistentes Glifosato:
- Fomesafén 25% (1-1,5l) (Flex)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Benazolín 50% (0,6-1l) (Dasen)

SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) / 2,4D 30% e.a. (1,5-2l) hasta V4-V6

=== MAÍZ ===

--- MAÍZ: CEBOLLÍN (Cyperus rotundus) ---
Fuente: Uso interno / Marbete Summit-Agro SEMPRA SENASA Nº35.981 / Marbete BASF Pivot SENASA Nº33.606.
Ver también sección CONSIDERACIONES GENERALES — CYPERUS ROTUNDUS para biología y estrategia completa.
Control nunca es 100% total. Aplicar siempre con cebollin en activo crecimiento (~15 cm de altura).

MAÍZ CONVENCIONAL — POE cultivo + maleza:
- Halosulfurón metil 75% (100-150 g/ha) (Sempra) — POE convencional, sin restricción de estado vegetativo del maíz.
  Coadyuvante obligatorio: surfactante no iónico 0,1-0,2% v/v.

MAÍZ RR/RG — POE cultivo + maleza:
- Halosulfurón metil 75% (30-50 g/ha) (Sempra) + Glifosato 48% (2,5 L/ha) — cebollin a ~15 cm.
- Glifosato 48% (3 L/ha) + Clorimurón 25% (60-80 g/ha) (Classic) — buenos resultados de campo.

MAÍZ CLEARFIELD (CL) — POE cultivo + maleza:
- Imazapic 240 g/L (1 L/ha) (Pivot) — cebollin desde emergencia hasta 4a hoja verdadera. Control parcial + acción residual.
  ADVERTENCIA CRITICA: Pivot es FITOTÓXICO en maíz convencional. Usar ÚNICAMENTE en maíz Clearfield.

COADYUVANTE: Surfactante no iónico 0,1-0,2% v/v en aplicaciones de ALS (Sempra, Pivot, Classic).

--- MAÍZ: AMARANTHUS SPP. ---

ANTES DE SIEMBRA DEL CULTIVO — POE maleza / PSI cultivo:
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Picloram (0,1-0,15l)
- Epirefenacil 5,5% (600cc) (Empera)
- Trifludimoxazin / Saflufenacil (0,15-0,2l) 7 DAS
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 2,4D + Carfentrazone 40% (70-80cc) (Shark)

PEE / PSI-PEE:
- Atrazina 90% (1-2kg) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Atrazina 90% (1-2kg) + Biciclopirona 20% (0,8-1l)
- Biciclopirona 20% (0,8-1l) + S-metolacloro 96% (1,1-1,3l) (Dual Gold) — premezclado (Acuron Pack)
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Mesotrione 48% (0,3l) (Callisto) + Piroxasulfone 85% (0,16-0,2kg) (Yamato)
- (Isoxaflutole/Thiencarbazone) (0,3-0,4l) (Adengo) + S-metolacloro 96% (Dual Gold) + Atrazina 90%

POST-EMERGENCIA CULTIVO (V2-V8):
- Atrazina 90% (1kg) + 2,4D 64,3% e.a. (0,4l)
- Atrazina 90% (1kg) + Picloram 24% (0,1-0,15l)
- Atrazina 90% (1kg) + Mesotrione 48% (0,3l) (Callisto)
- Atrazina 90% (1kg) + Topramezone 33,6% (0,1l) (Convey)
- Atrazina 90% (1kg) + Tolpyralate 42% (0,075-0,125l) (Brucia)
- Atrazina 90% (1kg) + Tembotrione 42% (0,25-0,3l) (Laudis)
- 2,4D V2-V8 / 2,4D sal colina 66,9% V1-V8 Maíz ENLIST
- Mesotrione 48% (0,3l) (Callisto) V2-V6
- Topramezone 33,6% (0,08-0,1l) (Convey) V1-V7
- Glufosinato de amonio 28% (1,8-2l) Maíz ENLIST V1-V8

MAÍZ ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V2-V4
- 2,4D 45,6% e.a. (1,5-2l) hasta V8
- Glufosinato de amonio 28% (2-3l) + 2,4D 45,6% e.a. (1,5-2l) V2-V4

--- MAÍZ: CRUCIFERAS ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Junio 2024.
ADVERTENCIA: Ver también sección BRASICACEAS para biología, flujos de emergencia y resistencias.

ANTES DE SIEMBRA DEL CULTIVO — POE maleza / PSI cultivo:
- Glifosato + 2,4D o MCPA — base en biotipos susceptibles
- Glifosato + 2,4D o MCPA + PPO (saflufenacil/carfentrazone/piraflufen)
- Glifosato + 2,4D o MCPA + Fotosistema II (atrazina/metribuzin/amicarbazone)
- Glifosato + 2,4D o MCPA + HPPD/PDS (biciclopirona/mesotrione/diflufenicán)
- Glufosinato de amonio 28% (1,5-3l)
- Paraquat 27,6% (Gramoxone)

PEE / PSI CULTIVO — Residuales:
- Atrazina 90% (1-2kg) (Gesaprim)
- Terbutilazina 75% (1-1,3kg) (Terbine/Gesatop)
- Flurocloridona 25% (0,75-1,5l) (Rainbow)
- Diflufenicán 50% (0,2-0,3l) (Brodal)
- Flumioxazin 48% (Sumisoya)
- Pyroxasulfone 85% (0,16-0,2kg) (Yamato)

POST-EMERGENCIA CULTIVO (V2-V8):
- MCPA 28% (1,5l) + Atrazina 90% (1kg) — V2-V8
- 2,4D 64,3% e.a. + Atrazina 90% (1kg) — V2-V8
- Mesotrione 48% (0,3l) (Callisto) + Atrazina 90% (1kg) — excelente sobre crucíferas pequeñas
- Topramezone 33,6% (0,08-0,1l) (Convey) + Atrazina 90% (1kg) — V1-V7
- Tembotrione 42% (0,25-0,3l) (Laudis) + Atrazina 90% (1kg) — V3-V6
- Tolpyralate 40% (0,075-0,125l) (Brucia) + Atrazina 90% (1kg) — V3-V6
ADVERTENCIA: HPPD deben mezclarse siempre con atrazina o terbutilazina para sinergizar el control.

MAÍZ ENLIST — POE:
- Glufosinato de amonio 28% (1,8-2l) V1-V8
- 2,4D 45,6% e.a. (1,5-2l) hasta V8
- Glufosinato 28% + 2,4D 45,6% e.a. V2-V4

=== GIRASOL ===

--- GIRASOL: CEBOLLÍN (Cyperus rotundus) ---
Fuente: Uso interno / Marbete BASF Clearsol II Plus Pack (Imazamox 70% + Imazapir 80%) — BASF Argentina.
Ver también sección CONSIDERACIONES GENERALES — CYPERUS ROTUNDUS para biología y estrategia completa.
Control nunca es 100% total.

BARBECHO / PRE-SIEMBRA — Sobre cebollin activo (6-8 hojas, activo crecimiento):
- Glifosato (≥2000 g.e.a./ha) — herramienta principal en barbecho previo a girasol.

PEE — Antes de emergencia del girasol:
- S-metolacloro 96% (Dual Gold) — VLCFA, reduce emergencia de nuevas plántulas
- Acetoclor 90% (Harness) — VLCFA, mismo efecto
  Los acetanilidas reducen emergencia pero no eliminan tubérculos establecidos.

POE — SOLO GIRASOLES CLEARFIELD PLUS (CL Plus):
ADVERTENCIA CRITICA: Clearsol II Plus Pack SOLO en híbridos con logo Clearfield PLUS. Causa severos daños en CL no Plus o convencionales.
- Clearsol II Plus Pack (Imazamox 70% + Imazapir 80%) dosis alta — control de cebollin entre 3a y 7a hoja.
- Clearsol II Plus Pack dosis media — control parcial.
- Clearsol II Plus Pack dosis baja — supresión.
  No aplicar con estrés hídrico o térmico.
  No usar organofosforados en mezcla.
  Orden de adición: 1 Imazamox, 2 Imazapir, 3 Clatrato BASF.

POE — GIRASOLES CLEARFIELD (CL, no Plus):
- Clearsol DF (Imazapir solo) — V2-V4. Menor espectro.
  En biotipos con resistencia a ALS: imazapir NO tiene efecto.

GIRASOLES CONVENCIONALES (no CL):
Sin opciones POE para cebollin. Control en barbecho y PEE únicamente.

--- GIRASOL: CRUCIFERAS ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Junio 2024.
ADVERTENCIA: Ver también sección BRASICACEAS para biología, flujos de emergencia y resistencias.
Crucíferas pueden generar pérdidas de girasol de hasta 79% con más de 30 pl/m2.

ANTES DE SIEMBRA DEL CULTIVO — POE maleza:
- Glifosato + 2,4D + PPO (saflufenacil/carfentrazone/piraflufen)
- Doble golpe en rosetas grandes: sistémico + paraquat/diquat
  Dicamba: respetar 45 DAS antes de siembra. 2,4D: 20 DAS.

PEE:
- Flurocloridona 25% (Rainbow) + Diflufenicán 50% (Brodal) — combinar cuando hay sospecha de resistencia a flurocloridona.
- Flumioxazin 48% (Sumisoya)
- Prometrina 50% (Gesagard)

POST-EMERGENCIA — OPCIONES MUY LIMITADAS:
GIRASOLES CL:
- Imazapir 80% (Clearsol) V2-V4
- Imazapir + Imazamox (Clearsol Plus II) V2-V4 — mejor espectro
- Imazapir + Aclonifén (Prodigio) — mejora eficacia sobre crucíferas
  En biotipos con resistencia a ALS el imazapir NO tiene efecto.

GIRASOLES NO CL: Sin opciones específicas. Control preventivo desde barbecho y PEE.

--- GIRASOL: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — POE maleza / PSI-PEE cultivo:
Fluroxipir y Halauxifén: seguridad de uso hasta la siembra (1 DAS).
Dicamba: respetar carencia de 45 DAS antes de siembra.
2,4D: respetar carencia 20 DAS, usar formulaciones éster ethyl o microemulsión.

AUXINAS SINTÉTICAS (barbecho): 2,4D (20 DAS) / Dicamba (Banvel) (45 DAS) / Fluroxipir (Starane) (1 DAS) / Halauxifén (Elevore) (1 DAS) / Fluroxipir+Halauxifén (Pixxaro) (1 DAS)
PPO (barbecho): Piraflufen-etil (Stagger) / Carfentrazone 40% (Shark) (15 DAS) / Flumioxazin 48% (Sumisoya/Vesdua) 30-60 DAS
FOTOSISTEMA I (barbecho): Diquat 40% (Reglone) / Paraquat 27,6% (Gramoxone)
EPSPS (barbecho): Glifosato

PEE / PSI-PEE:
PPO: Sulfentrazone 50% (Authority/Capaz/Shutdown) — ajustar dosis en suelos bajo MO, arenosos, pH>7,5
VLCFA: Acetoclor 90% (Harness) / S-metolacloro 96% (Dual Gold)
INH. SINT. MICROT.: Pendimetalín 45,5% (Herbadox) / Trifluralina 60% (Treflan)
FOTOSISTEMA II: Prometrina 50% (Gesagard)
PDS: Diflufenicán 50% (Brodal/Pelican L) / Flurocloridona 25% (Rainbow)
ALS (solo girasoles CL): Imazapyr 80% (Clearsol) / Imazapyr+Imazamox (Clearsol Plus II)
MEZCLAS PEE: Sulfentrazone 50% (Authority/Capaz) + S-metolacloro 96% (Dual Gold) / Sulfentrazone 50% + Acetoclor 90% (Harness)

POST-EMERGENCIA — OPCIONES MUY LIMITADAS:
Aclonifén (Prodigio): eficaz en yuyo colorado SOLO con plántulas <2cm. Ventana muy estrecha.
ALS (solo girasoles CL): Imazapyr 80% (Clearsol) V2-V4 / Imazapyr+Imazamox (Clearsol Plus II) V2-V4
ACCasa (gramíneas): Haloxyfop-R-metil (Galant Max) / Propaquizafop (Agil) / Quizalofop-P-etil (Assure) / Cletodim (Select)
DESECANTE POST MF: Carfentrazone etil (Shark 40 EC) / Saflufenacil (Heat) — SOLO como desecante POST MF.

NO USAR en girasol durante el ciclo: saflufenacil, fomesafén, diclosulam, biciclopirona, topramezone, sulfonilureas.

=== TRIGO ===

--- TRIGO: CONYZA SPP. ---

ANTES DE SIEMBRA DEL CULTIVO:
- Glifosato + 2,4D / Glifosato + Dicamba 57,8% (0,1-0,2l) (Banvel)
- Glifosato + 2,4D o MCPA + Saflufenacil 70% (35-40g) (Heat)
- Glifosato + 2,4D o MCPA + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D o MCPA + Epirefenacil 5,5% (600cc) (Empera)
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)

PEE maleza / PSI cultivo:
- Metsulfurón 60% (8-10g) (Ally) / Flumioxazin 48% (0,15l) (Sumisoya) 10 DAS
- Terbutrina 50% (1,2l) (Igran) / Terbutilazina 75% (1kg) (Terbine/Gesatop)
- Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)

POST-EMERGENCIA Z2.1-Z3.0:
- Metsulfurón 60% (5-6g) (Errasin WP/Ally) + Dicamba 57,8% (0,1-0,15l) (Banvel)
- 2,4D 64,3% e.a. (0,4l) + Dicamba 57,8% (0,1-0,15l) (Banvel)
- 2,4D 64,3% e.a. (0,4l) + Picloram 24% (0,1-0,12l) (Tordón)
- 2,4D 64,3% e.a. (0,4l) + Saflufenacil 70% (25g) (Heat)
- Saflufenacil 70% (25g) (Heat) solo — registro POE trigo confirmado. Malezas ≤10cm
- Clopyralid / MCPA (1,25-1,35l) (Lontrel)
- Glufosinato de amonio 28% (2-3l) Trigos HB4
VENTANA: Saflufenacil desde Z1.2-Z1.3 SIN aceite. 2,4D y sulfonilureas desde Z2.1.

--- TRIGO: CRUCIFERAS ---

ANTES DE SIEMBRA:
- Glifosato + 2,4D o MCPA + Saflufenacil 70% (35-40g) (Heat)
- Glifosato + 2,4D o MCPA + Carfentrazone 40% (70-80cc) (Shark)

PEE: Flurocloridona 25% (1,5l) (Rainbow) / Diflufenicán 50% (0,3l) (Brodal) / Flumioxazin 48% (Sumisoya)

POST-EMERGENCIA ESTADO DE HOJAS (Z1.2+):
- Bromoxinil 34,6% (0,8-1l) (Bromotril) — desde Z1.2. Eficaz en cruciferas en plantula.
- MCPA 28% (1,5-2,5l) — desde Z1.3-Z1.5.
- Saflufenacil 70% (25g) (Heat) — desde Z1.2-Z1.3. SIN aceite. Malezas cruciferas ≤10cm.
- Bromoxinil + MCPA 28% — desde Z1.3. Sinergia contacto+sistemico.
  Las cruciferas son RESISTENTES a ALS en gran parte de la zona nucleo — verificar biotipo.
  Las cruciferas son TOLERANTES/RESISTENTES al dicamba solo — usar en mezcla con otros activos.

POST-EMERGENCIA MACOLLAJE Z2.1+:
- Bromoxinil (Bromotril) + 2,4D o MCPA — Registro trigo y cebada
- Carfentrazone 40% (0,04l) (Shark) + 2,4D o MCPA — Registro trigo y cebada
- Saflufenacil 70% (25g) (Heat) + 2,4D o MCPA — Registro trigo. Malezas ≤10cm
- Flurocloridona 25% (Rainbow) + 2,4D o MCPA — Registro trigo

TRIGOS HB4:
- Glufosinato de amonio 28% (2-3l) / + 2,4D / + Metribuzin 48% (Sencorex) / + Flurocloridona 25% (Rainbow)

REGLA SAFLUFENACIL EN TRIGO POE: 25g/ha puede mezclarse con CUALQUIER hormonal desde Z1.2. SIN aceite en estado de hojas.

--- TRIGO: RAIGRAS ---

SITUACIÓN 1 — 1-2 hojas, baja densidad:
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) / Glufosinato de amonio 28% (1-2,5l)
- Glifosato + Cletodim 24% (0,7l) (Select)

SITUACIÓN 2 — 2-4 hojas, densidad media:
- Glifosato + Cletodim 24% (1l) (Select)
- Glifosato + Haloxyfop 54% (0,25-0,35l) (Galant Max)
- Glifosato + Cletodim 12%/Haloxyfop 6% (0,8l) (Gramini Elite)

SITUACIÓN 3 — >4 hojas o sospecha de resistencia:
- Glifosato + Cletodim 24% (Select) + Epirefenacil 5,5% (Empera)
- Glufosinato de amonio 28% + Cletodim 24% (Select)

SITUACIÓN 4 — Alta densidad, resistencia probable — Doble Golpe:
- 1° Glifosato + Cletodim 24% (Select) // 2° DG Paraquat 27,6% (Gramoxone) — ~7 dias
- 1° Glifosato + Cletodim 24% (Select) // 2° DG Glufosinato de amonio 28% — ~7 dias

PEE: Piroxasulfone 48% (Yamato Top) / Pendimetalín 45,6% (Herbadox) / Flumioxazin 48% (Sumisoya) 10 DAS

POST-EMERGENCIA:
- Pinoxaden 5% (0,6-0,8l) (Axial) — desde Z1.3 hasta encañazón
- Clodinafop 24% (0,2l) (Gizmo/Topick 24EC) — desde Z1.2-Z1.3
- Iodosulfurón/Mesosulfurón (0,2-0,3l) (Hussar Plus) — desde Z1.2
- Piroxulam 21,5% (84gr) (PowerFlex) — desde Z1.3 hasta fin macollaje
- Imazamox 70-100g (Pulsar/Trigosol) Trigos CL
- Glufosinato de amonio 28% (2-3l) Trigos HB4

=== SORGO ===

--- SORGO: LATIFOLIADAS/GRAMÍNEAS ---

ANTES DE SIEMBRA:
- Glifosato / 2,4D / Picloram / Fluroxipir (Starane) / Clopyralid (Lontrel)
- Paraquat 27,6% (Gramoxone) / Glufosinato de amonio 28%
- Cletodim 24% (0,7-1l) 20 DAS / Haloxyfop 54% (0,25-0,35l) 20 DAS
- Saflufenacil 70% (Heat) / Epirefenacil 5,5% (Empera) / Carfentrazone 40% (Shark)

PEE: Flumioxazin 48% (0,15l) / Terbutilazina 75% (Terbine) / Atrazina 90% (1-2kg)
- S-metolacloro 96% (Dual Gold)* / Pendimetalín 33% (Herbadox)
- Imazapyc 31,8% (0,2-0,3l) (Odyssey) Sorgos tolerantes
*semilla curada con Fluxofenim 96%

POST-EMERGENCIA V4-V8:
- Bromoxinil 34,6% (0,8-1l) (Bromotril) V2-V4 / Atrazina 90% (1-2kg) V2-V4
- Bentazón 60% (1,2-1,6l) (Basagran) V2-V8
- Imazapyc/Imazapy (Odyssey) Sorgos tolerantes
- Foramsulfurón 30% + Iodosulfurón 2% (120cc) (Equip) — sorgo de Alepo RG
- Nicosulfurón 75% (70g) (Accent) — sorgo de Alepo RG
Desecante: Paraquat 27,6% (Gramoxone) / Glifosato

=== COLZA / CANOLA / CARINATA ===

ANTES DE SIEMBRA: Paraquat / Glufosinato / Glifosato / 2,4D (15-20 DAS) / Saflufenacil (Heat) / Carfentrazone (Shark)
PEE: Trifluralina 60% (Treflan) / Pendimetalín (Herbadox). Carinata: solo trifluralina.
POST-EMERGENCIA: Cletodim (Select) / Haloxyfop (Galant Max) — graminicidas. Clopyralid (Lontrel) riesgo Bajo. Carinata: solo graminicidas y clopyralid.

RIESGO EN ROTACIÓN: Imidazolinonas Alto / Sulfonilureas Alto / Diclosulam Alto / Sulfentrazone Moderado / Flumioxazín Bajo / Piroxazulfone Bajo.

=== ARVEJA ===

ANTES DE SIEMBRA: Glifosato / Paraquat / Glufosinato / 2,4D (15 DAS) / Cletodim / Haloxyfop
PEE: Imazatapir 10% / Metribuzin / Terbutilazina / Prometrina (Gesagard) / Linurón / Flumioxazin / S-metolacloro / Pendimetalín / Trifluralina
POST-EMERGENCIA (BBCH 14 — antes de zarcillos BBCH 15): Cletodim / Haloxyfop / Imazatapir 10% (0,5l) / Metribuzin (Sencorex) / Bentazón (Basagran) / MCPA 28% (0,5-0,75l)
Desecante: Paraquat / Diquat (Reglone) / Saflufenacil / Glufosinato

=== CAMELINA ===

ANTES DE SIEMBRA: Paraquat / Glufosinato / Glifosato / 2,4D / Saflufenacil / Carfentrazone
PEE: Trifluralina 60% (Treflan) — ÚNICA opción residual
POST-EMERGENCIA (roseta BBCH 13-15): Cletodim 60% — ÚNICA opción, solo gramíneas
Desecante: Diquat (Reglone) / Saflufenacil / Carfentrazone
Cultivo con opciones muy limitadas.

=== CRUCÍFERAS RESISTENTES (Barbecho) ===
Fuente: AAPRESID Regional Tandilia / INTA Tandil. Campaña 2018-19.

CONTROL TOTAL — POE sobre maleza nacida:
- Glifosato + 2,4D 45,6% e.a. (1,5l) + Saflufenacil 70% (35g) (Heat) → mejores controles
- Glifosato + 2,4D 45,6% e.a. (1,5l) + Carfentrazone 40% (75cc) (Shark) → mejores controles
- Paraquat 27,6% (2,5l) (Gramoxone) + 2,4D 45,6% e.a. (1,5l) → control intermedio

CONTROL + RESIDUAL:
Alta infestación (16-18 pl/m2), solo funcionan >80%:
- Glifosato + 2,4D + Diclosulam + Halauxifén (Texaro)
- Glifosato + 2,4D + Piroxasulfone + Saflufenacil (Zidua Pack)

=== SENECIO ARGENTINUS (Barbecho) ===
- Emerge abril-mayo. Tamaño crítico: NO superar 10 cm al aplicar.
- MEJOR COMBINACIÓN: Glifosato Premium 1080 g.ea + Flumioxazin (Sumisoya 120ml) + S-metolacloro (Dual Gold 1000ml)

=== TRÉBOL BLANCO (Trifolium repens) — Barbecho ===
OPCION PRINCIPAL: Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha.
OPCION CON PPO: + Saflufenacil 70% (Heat) 25-35g/ha.
OPCION MARBETE: Glifosato 48% (3 l/ha) + Fluroxipir 33% (Starane Xtra) 360 cc/ha.

=== PROTOCOLO INTERNO DE ENSAYOS ===

PEE:
- GIRASOL: Glifosato 2L/1,5kg + Flurocloridona 1,5L + Piroxasulfone 160g
- MAIZ: Glifosato 2L/1,5kg + Atrazina 3L/1,5kg + Zidua Pack (HEAT 45g + Pyroxasulfone 200g) + Aceite
- SOJA: Glifosato 2L/1,5kg + Sulfentrazone 400cc + S-Metolacloro 1,5L + Metribuzin 48% 1,5L

POE:
- GIRASOL CL: Clearsol DF 100g + Aceite DASH 200cc + graminicida si hace falta
- GIRASOL NO CL: Prodigio 1,5L + Aceite o Benazolin 50% 0,3L + graminicida
- MAIZ: Glifosato 2L/1,5kg (RR) + Atrazina 1,5-3L + Tordon 150cc / Glufosinato (Maiz Enlist)
- SOJA: Glifosato 2L/1,5kg (RR) + Fomesafen 25% 1,5L + coadyuvante + Benazolin 50% 0,8L
"""


# --- CLIENTE ANTHROPIC ---
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- HISTORIAL DE CONVERSACION POR USUARIO ---
conversation_history = {}

# --- COMANDO /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Soy el asistente de <b>Control de Malezas</b>.\n\n"
        "Puedo ayudarte con recomendaciones de herbicidas para:\n"
        "🌱 Soja · Maíz · Girasol · Trigo · Sorgo\n"
        "🌿 Colza · Arveja · Camelina\n\n"
        "Preguntame sobre malezas específicas, momentos de aplicación, dosis, etc.\n\n"
        "Ejemplo: <i>¿Qué uso para control de yuyo colorado en PEE de soja?</i>",
        parse_mode="HTML"
    )

# --- COMANDO /nuevo ---
async def nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("🔄 Conversación reiniciada. ¿En qué puedo ayudarte?")

# --- MANEJO DE MENSAJES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=KNOWLEDGE_BASE,
            messages=conversation_history[user_id]
        )

        assistant_message = response.content[0].text

        conversation_history[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        if len(conversation_history[user_id]) > 10:
            conversation_history[user_id] = conversation_history[user_id][-10:]

        await update.message.reply_text(assistant_message)

    except Exception as e:
        logger.error(f"Error completo: {type(e).__name__}: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error: {type(e).__name__}: {str(e)[:200]}"
        )

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nuevo", nuevo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
