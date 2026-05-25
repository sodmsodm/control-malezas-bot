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
Ejemplo: "Aplicar sobre maleza nacida (POE maleza) / Antes de siembra del cultivo (PSI cultivo)" significa que se aplica ANTES de sembrar el cultivo, sobre maleza que ya nació. NO significa que se aplica sobre el cultivo emergido.

REGLA DE COINCIDENCIA EXACTA: Si el estadio, momento de aplicación, o condición específica mencionada por el usuario NO coincide exactamente con lo que figura en la base, SIEMPRE aclararlo con un ⚠️ antes de responder.

REGLA DE FENOLOGÍA: Para consultas sobre estadios fenológicos, respondé únicamente con las descripciones que figuran en la base. No agregues datos como días después de siembra, temperaturas, duraciones, ni ninguna otra información que no esté explícitamente escrita en la base de conocimiento.

REGLA DE BIOTIPOS: Cuando el usuario pregunta sobre control de malezas en soja, trigo, maíz o cualquier cultivo sin especificar el biotipo o tecnología (ej: RR, No GMO, STS, Enlist, HB4, CL), SIEMPRE presentar las opciones organizadas por biotipo disponible en la base. Nunca responder solo para un biotipo si existen opciones para otros biotipos en la misma consulta. Ejemplo: si preguntan "control de Conyza en soja", mostrar opciones para Soja RR, Soja Enlist, y aclarar si hay diferencias relevantes entre biotipos.

REGLA DE MARCAS COMERCIALES: Cada vez que menciones un principio activo que tenga una marca comercial asociada en esta base (indicada entre paréntesis), SIEMPRE incluí la marca junto al principio activo en tu respuesta. Nunca menciones solo el principio activo si tenés la marca disponible. Formato obligatorio: "Principio activo dosis (Marca)". Ejemplos correctos: "Topramezone 33,6% (0,08-0,1l) (Convey)", "Mesotrione 48% (0,3l) (Callisto)", "Pinoxaden 5% (0,6-0,8l) (Axial)". Esto aplica a TODAS las respuestas, incluyendo tablas, recomendaciones y ejemplos.

Respondés en español, de forma clara, técnica y organizada. Usás tablas cuando es útil.
Siempre aclarás el momento de aplicación (barbecho, PEE, PSI-PEE, POE) y el biotipo de cultivo cuando es relevante.

=== ACEITES Y COADYUVANTES ===
REGLA DE COADYUVANTES: Siempre que recomendés un herbicida de los grupos indicados abajo, incluí la recomendación de aceite o coadyuvante correspondiente. Es parte de la recomendación técnica completa.

REGLA CRÍTICA — MEZCLAS CON GLIFOSATO: El glifosato frecuentemente acompaña otras mezclas (ej: glifosato + cletodim para raigrás). En ese caso el aceite se recomienda igual, por el herbicida principal de la mezcla (cletodim en este ejemplo). La presencia de glifosato en la mezcla NO cancela la necesidad de aceite.

ACCasa — GRAMINICIDAS (cletodim/Select, haloxyfop/Galant Max, quizalofop/Assure, fluazifop/Super Onecide, pinoxaden/Axial, propaquizafop/Agil):
→ SIEMPRE incluir aceite vegetal o metilado de soja 0,5-1% v/v (o según marbete). Mejora absorción en gramíneas con cutícula cerosa. Sin aceite la eficacia cae significativamente.

PPO — CONTACTO (carfentrazone/Shark, piraflufen/Stagger, epirefenacil/Empera, flumioxazin/Sumisoya, trifludimoxazin+saflufenacil/Voraxor):
→ SIEMPRE incluir aceite metilado de soja o mineral 0,5-1% v/v. Favorece penetración cuticular rápida, clave para el efecto de contacto.
⚠️ EXCEPCIÓN CRÍTICA: Saflufenacil (Heat) en POE de trigo estado de hojas (Z1.2-Z1.3) — SIN aceite ni coadyuvante. El aceite aumenta la fitotoxicidad en trigo en ese estadio. Sí puede usarse con aceite en barbecho o en maíz POE.

SAFLUFENACIL (Heat) — según contexto:
→ En barbecho (POE maleza): con aceite metilado de soja 0,5% v/v
→ En trigo POE estado de hojas (Z1.2-Z1.3): SIN aceite
→ En trigo POE macollaje (Z2.1+): puede usarse con aceite según condiciones
→ En maíz POE: con aceite según marbete BASF

GLUFOSINATO DE AMONIO:
→ SIEMPRE incluir surfactante no iónico 0,1-0,5% v/v o aceite metilado de soja. Mejora cobertura y penetración. Recomendado también agregar Sulfato de Amonio 1,5-2 l/ha para mejorar absorción.

HPPD — MAÍZ POE (mesotrione/Callisto, topramezone/Convey, tembotrione/Laudis, tolpyralate/Brucia):
→ Incluir aceite mineral o metilado de soja según marbete. Importante en POE para favorecer absorción foliar.

ALS / SULFONILUREAS (metsulfurón/Errasin WP/Ally, imazetapir/Pivot, clorimurón/Classic, diclosulam/Spider, etc.):
→ Surfactante no iónico 0,1-0,2% v/v (200cc/100L). NO aceite mineral — puede aumentar fitotoxicidad en el cultivo.

HORMONALES (2,4D, MCPA, dicamba, fluroxipir/Starane, picloram/Tordón):
→ En general no es obligatorio. En condiciones adversas (maleza grande, sequía, frío) puede ser útil agregar surfactante no iónico o aceite metilado de soja para mejorar absorción. Consultar marbete del producto.

GLIFOSATO SOLO:
→ NO usar aceite vegetal. Usar Sulfato de Amonio 1-2% v/v para mejorar absorción, especialmente con agua dura o en condiciones de estrés.

TRIAZINAS / RESIDUALES DE SUELO (atrazina, metribuzin, terbutilazina, sulfentrazone, pyroxasulfone, etc.):
→ No requieren coadyuvante foliar. Son residuales de suelo, se activan con humedad.


=== RESIDUALIDAD DE HERBICIDAS ===
Fuente: Dto. Técnico DOW AgroSciences Argentina S.A. y otros.
Valores orientativos. Intervalo mínimo en días desde la aplicación hasta la siembra del cultivo siguiente.
s/d = sin dato disponible. Los valores de cletodim aplican solo con buena MO, sin lluvias y dosis no mayor a 600 g e.a./ha — RIESGOSO.

--- TABLA DE RESIDUALIDAD (días desde aplicación a siembra) ---

Herbicida          | P.activo         | Dosis(g/ha) | Trigo | Maíz | Sorgo | Soja | Girasol | Alfalfa | Tréboles | Colza
Spider             | Diclosulam       | 35          | 200   | 325  | 355   | 0    | 540     | s/d     | s/d      | 540
Starane Xtra       | Fluroxipir       | 210-450     | 0     | 0    | 0     | 1    | 1       | 1       | 1        | 1
2,4D               | 2,4D             | 300-500     | 3-5   | 3-5  | 3-5   | 7-15 | 7-15    | 7-15    | 7-15     | 7-15
Banvel             | Dicamba          | 120-150     | 0     | 0    | 0     | 15-20| 15-20   | 15-20   | 15-20    | 15-20
Lontrel            | Clopyralid       | 150         | 0     | 0    | 0     | 20   | 45      | 45      | 45       | 0
Tordon 24K         | Picloram         | 80-100      | 0     | 0    | 0     | 45   | 80      | 80      | 80       | 15-20
Koltar             | Oxifluorfén      | 300         | 10    | 10   | 10    | 80   | 0       | s/d     | s/d      | 7-10
Brodal             | Diflufenicán     | 250         | 15    | 20   | s/d   | 20   | 0       | s/d     | s/d      | s/d
Ally/Metsulfurón   | Metsulfurón      | 8-10        | 0     | 60   | s/d   | 90   | 120     | 90      | 90       | s/d
Classic            | Clorimurón       | 30-40       | 40    | 40   | s/d   | 0    | 120     | 120     | 120      | 40
Gesaprim/Atrazina  | Atrazina 90%     | 1,5 kg/ha   | 120   | 0    | 0     | 60   | 90      | s/d     | 90       | s/d
Authority/Capaz    | Sulfentrazone    | —           | 180   | 180  | 180   | 0    | 0       | s/d     | s/d      | s/d (270 colza)
Flex               | Fomesafén        | —           | 180   | 180  | 270   | 0    | 180     | 180     | 180      | 270
Select             | Cletodim         | 800-(500)   | 15(?) | 15(?)| 15(?) | 0    | 0       | 0       | 0        | 0
Shark              | Carfentrazone    | 75          | 0     | 0    | 0     | 0?   | 0       | 0       | 0        | 0

⚠️ NOTAS IMPORTANTES:
- Spider (diclosulam): residualidad en girasol luego de un año en suelos con 2% MO. Sin efecto en girasoles CL.
- Cletodim: valores con "?" indican incertidumbre. Aplicar solo con buena MO, sin lluvias y dosis ≤600 g e.a./ha.
- Tordon/Picloram: residualidad muy prolongada en suelos con pH alto o bajo contenido de MO.
- Residualidad de las AUXINAS en orden de mayor a menor: Picloram (Tordón) > Clopyralid (Lontrel) > Dicamba (Banvel) > 2,4D > Fluroxipir (Starane)


=== FENOLOGÍA DE CULTIVOS ===

--- FENOLOGÍA TRIGO Y CEBADA — Escala Zadoks (Zadoks et al., 1974) ---
Fuente: INTA Pergamino / Fernanda G. González (CONICET-EEA INTA Pergamino)

ESTADO 0 — GERMINACIÓN:
Z00: Semilla seca
Z01: Inicio absorción de agua
Z05: Extrusión de la radícula (germinación)
Z09: Hoja en punta del coleoptile

ESTADO 1 — CRECIMIENTO DE PLÁNTULA (nº hojas expandidas):
Z10: Primera hoja a través del coleoptile
Z11: Primera hoja expandida — 1 hoja
Z12: Dos hojas expandidas
Z13: Tres hojas expandidas
Z14: Cuatro hojas expandidas
Z15: Cinco hojas expandidas
Z19: Nueve o más hojas expandidas
⚠️ Una hoja está expandida cuando se observa la lígula en la base de la lámina

ESTADO 2 — MACOLLAJE (nº macollos):
Z21: Primer macollo
Z22: Dos macollos
Z23: Tres macollos
Z29: Nueve o más macollos
⚠️ El primer macollo aparece generalmente junto con la cuarta hoja

ESTADO 3 — ELONGACIÓN DE TALLO (encañazón):
Z30: Falso tallo erecto / Espiga a 1cm
Z31: Primer nudo detectable
Z32: Segundo nudo detectable
Z33: Tercer nudo detectable
Z37: Punta de hoja bandera visible
Z39: Hoja bandera expandida

ESTADO 4 — ESTADO DE BOTA:
Z41: Vaina de hoja bandera comenzando a ensancharse
Z45: Vainas notablemente ensanchadas
Z47: Vaina de hoja bandera abriéndose
Z49: Primeras aristas visibles por encima de la vaina
⚠️ Estado muy sensible a estrés hídrico y heladas

ESTADO 5 — ESPIGAZÓN:
Z51: Primeras espiguillas visibles
Z53: 1/4 espiga emergida
Z55: 1/2 espiga emergida
Z57: 3/4 espiga emergida
Z59: Emergencia completa

ESTADO 6 — ANTESIS:
Z61: Comienzo de antesis
Z65: 50% antesis
Z69: Antesis completa

ESTADO 7 — DESARROLLO LECHOSO DEL GRANO:
Z71: Grano acuoso (3mm, líquido claro al apretar)
Z73: Grano lechoso temprano (líquido acuoso blanco)
Z77: Grano lechoso tardío (contenido húmedo y pegajoso)

ESTADO 8 — DESARROLLO PASTOSO DEL GRANO:
Z85: Grano pastoso suave (contenido firme, impresión de uña desaparece rápido)
Z87: Grano pastoso duro (impresión de uña permanece, cercano a madurez fisiológica)

ESTADO 9 — MADUREZ:
Z92: Grano maduro para cosecha (grano seco, no se marca al apretar con la uña)

⚠️ CEBADA: usa la misma escala Zadoks. Diferencias: aristas visibles desde Z49, macollaje más corto en variedades de 2 carreras.

--- FENOLOGÍA MAÍZ — Escala Ritchie & Hanway (1982) ---
Fuente: FCA-UNC / Ing. Agr. Rubén E. Toledo

ESTADIOS VEGETATIVOS:
VE: Emergencia — el coleoptile alcanza la superficie del suelo y se establece la plántula
V1: Collar de 1ª hoja — hoja inferior completamente desplegada, collar y lígula visible
V2: Collar de 2ª hoja
V3: Collar de 3ª hoja — punto de crecimiento por debajo de la superficie del suelo
V4: Collar de 4ª hoja
V5: Collar de 5ª hoja — punto de crecimiento se acerca a la superficie del suelo
V6: Collar de 6ª hoja — ápice de crecimiento por encima de la superficie del suelo
V7: Collar de 7ª hoja
V8: Collar de 8ª hoja
V10: Collar de 10ª hoja
Vn: Collar de "n" hojas — "n" ésima hoja completamente desplegada, collar y lígula visible
VT: Antesis — aparición de la panoja con liberación de polen

ESTADIOS REPRODUCTIVOS:
R1: Silking — emergencia de los estigmas que capturan los granos de polen
R2: Ampolla o Blister — granos de color blanco asemejándose a una ampolla
R3: Grano lechoso — granos amarillos en parte exterior, interior líquido blanco lechoso
R4: Grano pastoso — fluido en endosperma espesado hasta consistencia pastosa, humedad ~70%
R5: Grano dentado — mazorca color rojo oscuro, inicio de secado, humedad ~55%
R5.25: 1/4 línea de leche — humedad ~45-50%
R5.5: 1/2 línea de leche — humedad ~40-45%
R5.75: 3/4 línea de leche — humedad ~35-40%
R6: Madurez fisiológica — capa negra formada, humedad del grano 30-35%

--- FENOLOGÍA SORGO — Escala Vanderlip & Reeves (1972) ---
Fuente: FCA-UNC

Estado 0: Emergencia — el coleoptile es visible en la superficie del suelo
Estado 1: Lígula de la 3ª hoja visible — collares y lígulas de tres hojas visibles sin disección
Estado 2: Lígula de la 5ª hoja visible — collares y lígulas de cinco hojas visibles sin disección
Estado 3: Diferenciación de meristemas — cambio del punto de crecimiento vegetativo a reproductivo
Estado 4: Inicio de panoja visible — panoja visible dentro de la vaina de la hoja bandera
Estado 5: Floración (antesis) — 50% de las plantas con antesis completa
Estado 6: Grano lechoso — granos con contenido lechoso
Estado 7: Grano pastoso — granos con contenido pastoso
Estado 8: Madurez fisiológica — capa negra formada en el grano
Estado 9: Madurez de cosecha

--- FENOLOGÍA SOJA — Escala Fehr & Caviness (1971/1977) ---
Fuente: INTA EEA Paraná / Santos, Diego (2010)

ESTADIOS VEGETATIVOS:
VE: Planta emergida — cotiledones por encima de la superficie, totalmente abiertos; primer par de hojas unifoliadas sin abrir
VC: Estado cotiledonar — primer par de hojas unifoliadas separadas y visibles; siguiente hoja trifoliada aún cerrada
V1: Primer nudo verdadero desarrollado — primera hoja unifoliada totalmente desarrollada
V2: Segunda hoja trifoliada totalmente desarrollada
V3: Tercera hoja trifoliada totalmente desarrollada
Vn: "n" ésima hoja trifoliada totalmente desarrollada
⚠️ Una hoja está totalmente desarrollada cuando la siguiente (más arriba) ya separó los bordes de sus folíolos

ESTADIOS REPRODUCTIVOS:
R1: Inicio floración — una flor abierta en cualquier nudo de la planta
R2: Plena floración — una flor abierta en alguno de los dos nudos superiores del tallo principal
R3: Inicio fructificación — una vaina de al menos 0,5 cm en alguno de los cuatro últimos nudos con hoja desarrollada
R4: Plena fructificación — una vaina de al menos 2 cm en alguno de los cuatro últimos nudos con hoja desarrollada
R5: Inicio llenado de semilla — semilla de al menos 3 mm de diámetro en vaina de los cuatro últimos nudos ("semilla que se siente al tacto o se ve a trasluz")
R6: Pleno llenado — semilla que ocupó toda su cavidad en vaina de los cuatro últimos nudos (vaina que se quiebra al doblar)
R7: Inicio madurez — UNA vaina normal del tallo principal llega a color marrón o gris (madurez fisiológica)
R8: Plena madurez — 95% de vainas normales del tallo principal con color marrón o gris (madurez cosecha)
⚠️ Luego de R7 un desecante NO incide en el rendimiento

--- FENOLOGÍA GIRASOL — Escala Schneiter & Miller (1981) adaptada ---
Fuente: INTA Reconquista / Ing. Agr. Sebastián Zuil

ESTADIOS VEGETATIVOS:
VE: Emergencia — hipocótilo y cotiledones emergidos, primera hoja verdadera menor a 4 cm
Vn: n hojas verdaderas (más de 4 cm de largo). Ej: V2=dos hojas, V8=ocho hojas
⚠️ Estado vegetativo continúa hasta aproximadamente V10-V12 según genotipo

ESTADIOS REPRODUCTIVOS:
R1: Inflorescencia rodeada de brácteas inmaduras visible (vista desde arriba parece estrella)
R2: Entrenudo debajo de la base de la inflorescencia se elonga 0,5 a 2 cm sobre última hoja
R3: Entrenudo debajo del órgano reproductivo lleva inflorescencia a más de 2 cm de última hoja
R4: Inflorescencia comienza a abrirse — flores liguladas comienzan a verse
R5: Antesis de flores tubuladas — flores liguladas completamente expandidas
R5.1: 10% del capítulo en antesis
R5.5: 50% del capítulo en antesis
R5.9: 90% del capítulo en antesis
R6: Antesis completa — flores liguladas perdieron turgencia y se marchitan
R7: Receptáculo comienza a cambiar de color (amarillo claro)
R8: Receptáculo completamente amarillo, brácteas aún verdes
R9: Brácteas cambian a color marrón — madurez fisiológica del cultivo

--- FENOLOGÍA COLZA/CANOLA — Escala BBCH ---
Fuente: Conocimiento general (pendiente de validación con fuente propia)

BBCH 00: Semilla seca
BBCH 10: Cotiledones emergidos
BBCH 11: Primera hoja verdadera
BBCH 12: Segunda hoja verdadera
BBCH 13: Tercera hoja verdadera
BBCH 15-19: Estado de roseta (5 a 9+ hojas)
⚠️ Ventana óptima herbicidas POE: BBCH 12-15 (roseta temprana)
BBCH 30: Inicio elongación del tallo
BBCH 31: Primer entrenudo visible
BBCH 51: Primeros botones florales visibles (rodeados de hojas)
BBCH 53: Botones florales visibles por encima de hojas
BBCH 55: Botones florales individuales separados
BBCH 60: Primeras flores abiertas
BBCH 65: Plena floración
BBCH 69: Fin de floración
BBCH 71: 10% de vainas con tamaño final
BBCH 75: 50% de vainas con tamaño final
BBCH 79: Vainas con tamaño final completo
BBCH 85: 10% de semillas con color madurez
BBCH 87: Semillas oscuras/maduras, vainas comenzando a abrirse
BBCH 89: Madurez fisiológica
BBCH 99: Madurez cosecha

--- FENOLOGÍA ARVEJA — Escala BBCH ---
Fuente: Conocimiento general (pendiente de validación con fuente propia)

BBCH 00: Semilla seca
BBCH 05: Germinación — raíz emergida
BBCH 09: Emergencia — plántula en superficie
BBCH 11: Primera hoja verdadera expandida (1 par de folíolos)
BBCH 12: Segunda hoja verdadera
BBCH 13: Tercera hoja verdadera
BBCH 14: Cuarta hoja verdadera
BBCH 15: Quinta hoja verdadera — inicio de zarcillos
⚠️ Ventana POE herbicidas: BBCH 11 a BBCH 14 (antes de zarcillos)
BBCH 51: Primeros botones florales visibles
BBCH 60: Primeras flores abiertas
BBCH 65: Plena floración
BBCH 69: Fin de floración
BBCH 71: Vainas pequeñas visibles
BBCH 75: Vainas al 50% tamaño final
BBCH 79: Vainas con tamaño final — semillas en desarrollo
BBCH 85: Semillas llenando vaina — grano pastoso
BBCH 89: Madurez fisiológica — vainas comenzando a secarse
BBCH 92: Madurez cosecha — vainas secas, semillas duras
⚠️ Desecación: desde BBCH 89

--- FENOLOGÍA CAMELINA — Escala BBCH ---
Fuente: Conocimiento general (pendiente de validación con fuente propia)

BBCH 00: Semilla seca
BBCH 10: Cotiledones emergidos
BBCH 11: Primera hoja verdadera
BBCH 12: Segunda hoja verdadera
BBCH 13-15: Estado de roseta (3 a 5 hojas)
BBCH 30: Inicio elongación del tallo
BBCH 51: Primeros botones florales visibles
BBCH 60: Primeras flores abiertas
BBCH 65: Plena floración
BBCH 69: Fin de floración
BBCH 79: Silículas con tamaño final
BBCH 89: Madurez fisiológica
BBCH 99: Madurez cosecha
⚠️ Opciones herbicidas muy limitadas — ver sección Camelina en base de conocimiento


=== CONSIDERACIONES GENERALES DE MANEJO ===

--- GIRASOL: ESTRATEGIA Y MALEZAS PROBLEMA ---
Fuente: REM Aapresid / Jorgelina Montoya INTA Anguil. Campaña 2025.

BIOLOGÍA Y VENTANA CRÍTICA:
- Baja densidad (5 pl/m²) + crecimiento inicial lento → el cultivo tarda ~5 semanas en cerrar canopeo
- Los primeros 30-35 días desde emergencia son la ventana crítica de competencia de malezas
- Después del cierre de canopeo el cultivo gana ventaja por sombreo — llegar limpio a ese punto es el objetivo

MALEZAS PROBLEMA CLAVE EN GIRASOL (2025):
- Rama negra (Conyza): biotipos con resistencia múltiple ampliamente expandidos → control anticipado obligatorio
- Crucíferas: biotipos resistentes a ALS, glifosato, 2,4D y ⚠️ RECIENTEMENTE A FLUROCLORIDONA
- Morenita: resistencia a ALS y glifosato confirmada en oeste de Buenos Aires
- Yuyo colorado: biotipos resistentes a glifosato, 2,4D, ALS y ⚠️ PREOCUPACIÓN CRECIENTE por resistencia a PPO (pre y postemergentes)
- Gramíneas estivales (anuales y perennes): muchas con resistencia a glifosato, ALS y graminicidas
- Raigrás: avanzando del sur al centro del país en lotes que van a girasol

CARRY-OVER — RIESGO FITOTOXICIDAD EN CULTIVO ANTECESOR:
⚠️ El girasol es MUY sensible a residuos de herbicidas de cultivos anteriores. Verificar siempre:
- Fomesafen (Flex) en soja antecesora + <300mm acumulados antes de siembra → RIESGO en girasol
- Diclosulam (Spider) en soja antecesora → RESTRINGE directamente la posibilidad de sembrar girasol
- Topramezone (Convey) en maíz + campaña seca + lote de baja productividad → daños residuales posibles
- Sulfonilureas en barbecho o cultivo invernal + ambiente seco → riesgo de carry-over para girasol
- HERRAMIENTA: bioensayo con muestras de suelo en macetas → si el girasol emerge y crece normal, es seguro avanzar

ESTRATEGIA POR MOMENTO:
- BARBECHO: clave para malezas otoño-invernales. Hormonales (2,4D, dicamba, fluroxipir, halauxifén), PPO (piraflufen, carfentrazone, flumioxazin). También trifludimoxazin y residuales PDS (diflufenicán, prometrina) si no se van a usar en PEE
- PEE: momento más importante. Dosis ajustar por MO, arena, pH y humedad de suelo — no importar recetas de otras zonas
- POE: opciones muy limitadas. La clave NO es el rescate en POE sino llegar limpio desde barbecho+PEE

CONSIDERACIONES POE EN GIRASOL:
- Aclonifén (Prodigio): eficaz en yuyo colorado SOLO con plántulas <2cm. Ventana muy estrecha
- Girasoles CL: imidazolinonas amplían espectro, aplicar V2-V4
- Graminicidas ACCasa (Select, Galant Max): eficaces en escapes de gramíneas con maleza chica y sin resistencia
- Fluroxipir y halauxifén: seguridad de uso hasta la siembra sin carencia


--- BRASICÁCEAS / CRUCÍFERAS: BIOLOGÍA, RESISTENCIAS Y ESTRATEGIA TRANSVERSAL ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Brasicáceas o Crucíferas: Bases para su manejo y control en Sistemas de Siembra Directa. Junio 2024.

IDENTIFICACIÓN DE LAS PRINCIPALES ESPECIES MALEZA EN ARGENTINA:
- Brassica rapa Nabo/nabolza: flores abiertas sobre botones, hojas caulinares amplexicaules, pelos mamelonados, flor AMARILLA, silicua dehiscente. Nabolza = biotipo con gen GT73 (transgén colza RR resistente a glifosato).
- Raphanus sativus Nabón: flor VIOLÁCEA/ROSADA/BLANCA, silicua INDEHISCENTE y corchosa. Hojas caulinares pecioladas (NO amplexicaules). Clave diferenciadora del nabo.
- Hirschfeldia incana Nabillo/mostacilla: flor AMARILLO PÁLIDO, silicua adpresa al raquis, densamente pubescente.
- Rapistrum rugosum Mostacilla: fruto SILÍCULA (no silicua) indehiscente globosa, flor amarillo pálido.
- Diplotaxis spp. Flor amarilla: hojas aromáticas algo carnosas, cotiledones con ápice truncado.
- Sisymbrium officinale Mostacilla: silicua lineal adpresa al raquis, hojas caulinares hastadas.
Clave rápida de campo: color de flor (amarillo vs violáceo/rosado) + tipo de fruto (dehiscente vs indehiscente) + inserción hoja caulinar (amplexicaule vs peciolada).

FLUJOS DE EMERGENCIA (define el momento óptimo de intervención):
- Brassica rapa: todo el año, picos en OTOÑO (mayor magnitud) y primavera. Compite con cultivos invernales Y estivales.
- Raphanus sativus: concentrado en OTOÑO y primavera. Compite en ambos tipos de cultivos.
- Rapistrum rugosum: principalmente OTOÑO. Especialmente problemática en invernales.
- Hirschfeldia incana / Diplotaxis spp.: principalmente otoño-invierno.
Dispersión: principalmente por maquinaria agrícola. Semillas viables en suelo hasta 6+ años. Germinan desde 5-6 cm de profundidad; no emergen desde más de 5 cm.

RESISTENCIAS CONFIRMADAS EN ARGENTINA (REM Aapresid 2024):
La nabolza pasó del 8% al 86% de los lotes en agricultura continua del SE bonaerense (2024). Las Crucíferas son la 2ª familia con más resistencias en Argentina (luego de gramíneas).

Especie              | Nombre vulgar      | Resistencia confirmada
Hirschfeldia incana  | Nabillo/mostacilla | ALS / ALS+2,4D / Glifosato+2,4D
Brassica napus       | Colza feral        | Glifosato (transgén GT73)
Brassica rapa        | Nabo/nabolza       | ALS+Glifosato / ALS+Glifosato+2,4D (triple)
Rapistrum rugosum    | Mostacilla         | ALS (desde 2018 Entre Ríos, expandiéndose)
Raphanus sativus     | Nabón              | ALS (mutación W574L)

PÉRDIDAS DE RENDIMIENTO (Fuente: ensayos citados en REM 2024):
- Trigo: -48% con 150 nabones/m2 (Leaden, 1995)
- Girasol: -5 a 12% con 1,6-16 nabones/m2; hasta -79% con más de 30 nabones/m2 (Pandolfo, 2016)
- Soja: -12 a 15% con más de 40 nabones/m2 (Bianchi et al., 2011)

PRINCIPIOS DE MANEJO INTEGRADO:
- Identificar especie y biotipo (resistencias) ANTES de elegir herbicidas
- Estrategia: controlar plantas nacidas + incorporar residual (período de emergencia prolongado)
- Cultivos de servicio con base GRAMÍNEA (raigrás+avena o avena+vicia) reducen stand y fecundidad
  ADVERTENCIA: NO usar crucíferas como cultivo de servicio — imposible garantizar ausencia de biotipos resistentes
- Mayor densidad de siembra en cereales (de 64 a 188 pl/m2 redujo biomasa ~65%)
- Las Crucíferas son muy competitivas en suelos ricos en N — la fertilización puede favorecer a la maleza

ESTRATEGIA QUÍMICA EN BARBECHO (transversal a todos los cultivos):

ROSETA CHICA menor a 10 cm:
Base: Glifosato + Hormonal (2,4D o MCPA) + acompañante de sitio de acción diferente:
- PPO: carfentrazone 40% (Shark), piraflufen 2,5% (Stagger), saflufenacil 70% (Heat), flumioxazin 48% (Sumisoya)
- Fotosistema II: atrazina 90%, metribuzin 48% (Sencorex), amicarbazone 70% (Dinamic), terbutilazina 75% (Terbine)
- HPPD/PDS: biciclopirona 20%, mesotrione 48% (Callisto), diflufenicán 50% (Brodal)
- Glufosinato 28%: puede reemplazar glifosato si malezas acompañantes lo permiten

ROSETA GRANDE mayor a 10 cm — Doble Golpe:
- 1 Aplicación sistémica: Glifosato + 2,4D o MCPA + PPO/Triazina/HPPD
- 2 Aplicación desecante: Paraquat 27,6% (Gramoxone) / Diquat 40% (Reglone) / Glufosinato 28%

HERBICIDAS RESIDUALES PARA BARBECHO (previenen nuevos nacimientos):
- Pre trigo/cebada: flurocloridona 25% (Rainbow), diflufenicán 50% (Brodal), flumioxazin 48% (Sumisoya), terbutilazina 75% (Terbine), terbutrina 50% (Igran), pyroxasulfone 85% (Yamato). Nuevas alternativas: aclonifen, mesotrione.
- Pre cultivos de gruesa: ver secciones específicas por cultivo.

REGLA CRÍTICA POR TIPO DE RESISTENCIA:
- Con resistencia a ALS: NO usar sulfonilureas ni imidazolinonas. Cambiar a PPO/Triazinas/HPPD.
- Con resistencia a glifosato: agregar PPO quemante (Heat, Shark) a la mezcla base. Ver sección CRUCIFERAS RESISTENTES BARBECHO.
- Con resistencia a 2,4D: agregar PPO quemante; no depender del control hormonal.
- Con TRIPLE resistencia (ALS+glifosato+2,4D): Glifosato+PPO/Triazina en 1° app + desecante DG. Sin opciones sencillas — enfocarse en manejo preventivo y rotación de cultivos.

--- COMMELINA ERECTA: BIOLOGÍA Y ESTRATEGIA DE CONTROL (transversal — todos los cultivos) ---
Fuente: Panigo E., Cortés E., Vernier F. — REM Aapresid. "Commelina erecta L.: Bases para su manejo y control en Sistemas de Siembra Directa". Mayo 2025. Editora: REM Aapresid, Rosario.

NOMBRE VULGAR: Flor de Santa Lucía
TIPO: Monocotiledónea herbácea PERENNE (familia Commelináceas)
DISTRIBUCIÓN ARGENTINA: Presente en Buenos Aires, Catamarca, Chaco, Córdoba, Corrientes, Entre Ríos, Formosa, Jujuy, La Pampa, La Rioja, Misiones, Salta, Santiago del Estero, Santa Fe, San Juan, San Luis y Tucumán (REM Aapresid, 2023). Entre 2013 y 2023 pasó de 117 a 164 departamentos (>80% de zonas encuestadas).

CARACTERÍSTICAS BIOLÓGICAS CLAVE (explican la dificultad de control):
- Ciclo PERENNE: rebrote de rizomas en septiembre, plántulas de semilla desde octubre. Floración/fructificación: fin de primavera a otoño. En invierno solo persisten rizomas subterráneos.
- Rizomas: fragmentos cortos engrosados en base de tallos. Actúan como órganos de reserva + permiten rebrote. La tolerancia al glifosato SOLO se observa en plantas con rizomas desarrollados (>5 hojas).
- Banco de yemas latentes: ~50% de nudos del tallo conservan yemas vivas incluso tras aplicación de glifosato → rebrote garantizado si no se afecta el sistema subterráneo.
- Dos tipos de semillas: alargadas (baja dormición, germina primavera-otoño) y ovoides (alta dormición, mayor longevidad en suelo). Producción estimada: ~750 semillas/planta/temporada.
- Ceras epicuticulares: plantas adultas (>5 hojas) tienen mayor cantidad de ceras que plántulas → menor absorción foliar de herbicidas.
- Alta capacidad competitiva: plantas de rizoma superan en competencia a Digitaria sanguinalis y Amaranthus hybridus.
- Dispersión por aves: semillas resisten tracto digestivo de palomas.

TOLERANCIA AL GLIFOSATO:
- Plantas <5 hojas de semilla: buen manejo posible con herbicidas
- Plantas >5 hojas o de rebrote de rizoma: TOLERANTES — glifosato solo alcanza <30% de control incluso a dosis altas
- El almacenamiento de almidón en rizoma + ceras epicuticulares son los mecanismos principales de tolerancia

P�RDIDAS EN SOJA: hasta 45% de rendimiento con 348 kg MS/ha de biomasa de Commelina (Ustarroz y Rainero, 2008)

PRINCIPIOS DE MANEJO INTEGRADO:
- Monitoreo: se establece primero en alambrados y cabeceras → controlar ahí antes de que invada el lote
- Rotaciones: incluir cultivos invernales (trigo, cebada, servicios) → competencia del cultivo reduce rebrotes notablemente. Un ensayo (Marzetti) mostró mejor control de rebrotes con trigo que en barbecho desnudo.
- Manejo químico: apuntar al AGOTAMIENTO PROGRESIVO del sistema de reservas. Una aplicación aislada no es suficiente → requiere estrategia encadenada.

DOS ÉPOCAS CLAVE DE INTERVENCIÓN QUÍMICA:

>> OTOÑO (1 momento):
Aprovechar etapa de acumulación de reservas, POST-COSECHA de cultivos estivales (principalmente soja/girasol por baja cobertura de rastrojos).
- Base: Glifosato + 2,4D
- Opción específica para rizomas: Imazapir 200 cc/ha (formulado al 48%) — sistémico, puede alcanzar rizomas
  ⚠️ Imazapir: aplicar ANTES de heladas (requiere actividad metabólica para translocación)
  ⚠️ Imazapir: planificar cuidadosamente rotación siguiente (persistencia en suelo limita cultivos inmediatos)
  ⚠️ Imazapir: menos eficaz post-cosecha de maíz/sorgo por cantidad de rastrojo que impide llegada al blanco
  ⚠️ Alternativa: usar híbridos/variedades tolerantes a imidazolinonas para ampliar opciones de manejo

>> PRIMAVERA (2-3 momentos escalonados):
Desde fines de septiembre, rebrotes de rizomas + nuevas plántulas de semilla emergen desde octubre.
OBJETIVO: intervenir con plantas ≤10-15 cm de diámetro (máxima susceptibilidad).

PRIMERA APLICACIÓN PRIMAVERAL — Base + acompañante residual:
⚠️ Base obligatoria: Glifosato + 2,4D
⚠️ Priorizar acompañante con efecto RESIDUAL — los flujos de emergencia de Commelina van de octubre a principios de febrero
⚠️ Elegir acompañante en función del cultivo siguiente a sembrar

Acompañantes según eficacia (ensayos de campo — Fuente: REM Aapresid 2025):

HPPD — promedio 72% de control:
- Biciclopirona 20% 1000 cc/ha → MEJOR de este grupo (84% en ensayos individuales)
- Mesotrione 48% (0,3 l) — POE maleza, PRE-POE maíz
- Tembotrione 42% — POE maleza, POE maíz
- Topramezone 33,6% — POE maleza, POE maíz
- Tolpiralate 42% — POE maleza, POE maíz

ALS — promedio 64% de control:
- Diclosulam 84% 30-40 g/ha → MEJOR de este grupo (84% en ensayos — PRE-POE soja, PRE maíz)
- Imazetapir 10% — PRE-POE maíz y soja
- Iodosulfurón+Thiencarbazone — PRE-POE maleza, PRE maíz, PRE* soja STS
- Nicosulfuron — POE maleza, POE maíz

PPO — promedio 63% de control:
- Flumioxazin 48% 150 cc/ha → MEJOR de este grupo (PRE maleza, PSI maíz, PRE soja)
- Saflufenacil 70% — POE maleza, PSI maíz, PRE soja
- Trifludiomoxazín — POE maleza, PSI maíz, PRE soja
- Carfentrazone 40% 100 cc/ha — POE maleza, PSI maíz, PRE soja
- Epirefenacil 5,5% 600 cc/ha — POE maleza, PSI maíz, PSI soja
- Sulfentrazone 50% — PRE maleza, PRE maíz, PRE soja
- Lactofen 24% — POE maleza/maíz, POE soja
- Piraflufen — POE maleza, PSI maíz, PSI soja

TRIAZINAS — promedio 59% de control:
- Metribuzin 48% 0,8-1 l/ha → mejor desempeño de este grupo (PRE-POE maleza, PRE soja)
- Amicarbazone 70% 0,4-0,5 kg/ha → mejor desempeño (PRE-POE maleza, PSI maíz)
- Atrazina 90% — PRE-POE maleza, PRE-POE maíz

OTRAS (sin efecto residual, solo acompañantes de contacto):
- Trifludimoxazin + Saflufenacil (Voraxor) 150-200 cc/ha — buen control pero sin residualidad
- Carfentrazone 40% 100 cc/ha
- Dicamba al 57,8% 200-300 cc/ha
- Glufosinato de amonio 28% 2500 cc/ha (formulación 28%)

NOTA SOBRE RESIDUALES COMBINADOS:
- Residuales solos (aplicación individual): 50-60% de control
- Residuales en mezcla o solapados en el tiempo: hasta 80% → combinar modos de acción

DESECANTE ÚNICO (sin residualidad, control ≤70%):
- Paraquat 27,6% (Gramoxone) + Atrazina 90% — NO supera 70%, cantidad considerable de plantas sobrevive

DOBLE GOLPE (DG) — Aplicación secuencial:
Estrategia de mayor eficacia: 1° aplicación sistémica + 2° aplicación desecante, con intervalo acotado.
- CUANTO MEJOR SEA LA 1° APLICACIÓN → mejor resultado del doble golpe total
- 2° aplicación: Paraquat 27,6% (Gramoxone) o Glufosinato de amonio 28% 2500-3000 cc/ha
- Agregar activo a la 2° aplicación no mejoró significativamente la performance de los desecantes de contacto
- Incluir adyuvante de buena calidad (penetración + translocación) → especialmente importante en plantas con cutículas cerosas

ESTRATEGIA POR BIOTIPO DE CULTIVO:

SOJA RR (solo glifosato):
⚠️ Glifosato solo: <30% de control. Control efectivo pre-siembra obligatorio. Sin herramientas eficaces en POE.

SOJA ENLIST:
- POE dentro del cultivo: Glufosinato + Glifosato + 2,4D → >80% de control
- Amplía la ventana de acción y mejora resultado del doble golpe

MAÍZ ENLIST:
- Mismos principios que soja Enlist → muy buenos niveles de control en POE

MAÍZ SIN ENLIST:
- Estrategia más eficaz: HPPD + Triazina como aplicación secuencial POE
- ⚠️ Para máximo potencial: 1° aplicación PRE-siembra con residual que limite nacimientos tempranos
- HPPD + Triazina como tratamiento simple (sin intervención previa) en cultivo emergido: rara vez supera 60%

CONSIDERACIONES AGRONÓMICAS CLAVE:
- Usar adyuvante de calidad en todas las aplicaciones (hojas cerosas)
- Aplicar POE con plantas en estadios iniciales: idealmente ≤10-15 cm de diámetro
- No depender de una aplicación aislada: planificar la secuencia completa de la campaña
- Definir tecnología del cultivo siguiente ANTES de elegir herbicidas (condiciona activos y estrategia DG)


--- TRÉBOL BLANCO (Trifolium repens): ESTRATEGIA DE CONTROL EN BARBECHO ---
Fuente: Corteva Agriscience, Manual Barbecho Quimico / Ensayos EEA INTA Oliveros / Marbete Starane Xtra SENASA No.35.712.

BIOLOGÍA Y DIFICULTAD DE CONTROL:
- Perenne por stolones (tallos rastreros que enraízan en nudos) — el control foliar no elimina la planta si no se transloca a stolones
- Alta producción de semillas con dormición prolongada en el suelo
- Muy competitiva en barbechos húmedos y suelos fértiles
- Momento óptimo de control: follaje joven, receptivo, en activo crecimiento (NO en estrés hídrico ni frío intenso)

CONTROL QUÍMICO EN BARBECHO:

OPCIÓN PRINCIPAL (mejor desempeño en ensayos INTA Oliveros + Manual Corteva):
- Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha
  Sin carencia previa a siembra de cultivos. Glifosato actua en hojas; fluroxipir se transloca a stolones.
  Cultivos en rotacion: soja 3 DAS, girasol/algodon 10 DAS, maiz/trigo sin restriccion.

OPCIÓN CON PPO (refuerzo de quemado sobre follaje):
- Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha + Saflufenacil 70% (Heat) 25-35g/ha
  Saflufenacil suma efecto de contacto/quemado rapido sobre follaje. Combinar modos de accion.

OPCIÓN MARBETE (dosis estandar):
- Glifosato 48% (3 l/ha) [=1440 g.e.a./ha] + Fluroxipir 33% (Starane Xtra) 360 cc/ha
  Marbete Starane Xtra — uso en barbecho quimico presiembra trigo.

⚠️ CONDICIONES PARA ÉXITO:
- Trebol con suficiente follaje joven y receptivo (activo crecimiento)
- No aplicar con estres hidrico severo ni temperaturas <10°C
- El fluroxipir necesita translocarse hasta los stolones — requiere buena absorcion foliar
- En reinfestation por semillas del banco: planificar 2da aplicacion o residual PEE



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
- Sulfentrazone 10%/S-metolacloro 60% (2,5l) — premezclado
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
- Flumioxazin 4,2%/Acetoclor 90% (1,5l) (Harness) — premezclado 7 DAS
- Sulfentrazone 50% (0,4l) (Authority/Capaz) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Sulfometurón 30,7% (0,25l) 7 DAS SOJAS STS
- Sulfometurón 15%+Clorimurón 20% (0,1kg) (Ligate) + Sulfentrazone 50% (0,5l) (Authority/Capaz) SOJAS STS
- Metribuzin 14,9%/S-metolacloro 62,8% (2,5l) (Boundary Syngenta)
- Fomesafén 50% (0,4-0,5l) + Metribuzin 48% (0,8-1l) (Sencorex) + Acetoclor 90% (1,5l) (Harness)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)

POST-EMERGENCIA CULTIVO (V4-V6) — Aplicar sobre cultivo emergido:
- Fomesafén 25% (1-1,5l) (Flex)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Cletodim 24% (0,7-1l) (Select); Cletodim 36% (0,5-0,7 l/ha) (Select 36)
- Piroxasulfone 85% (0,16-0,2 kg/ha) (Yamato) hasta V4 o V8
- Fomesafén 25% (1-1,5l) (Flex) + Benazolín 50% (0,8l) (Dasen)
- Fomesafén 25% (1-1,5l) (Flex) + 2,4DB 97% e.a. (0,04l)
- Fomesafén 11,95%/S-metolacloro 51,8% (1,5-2,5l) — premezclado
- Fomesafén 25% (1-1,5l) (Flex) + Benazolín 50% (0,015kg) (Dasen)
- Fomesafén 25% (1-1,5l) (Flex) + Clorimurón 25% (0,03kg) (Classic)
- Clorimurón 25% (0,04-0,05kg) (Classic)
- Cloransulam 84% (0,04-0,05kg) (Pacto)
- Imazetapir 10% (0,5-0,8l) (Pivot)
- 2,4DB 97% e.a. (0,04l) + Bentazón 60% (0,8-1l) (Basagran)
- Cletodim 24% (0,7-1l) (Select); Cletodim 36% (0,5-0,7 l/ha) (Select 36)
- Benazolín 50% (0,6l) (Dasen) + Clorimurón 25% (0,03g) (Classic)
- Benazolín 50% (0,6l) (Dasen) + Diclosulam 84% (0,015g) (Spider)

--- SOJA: COMMELINA ERECTA ---
⚠️ Ver también sección "CONSIDERACIONES GENERALES DE MANEJO — COMMELINA ERECTA" para biología, estrategia de otoño y primavera completa, tabla de acompañantes y doble golpe.

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
⚠️ NOTA: + indica mezcla de tanque. // indica Doble Golpe (~7 días entre aplicaciones). () = producto premezclado.
⚠️ Sin control total — estas son las mejores opciones de quemado disponibles.

CON GLIFOSATO — Aplicación única:
- Glifosato 1260 g.e.a. + 2,4D (1-1,5l éster ethyl hexyl) + Saflufenacil 70% (40g) (Heat)
- Glifosato + 2,4D + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D + Flumioxazin 48% (150cc) (Sumisoya)
- Glifosato + 2,4D + (Iodosulfurón/Thiencarbazone) (30-45g) 30-45 DAS
- Glifosato + 2,4D + Imazetapir 10% (0,8-1l) (Pivot)
- Glifosato + 2,4D + (Trifludimoxazin/Saflufenacil) (0,1-0,2l) (Voraxor)
- Glifosato + 2,4D + Metribuzin 48% (0,8-1l) (Sencorex)
- Glifosato + 2,4D + Amicarbazone 70% (0,4g) (Dinamic) — hasta 45 DAS

CON GLUFOSINATO — Aplicación única (verde = opción en biotipos RG resistentes a glifosato):
- Glufosinato de amonio 28% (2,5l) + 2,4D
- Glufosinato de amonio 28% + 2,4D + Metribuzin 48% (0,8-1l) (Sencorex)
- Glufosinato de amonio 28% + 2,4D + Amicarbazone 70% (0,4g) (Dinamic) — hasta 45 DAS
- Glufosinato de amonio 28% + 2,4D + Saflufenacil 70% (Heat)
- Glufosinato de amonio 28% + 2,4D + Saflufenacil 70% (Heat) + Flumioxazin 48% (Sumisoya)
- Glufosinato de amonio 28% + 2,4D + Carfentrazone 40% (Shark)
- Glufosinato de amonio 28% + 2,4D + Epirefenacil 5,5% (Empera)
- Glufosinato de amonio 28% + 2,4D + Flumioxazin 48% (Sumisoya)
- Glufosinato de amonio 28% + 2,4D + (Trifludimoxazin/Saflufenacil) (Voraxor)

DOBLE GOLPE — 1° aplicación sistémica + 2° desecante ~7 días después:
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (Gramoxone)
- 1° Glifosato + 2,4D // 2° DG Glufosinato de amonio 28%
- 1° Glifosato + 2,4D // 2° DG (Paraquat 27,6% + Atrazina 90%) — hasta 40 DAS
- 1° Glifosato + 2,4D // 2° DG (Glufosinato + Atrazina 90%) — hasta 40 DAS
- 1° Glifosato + 2,4D // 2° DG (Glufosinato + Saflufenacil 70%) (Heat)
- 1° Glifosato + 2,4D // 2° DG (Glufosinato + Carfentrazone 40%) (Shark)
- 1° Glifosato + 2,4D // 2° DG (Glufosinato + Epirefenacil 5,5%) (Empera)
- 1° Glifosato + 2,4D + Dicamba 57,1% (0,2l) // 2° DG (Paraquat + Atrazina) — hasta 40 DAS
- 1° Glufosinato 28% + 2,4D // 2° DG Paraquat 27,6% (Gramoxone) (2-3l)
- 1° Glufosinato 28% + 2,4D // 2° DG (Glufosinato + Saflufenacil)
- 1° Glufosinato 28% + 2,4D // 2° DG (Glufosinato + Carfentrazone)
- 1° Glufosinato 28% + 2,4D // 2° DG (Trifludimoxazin/Saflufenacil) (Voraxor)

SIN DOBLE GOLPE — Paraquat único:
- Paraquat 27,6% (Gramoxone) + 2,4D + Atrazina 90% — hasta 40 DAS

NOTA: Mejores opciones de quemado disponibles. Sin control total garantizado.
SOJAS RESISTENTES GLIFOSATO: Sin opciones efectivas

SOJAS ENLIST:
- Glifosato 1260 g.e.a. + Glufosinato de amonio 28% + 2,4D 30% e.a. (1,5-2l) — hasta V4-V6
- Glufosinato de amonio / 2,4D 30% e.a. (1,5-2l) V4-V6
- Agregar Sulfato de Amonio 1,5-2 l/ha en mezclas con Glufosinato

--- SOJA: CRUCIFERAS ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato + 2,4D (carencia v.s.f.)
- Glifosato + MCPA 28% (1,5-2,5l)
- Glifosato + 2,4D + Dicamba — 25 DAS
- Glifosato + 2,4D o MCPA + Saflufenacil 70% (35-40g) (Heat)
- Glifosato + 2,4D o MCPA + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D o MCPA + Piraflufén 2,5% (200cc) (Stagger)
- Glifosato + 2,4D o MCPA + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D o MCPA + (Trifludimoxazin/Saflufenacil) (0,1-0,15l) (Voraxor)
- Glufosinato de amonio 28% (1-2,5l) + 2,4D
- Glufosinato de amonio 28% + 2,4D + Saflufenacil 70% (Heat)
- Glufosinato de amonio 28% + 2,4D + Carfentrazone 40% (Shark)
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 1° Glifosato + 2,4D // 2° DG Glufosinato de amonio 28%

MALEZA PEE BARBECHO LARGO — Aplicar sobre suelo sin maleza emergida (PEE maleza):
- Atrazina 90% (1kg) hasta 30 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (0,8-1kg) (Terbine/Gesatop) desde 45-60 DAS desde primera lluvia
- Flurocloridona 25% (1,5l) (Rainbow) hasta 45 DAS
- Biciclopirona 20% (0,5l) / Atrazina 90% (0,5kg) 120 DAS
- Diflufenicán 50% (0,3l) (Brodal)
- Flumioxazin 48% (0,1-0,15l) (Sumisoya)
- Terbutilazina 50% / Flumioxazin 3,8% (1,15-1,25l) 30 DAS

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Metribuzin 48% (0,8-1kg) (Sencorex)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz)
- Flumioxazin 48% (0,1-0,15l) (Sumisoya) 7 DAS
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) 15 DAS
- Fomesafén 11,9%/S-metolacloro 51,8% (2,5l) — premezclado
- Flumioxazin 15% / Piroxasulfone 34,5% (0,3l/0,1l) 7 DAS
- Sulfentrazone 50% / Diflufenicán 50% (0,3l/0,3l) 15 DAS
- Trifludimoxazin 12,5%/Saflufenacil 25% (Voraxor) (0,1-0,2l) 7 DAS

POST-EMERGENCIA CULTIVO — Aplicar sobre cultivo emergido (Soja RR o No GMO):
CONDICIÓN CLAVE: Maleza en ROSETA PEQUEÑA (5-8 cm). Con rosetas grandes la eficacia cae drásticamente.
- Fomesafén 25% (1-1,5l) (Flex) — PPO, eficaz con roseta 5-8 cm
- Acifluorfén 24% (1-1,5l) (Blazer) — PPO, eficaz con roseta 5-8 cm
- Lactofén 24% (0,6-0,8l) (Cobra) — PPO, eficaz con roseta 5-8 cm
- Fomesafén 25% (1-1,5l) (Flex) + Benazolín 50% (0,6l) (Dasen)
- Bentazón 60% (1,5l) (Basagran) — Fotosistema II, alternativa POE precoz
- Imazetapir 10% (0,5-0,8l) (Pivot) + Clorimurón 25% (0,04kg) (Classic)
ADVERTENCIA: En biotipos con resistencia a ALS no usar sulfonilureas ni imidazolinonas.
ADVERTENCIA: El glifosato solo tiene control muy limitado en biotipos susceptibles; insuficiente en resistentes.

SOJAS ENLIST — DOBLE GOLPE POSIBLE DENTRO DEL CULTIVO:
El sinergismo glufosinato + 2,4D permite hacer doble golpe dentro del cultivo (herramienta diferencial).
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) + 2,4D 30% e.a. (1,5-2l) hasta V4-V6 — mejor opción

--- SOJA: PARIETARIA ---

BARBECHO LARGO — Aplicar sobre suelo o maleza en distintos estadios:
- Atrazina 90% (1-1,5kg) PEE-POST MALEZA hasta 60 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS PEE-POST MALEZA
- Terbutilazina 75% (0,8-1kg) (Terbine/Gesatop) hasta 45 DAS PEE-POST MALEZA
- Metsulfurón 60% (6-8g) hasta 60 DAS PEE MALEZA
- Metsulfurón/Clorsulfurón (12-15g) (Finesse WG) SOJAS STS o hasta 150 DAS PEE MALEZA
- Biciclopirona 20% (0,5l) + Atrazina 90% (0,5kg) 120 DAS PEE-POST MALEZA
- Flumioxazin 48% (0,1-0,15l) (Sumisoya) PEE-POST MALEZA
- Terbutilazina 75% (1kg) (Terbine/Gesatop) + Flumioxazin 48% (0,12l) (Sumisoya) PEE-POST MALEZA — o (Terbyne Max Sipcam)

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Atrazina 90% (0,5kg) PEE-POST MALEZA hasta 30 DAS
- Metribuzin 48% (0,8-1l) (Sencorex) PEE-POST MALEZA
- Prometrina 48% (1,5-2l) (Gesagard) PEE-POST MALEZA
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) + Metribuzin 48% (0,8-1l) (Sencorex) PEE-POST MALEZA
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) + Atrazina 90% (0,5kg) hasta 30 DAS
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) + Prometrina 48% (1,5-2l) (Gesagard)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) + Flumioxazin 48% (0,1-0,15l) (Sumisoya) 7 DAS
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) + (Trifludimoxazin/Saflufenacil) (0,1-0,2l) (Voraxor) 7 DAS
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) PEE-POST MALEZA 7 DAS
- Glifosato 1260 g.e.a. + Epirefenacil 5,5% (600cc) (Empera) POST MALEZA

POST-EMERGENCIA CULTIVO: Sin opciones efectivas
- Dosis glifosato > 1360 g.e.a. + sulfato de amonio + aceite, controles hasta 60%

--- SOJA: AMARANTHUS SPP. (Yuyo Colorado) ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Epirefenacil 5,5% (600cc) (Empera)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) Acción POE y PEE MALEZA
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 2,4D + Saflufenacil 70% (40g) (Heat)
- 2,4D + Carfentrazone 40% (70-80cc) (Shark)
- 2,4D + Epirefenacil 5,5% (600cc) (Empera)
- Glufosinato de amonio 28% + 2,4D + PPO acompañante a elección:
  opciones PPO: Saflufenacil 70% (Heat) / Flumioxazin 48% (Sumisoya) / Carfentrazone 40% (Shark) / Epirefenacil 5,5% (Empera)

MALEZA PEE BARBECHO INTERMEDIO (45-60 DAS) — Aplicar sobre suelo sin maleza emergida:
- Flumioxazin 48% (150cc) (Sumisoya)
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) hasta 15 DAS
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (1kg) (Terbine/Gesatop) hasta 45 DAS
- Metribuzin 48% (1l) (Sencorex)
- Terbutilazina 75% (1kg) (Terbine/Gesatop) + Flumioxazin 48% (0,25l) (Sumisoya) hasta 45 DAS — o (Terbyne Max Sipcam)

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Metribuzin 10%/S-metolacloro 60% (2,5l) — premezclado
- Sulfentrazone 50% (Authority/Capaz) + Piroxasulfone 48% (0,355l)
- Flumioxazin 15%/Piroxasulfone 34,5% (0,5l) (Fierce FMC) 7 DAS
- Flumioxazin 4,2%/S-metolacloro 84% (1,75l) (Apresa ADAMA) 7 DAS
- Flumioxazin 4,2% / Acetoclor 90% (1,5l) (Harness) 7 DAS
- Fomesafén 11,9% / S-metolacloro 51,8% (2,5l)
- Sulfentrazone 50% (0,4l) (Authority/Capaz) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) + Metribuzin 48% (0,8-1l) (Sencorex) + Acetoclor 90% (1,5l) (Harness)
- (Trifludimoxazin/Saflufenacil) (Voraxor) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)

POST-EMERGENCIA CULTIVO — Aplicar sobre cultivo emergido (Sojas Resistentes Glifosato):
- Fomesafén 25% (1-1,5l) (Flex)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Benazolín 50% (0,6-1l) (Dasen)
- Fomesafén 25% (Flex) / Benazolín 50% (0,6l) (Dasen)
- Fomesafén 11,9% / S-metolacloro 51,8% (1,5-2l)

SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) / 2,4D 30% e.a. (1,5-2l) hasta V4-V6


=== MAÍZ ===

--- MAÍZ: AMARANTHUS SPP. ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Picloram (0,1-0,15l)
- Epirefenacil 5,5% (600cc) (Empera)
- Trifludimoxazin / Saflufenacil (0,15-0,2l) Acción POE y PEE MALEZA 7 DAS
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 2,4D + Carfentrazone 40% (70-80cc) (Shark)
- 2,4D + PPO acompañante a elección:
  opciones PPO: Epirefenacil 5,5% (Empera) / Saflufenacil 70% (Heat) / Carfentrazone 40% (Shark) / Flumioxazin 48% (Sumisoya) / (Trifludimoxazin/Saflufenacil) (Voraxor)

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Atrazina 90% (1-2kg) + S-metolacloro 96% (1,1-1,3l) (Dual Gold) — o premezclado (BicepPack Gold)
- Atrazina 90% (1-2kg) + Biciclopirona 20% (0,8-1l)
- Biciclopirona 20% (0,8-1l) + S-metolacloro 96% (1,1-1,3l) (Dual Gold) — premezclado (Acuron Pack)
- Biciclopirona 20% (0,8-1l) + Piroxasulfone 85% (0,2kg)
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Terbutilazina 75% (0,8-1kg) (Terbine/Gesatop) + Piroxasulfone 85% (0,16-0,2kg) (Yamato)
- Terbutilazina 50% (0,8-1kg) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Mesotrione 48% (0,3l) (Callisto) + Piroxasulfone 85% (0,16-0,2kg) (Yamato)
- Trifludimoxazin 8,1% (1,77-2,2l) + S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Flumioxazin 4,2%/Acetoclor 90% (1,5l) — premezclado
- (Isoxaflutole/Thiencarbazone) (0,3-0,4l) (Adengo) + S-metolacloro 96% (Dual Gold) + Atrazina 90%

POST-EMERGENCIA CULTIVO (V2-V8) — Aplicar sobre cultivo emergido:
- Atrazina 90% (1kg) + 2,4D 64,3% e.a. (0,4l)
- Atrazina 90% (1kg) + Picloram 24% (0,1-0,15l)
- Atrazina 90% (1kg) + Mesotrione 48% (0,3l) (Callisto)
- Atrazina 90% (1kg) + Topramezone 33,6% (0,1l) (Convey)
- Atrazina 90% (1kg) + Tolpyralate 42% (0,075-0,125l) (Brucia)
- Atrazina 90% (1kg) + Tembotrione 42% (0,25-0,3l) (Laudis)
- Terbutilazina 55%/Mesotrione 8,1% (2l) (premezclado) + Atrazina 90% (1kg)

MAÍZ ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V2-V4
- 2,4D 45,6% e.a. (1,5-2l) hasta V8
- Glufosinato de amonio 28% (2-3l) + 2,4D 45,6% e.a. (1,5-2l) V2-V4

CONTROL QUÍMICO YUYO COLORADO EN MAÍZ (detallado):

ACCIÓN SOBRE MALEZA NACIDA / CULTIVO AÚN NO SEMBRADO (POE maleza / PSI cultivo):
- 2,4D (3-5 DAS) Hormonal
- 2,4D sal colina 66,9% (1,5-2,5l) Maíz ENLIST
- Dicamba 57,7% (0,15-0,2l) Hormonal
- Picloram 27,7% (0,1-0,15l)
- Paraquat 27,6% (1-3,5l) (Gramoxone) Fot.I
- Saflufenacil 70% (35g) (Heat) PPO
- Carfentrazone 40% (50-75cc) PPO
- Piraflufén etil 2,5% (150-200cc) (Stagger) PPO
- Oxifluorfén 24% (0,25-0,3l) (Galigan) PPO
- Glifosato (dosis v.s.f.) EPSPS
- Glufosinato de amonio 28% (1,5-3l)
- Paraquat/diurón (1,5-2,5l)
- Fluroxipyr/halauxifén (400-500cc) (Pixxaro)

ACCIÓN RESIDUAL SOBRE SUELO SIN MALEZA EMERGIDA / CULTIVO AÚN NO SEMBRADO (PEE maleza / PSI cultivo):
- Atrazina 90% (1,8-2,2kg) (Gesaprim) Fot.II
- Terbutilazina 75% (1,3-1,5kg) (Terbine) Fot.II
- Amicarbazone 70% (0,4-0,7) Dinamic Fot.II
- Linurón 50% (2-3l) (Afalon) Fot.II
- S-metolacloro 96% (0,8-1,6l) Dual Gold
- Acetoclor 90% (2-3l) (Harness)
- Piroxazulfone 85% (0,16-0,2kg) Yamato 15 DAS
- Dimetenamida 90% (1,2-1,8l) (Frontier)
- Diflufenicán 50% (0,2-0,3l)
- Biciclopirona 20% (0,75-1l) (Acuron Uno)
- Flurocloridona 25% (0,75-1,5l) (Rainbow)
- Piroxasulfone/Saflufenacil (Zidua Pack) - también POE maleza
- Piroxasulfone/Flumioxazin (Fierce) 10-15 DAS
- Atrazina/S-metolacloro (BicepPack Gold)
- Isoxaflutole/Thiencarbazone (Adengo)

ACCIÓN SOBRE MALEZA NACIDA / CULTIVO EMERGIDO (POE maleza / POE cultivo V2-V8):
⚠️ Malezas <5cm, evitar estrés:
- Atrazina 90% (1,5-2kg) (Gesaprim) hasta V6
- Bentazón 60% (1,2-1,6l) (Basagran) V2-V8 (cotiledonar)
- Metribuzin 70% (210-270g) Tribune hasta V2-V8
- Linurón 50% (2-2,5l) (Afalon) tratamientos en bandas
- 2,4D V2-V8 Hormonal
- 2,4D sal colina 66,9% (1,5-2,5l) V1-V8 Maíz ENLIST
- Dicamba 57,7% (0,15-0,2l) V2-V8
- Picloram 27,7% (0,1-0,15l) V2-V8
- MCPA 28% (1,5l) V2-V8
- Mesotrione 48% (0,3l) (Callisto) V2-V6
- Topramezone 33,6% (0,08-0,1l) (Convey) V1-V7
- Tolpyralate 40% (0,075-0,125l) (Brucia) V3-V6
- Tembotrione 42% (0,25-0,3l) (Laudis) V3-V6
- Glufosinato de amonio 28% (1,8-2l) Maíz ENLIST V1-V8
- Pendimetalín 33% (2,5-4l) (Herbadox) V3-V4 Maleza no emergida


--- MAÍZ: CRUCIFERAS ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Brasicáceas o Crucíferas. Junio 2024.
ADVERTENCIA: Ver también sección CONSIDERACIONES GENERALES DE MANEJO — BRASICACEAS para biología, flujos de emergencia y resistencias.

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato + 2,4D o MCPA — base en biotipos susceptibles
- Glifosato + 2,4D o MCPA + PPO (saflufenacil/carfentrazone/piraflufen) — con resistencia a hormonales o para mejorar control
- Glifosato + 2,4D o MCPA + Fotosistema II (atrazina/metribuzin/amicarbazone)
- Glifosato + 2,4D o MCPA + HPPD/PDS (biciclopirona/mesotrione/diflufenicán)
- Glufosinato de amonio 28% (1,5-3l) — opción si las malezas acompañantes lo permiten
- Paraquat 27,6% (Gramoxone) — desecante para DG o aplicación directa
ADVERTENCIA: Con resistencia a ALS no usar sulfonilureas ni imidazolinonas. Con biotipos resistentes a glifosato agregar PPO quemante.

PEE / PSI CULTIVO — Residuales antes de emergencia del cultivo:
- Atrazina 90% (1-2kg) (Gesaprim) — Fotosistema II
- Terbutilazina 75% (1-1,3kg) (Terbine/Gesatop) — Fotosistema II
- Amicarbazone 70% (0,4-0,7kg) (Dinamic) — Fotosistema II
- Metribuzin 70% (Tribune) — Fotosistema II
- Flurocloridona 25% (0,75-1,5l) (Rainbow) — PDS, muy eficaz en crucíferas
- Diflufenicán 50% (0,2-0,3l) (Brodal) — PDS
- Biciclopirona 20% (0,75-1l) — HPPD
- Flumioxazin 48% (Sumisoya) — PPO
- Pyroxasulfone 85% (0,16-0,2kg) (Yamato) — VLCFA
Ver también sección MAÍZ: AMARANTHUS SPP. para combinaciones de residuales.

POST-EMERGENCIA CULTIVO (V2-V8) — Aplicar sobre cultivo emergido:
CONDICIÓN CLAVE: En biotipos susceptibles, MCPA y 2,4D son los hormonales de elección. Mezclar con HPPD sinergiza el quemado sobre la maleza.
- MCPA 28% (1,5l) + Atrazina 90% (1kg) — V2-V8. Base clásica maíz convencional.
- 2,4D 64,3% e.a. + Atrazina 90% (1kg) — V2-V8
- Mesotrione 48% (0,3l) (Callisto) + Atrazina 90% (1kg) — sinergismo HPPD+Triazina, excelente sobre crucíferas pequeñas
- Topramezone 33,6% (0,08-0,1l) (Convey) + Atrazina 90% (1kg) — V1-V7
- Tembotrione 42% (0,25-0,3l) (Laudis) + Atrazina 90% (1kg) — V3-V6
- Tolpyralate 40% (0,075-0,125l) (Brucia) + Atrazina 90% (1kg) — V3-V6
ADVERTENCIA: Los HPPD deben mezclarse siempre con atrazina o terbutilazina para sinergizar el control.
ADVERTENCIA: En biotipos resistentes a hormonales o ALS, priorizar HPPD+Triazina como POE.

MAÍZ ENLIST — POE:
- Glufosinato de amonio 28% (1,8-2l) V1-V8 — excelente sobre crucíferas, mismos principios que soja Enlist
- 2,4D 45,6% e.a. (1,5-2l) hasta V8
- Glufosinato 28% + 2,4D 45,6% e.a. (1,5-2l) V2-V4 — doble golpe dentro del cultivo

=== GIRASOL ===

--- GIRASOL: CRUCIFERAS ---
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Brasicáceas o Crucíferas. Junio 2024.
ADVERTENCIA: Ver también sección CONSIDERACIONES GENERALES DE MANEJO — BRASICACEAS para biología, flujos de emergencia y resistencias.
ADVERTENCIA: Crucíferas resistentes a nabón/nabo (Raphanus sativus/Brassica rapa) generan pérdidas de girasol de hasta 79% con más de 30 pl/m2. El control previo a la siembra es crítico.

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza):
Mismas opciones que la estrategia transversal de barbecho (ver sección BRASICACEAS CONSIDERACIONES GENERALES).
- Glifosato + 2,4D + PPO (saflufenacil/carfentrazone/piraflufen) — primera opción en lotes con problemas
- Doble golpe en rosetas grandes: sistémico + paraquat/diquat
ADVERTENCIA: Dicamba: respetar 45 DAS antes de siembra de girasol. 2,4D: 20 DAS.

PEE — Residuales antes de emergencia del cultivo:
Ver sección GIRASOL: MALEZA GENERAL para opciones residuales por mecanismo de acción.
Crucíferas específicamente:
- Flurocloridona 25% (Rainbow) — PDS, muy eficaz pero biotipos resistentes ya presentes en zona. Combinar con Diflufenicán (Brodal) en zonas con sospecha de resistencia.
- Diflufenicán 50% (Brodal) — PDS, complementario
- Flumioxazin 48% (Sumisoya) — PPO
- Prometrina 50% (Gesagard) — Fotosistema II
ADVERTENCIA: Flurocloridona + Diflufenicán cuando hay sospecha de biotipos resistentes a flurocloridona.

POST-EMERGENCIA CULTIVO — Aplicar sobre cultivo emergido:
OPCIONES MUY LIMITADAS en girasol. La clave es llegar limpio desde barbecho+PEE.

GIRASOLES CL (Clearfield):
- Imazapir 80% (Clearsol) V2-V4 — eficaz en biotipos ALS-susceptibles
- Imazapir + Imazamox (Clearsol Plus II) V2-V4 — mejor espectro
- Imazapir + Aclonifén (Prodigio) — la mezcla mejora notablemente la eficacia sobre crucíferas
ADVERTENCIA: En biotipos con resistencia a ALS (nabillo, nabolza, mostacilla resistente) el imazapir NO tiene efecto.

GIRASOLES NO CL:
- Sin opciones específicas hormonales ni ALS (fitotóxicos en girasol)
- La clave es el control preventivo desde barbecho y PEE
- Crucíferas que escapan: evaluar intervención mecánica o manual en manchones

--- GIRASOL: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI-PEE cultivo):
⚠️ Barbecho cumple doble rol en girasol: control de malezas otoño-invernales + acumulación de agua en perfil
⚠️ Fluroxipir y Halauxifén: seguridad de uso hasta la siembra (1 DAS = sin carencia práctica)
⚠️ Dicamba: respetar carencia de 45 DAS antes de siembra
⚠️ 2,4D: respetar carencia 20 DAS, usar formulaciones éster ethyl o microemulsión
⚠️ Trifludimoxazin: suelos >2% MO y textura pesada/mediana → 15 DAS + lluvias >20mm. Suelos <2% MO, >50% arena, pH>7 → 45 DAS + lluvias >50mm
⚠️ Flumioxazin: 30 DAS (50cc/ha) o 45-60 DAS (dosis mayor). Riesgo fitotoxicidad aumenta en suelos arenosos <1% MO

AUXINAS SINTÉTICAS (barbecho):
- 2,4D (20 DAS) — éster ethyl o microemulsión
- Dicamba (Banvel) (45 DAS)
- Fluroxipir (Starane) (1 DAS) — seguro hasta siembra
- Halauxifén (Elevore) (1 DAS) — seguro hasta siembra
- Fluroxipir+Halauxifén (Pixxaro) (1 DAS) — seguro hasta siembra

PPO (barbecho):
- Piraflufen-etil (Stagger) (0 DAS)
- Carfentrazone 40% (Shark) (15 DAS)
- Trifludimoxazin (Vulcarus) (15-45 DAS según suelo — ver ⚠️ arriba) — no usar si se va a aplicar en PEE
- Flumioxazin 48% (Sumisoya/Vesdua) CR — 30 DAS (50cc/ha) o 45-60 DAS (dosis mayor) — no usar si se va a aplicar en PEE

FOTOSISTEMA I (barbecho):
- Diquat 40% (Reglone)
- Paraquat 27,6% (Gramoxone)
- Paraquat/diurón (Cerillo)

EPSPS (barbecho):
- Glifosato (dosis v.s.f.)

INHIB. GLUTAMINO SINT. (barbecho):
- Glufosinato de amonio 28% (Lifeline)

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
⚠️ Dosis muy dependientes de MO, arena, pH y humedad — ajustar por zona, no importar recetas
⚠️ YUYO COLORADO: Sulfentrazone + S-metolacloro o Acetoclor en el límite de fitotoxicidad. En suelos arenosos/baja MO reducir dosis y compensar con Diflufenicán (Brodal) o Flurocloridona (Rainbow)
⚠️ CRUCÍFERAS: Flurocloridona (Rainbow) buena opción pero ya hay biotipos resistentes → combinar con Diflufenicán (Brodal) para sostener eficacia

AUXINAS SINTÉTICAS (PEE):
- Fluroxipir (Starane) (1 DAS) — seguro hasta siembra
- Halauxifén (Elevore) (0 DAS) — seguro hasta siembra
- Fluroxipir+Halauxifén (Pixxaro) (0 DAS) — seguro hasta siembra

PPO (PEE):
- Sulfentrazone 50% (Authority/Capaz/Shutdown) *** ajustar dosis en suelos bajo %MO, textura arenosa y pH>7,5

VLCFA / INH. DIV. CEL. (PEE):
- Acetoclor 90% (Harness)
- S-metolacloro 96% (Dual Gold)
- Metolacloro (dosis v.s.f.)

INH. SINT. MICROT. (PEE):
- Pendimetalín 45,5% (Herbadox)
- Trifluralina 60% (Treflan)

FOTOSISTEMA II (PEE):
- Prometrina 50% (Gesagard)

PDS / INH. CAROTENOIDES (PEE):
- Diflufenicán 50% (Brodal/Pelican L)
- Flurocloridona 25% (Rainbow)
- Flurocloridona 25% (Rainbow) + Diflufenicán 50% (Brodal) — crucíferas con resistencia a flurocloridona

EPSPS (PEE):
- Glifosato (dosis v.s.f.)

FOTOSISTEMA I (PEE):
- Diquat 40% (Reglone)
- Paraquat 27,6% (Gramoxone)

INHIB. GLUTAMINO SINT. (PEE):
- Glufosinato de amonio 28% (Lifeline)

ALS / IMIDAZOLINONAS (PEE — solo girasoles CL):
- Imazapyr 80% (Clearsol) Girasoles CL
- Imazapyr+Imazamox (Clearsol Plus II) Girasoles CL Plus

MEZCLAS (PEE):
- Sulfentrazone 50% (Authority/Capaz) + S-metolacloro 96% (Dual Gold) — mezcla comercial: (Capaz Elite) — yuyo colorado. Dosis ajustada
- Sulfentrazone 50% (Authority/Capaz) + Acetoclor 90% (Harness) — yuyo colorado

POST-EMERGENCIA CULTIVO — Aplicar sobre cultivo emergido:
⚠️ OPCIONES MUY LIMITADAS — la clave es llegar limpio desde barbecho+PEE, no depender del rescate POE
⚠️ Aclonifén (Prodigio): eficaz en yuyo colorado SOLO con plántulas <2cm. Ventana muy estrecha

SDPS (POE):
- Aclonifén 60% (1-1,5l) (Prodigio) — yuyo <2cm, crucíferas pequeñas. NO mezclar con graminicidas

ALS / IMIDAZOLINONAS (POE — solo girasoles CL):
- Imazapyr 80% (Clearsol) V2-V4
- Imazapyr+Imazamox (Clearsol Plus II) V2-V4

ACCasa (POE — gramíneas):
- Haloxyfop-R-metil (Galant Max/Zavobia)
- Propaquizafop (Agil)
- Quizalofop-P-etil (Assure)
- Cletodim (Select/Latium/Traspect)
- Cletodim + Quizalofop-P-etil (Celebrate) — mezcla ACCasa

DESECANTE (madurez fisiológica — POST MF):
- Carfentrazone etil (Shark 40 EC) — POST madurez fisiológica
- Saflufenacil (Heat) — POST madurez fisiológica
⚠️ Saflufenacil solo como desecante POST madurez — NO aplicar en la temporada de cultivo

⚠️ NO USAR en girasol: saflufenacil durante el ciclo (solo como desecante POST MF), fomesafén (275 días + >300mm lluvia acumulada), diclosulam (no sembrar girasol temporada siguiente), biciclopirona, topramezone, sulfonilureas


=== TRIGO ===

--- TRIGO: CONYZA SPP. ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato + 2,4D (v.s.f.)
- Glifosato + Dicamba 57,8% (0,1-0,2l) (Banvel)
- Glifosato + 2,4D + Dicamba
- Glifosato + 2,4D o MCPA + Saflufenacil 70% (35-40g) (Heat)
- Glifosato + 2,4D o MCPA + Carfentrazone 40% (70-80cc) (Shark)
- Glifosato + 2,4D o MCPA + Piraflufén 2,5% (200cc) (Stagger)
- Glifosato + 2,4D o MCPA + Epirefenacil 5,5% (600cc) (Empera)
- Glifosato + 2,4D o MCPA + (Trifludimoxazin/Saflufenacil) (0,1-0,15l) (Voraxor)
- Glufosinato de amonio 28% + 2,4D + PPO acompañante:
  opciones PPO: Saflufenacil 70% (Heat) / Carfentrazone 40% (Shark)
- 1° Glifosato + 2,4D // 2° DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 1° Glifosato + 2,4D // 2° DG Glufosinato de amonio 28%

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre suelo sin maleza emergida (PEE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Metsulfurón 60% (8-10g) (Ally)
- Metsulfurón/Clorsulfurón (12-15g) (Finesse WG)
- Flumioxazin 48% (0,15l) (Sumisoya) 10 DAS
- Terbutrina 50% (1,2l) (Igran)
- Terbutilazina 75% (1kg) (Terbine/Gesatop)
- Amicarbazone (sin registro) (Dinamic)
- Terbutilazina 50%/Flumioxazin 3,8% (1,5l) (Terbyne Max Sipcam) 15 DAS
- Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)

POST-EMERGENCIA CULTIVO (estadio Z2.1-Z3.0) — Aplicar sobre cultivo emergido en macollaje:
- Metsulfurón 60% (5-6g) (Errasin WP/Ally) + Dicamba 57,8% (0,1-0,15l) (Banvel)
- Metsulfurón 30% + Aminopyralid 44% (2 bolsas 67g/ha) (Tronador Xtra)
- Metsulfurón/Clorsulfurón (10-12g) (Finesse WG) + Dicamba 57,8% (0,4l) (Banvel)
- Metsulfurón/Clorsulfurón (10-12g) (Finesse WG) + 2,4D 64,3% e.a. (0,4l)
- 2,4D 64,3% e.a. (0,4l) + Dicamba 57,8% (0,1-0,15l) (Banvel)
- 2,4D 64,3% e.a. (0,4l) + Picloram 24% (0,1-0,12l) (Tordón)
- 2,4D 64,3% e.a. (0,4l) + Fluroxipir 48% (0,2-0,4l) (Starane)
- 2,4D 64,3% e.a. (0,4l) + Carfentrazone 40% (0,04l) (Shark)
- 2,4D 64,3% e.a. (0,4l) + Terbutrina 50% (0,8-1l) (Igran)
- 2,4D 64,3% e.a. (0,4l) + Saflufenacil 70% (25g) (Heat)
- Saflufenacil 70% (25g) (Heat) solo — registro POE trigo confirmado BASF Argentina. Malezas ≤10cm
- 2,4D 64,3% e.a. (0,4l) + Diflufenicán 50% (0,15l) (Brodal)
- 2,4D 64,3% e.a. (0,4l) + Metribuzin 48% (0,4l) (Sencorex)
- 2,4D 64,3% e.a. (0,4l) + Piraflufén 2,5% (0,08l) (Stagger)
- Clopyralid / MCPA (1,25-1,35l) (Lontrel)
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / 2,4D 64,3% e.a. (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Metribuzin 48% (0,4l) (Sencorex) Trigos HB4
- Glufosinato de amonio 28% (2-3l) // DG Glufosinato de amonio 28% (2-3l) Trigos HB4

⚠️ CONSIDERACIONES: Evitar repetir mecanismos de acción. Usar coadyuvantes. Control POE con malezas pequeñas. Evitar aplicaciones con estrés por frío o falta de agua.
⚠️ VENTANA DE APLICACIÓN POR PRINCIPIO ACTIVO (desde estado de hojas):
- Bromoxinil (Bromotril): desde Z1.2 (2-3 hojas). Marbete ADAMA SENASA No.30.009.
- MCPA 28%: desde Z1.3-Z1.5 (3-5 hojas) hasta primer nudo encane. Marbete Sumitomo SENASA No.34.567.
- Saflufenacil (Heat) 25g/ha: desde Z1.2-Z1.3 (2-3 hojas) SIN aceite. Puede mezclarse con CUALQUIER hormonal.
- Fluroxipir 33% (Starane Xtra): desde Z1.3 (3 hojas) hasta hoja bandera visible (Z3.9). Marbete Corteva SENASA No.35.712.
- Dicamba 48% (Banvel/Dicamba Sigma): desde inicio del cultivo hasta fin macollaje. Marbete Sigma SENASA No.38.176.
- Metsulfuron (Errasin WP/Ally): desde Z1.3 (3 hojas) hasta encanzaon. Marbete Chemotecnica SENASA No.38.939.
- 2,4D y sulfonilureas (Metsulfuron a dosis plena): desde Z2.1 (macollaje) hasta encanzaon.
- Para gramineas (raigras): Axial desde Z1.3 (3 hojas), Hussar Plus desde Z1.2 (2 hojas), Topick desde Z1.2-Z1.3.
  REGLA SAFLUFENACIL: 25g/ha + cualquier hormonal desde Z1.2 en adelante = sinergia sistémico+contacto. Sin aceite en estado de hojas.
--- TRIGO: CRUCIFERAS ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato / 2,4D (v.s.f.)
- Glifosato / MCPA 28% (1,5-2,5l)
- Glifosato / 2,4D + Dicamba
- Glifosato / 2,4D o MCPA / Saflufenacil 70% (35-40g) (Heat)
- Glifosato / 2,4D o MCPA / Carfentrazone 40% (70-80cc) (Shark)
- Glifosato / 2,4D o MCPA / Piraflufén 2,5% (200cc) (Stagger)
- Glifosato / 2,4D o MCPA / Tiafenacil 70% (35-50g)
- Glifosato / 2,4D o MCPA / Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)
- Glufosinato de amonio 28% (1-2,5l) / 2,4D
- Glifosato / 2,4D // DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre suelo sin maleza emergida (PEE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Flurocloridona 25% (1,5l) (Rainbow)
- Diflufenicán 50% (0,3l) (Brodal)
- Flumioxazin 48% (0,12l) (Sumisoya) 10 DAS
- Piroxasulfone 85% (0,12kg)
- Flurocloridona 25% (1,5l) (Rainbow) / Piroxasulfone 48% (0,21l) 15 DAS
- Terbutrina 50% (1,2l) (Igran)
- Terbutilazina 75% (1kg) (Terbine/Gesatop)
- Amicarbazone (sin registro) (Dinamic)
- Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)
- Diflufenicán / Aclonifén / Fluferacet (2-2,25l)

POST-EMERGENCIA CULTIVO — DESDE ESTADO DE HOJAS (Z1.2-Z1.9):
Fuente: Marbete ADAMA Bromotril SENASA No.30.009 / Marbete Sumitomo MCPA 28 SENASA No.34.567 / BASF Heat / Marbete Sigma Agro Dicamba SENASA No.38.176 / Marbete Chemotecnica Errasin WP SENASA No.38.939 / Marbete Corteva Starane Xtra SENASA No.35.712.
REGLA CRITICA: Hay opciones eficaces desde estado de hojas para cruciferas. NO es correcto decir que todo espera al macollaje.

- Bromoxinil 34,6% (0,8-1l) (Bromotril) SOLO — desde Z1.2 (2-3 hojas) hasta fin macollaje. Contacto, eficaz con cruciferas en plantula (3-6 hojas o <10cm roseta). Marbete ADAMA SENASA No.30.009.
- MCPA 28% (1,5-2,5l) SOLO — desde Z1.3-Z1.5 (3-5 hojas) hasta primer nudo encane. Eficaz en biotipos sensibles a hormonales. Marbete Sumitomo SENASA No.34.567.
- Saflufenacil 70% (25g) (Heat) SOLO — desde Z1.2-Z1.3 (2-3 hojas). SIN aceite ni coadyuvante a esta dosis. Malezas crucifera igual o menor a 10cm o roseta igual o menor a 5cm. Con aceite aumenta fitotoxicidad en estado de hojas.
- Bromoxinil (0,5-0,8l) (Bromotril) + MCPA 28% (0,75-1l) — desde Z1.3 (3 hojas). Sinergia contacto+sistemico. Marbete Bromotril admite esta mezcla explicitamente.
- Bromoxinil (0,8-1l) (Bromotril) + Saflufenacil 70% (25g) (Heat) — desde Z1.2 (2-3 hojas). Sin coadyuvante. Buen espectro en cruciferas pequeñas.

- Dicamba 48% (100-150 cc/ha) (Dicamba Sigma / Banvel) SOLO — desde inicio del cultivo hasta fin macollaje. Maleza en 2-4 hojas o rosetas <10cm. Eficaz sobre Conyza, cardos, latifoliadas susceptibles. Marbete Sigma Agro SENASA No.38.176.
  ACLARACION CRITICA: Las cruciferas (nabo, nabon, nabillo, mostacilla) son TOLERANTES/RESISTENTES al dicamba — el dicamba NO controla cruciferas. Usarlo en mezcla cuando hay cruciferas + otras latifoliadas acompanantes (ej. Conyza).
- Dicamba 48% (100-150 cc/ha) + MCPA 28% (700-1000 cc/ha) — desde Z1.4 (4 hojas) hasta fin macollaje. Marbete Dicamba Sigma admite esta mezcla explicitamente. Doble modo de accion hormonal.
- Dicamba 48% (100-150 cc/ha) + Bromoxinil 34,6% (750-1200 cc/ha) (Bromotril) — desde Z1.2 (2-3 hojas) hasta fin macollaje. Marbete Dicamba Sigma admite esta mezcla. Dicamba cubre Conyza y cardos; Bromoxinil cubre cruciferas y otras latifoliadas. Buena combinacion cuando hay mezcla de malezas.
- Dicamba 48% (100-150 cc/ha) + 2,4D ester 100% (240-320 cc/ha) — desde inicio del cultivo hasta fin macollaje. Mezcla clasica hormonal de amplio espectro en latifoliadas susceptibles. Marbete Dicamba Sigma.

- Metsulfuron metil 60% (8-10 g/ha) (Errasin WP / Ally) SOLO — desde Z1.3 (3 hojas) hasta encanzaon. ALS sistemico, muy eficaz en Conyza, cardos, quenopodiaceas, enredaderas. Marbete Chemotecnica SENASA No.38.939.
  ACLARACION CRITICA: Las cruciferas son RESISTENTES a ALS en gran parte de la zona nucleo (nabillo, nabolza, mostacilla, nabon con resistencia ALS confirmada). Verificar biotipo antes de usar como unica opcion en cruciferas.
  Eficaz en: Conyza spp. (rama negra), Chenopodium (quinoa), Polygonum (sanguinaria/enredadera), Stellaria (caapiqui), Lamium (ortiga mansa), cardos susceptibles.
- Metsulfuron 60% (6-7 g/ha) (Errasin WP / Ally) + Dicamba 48% (100 cc/ha) — desde Z1.3 (3 hojas) hasta encanzaon. Mezcla explicita en marbete Errasin. Doble modo de accion ALS+hormonal. Muy eficaz en Conyza + latifoliadas mixtas.
- Metsulfuron 60% (6-7 g/ha) (Errasin WP / Ally) + Picloram 24% (80 cc/ha) (Tordon) — desde Z1.3 (3 hojas). Mezcla explicita en marbete Errasin. Alternativa cuando se busca mayor accion sobre cruciferas susceptibles a hormonales.
- Metsulfuron 60% (6-7 g/ha) (Errasin WP / Ally) + Bromoxinil 34,6% (0,8-1l) (Bromotril) — desde Z1.3 (3 hojas). ALS + contacto PPO. Excelente cobertura de espectro: Conyza + cruciferas + otras latifoliadas.
  NOTA METSULFURON: No aplicar en suelos calcarios o pH>8 (aumenta residualidad). Carencia trigo grano: 30 dias. Cebada: 90 dias. Usar surfactante no ionico 200cc/100L.


- Fluroxipir 33% (Starane Xtra) 270-360 cc/ha SOLO — desde Z1.3 (3 hojas) hasta hoja bandera visible (Z3.9).
  Marbete Corteva SENASA No.35.712. Malezas objetivo: caapiqui (Stellaria), sanguinaria (Polygonum aviculare),
  enredadera anual (Polygonum convolvulus), senecio (Senecio sp.), lengua de vaca (Rumex), yuyo sapo (Wedelia).
  NO controla cruciferas por si solo — requiere MCPA o 2,4D en mezcla para cruciferas.
- Fluroxipir 33% (Starane Xtra) 270-360 cc/ha + MCPA 28% (1000-1500 cc/ha) — desde Z1.3 (3-4 hojas) hasta hoja bandera.
  Mezcla explicita en marbete Starane Xtra. MCPA aporta control de cruciferas + latifoliadas susceptibles.
  Ventana MCPA en la mezcla: Z1.3 (3-4 hojas) hasta hoja bandera visible (Z3.9).
- Fluroxipir 33% (Starane Xtra) 270-360 cc/ha + 2,4D ester (300-400 cc/ha) — desde Z2.1 (macollaje) hasta Z3.1.
  Mezcla explicita en marbete. Ventana 2,4D: macollaje a encanzaon segun variedad.
- Fluroxipir 33% (Starane Xtra) 270-360 cc/ha + Saflufenacil 70% (Heat) 25g/ha — desde Z1.3 (3 hojas). SIN aceite.
  Hormonal sistemico (fluroxipir) + PPO contacto (saflufenacil). Amplio espectro latifoliadas. Cruciferas: cobertura parcial via PPO.

REGLA GENERAL — SAFLUFENACIL EN TRIGO POE:
Saflufenacil 70% (Heat) 25g/ha puede agregarse en mezcla con CUALQUIER hormonal (2,4D, MCPA, fluroxipir, dicamba)
en POE de trigo desde Z1.2-Z1.3 (2-3 hojas) en adelante. SIN aceite/coadyuvante a esta dosis en estado de hojas.
Aporta efecto de contacto PPO inmediato que complementa el sistemico del hormonal. Amplia espectro de control.
Fuente: BASF Argentina — registro POE trigo confirmado.

POST-EMERGENCIA CULTIVO (estadio Z2.1-Z3.0) — Aplicar sobre cultivo emergido en macollaje:
ESTRATEGIA: Hormonales (2,4D/MCPA) son la base en biotipos susceptibles. Mezclarlos con otros sitios de acción mejora control y retrasa resistencias. Fluroxipir en estados avanzados pero con control más deficitario.
ADVERTENCIA: En biotipos con resistencia a hormonales o ALS, las mezclas con PPO/Fotosistema II/PDS son la alternativa clave.

OPCIONES CON REGISTRO EN TRIGO Y CEBADA (Fuente: REM Aapresid 2024, Tabla 4):
- Bromoxinil 34,6% (0,8-1l) (Bromotril) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo y cebada
- Bentazón 60% (1-1,5l) (Basagran) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo y cebada
- Carfentrazone 40% (0,04l) (Shark) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo y cebada
- Terbutrina 50% (0,8-1l) (Igran) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo y cebada

OPCIONES CON REGISTRO EN TRIGO:
- Bromoxinil 34,6% (Bromotril) + Flurocloridona 25% (Rainbow) — Registro trigo
- Metribuzin 48% (0,4l) (Sencorex) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo
- Piraflufen 2,5% (0,08l) (Stagger) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo
- Saflufenacil 70% (25g) (Heat) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo. Malezas ≤10cm o ≤5cm roseta
- Saflufenacil 70% (25g) (Heat) solo — Registro POE trigo confirmado BASF Argentina. Malezas ≤10cm
- Flurocloridona 25% (0,5l) (Rainbow) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — Registro trigo
- Diflufenicán 50% (0,15l) (Brodal) + 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) — SIN REGISTRO en Argentina (Brodal marbete dice PEE). Se usa en práctica como POE precoz en macollaje con buenos resultados pero con algo de fitotoxicidad (10-20%). Consultar marbete vigente.
- Bromoxinil 34,6% (Bromotril) + Diflufenicán 50% (Brodal) — SIN REGISTRO en Argentina

OPCIONES SIN REGISTRO EN ARGENTINA (informativo — no recomendar como primera opción):
- Diflufenican + 2,4D/MCPA — Sin registro en Argentina
- Metribuzin + Diflufenican — Sin registro en Argentina
- Bromoxynil + Diflufenican — Sin registro en Argentina

TRIGOS HB4 (glufosinato):
- Glufosinato de amonio 28% (2-3l)
- Glufosinato de amonio 28% (2-3l) + 2,4D 64,3% e.a. (0,4l)
- Glufosinato de amonio 28% (2-3l) + Metribuzin 48% (0,4l) (Sencorex)
- Glufosinato de amonio 28% (2-3l) + Flurocloridona 25% (Rainbow)
- Glufosinato de amonio 28% (2-3l) // DG Glufosinato de amonio 28% (2-3l)

ADVERTENCIA VENTANA POR PRINCIPIO ACTIVO: Bromoxinil (Bromotril) y MCPA aplican desde estado de hojas (Z1.2-Z1.3). Saflufenacil (Heat) 25g/ha desde Z1.2 sin aceite. 2,4D y metsulfuron: desde Z2.1 (macollaje). Para gramineas: Axial desde Z1.3, Hussar Plus desde Z1.2, Topick desde Z1.2-Z1.3.
ADVERTENCIA: Fluroxipir puede usarse en estados avanzados del trigo para control de crucíferas pero con eficacia mucho menor.
ADVERTENCIA: En biotipos ALS-resistentes, no usar sulfonilureas. Mezclar hormonales con PPO/Triazinas/PDS mejora control y retrasa resistencias.

--- TRIGO: RAIGRAS ---
Fuente: INTA Pergamino / RG Malezas. Infografia Raigrás en Trigo.

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
⚠️ IMPORTANTE: Todos estos productos actúan sobre el RAIGRÁS ya nacido, ANTES de sembrar el trigo. NO aplicar sobre trigo emergido.
⚠️ NOTA DE LECTURA: El símbolo + indica mezcla de tanque en una sola aplicación. // indica Doble Golpe (dos aplicaciones separadas ~7 días).

--- ESTRATEGIA POR SITUACIÓN (en orden creciente de dificultad de control) ---

SITUACIÓN 1 — Raigrás recién emergido (1-2 hojas), baja densidad, biotipo desconocido:
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) — contacto rápido, eficaz solo con maleza chica (hasta 4 hojas)
- Glufosinato de amonio 28% (1-2,5l) — contacto, también solo hasta 4 hojas
- Glifosato (dosis v.s.f.) + Cletodim 24% (0,7l) (Select) — sistémico doble, buena base en biotipos susceptibles

SITUACIÓN 2 — Raigrás 2-4 hojas, densidad media, sin historial de resistencia:
- Glifosato + Cletodim 24% (1l) (Select) — dosis alta dentro del rango
- Glifosato + Cletodim 36% (0,5-0,7l) (Select 36) — formulación concentrada
- Glifosato + Haloxyfop 54% (0,25-0,35l) (Galant Max) — ACCasa diferente al cletodim
- Glifosato + Cletodim 12%/Haloxyfop 6% (0,8l) (Gramini Elite) — premezclado comercial, cómodo
- Glifosato + Cletodim 24%/Quizalofop 12% (0,5l) (Celebrate UPL) — premezclado comercial alternativo
- Fluazifop-p-butil 35% (0,4-0,6l) (Super Onecide) — ACCasa, también POE sobre cultivo

SITUACIÓN 3 — Raigrás avanzado (>4 hojas), alta densidad, o sospecha de resistencia a glifosato:
- Glifosato + Cletodim (Select) + Epirefenacil 5,5% (0,6l) (Empera) — triple: EPSPS+ACCasa+PPO
- Glifosato + Cletodim (Select) + Terbutilazina/Flumioxazin (Terbyne Max Sipcam) — triple con residual
- Glufosinato de amonio 28% (1-2,5l) + Cletodim (Select) — alternativa sin glifosato
- Glufosinato de amonio 28% + Cletodim (Select) + Glifosato — triple única aplicación
- Paraquat 27,6% (Gramoxone) + Cletodim (Select) + Glifosato — triple única aplicación
- Paraquat 27,6% (Gramoxone) + Terbutilazina/Flumioxazin (Terbyne Max Sipcam) — desecante con residual

SITUACIÓN 4 — Raigrás muy avanzado, muy alta densidad, resistencia confirmada o muy probable:
⚠️ En estos casos una sola aplicación es insuficiente — el Doble Golpe es la estrategia correcta.
- 1° Glifosato + Cletodim (Select) // 2° DG Paraquat 27,6% (Gramoxone) — ~7 días entre aplicaciones
- 1° Glifosato + Cletodim (Select) // 2° DG Glufosinato de amonio 28% — ~7 días entre aplicaciones
⚠️ En el DG: cuanto mejor sea la 1° aplicación, mejor el resultado total. No esperar demasiado entre golpes.

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre suelo sin maleza emergida (PEE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Piroxasulfone 48% (0,18-0,21l) (Yamato Top)
- Pendimetalín 45,6% (2,5-3,5l) (Herbadox)
- Flumioxazin 48% (0,15l) (Sumisoya) 10 DAS
- Terbutrina 50% (1,2l) (Igran)
- Terbutilazina 75% (1kg) (Terbine/Gesatop)
- Terbutilazina 50%/Flumioxazin 3,8% (1,5l) (Terbyne Max Sipcam) 15 DAS
- Bidozone 40% (1,2-1,5l) 15 DAS
- Flumioxazin 48% (0,12l) / Piroxasulfone 48% (0,21l) 10 DAS
- Diflufenicán / Aclonifén / Fluferacet (2-2,25l)
- Imazapyc / Xmazapy (0,2-0,3l) Trigos CL

POST-EMERGENCIA CULTIVO — DESDE 3 HOJAS HASTA ENCAÑAZÓN (Z1.3-Z3.1):
⚠️ Solo graminicidas — los latifoliadas (hormonales, sulfonilureas) requieren macollaje mínimo (Z2.1)
- Pinoxaden 5% (0,6-0,8l) (Axial) — desde Z1.3 (3 hojas) hasta encañazón. Maleza: 2-4 hojas a inicio macollaje
- Clodinafop 24% (0,2l) (Gizmo/Topick 24EC) — desde Z1.2-Z1.3 (2-3 hojas). Maleza: 1-2 hojas a macollaje
- Iodosulfurón/Mesosulfurón (0,2-0,3l) (Hussar Plus) — desde Z1.2 (2 hojas) hasta encañazón. Maleza: 2-4 hojas (gramíneas) o 6 hojas (latifoliadas)

POST-EMERGENCIA CULTIVO — DESDE MACOLLAJE (Z2.1-Z3.1):
⚠️ IMPORTANTE: Estos graminicidas también aplican desde estado de hojas (ver arriba). Los latifoliadas ÚNICAMENTE desde macollaje.
- Pinoxaden 5% (0,6-0,8l) (Axial)
- Clodinafop 24% (0,2l) (Gizmo/Topick 24EC)
- Piroxulam 21,5% (84gr) (PowerFlex) — también como Piroxulam+Metsulfurón (Merit WG Pack) 400cc+6,7g. Desde Z1.3 (3 hojas) hasta fin macollaje
- Iodosulfurón/Mesosulfurón (0,2-0,3l) (Hussar Plus)
- Flucarbazone (80-100gr) (Everest 70 WDG) — desde Z1.1 (1 hoja) hasta Z1.6 (6 hojas)
- Imazamox 70-100g (Pulsar/Trigosol) Trigos CL
- Imazapyc/Imazapyr (0,2-0,3l) (Odyssey/Mayoral) Trigos CL
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% / Pinoxaden 5% (0,6-0,8l) (Axial) Trigos HB4

⚠️ CONSIDERACIONES: Graminicidas (cletodim, haloxyfop, quizalofop) 25 DAS. Paraquat solo maleza hasta 4 hojas. Glufosinato de amonio solo malezas hasta 4 hojas.
⚠️ Las opciones LATIFOLIADAS aplican desde Z2.3 (macollaje). Para gramíneas: Axial desde Z1.3 (3 hojas), Hussar Plus desde Z1.2 (2 hojas), Topick desde Z1.2 (2-3 hojas).

=== SORGO ===

--- SORGO: LATIFOLIADAS/GRAMÍNEAS ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato
- 2,4D (carencia v.s.f.) — opción individual
- Picloram (carencia v.s.f.) — opción individual
- Fluroxipir (Starane) — opción individual
- Clopyralid (Lontrel) — opción individual
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glufosinato de amonio 28% (1-2,5l)
- Cletodim 24% (0,7-1l); 36% (0,5-0,7 l/ha) 20 DAS
- Haloxyfop 54% (0,25-0,35l) 20 DAS
- Saflufenacil 70% (35-40g) (Heat)
- Epirefenacil 5,5% (0,6l) (Empera)
- Carfentrazone 40% (70-80cc) (Shark)
- Piraflufén 2,5% (200cc) (Stagger)

PEE / PSI CULTIVO — Aplicar antes de emergencia del cultivo:
- Flumioxazin 48% (0,15l) 20-30 DAS
- Terbutilazina 75% (1kg) (Terbine/Gesatop)
- Atrazina 90% (1-2kg)
- S-metolacloro 96% (0,9-1,3l) (Dual Gold)* (*semilla curada con Fluxofenim 96%)
- Pendimetalín 33% (2,5-4,5l) (Herbadox)
- Imazapyc 31,8% (0,2-0,3l) (Odyssey) Sorgos tolerantes
- Atrazina 90% (1-2kg) + S-metolacloro 96% (0,9-1,3l) (Dual Gold)* — mezcla tanque
- Atrazina 90% (1-2kg) + Imazapyc/Imazapy (Odyssey) — Sorgos tolerantes

POST-EMERGENCIA CULTIVO (V4-V8) — Aplicar sobre cultivo emergido:
- 2,4D (aplicación dirigida >V8)
- MCPA 28% (1,5l) — opción individual
- Picloram 24% — opción individual
- Clopyralid (Lontrel) — opción individual
- Dicamba 57,7% — opción individual
- Bromoxinil 34,6% (0,8-1l) (Bromotril) V2-V4
- Atrazina 90% (1-2kg) V2-V4
- Bentazón 60% (1,2-1,6l) (Basagran) V2-V8
- Pendimetalín 33% (2,5-4l) (Herbadox) V3-V4 maleza no emergida
- Imazapyc/Imazapy (0,2-0,3l) (Odyssey) Sorgos tolerantes
- Foramsulfurón 30% + Iodosulfurón 2% (120cc) (Equip) + Sulfato amonio + Aceite — Maíz convencional, sorgo de Alepo RG
- Nicosulfurón 75% (70g) (Accent) + Sulfato amonio — Maíz convencional, sorgo de Alepo RG
- Atrazina 90% (1-2kg) + Hormonal (2,4D o MCPA) — mezcla tanque

Desecante: Paraquat / Glifosato

⚠️ *Semilla curada con Fluxofenim 96% requerida para usar atrazina + s-metolacloro

=== COLZA / CANOLA / CARINATA ===

--- COLZA: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glufosinato de amonio 28% (1-2,5l)
- Glifosato
- 2,4D (15-20 DAS) — opción individual
- Fluroxipir (Starane) — opción individual
- Clopyralid (Lontrel) — opción individual
- Saflufenacil 70% (35-40g) (Heat)
- Carfentrazone 40% (70-80cc) (Shark)

PEE / PSI CULTIVO — Aplicar antes de emergencia del cultivo:
- Clomazone 36% (1,5l) (Command) sin registro
- Trifluralina 60% (1,5l) (Treflan)
- Pendimetalín 45,6% (2,5-3,5l) (Herbadox)
- Imidazolinonas (Colzas CL) sin registro
- Triazinas: atrazina, metribuzin, terbutilazina (Colzas con resistencia a triazinas) sin registro
- ⚠️ Carinata: solo trifluralina

POST-EMERGENCIA CULTIVO (estado roseta) — Aplicar sobre cultivo emergido:
- Cletodim 24% (Select) / Cletodim 36% (Select 36) — graminicida ACCasa
- Haloxyfop 54% (Galant Max) — graminicida ACCasa
- Clopyralid 47,5% (100-150cc) (Lontrel) → riesgo Bajo
- Halauxifén (registro Uruguay) → riesgo Bajo
- Dicamba 57,5% (40-60cc) → riesgo Medio
- Picloram 24% (40-80cc) → riesgo Moderado/alto
- Fluroxipir 48% (200cc) → riesgo Moderado/alto
- Imidazolinonas (Colzas CL)
- Triazinas (Colzas con resistencia a triazinas)
- ⚠️ Carinata: solo graminicidas y clopyralid

RIESGO HERBICIDAS EN ROTACIÓN (Norte Buenos Aires):
- Imidazolinonas: riesgo Alto, >300mm, 4-6 meses
- Sulfonilureas: riesgo Alto, >300mm, 4 meses
- Sulfentrazone: riesgo Moderado, >200mm, 4 meses
- Flumioxazín: riesgo Bajo, >150mm, 2 meses
- Diclosulam: riesgo Alto, >300mm, 4-6 meses
- Topramazone: riesgo Medio, >250mm, 4 meses
- Mesotrione: riesgo Bajo-Medio, >200mm, 4 meses
- Biciclopirona: riesgo Moderado, >200mm, 4 meses
- Piroxazulfone: riesgo Bajo, >100mm, 2 meses

=== ARVEJA ===

--- ARVEJA: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glufosinato de amonio 28% (1-2,5l)
- 2,4D (15 DAS) / Fluroxipir / Saflufenacil 70% / Carfentrazone 40% / Piraflufén 2,5%
- Cletodim 24% / Haloxyfop 54%

PEE / PSI CULTIVO — Aplicar antes de emergencia del cultivo:
- Imazatapir 10% (0,8-1l)
- Metsulfurón 60% (4-5g) sin registro 30-40 DAS
- Metribuzin 48% (0,5-0,8l)
- Terbutilazina 75% (0,8-1kg) (Terbine/Gesatop)
- Prometrina 50% (2l) (Gesagard)
- Linurón 50% (2l) (Afalon)
- Atrazina 90% (0,5-1kg) sin registro
- Flumioxazin 48% (0,1l) (Sumisoya)
- S-metolacloro 96% (0,8-1l) (Dual Gold)
- Pendimetalín 45,6% (2,5-3,5l) (Herbadox)
- Trifluralina 60% (1-2,5l) (Treflan)
- Piroxasulfone 48% (0,1l) sin registro 10-15 DAS
- Diflufenicán 50% (0,2l) (Brodal) sin registro 10-15 DAS
- Imazatapir + Atrazina

POST-EMERGENCIA CULTIVO (4ª hoja verdadera BBCH 14 — antes de zarcillos BBCH 15) — Aplicar sobre cultivo emergido:
- Cletodim 24% / Haloxyfop 54% (graminicidas)
- Setoxidim (no disponible en Argentina)
- Imazatapir 10% (0,5l)
- Metribuzin 48% (0,5l) (Sencorex)
- Terbutilazina 75% (0,8kg) (Terbine/Gesatop)
- Bentazón 60% (1-1,5l) (Basagran)
- MCPA 28% (0,5-0,75l)

Desecante: Paraquat 27,6% / Diquat 40% (Reglone) / Saflufenacil 70% / Glufosinato 28%
⚠️ Evitar POE con condiciones de estrés

=== CAMELINA ===

--- CAMELINA: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glufosinato de amonio 28% (1-2,5l)
- Glifosato
- 2,4D (15-20 DAS) / Fluroxipir
- Saflufenacil 70% / Carfentrazone 40%

PEE / PSI CULTIVO — Aplicar antes de emergencia del cultivo:
Trifluralina 60% (1,5l) (Treflan) — ÚNICA opción residual

POST-EMERGENCIA CULTIVO (estado roseta BBCH 13-15) — Aplicar sobre cultivo emergido:
Cletodim 60% (1,5l) — ÚNICA opción, solo gramíneas

Desecante: Diquat 40% (Reglone) / Saflufenacil 70% / Carfentrazone 40%
⚠️ Cultivo con opciones muy limitadas

=== CRUCÍFERAS RESISTENTES (Barbecho) ===
Fuente: AAPRESID Regional Tandilia / INTA Tandil. Campaña 2018-19. Corredor Azul-Tandil, SE bonaerense.

--- CONTEXTO DE RESISTENCIA ---
En el SE bonaerense (partidos de Azul y Tandil) se han confirmado poblaciones con resistencia múltiple:
- Nabo (Brassica rapa): resistencia a EPSPS (glifosato) + inhibidores ALS + 2,4D
- Nabón (Raphanus sativus): resistencia a inhibidores ALS
- Nabillo (Hirschfeldia incana): resistencia múltiple a inhibidores ALS y 2,4D
- Colza (Brassica napus): resistencia a inhibidores de la EPSPS
⚠️ Estas poblaciones nacen durante todo el año, lo que dificulta el manejo

--- CONTROL DE CRUCÍFERAS RESISTENTES EN BARBECHO ---

CONTROL TOTAL (reseteo del lote) — POE sobre maleza nacida:
⚠️ Glifosato + 2,4D solo: control INSUFICIENTE (10-20%) en poblaciones resistentes
- Glifosato + 2,4D 45,6% e.a. (1,5l) + Saflufenacil 70% (35g) (Heat) → mejores controles
- Glifosato + 2,4D 45,6% e.a. (1,5l) + Carfentrazone 40% (75cc) (Shark) → mejores controles
- Paraquat 27,6% (2,5l) (Gramoxone) → control intermedio (sin residualidad)
- Paraquat 27,6% (2,5l) (Gramoxone) + 2,4D 45,6% e.a. (1,5l) → control intermedio
⚠️ El agregado de PPO quemante (Heat o Shark) al tratamiento base es clave para mejorar el control

CONTROL + RESIDUAL (barbecho previo a soja) — sobre maleza nacida + nuevos nacimientos:
⚠️ El éxito del residual depende FUERTEMENTE de la infestación inicial:

Con baja infestación previa (1-2 pl/m2, lote limpio):
- Todos los residuales funcionan >85% de control a los 25-40 días:
  - Glifosato + 2,4D + Diflufenicán 50% (350g) (Brodal) (Tuken)
  - Glifosato + 2,4D + Metribuzin + S-metolacloro + Flumioxazin (Tailwind+Oxalis)
  - Glifosato + 2,4D + Diclosulam 58% (45g) (Spider) + Halauxifén 11,5% (45g) (Texaro)
  - Glifosato + 2,4D + Piroxasulfone 85% (160g) (Yamato) + Saflufenacil 70% (35g) (Zidua Pack)
  - Glifosato + 2,4D + Diflufenicán 50% (250cc) (Brodal)

Con alta infestación (16-18 pl/m2, lote sucio):
⚠️ Solo funcionan con control >80%:
  - Glifosato + 2,4D + Diclosulam + Halauxifén (Texaro) → >80% a 25 y 40 días
  - Glifosato + 2,4D + Piroxasulfone + Saflufenacil (Zidua Pack) → >80% a 25 y 40 días
  - Resto de residuales: control parcial e insuficiente con alta infestación

=== SENECIO ARGENTINUS (Barbecho) ===

- Especie anual/bianual, emerge abril-mayo
- Asociada con Conyza spp. en barbechos largos
- Produce 15.000-25.000 semillas, viabilidad 2-4 años
- Tamaño crítico: NO superar 10 cm al aplicar

CONTROL:
- Glifosato 2000-2500 g.ea/ha (plantas juveniles, sin estrés)
- Otoño húmedo: Glifosato + hormonal (2,4D, fluroxipir, clopyralid, picloram)
- Otoño seco: Glifosato + PPO quemante (flumioxazin, saflufenacil, carfentrazone, piraflufén)
- Desecación: Diquat (Reglone) / Paraquat
- MEJOR COMBINACIÓN: Glifosato Premium 1080 g.ea + Flumioxazin (Sumisoya 120ml) + S-metolacloro (Dual Gold 1000ml) → 85-95% control
- Agregar cloracetamida puede tener efecto activador

=== TRÉBOL BLANCO (Trifolium repens) — Barbecho ===
Fuente: Corteva Agriscience, Manual Barbecho Quimico / Ensayos EEA INTA Oliveros / Marbete Starane Xtra SENASA No.35.712.

- Perenne por stolones — el control foliar aislado no elimina la planta si no se transloca a stolones
- Momento optimo: follaje joven y receptivo en activo crecimiento. No aplicar con estres hidrico ni frio intenso (<10°C)

OPCION PRINCIPAL (mejor desempeño en ensayos INTA Oliveros + Corteva):
- Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha
  Sin carencia previa a siembra. Glifosato actua en hojas; fluroxipir se transloca a stolones.
  Carencia rotacion: soja 3 DAS, girasol/algodon 10 DAS, maiz/trigo sin restriccion.

OPCION CON PPO (refuerzo de quemado sobre follaje):
- Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha + Saflufenacil 70% (Heat) 25-35g/ha
  Saflufenacil suma efecto contacto/quemado rapido sobre follaje. Combina 3 modos de accion.

OPCION MARBETE ESTANDAR:
- Glifosato 48% (3 l/ha) + Fluroxipir 33% (Starane Xtra) 360 cc/ha
  Marbete Starane Xtra — uso en barbecho quimico presiembra trigo.

⚠️ Reinfestacion por banco de semillas: planificar 2da aplicacion o residual PEE segun cultivo siguiente.

=== PROTOCOLO INTERNO DE ENSAYOS ===

PEE (Preemergente de cultivo):
- GIRASOL: Glifosato 2L/1,5kg + Flurocloridona 1,5L + Piroxasulfone 160g
- MAÍZ: Glifosato 2L/1,5kg + Atrazina 3L/1,5kg + Zidua Pack (HEAT 45g + Pyroxasulfone 200g) + Aceite
  Si emerge/emergido: cambiar Zidua por Adengo 280cc/ha
- SOJA: Glifosato 2L/1,5kg + Sulfentrazone 400cc + S-Metolacloro 1,5L + Metribuzin 48% 1,5L
  Opcionales: Texaro 43g+Aceite MS (Conyza) / Enlist 1,8L (Soja Enlist, maleza nacida)

POE (Postemergencia de cultivo):
- GIRASOL CL: Clearsol DF 100g + Aceite DASH 200cc + graminicida si hace falta
- GIRASOL NO CL: Prodigio 1,5L + Aceite (NO mezclar con graminicidas) o Benazolin 50% 0,3L + graminicida
- MAÍZ: Glifosato 2L/1,5kg (RR) + Atrazina 1,5-3L + Tordon 150cc / Glufosinato (Maíz Enlist)
- SOJA: Glifosato 2L/1,5kg (RR) + Fomesafén 25% 1,5L + coadyuvante + Benazolin 50% 0,8L
  Enlist 1,8L (Soja Enlist) / Glufosinato (Soja Enlist)
"""


# --- CLIENTE ANTHROPIC ---
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- HISTORIAL DE CONVERSACION POR USUARIO ---
conversation_history = {}

# --- COMANDO /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Soy el asistente de *Control de Malezas*.\n\n"
        "Puedo ayudarte con recomendaciones de herbicidas para:\n"
        "🌱 Soja · Maíz · Girasol · Trigo · Sorgo\n"
        "🌿 Colza · Arveja · Camelina\n\n"
        "Preguntame sobre malezas específicas, momentos de aplicación, dosis, etc.\n\n"
        "Ejemplo: _¿Qué uso para control de yuyo colorado en PEE de soja?_",
        parse_mode="Markdown"
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

        await update.message.reply_text(assistant_message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ Hubo un error procesando tu consulta. Por favor intentá de nuevo."
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
