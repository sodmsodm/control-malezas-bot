import os
import logging
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters, CallbackQueryHandler

# --- CONFIGURACION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- INFO DE COADYUVANTES ---
COADYUVANTES_INFO = """
💧 *COADYUVANTES Y ACEITES — Opciones y dosis:*

*Coadyuvantes:*
✅ A35 T Bio — Coadyuvante — 40-80 cc/ha
✅ wr4 BIO — Corrector — 40-80 cc/ha
✅ Alltec Ultra — Coadyuvante + Corrector — 80-100 cc/ha
✅ Mso max — Coadyuvante + Aceite — 200-250 cc/ha
✅ Version — Aceite — 0,5-1 l/ha
✅ A35 T GOLD — Coadyuvante + Aceite — 100-150 cc/ha

*Compatibilizador:*
✅ ALL OK — Prevén / Correctivo — 400-600 cc/ha
"""

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

REGLA DE COADYUVANTES EN RESPUESTA:
Cuando en tu respuesta menciones aceite, coadyuvante, surfactante o sulfato de amonio, al FINAL de toda la respuesta agregá SIEMPRE esta línea exacta (sin modificarla):
💧 ¿Querés ver opciones y dosis de coadyuvantes disponibles?

Esta línea debe aparecer una sola vez, al final, solo cuando la respuesta incluya alguna recomendación de aceite o coadyuvante. No la incluyas en respuestas sobre fenología, residualidad u otras consultas sin herbicidas.

=== ACEITES Y COADYUVANTES ===
REGLA DE COADYUVANTES: Siempre que recomendés un herbicida de los grupos indicados abajo, incluí la recomendación de aceite o coadyuvante correspondiente.

ACCasa — GRAMINICIDAS (cletodim/Select, haloxyfop/Galant Max, quizalofop/Assure, fluazifop/Super Onecide, pinoxaden/Axial, propaquizafop/Agil):
→ SIEMPRE incluir aceite vegetal o metilado de soja 0,5-1% v/v. Sin aceite la eficacia cae significativamente.

PPO — CONTACTO (carfentrazone/Shark, piraflufen/Stagger, epirefenacil/Empera, flumioxazin/Sumisoya, trifludimoxazin+saflufenacil/Voraxor):
→ SIEMPRE incluir aceite metilado de soja o mineral 0,5-1% v/v.
EXCEPCION CRITICA: Saflufenacil (Heat) en POE de trigo estado de hojas (Z1.2-Z1.3) — SIN aceite ni coadyuvante.

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
- Pivot (imazapic): carencia 90 días en soja. En Maíz CL y alfalfa: uso posicionado sin restricción práctica.
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
- Baja densidad (5 pl/m2) + crecimiento inicial lento → el cultivo tarda ~5 semanas en cerrar canopeo
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

ESTRATEGIA POR MOMENTO:
- BARBECHO: clave para malezas otoño-invernales.
- PEE: momento más importante. Dosis ajustar por MO, arena, pH y humedad de suelo.
- POE: opciones muy limitadas.


--- BRASICÁCEAS / CRUCÍFERAS: BIOLOGÍA, RESISTENCIAS Y ESTRATEGIA TRANSVERSAL ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Junio 2024.

IDENTIFICACIÓN:
- Brassica rapa Nabo/nabolza: flor AMARILLA, silicua dehiscente, hojas amplexicaules.
- Raphanus sativus Nabón: flor VIOLÁCEA/ROSADA/BLANCA, silicua INDEHISCENTE y corchosa, hojas pecioladas.
- Hirschfeldia incana Nabillo/mostacilla: flor AMARILLO PÁLIDO, silicua adpresa al raquis.
- Rapistrum rugosum Mostacilla: fruto SILÍCULA indehiscente globosa.

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
- Con resistencia a ALS: NO usar sulfonilureas ni imidazolinonas.
- Con resistencia a glifosato: agregar PPO quemante (Heat, Shark) a la mezcla base.
- Con TRIPLE resistencia: Glifosato+PPO/Triazina en 1° app + desecante DG.


--- COMMELINA ERECTA: BIOLOGÍA Y ESTRATEGIA DE CONTROL ---
Fuente: Panigo E., Cortés E., Vernier F. — REM Aapresid. Mayo 2025.

TOLERANCIA AL GLIFOSATO:
- Plantas <5 hojas de semilla: buen manejo posible con herbicidas
- Plantas >5 hojas o de rebrote de rizoma: TOLERANTES — glifosato solo alcanza <30% de control

DOS ÉPOCAS CLAVE DE INTERVENCIÓN QUÍMICA:
>> OTOÑO: Base Glifosato + 2,4D. Opción para rizomas: Imazapir 200 cc/ha (al 48%) — ANTES de heladas.
>> PRIMAVERA: Base Glifosato + 2,4D + acompañante residual según cultivo siguiente.

Acompañantes según eficacia (REM Aapresid 2025):
HPPD — promedio 72%: Biciclopirona 20% 1000 cc/ha MEJOR / Mesotrione 48% / Tembotrione 42%
ALS — promedio 64%: Diclosulam 84% 30-40 g/ha MEJOR / Imazetapir 10% / Nicosulfuron
PPO — promedio 63%: Flumioxazin 48% 150 cc/ha MEJOR / Saflufenacil 70% / Carfentrazone 40%
TRIAZINAS — promedio 59%: Metribuzin 48% 0,8-1 l/ha / Amicarbazone 70% / Atrazina 90%

DOBLE GOLPE (DG):
- 2° aplicación: Paraquat 27,6% (Gramoxone) o Glufosinato de amonio 28% 2500-3000 cc/ha

ESTRATEGIA POR BIOTIPO:
SOJA RR: glifosato solo <30% de control. Control pre-siembra obligatorio.
SOJA ENLIST: POE — Glufosinato + Glifosato + 2,4D → >80% de control.
MAÍZ ENLIST: muy buenos niveles de control en POE.
MAÍZ SIN ENLIST: HPPD + Triazina como aplicación secuencial POE.


--- TRÉBOL BLANCO (Trifolium repens): ESTRATEGIA DE CONTROL EN BARBECHO ---
Fuente: Corteva / INTA Oliveros / Marbete Starane Xtra SENASA No.35.712.

OPCIÓN PRINCIPAL: Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha
OPCIÓN CON PPO: + Saflufenacil 70% (Heat) 25-35g/ha
OPCIÓN MARBETE: Glifosato 48% (3 l/ha) + Fluroxipir 33% (Starane Xtra) 360 cc/ha


--- CYPERUS ROTUNDUS (CEBOLLÍN): BIOLOGÍA Y ESTRATEGIA TRANSVERSAL ---
Fuente: Uso interno / Marbete SEMPRA SENASA Nº35.981 / Marbete Pivot SENASA Nº33.606.

SENSIBILIDAD A HERBICIDAS:
- Glifosato: sensible a dosis altas (>=2000 g.e.a./ha). Requiere cebollin en activo crecimiento, 6-8 hojas.
- Halosulfurón metil (Sempra): muy eficaz. Aplicar con cebollin a ~15 cm.
- Imazapic (Pivot): control PARCIAL. Tiene acción residual que limita rebrotes.
- Imazetapir 10%: buenos resultados en mezcla con glifosato. Aporta residualidad.
- Clorimurón (Classic): buenos resultados en mezcla con glifosato.
CONTROL NUNCA ES 100% TOTAL — requiere estrategia de largo plazo.

MEZCLAS CON BUENOS RESULTADOS (uso antes de siembra):
- Glifosato 3 L/ha + Clorimurón 25% (60-80 g/ha) (Classic)
- Glifosato 3,5 L/ha + Imazetapir 10% (800 cc/ha) + humectante — NO sembrar alfalfa pura en rotación.
Aplicar siempre con surfactante no iónico 0,1-0,2% v/v.

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
- Fomesafén 25% (1-1,5l) (Flex) + Clorimurón 25% (0,03kg) (Classic)
- Clorimurón 25% (0,04-0,05kg) (Classic)
- Cloransulam 84% (0,04-0,05kg) (Pacto)
- Imazetapir 10% (0,5-0,8l) (Pivot)
- 2,4DB 97% e.a. (0,04l) + Bentazón 60% (0,8-1l) (Basagran)
- Benazolín 50% (0,6l) (Dasen) + Clorimurón 25% (0,03g) (Classic)

--- SOJA: CEBOLLÍN (Cyperus rotundus) ---
PRE-SIEMBRA — cebollin a ~15 cm. Mínimo 10 DAS.
- Halosulfurón metil 75% (100-150 g/ha) (Sempra) — muy eficaz.
- Halosulfurón metil 75% (30-50 g/ha) (Sempra) + Glifosato 48% (2,5 L/ha)
- Glifosato 48% (3 L/ha) + Clorimurón 25% (60-80 g/ha) (Classic)
- Glifosato 48% (3,5 L/ha) + Imazetapir 10% (800 cc/ha) + humectante — NO alfalfa en rotación
- Glifosato (>=2000 g.e.a./ha) solo — 6-8 hojas activo crecimiento. Control parcial.
POE CULTIVO:
- Imazapic 240 g/L (1 L/ha) (Pivot) — hasta 4a hoja cebollin. Control parcial + residual.
  Carencia Pivot: 90 días. Verificar tolerancia variedad soja.
COADYUVANTE: Surfactante no iónico 0,1-0,2% v/v. NO aceite mineral.

--- SOJA: COMMELINA ERECTA ---
ANTES DE SIEMBRA — POE maleza / PSI cultivo:
CON GLIFOSATO:
- Glifosato 1260 g.e.a. + 2,4D (1-1,5l) + Saflufenacil 70% (40g) (Heat)
- Glifosato + 2,4D + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D + Flumioxazin 48% (150cc) (Sumisoya)
- Glifosato + 2,4D + Imazetapir 10% (0,8-1l) (Pivot)
- Glifosato + 2,4D + (Trifludimoxazin/Saflufenacil) (0,1-0,2l) (Voraxor)
- Glifosato + 2,4D + Metribuzin 48% (0,8-1l) (Sencorex)
- Glifosato + 2,4D + Amicarbazone 70% (0,4g) (Dinamic) — hasta 45 DAS
CON GLUFOSINATO:
- Glufosinato de amonio 28% (2,5l) + 2,4D
- Glufosinato de amonio 28% + 2,4D + Metribuzin 48% (0,8-1l) (Sencorex)
- Glufosinato de amonio 28% + 2,4D + Saflufenacil 70% (Heat)
- Glufosinato de amonio 28% + 2,4D + Carfentrazone 40% (Shark)
- Glufosinato de amonio 28% + 2,4D + Flumioxazin 48% (Sumisoya)
- Glufosinato de amonio 28% + 2,4D + (Trifludimoxazin/Saflufenacil) (Voraxor)
DOBLE GOLPE:
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (Gramoxone)
- 1° Glifosato + 2,4D // 2° DG Glufosinato de amonio 28%
- 1° Glifosato + 2,4D // 2° DG (Glufosinato 28% 2-3l + Saflufenacil 70% 35-40g) (Heat)
- 1° Glifosato + 2,4D // 2° DG (Glufosinato 28% 2-3l + Carfentrazone 40% 70-80cc) (Shark)
SOJAS ENLIST:
- Glifosato 1260 g.e.a. + Glufosinato de amonio 28% + 2,4D 30% e.a. (1,5-2l) — hasta V4-V6
- Glufosinato de amonio 28% (2-2,5l) + 2,4D 30% e.a. (1,5-2l) — hasta V4-V6

--- SOJA: CRUCIFERAS ---
ANTES DE SIEMBRA — POE maleza / PSI cultivo:
- Glifosato + 2,4D / Glifosato + MCPA 28% (1,5-2,5l)
- Glifosato + 2,4D o MCPA + Saflufenacil 70% (35-40g) (Heat)
- Glifosato + 2,4D o MCPA + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D o MCPA + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D o MCPA + (Trifludimoxazin/Saflufenacil) (0,1-0,15l) (Voraxor)
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)
PEE / PSI-PEE:
- Metribuzin 48% (0,8-1kg) (Sencorex) / Sulfentrazone 50% (Authority/Capaz)
- Flumioxazin 48% (Sumisoya) 7 DAS / Diflufenicán 50% (Brodal) 15 DAS
- Trifludimoxazin 12,5%/Saflufenacil 25% (Voraxor) 7 DAS
POST-EMERGENCIA CULTIVO — Maleza ROSETA PEQUEÑA (5-8 cm):
- Fomesafén 25% (1-1,5l) (Flex) / Acifluorfén 24% (1-1,5l) (Blazer) / Lactofén 24% (Cobra)
- Bentazón 60% (1,5l) (Basagran)
- Imazetapir 10% (0,5-0,8l) (Pivot) + Clorimurón 25% (0,04kg) (Classic)
ADVERTENCIA: En biotipos con resistencia a ALS no usar sulfonilureas ni imidazolinonas.
SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) + 2,4D 30% e.a. (1,5-2l) hasta V4-V6

--- SOJA: PARIETARIA ---
BARBECHO LARGO:
- Atrazina 90% (1-1,5kg) hasta 60 DAS / Amicarbazone 70% (Dinamic) hasta 45 DAS
- Terbutilazina 75% (Terbine/Gesatop) hasta 45 DAS / Metsulfurón 60% (6-8g) hasta 60 DAS
- Flumioxazin 48% (Sumisoya)
PEE / PSI-PEE:
- Metribuzin 48% (Sencorex) / Prometrina 48% (Gesagard)
- Paraquat 27,6% (Gramoxone) + Metribuzin 48% (Sencorex)
- Trifludimoxazin/Saflufenacil (Voraxor) 7 DAS
POST-EMERGENCIA: Sin opciones efectivas.

--- SOJA: AMARANTHUS SPP. (Yuyo Colorado) ---
ANTES DE SIEMBRA:
- 2,4D (1-1,5l) / Epirefenacil 5,5% (Empera) / Glufosinato de amonio 28% (2,5l) / Paraquat (Gramoxone)
- 2,4D + Saflufenacil 70% (40g) (Heat) / 2,4D + Carfentrazone 40% (Shark)
PEE BARBECHO INTERMEDIO: Flumioxazin (Sumisoya) / Piroxasulfone (Yamato) / Atrazina 90% / Metribuzin (Sencorex)
PEE / PSI-PEE:
- Sulfentrazone 50% (Authority/Capaz) + S-metolacloro 96% (Dual Gold)
- Flumioxazin 15%/Piroxasulfone 34,5% (Fierce FMC) 7 DAS
- Flumioxazin 4,2%/S-metolacloro 84% (Apresa ADAMA) 7 DAS
- (Trifludimoxazin/Saflufenacil) (Voraxor) + S-metolacloro 96% (Dual Gold)
POST-EMERGENCIA — Sojas RR: Fomesafén 25% (Flex) / Lactofén 24% (Cobra) / Benazolín 50% (Dasen)
SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2

=== MAÍZ ===

--- MAÍZ: CEBOLLÍN (Cyperus rotundus) ---
MAÍZ CONVENCIONAL — POE:
- Halosulfurón metil 75% (100-150 g/ha) (Sempra) — sin restricción estadio maíz. Cebollin a ~15 cm.
  Coadyuvante obligatorio: surfactante no iónico 0,1-0,2% v/v.
MAÍZ RR/RG — POE:
- Halosulfurón metil 75% (30-50 g/ha) (Sempra) + Glifosato 48% (2,5 L/ha)
- Glifosato 48% (3 L/ha) + Clorimurón 25% (60-80 g/ha) (Classic)
MAÍZ CLEARFIELD (CL) — POE:
- Imazapic 240 g/L (1 L/ha) (Pivot) — cebollin hasta 4a hoja.
  ADVERTENCIA CRITICA: Pivot FITOTÓXICO en maíz convencional. Solo Clearfield.
COADYUVANTE: Surfactante no iónico 0,1-0,2% v/v.

--- MAÍZ: AMARANTHUS SPP. ---
ANTES DE SIEMBRA:
- 2,4D / Picloram / Epirefenacil (Empera) / Glufosinato 28% / Paraquat (Gramoxone)
- 2,4D + Carfentrazone 40% (Shark)
PEE / PSI-PEE:
- Atrazina 90% (1-2kg) + S-metolacloro 96% (Dual Gold) / (Acuron Pack premezclado)
- Atrazina 90% + Biciclopirona 20% / Amicarbazone (Dinamic) + S-metolacloro (Dual Gold)
- Mesotrione 48% (Callisto) + Piroxasulfone (Yamato)
- (Isoxaflutole/Thiencarbazone) (Adengo) + S-metolacloro (Dual Gold) + Atrazina
POST-EMERGENCIA CULTIVO (V2-V8):
- Atrazina 90% (1kg) + 2,4D / + Picloram / + Mesotrione (Callisto) / + Topramezone (Convey)
- Atrazina 90% (1kg) + Tolpyralate (Brucia) / + Tembotrione (Laudis)
- 2,4D V2-V8 / 2,4D sal colina V1-V8 Maíz ENLIST
- Mesotrione 48% (Callisto) V2-V6 / Topramezone 33,6% (Convey) V1-V7
- Glufosinato de amonio 28% (1,8-2l) Maíz ENLIST V1-V8
MAÍZ ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V2-V4
- 2,4D 45,6% e.a. (1,5-2l) hasta V8
- Glufosinato 28% + 2,4D 45,6% e.a. V2-V4

--- MAÍZ: CRUCIFERAS ---
ANTES DE SIEMBRA:
- Glifosato + 2,4D o MCPA (base susceptibles) + PPO / Fotosistema II / HPPD/PDS según biotipo
PEE: Atrazina (Gesaprim) / Terbutilazina (Terbine) / Flurocloridona (Rainbow) / Diflufenicán (Brodal) / Flumioxazin (Sumisoya) / Pyroxasulfone (Yamato)
POST-EMERGENCIA V2-V8:
- MCPA 28% (1,5l) + Atrazina 90% (1kg) — base clásica
- Mesotrione 48% (Callisto) + Atrazina 90% (1kg) — excelente sobre crucíferas pequeñas
- Topramezone 33,6% (Convey) + Atrazina (1kg) — V1-V7
- Tembotrione 42% (Laudis) + Atrazina (1kg) — V3-V6
- Tolpyralate 40% (Brucia) + Atrazina (1kg) — V3-V6
ADVERTENCIA: HPPD siempre con atrazina o terbutilazina para sinergizar.
MAÍZ ENLIST: Glufosinato 28% (1,8-2l) V1-V8 / 2,4D 45,6% hasta V8

=== GIRASOL ===

--- GIRASOL: CEBOLLÍN (Cyperus rotundus) ---
BARBECHO: Glifosato (>=2000 g.e.a./ha) — herramienta principal.
PEE: S-metolacloro 96% (Dual Gold) / Acetoclor 90% (Harness) — reducen emergencia, no eliminan tubérculos.
POE — SOLO GIRASOLES CLEARFIELD PLUS (CL Plus):
ADVERTENCIA CRITICA: Clearsol II Plus Pack SOLO en híbridos Clearfield PLUS. Daña CL no Plus o convencionales.
- Clearsol II Plus Pack (Imazamox 70% + Imazapir 80%) dosis alta — control entre 3a y 7a hoja cebollin.
- Clearsol II Plus Pack dosis media — control parcial.
- Clearsol II Plus Pack dosis baja — supresión.
  No aplicar con estrés hídrico o térmico. No usar organofosforados en mezcla.
  Orden adición: 1° Imazamox, 2° Imazapir, 3° Clatrato BASF.
POE — GIRASOLES CLEARFIELD (CL, no Plus): Clearsol DF (Imazapir solo) — V2-V4. Menor espectro.
GIRASOLES CONVENCIONALES: Sin opciones POE. Control en barbecho y PEE únicamente.

--- GIRASOL: CRUCIFERAS ---
ANTES DE SIEMBRA: Glifosato + 2,4D + PPO. Dicamba: 45 DAS. 2,4D: 20 DAS.
PEE: Flurocloridona (Rainbow) + Diflufenicán (Brodal) — combinar con sospecha de resistencia.
POST-EMERGENCIA — MUY LIMITADAS:
GIRASOLES CL: Imazapir 80% (Clearsol) V2-V4 / Imazapir+Imazamox (Clearsol Plus II) V2-V4
GIRASOLES NO CL: Sin opciones. Control preventivo desde barbecho y PEE.

--- GIRASOL: MALEZA GENERAL ---
BARBECHO: 2,4D (20 DAS) / Dicamba (45 DAS) / Fluroxipir (Starane) (1 DAS) / Halauxifén (Elevore) (1 DAS)
PPO barbecho: Piraflufen (Stagger) / Carfentrazone (Shark) (15 DAS) / Flumioxazin (Sumisoya) 30-60 DAS
Fotosistema I: Diquat (Reglone) / Paraquat (Gramoxone) / Glifosato
PEE: Sulfentrazone 50% (Authority/Capaz) / Acetoclor (Harness) / S-metolacloro (Dual Gold)
PDS: Diflufenicán (Brodal) / Flurocloridona (Rainbow)
MEZCLAS PEE: Sulfentrazone + S-metolacloro (Dual Gold) / Sulfentrazone + Acetoclor (Harness)
POST-EMERGENCIA — MUY LIMITADAS:
Aclonifén (Prodigio): yuyo colorado SOLO <2cm. Ventana muy estrecha.
ALS (solo girasoles CL): Imazapyr (Clearsol) V2-V4 / Imazapyr+Imazamox (Clearsol Plus II) V2-V4
ACCasa (gramíneas): Haloxyfop-R-metil (Galant Max) / Propaquizafop (Agil) / Cletodim (Select)
DESECANTE POST MF: Carfentrazone (Shark) / Saflufenacil (Heat) — SOLO POST MF.
NO USAR durante ciclo: saflufenacil, fomesafén, diclosulam, biciclopirona, topramezone, sulfonilureas.

=== TRIGO ===

--- TRIGO: CONYZA SPP. ---
ANTES DE SIEMBRA:
- Glifosato + 2,4D / Glifosato + Dicamba (Banvel)
- Glifosato + 2,4D o MCPA + Saflufenacil (Heat) / Carfentrazone (Shark) / Epirefenacil (Empera)
- 1° Glifosato + 2,4D // 2° DG Paraquat (Gramoxone)
PEE: Metsulfurón (Ally) / Flumioxazin (Sumisoya) 10 DAS / Terbutrina (Igran) / Terbutilazina (Terbine) / Voraxor
POST-EMERGENCIA Z2.1-Z3.0:
- Metsulfurón (Errasin WP/Ally) + Dicamba (Banvel)
- 2,4D + Dicamba (Banvel) / 2,4D + Picloram (Tordón)
- 2,4D + Saflufenacil 70% (25g) (Heat) / Saflufenacil 70% (25g) solo — Malezas ≤10cm
- Clopyralid/MCPA (Lontrel) / Glufosinato 28% Trigos HB4
VENTANA: Saflufenacil desde Z1.2-Z1.3 SIN aceite. 2,4D y sulfonilureas desde Z2.1.

--- TRIGO: CRUCIFERAS ---
ANTES DE SIEMBRA: Glifosato + 2,4D o MCPA + Saflufenacil (Heat) / Carfentrazone (Shark)
PEE: Flurocloridona (Rainbow) / Diflufenicán (Brodal) / Flumioxazin (Sumisoya)
POST-EMERGENCIA ESTADO DE HOJAS (Z1.2+):
- Bromoxinil 34,6% (Bromotril) — desde Z1.2. Cruciferas en plantula.
- MCPA 28% (1,5-2,5l) — desde Z1.3-Z1.5.
- Saflufenacil 70% (25g) (Heat) — desde Z1.2-Z1.3. SIN aceite. Cruciferas ≤10cm.
- Bromoxinil + MCPA — desde Z1.3. Sinergia contacto+sistemico.
  Las cruciferas son RESISTENTES a ALS en gran parte de la zona nucleo — verificar biotipo.
  Las cruciferas son TOLERANTES/RESISTENTES al dicamba solo — usar en mezcla.
POST-EMERGENCIA MACOLLAJE Z2.1+:
- Bromoxinil (Bromotril) + 2,4D o MCPA / Carfentrazone (Shark) + 2,4D o MCPA
- Saflufenacil 70% (25g) (Heat) + 2,4D o MCPA — Malezas ≤10cm
- Flurocloridona (Rainbow) + 2,4D o MCPA
TRIGOS HB4: Glufosinato 28% / + 2,4D / + Metribuzin (Sencorex) / + Flurocloridona (Rainbow)
REGLA SAFLUFENACIL EN TRIGO POE: 25g/ha mezclable con CUALQUIER hormonal desde Z1.2. SIN aceite en estado de hojas.

--- TRIGO: RAIGRAS ---
SITUACIÓN 1 — 1-2 hojas, baja densidad:
- Paraquat (Gramoxone) / Glufosinato 28% / Glifosato + Cletodim 24% (Select)
SITUACIÓN 2 — 2-4 hojas, densidad media:
- Glifosato + Cletodim 24% (Select) / Glifosato + Haloxyfop 54% (Galant Max)
- Glifosato + Cletodim 12%/Haloxyfop 6% (Gramini Elite)
SITUACIÓN 3 — >4 hojas o sospecha de resistencia:
- Glifosato + Cletodim (Select) + Epirefenacil (Empera)
- Glufosinato 28% + Cletodim (Select)
SITUACIÓN 4 — Resistencia probable — Doble Golpe:
- 1° Glifosato + Cletodim (Select) // 2° DG Paraquat (Gramoxone) — ~7 dias
- 1° Glifosato + Cletodim (Select) // 2° DG Glufosinato 28% — ~7 dias
PEE: Piroxasulfone (Yamato Top) / Pendimetalín (Herbadox) / Flumioxazin (Sumisoya) 10 DAS
POST-EMERGENCIA:
- Pinoxaden 5% (Axial) — desde Z1.3
- Clodinafop 24% (Gizmo/Topick 24EC) — desde Z1.2-Z1.3
- Iodosulfurón/Mesosulfurón (Hussar Plus) — desde Z1.2
- Piroxulam 21,5% (PowerFlex) — desde Z1.3 hasta fin macollaje
- Imazamox (Pulsar/Trigosol) Trigos CL / Glufosinato 28% Trigos HB4

=== SORGO ===

ANTES DE SIEMBRA: Glifosato / 2,4D / Picloram / Fluroxipir (Starane) / Paraquat (Gramoxone) / Glufosinato 28%
- Cletodim 24% (0,7-1l) 20 DAS / Haloxyfop 54% 20 DAS
- Saflufenacil (Heat) / Epirefenacil (Empera) / Carfentrazone (Shark)
PEE: Flumioxazin / Terbutilazina (Terbine) / Atrazina 90% / S-metolacloro (Dual Gold)* / Pendimetalín (Herbadox)
*semilla curada con Fluxofenim 96%
POST-EMERGENCIA V4-V8:
- Bromoxinil (Bromotril) V2-V4 / Atrazina V2-V4 / Bentazón (Basagran) V2-V8
- Foramsulfurón + Iodosulfurón (Equip) — sorgo de Alepo RG
- Nicosulfurón (Accent) — sorgo de Alepo RG
Desecante: Paraquat (Gramoxone) / Glifosato

=== COLZA / CANOLA / CARINATA ===
ANTES DE SIEMBRA: Paraquat / Glufosinato / Glifosato / 2,4D (15-20 DAS) / Saflufenacil (Heat) / Carfentrazone (Shark)
PEE: Trifluralina (Treflan) / Pendimetalín (Herbadox). Carinata: solo trifluralina.
POST-EMERGENCIA: Cletodim (Select) / Haloxyfop (Galant Max) — graminicidas. Clopyralid (Lontrel) riesgo Bajo.
RIESGO ROTACIÓN: Imidazolinonas Alto / Sulfonilureas Alto / Diclosulam Alto / Flumioxazín Bajo.

=== ARVEJA ===
ANTES DE SIEMBRA: Glifosato / Paraquat / Glufosinato / 2,4D (15 DAS) / Cletodim / Haloxyfop
PEE: Imazatapir 10% / Metribuzin / Terbutilazina / Prometrina (Gesagard) / Linurón / Flumioxazin / S-metolacloro / Pendimetalín / Trifluralina
POST-EMERGENCIA (BBCH 14): Cletodim / Haloxyfop / Imazatapir 10% (0,5l) / Metribuzin (Sencorex) / Bentazón (Basagran) / MCPA 28% (0,5-0,75l)
Desecante: Paraquat / Diquat (Reglone) / Saflufenacil / Glufosinato

=== CAMELINA ===
ANTES DE SIEMBRA: Paraquat / Glufosinato / Glifosato / 2,4D / Saflufenacil / Carfentrazone
PEE: Trifluralina (Treflan) — ÚNICA opción residual
POST-EMERGENCIA (roseta BBCH 13-15): Cletodim 60% — ÚNICA opción, solo gramíneas
Desecante: Diquat (Reglone) / Saflufenacil / Carfentrazone

=== CRUCÍFERAS RESISTENTES (Barbecho) ===
CONTROL TOTAL:
- Glifosato + 2,4D (1,5l) + Saflufenacil 70% (35g) (Heat) → mejores controles
- Glifosato + 2,4D (1,5l) + Carfentrazone 40% (75cc) (Shark) → mejores controles
- Paraquat (2,5l) (Gramoxone) + 2,4D (1,5l) → control intermedio
CONTROL + RESIDUAL Alta infestación — solo funcionan >80%:
- Glifosato + 2,4D + Diclosulam + Halauxifén (Texaro)
- Glifosato + 2,4D + Piroxasulfone + Saflufenacil (Zidua Pack)

=== SENECIO ARGENTINUS (Barbecho) ===
Emerge abril-mayo. Tamaño crítico: NO superar 10 cm al aplicar.
MEJOR COMBINACIÓN: Glifosato Premium 1080 g.ea + Flumioxazin (Sumisoya 120ml) + S-metolacloro (Dual Gold 1000ml)

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

    # Si el usuario responde "si" o "sí" y el mensaje anterior del bot tenía el botón de coadyuvantes
    if user_message.lower().strip() in ["si", "sí", "s"]:
        history = conversation_history.get(user_id, [])
        if history and history[-1]["role"] == "assistant":
            last_bot_msg = history[-1]["content"]
            if "Querés ver opciones y dosis de coadyuvantes" in last_bot_msg or "💧" in last_bot_msg:
                await update.message.reply_text(COADYUVANTES_INFO, parse_mode="Markdown")
                return

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

        # Detectar si la respuesta menciona coadyuvantes/aceite
        trigger_words = [
            "aceite", "coadyuvante", "surfactante", "sulfato de amonio",
            "aceite vegetal", "aceite metilado", "aceite mineral"
        ]
        needs_coady_button = any(w in assistant_message.lower() for w in trigger_words)

        # Separar la línea de invitación del texto principal
        main_message = assistant_message
        if "💧 ¿Querés ver opciones" in assistant_message:
            parts = assistant_message.rsplit("💧 ¿Querés ver opciones", 1)
            main_message = parts[0].rstrip()

        if needs_coady_button:
            # Enviar el texto principal
            await update.message.reply_text(main_message)
            # Enviar el botón inline como mensaje separado
            keyboard = [[InlineKeyboardButton(
                "💧 Ver opciones y dosis de coadyuvantes",
                callback_data="show_coadyuvantes"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "¿Querés ver opciones y dosis de coadyuvantes?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(main_message)

    except Exception as e:
        logger.error(f"Error completo: {type(e).__name__}: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error: {type(e).__name__}: {str(e)[:200]}"
        )

# --- CALLBACK HANDLER — botón inline de coadyuvantes ---
async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "show_coadyuvantes":
        await query.message.reply_text(COADYUVANTES_INFO, parse_mode="Markdown")

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nuevo", nuevo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
