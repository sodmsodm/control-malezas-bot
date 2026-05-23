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

Respondés en español, de forma clara, técnica y organizada. Usás tablas cuando es útil.
Siempre aclarás el momento de aplicación (barbecho, PEE, PSI-PEE, POE) y el biotipo de cultivo cuando es relevante.

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

=== SOJA ===

--- SOJA: MALEZA GENERAL (No GMO) ---

BARBECHO INTERMEDIO (45-60 DAS):
- Flumioxazin 48% (150cc)
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) hasta 15 DAS
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (1kg) hasta 45 DAS
- Metribuzin 48% (1l) (Sencorex)
- Terbutilazina 50% / Flumioxazin 3,8% (1,25) hasta 30 DAS
- Sulfometurón 15% (Classic) / Clorimurón 20% (Classic) (0,1kg) SOJAS STS

PEE / PSI-PEE:
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Sulfentrazone 10% / S-metolacloro 60% (2,5l)
- Sulfentrazone 50% (0,5l) (Authority/Capaz) / Piroxasulfone 48% (0,355l)
- Sulfentrazone 50% (0,5l) (Authority/Capaz) / Imazetapir 10% (0,8-1l) (Pivot)
- Sulfentrazone 50% (0,5l) (Authority/Capaz) / Diclosulam 84% (0,03kg) (Spider)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) / Metribuzin 48% (0,8-1l) (Sencorex)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) / Clomazone 36% (1,75-2l) (Command)
- Flumioxazin 15% / Piroxasulfone 34,5% (0,5l) 7 DAS
- Flumioxazin 4,2% / S-metolacloro 84% (1,75l) 7 DAS
- Flumioxazin 5% / S-metolacloro 57,6% / Imazetapir 5% (1,5l) 7 DAS
- Flumioxazin 14,5% / Diclosulam 6,5% (Spider) / Imazetapir 20% (0,5l) 7 DAS
- Flumioxazin 28,8% / Diclosulam 8,4% (Spider) (0,25l) / S-metolacloro 96% (1,1-1,3l) (Dual Gold) 7 DAS
- Flumioxazin 4,2% / Acetoclor 90% (1,5l) (Harness) 7 DAS
- Sulfentrazone 50% (0,4l) (Authority/Capaz) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Sulfometurón 30,7% (0,25l) 7 DAS SOJAS STS
- Sulfometurón 15% (Classic) / Clorimurón 20% (Classic) (0,1kg) / Sulfentrazone 50% (0,5l) (Authority/Capaz) SOJAS STS
- Metribuzin 14,9% / S-metolacloro 62,8% (2,5l)
- Fomesafén 50% (0,4-0,5l) / Metribuzin 48% (0,8-1l) (Sencorex) / Acetoclor 90% (1,5l) (Harness)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)

POST-EMERGENCIA CULTIVO (V4-V6) — Aplicar sobre cultivo emergido:
- Fomesafén 25% (1-1,5l) (Flex)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Cletodim 24% (0,7-1l) (Select); Cletodim 36% (0,5-0,7 l/ha) (Select 36)
- Piroxasulfone 85% (0,16-0,2 kg/ha) (Yamato) hasta V4 o V8
- Fomesafén 25% (1-1,5l) (Flex) / Benazolín 50% (0,8l) (Dasen)
- Fomesafén 25% (1-1,5l) (Flex) / 2,4DB 97% e.a. (0,04l)
- Fomesafén 11,95% / S-metolacloro 51,8% (1,5-2,5l)
- Fomesafén 25% (1-1,5l) (Flex) / Benazolín 50% (0,015kg) (Dasen)
- Fomesafén 25% (1-1,5l) (Flex) / Clorimurón 25% (0,03kg) (Classic)
- Clorimurón 25% (0,04-0,05kg) (Classic)
- Cloransulam 84% (0,04-0,05kg) (Pacto)
- Imazetapir 10% (0,5-0,8l) (Pivot)
- 2,4DB 97% e.a. (0,04l) / Bentazón 60% (0,8-1l) (Basagran)
- Cletodim 24% (0,7-1l) (Select); Cletodim 36% (0,5-0,7 l/ha) (Select 36)
- Benazolín 50% (0,6l) (Dasen) / Clorimurón 25% (0,03g) (Classic)
- Benazolín 50% (0,6l) (Dasen) / Diclosulam 84% (0,015g) (Spider)

--- SOJA: COMMELINA ERECTA ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato 1260 g.e.a. / 2,4D (1-1,5l) / Saflufenacil 70% (40g) (Heat) / DG Paraquat 27,6% (2-3l) (Gramoxone)
- Glifosato / 2,4D / Carfentrazone 40% (70-80cc) / DG Paraquat
- Glifosato / 2,4D / Epirefenacil 5,5% (600cc) (Empera) / DG Paraquat
- Glifosato / 2,4D / Flumioxazin 48% (150cc) / DG Paraquat
- Glifosato / 2,4D / Iodosulfurón / Imazetapir (30-45g) 30-45 DAS / DG Paraquat
- Glifosato / 2,4D / Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) / DG Paraquat
- Glufosinato de amonio 28% (2,5l) / 2,4D / DG Paraquat
- Glufosinato de amonio / 2,4D / Metribuzin 48% (0,8-1l) (Sencorex) / DG Paraquat
- Glufosinato de amonio / 2,4D / Amicarbazone 70% (0,4g) (Dinamic) / DG Paraquat hasta 45 DAS
- Glufosinato de amonio / 2,4D / Saflufenacil / Flumioxazin
- Glufosinato de amonio / 2,4D / Carfentrazone / DG
- Paraquat / 2,4D / Atrazina hasta 40 DAS

NOTA: Mejores opciones quemado. Sin control total.
DG = doble golpe

SOJAS RESISTENTES GLIFOSATO: Sin opciones efectivas

SOJAS ENLIST:
- Glifosato 1260 g.e.a. / Glufosinato de amonio / 2,4D 30% e.a. (1,5-2l) Hasta V4-V6
- Glufosinato de amonio / 2,4D 30% e.a. (1,5-2l) V4-V6
- Agregar Sulfato de Amonio 1,5-2 l/ha en mezclas con Glufosinato

--- SOJA: CRUCIFERAS ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato / 2,4D (carencia v.s.f.)
- Glifosato / MCPA 28% (1,5-2,5l)
- Glifosato / 2,4D + Dicamba 25 DAS
- Glifosato / 2,4D o MCPA / Saflufenacil 70% (35-40g) (Heat)
- Glifosato / 2,4D o MCPA / Carfentrazone 40% (70-80cc) (Shark)
- Glifosato / 2,4D o MCPA / Piraflufén 2,5% (200cc) (Stagger)
- Glifosato / 2,4D o MCPA / Epirefenacil 5,5% (600cc) (Empera)
- Glifosato / 2,4D o MCPA / Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)
- Glufosinato de amonio 28% (1-2,5l) / 2,4D
- Glufosinato de amonio / 2,4D / Saflufenacil
- Glufosinato de amonio / 2,4D / Carfentrazone
- Glifosato / 2,4D // DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glifosato / 2,4D // DG Glufosinato de amonio

MALEZA PEE BARBECHO LARGO — Aplicar sobre suelo sin maleza emergida (PEE maleza):
- Atrazina 90% (1kg) hasta 30 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (0,8-1kg) desde 45-60 DAS desde primera lluvia
- Flurocloridona 25% (1,5l) hasta 45 DAS
- Biciclopirona 20% (0,5l) / Atrazina 90% (0,5kg) 120 DAS
- Diflufenicán 50% (0,3l) (Brodal)
- Flumioxazin 48% (0,1-0,15l)
- Terbutilazina 50% / Flumioxazin 3,8% (1,15-1,25l) 30 DAS

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Metribuzin 48% (0,8-1kg) (Sencorex)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz)
- Flumioxazin 48% (0,1-0,15l) 7 DAS
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) 15 DAS
- Fomesafén 11,9% / S-metolacloro 51,8% (2,5l)
- Flumioxazin 15% / Piroxasulfone 34,5% (0,3l/0,1l) 7 DAS
- Sulfentrazone 50% / Diflufenicán 50% (0,3l/0,3l) 15 DAS
- Trifludimoxazin 12,5%/Saflufenacil 25% (Voraxor) (0,1-0,2l) 7 DAS

POST-EMERGENCIA CULTIVO — Aplicar sobre cultivo emergido (Soja Resistente Glifosato o No GMO):
- Fomesafén 25% (1-1,5l) (Flex)
- Acifluorfén 24% (1-1,5l) (Blazer)
- Lactofén 24% (0,6-0,8l) (Cobra)
- Fomesafén 25% (1-1,5l) (Flex) / Benazolín 50% (0,6l) (Dasen)
- Bentazón 60% (1,5l) (Basagran)

SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) / 2,4D 30% e.a. (1,5-2l) hasta V4-V6

--- SOJA: PARIETARIA ---

BARBECHO LARGO — Aplicar sobre suelo o maleza en distintos estadios:
- Atrazina 90% (1-1,5kg) PEE-POST MALEZA hasta 60 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS PEE-POST MALEZA
- Terbutilazina 75% (0,8-1kg) hasta 45 DAS PEE-POST MALEZA
- Metsulfurón 60% (6-8g) hasta 60 DAS PEE MALEZA
- Metsulfurón / Clorsulfurón (12-15g) SOJAS STS o hasta 150 DAS PEE MALEZA
- Biciclopirona 20% (0,5l) / Atrazina 90% (0,5kg) 120 DAS PEE-POST MALEZA
- Flumioxazin 48% (0,1-0,15l) PEE-POST MALEZA
- Terbutilazina 75% (1kg) / Flumioxazin 48% (0,12l) PEE-POST MALEZA

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Atrazina 90% (0,5kg) PEE-POST MALEZA hasta 30 DAS
- Metribuzin 48% (0,8-1l) (Sencorex) PEE-POST MALEZA
- Prometrina 48% (1,5-2l) (Gesagard) PEE-POST MALEZA
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) / Metribuzin 48% (0,8-1l) (Sencorex) PEE-POST MALEZA
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) / Atrazina 90% (0,5kg) hasta 30 DAS
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) / Prometrina 48% (1,5-2l) (Gesagard)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) / Flumioxazin 48% (0,1-0,15l) 7 DAS
- Paraquat 27,6% (1,5-2,5l) (Gramoxone) / Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) PEE-POST 7 DAS
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) PEE-POST MALEZA 7 DAS
- Glifosato 1260 g.e.a. / Epirefenacil 5,5% (600cc) (Empera) POST MALEZA

POST-EMERGENCIA CULTIVO: Sin opciones efectivas
- Dosis glifosato > 1360 g.e.a. + sulfato de amonio + aceite, controles hasta 60%

--- SOJA: AMARANTHUS SPP. (Yuyo Colorado) ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Epirefenacil 5,5% (600cc) (Empera)
- Trifludimoxazin/Saflufenacil (0,1-0,2l) (Voraxor) Acción POE y PEE MALEZA
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- 2,4D / Saflufenacil 70% (40g) (Heat)
- 2,4D / Carfentrazone 40% (70-80cc) (Shark)
- 2,4D / Epirefenacil 5,5% (600cc) (Empera)
- Glufosinato de amonio / 2,4D / Saflufenacil / Flumioxazin / Carfentrazone / Epirefenacil

MALEZA PEE BARBECHO INTERMEDIO (45-60 DAS) — Aplicar sobre suelo sin maleza emergida:
- Flumioxazin 48% (150cc)
- Piroxasulfone 85% (160-200g) (Yamato)
- Diflufenicán 50% (0,3l) (Brodal) hasta 15 DAS
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) hasta 45 DAS
- Terbutilazina 75% (1kg) hasta 45 DAS
- Metribuzin 48% (1l) (Sencorex)
- Terbutilazina / Flumioxazin (1,25) hasta 45 DAS

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Metribuzin 10% / S-metolacloro 60% (2,5l)
- Sulfentrazone / Piroxasulfone 48% (0,355l)
- Flumioxazin 15% / Piroxasulfone 34,5% (0,5l/0,1l) 7 DAS
- Flumioxazin 4,2% / S-metolacloro 84% (1,75l) 7 DAS
- Flumioxazin 4,2% / Acetoclor 90% (1,5l) (Harness) 7 DAS
- Fomesafén 11,9% / S-metolacloro 51,8% (2,5l)
- Sulfentrazone 50% (0,4l) (Authority/Capaz) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Sulfentrazone 50% (0,4-0,5l) (Authority/Capaz) / Metribuzin 48% (0,8-1l) (Sencorex) / Acetoclor 90% (1,5l) (Harness)
- Trifludimoxazin / Saflufenacil / S-metolacloro 96% (1,1-1,3l) (Dual Gold)

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
- 2,4D / Carfentrazone 40% (70-80cc) (Shark)
- 2,4D / Epirefenacil / Saflufenacil / Carfentrazone / Flumioxazin / Trifludimoxazin

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Atrazina 90% (1-2kg) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Atrazina 90% (1-2kg) / Biciclopirona 20% (0,8-1l)
- Biciclopirona 20% (0,8-1l) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Biciclopirona 20% (0,8-1l) / Piroxasulfone 85% (0,2kg)
- Amicarbazone 70% (0,4-0,5kg) (Dinamic) / S-metolacloro
- Terbutilazina 75% (0,8-1kg) / Piroxasulfone 85%
- Terbutilazina 50% (0,8-1kg) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Mesotrione 48% (0,3l) / Piroxasulfone
- Trifudimoxazin 8,1% (1,77-2,2l) / S-metolacloro 96% (1,1-1,3l) (Dual Gold)
- Flumioxazin 4,2% / Acetoclor 90% (1,5l) (Harness)
- Isoxaflutole / Thiencarbazone (0,3-0,4l) / S-metolacloro / Atrazina

POST-EMERGENCIA CULTIVO (V2-V8) — Aplicar sobre cultivo emergido:
- Atrazina 90% (1kg) / 2,4D 64,3% e.a. (0,4l)
- Atrazina 90% (1kg) / Picloram 24% (0,1-0,15l)
- Atrazina 90% (1kg) / Mesotrione 48% (0,3l)
- Atrazina 90% (1kg) / Topramezone 33,6% (0,1l)
- Atrazina 90% (1kg) / Tolpyralate 42% (0,075-0,125l)
- Atrazina 90% (1kg) / Tembotrione 42% (0,25-0,3l)
- Terbutilazina 55% / Mesotrione 8,1% (2l) / Atrazina 90% (1kg)

MAÍZ ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V2-V4
- 2,4D 45,6% e.a. (1,5-2l) hasta V8
- Glufosinato de amonio 28% (2-3l) / 2,4D 45,6% e.a. (1,5-2l) V2-V4

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
- Atrazina 90% (1,8-2,2kg) Gesaprim Fot.II
- Terbutilazina 75% (1,3-1,5kg) Terbine Fot.II
- Amicarbazone 70% (0,4-0,7) Dinamic Fot.II
- Linurón 50% (2-3l) (Afalon) Fot.II
- S-metolacloro 96% (0,8-1,6l) Dual Gold
- Acetoclor 90% (2-3l) (Harness)
- Piroxazulfone 85% (0,16-0,2kg) Yamato 15 DAS
- Dimetenamida 90% (1,2-1,8l) (Frontier)
- Diflufenicán 50% (0,2-0,3l)
- Biciclopirona 20% (0,75-1l) Acuron Uno
- Flurocloridona 25% (0,75-1,5l) Rainbow
- Piroxasulfone/saflufenacil (Zidua Pack) También POE maleza
- Piroxasulfone/flumioxazin (Fierce 10-15 DAS)
- Atrazina/s-metolacloro (BicepPack Gold)
- Isoxaflutole/thiencarbazone (ALS) Adengo

ACCIÓN SOBRE MALEZA NACIDA / CULTIVO EMERGIDO (POE maleza / POE cultivo V2-V8):
⚠️ Malezas <5cm, evitar estrés:
- Atrazina 90% (1,5-2kg) Gesaprim hasta V6
- Bentazón 60% (1,2-1,6l) (Basagran) V2-V8 (cotiledonar)
- Metribuzin 70% (210-270g) Tribune hasta V2-V8
- Linurón 50% (2-2,5l) (Afalon) tratamientos en bandas
- 2,4D V2-V8 Hormonal
- 2,4D sal colina 66,9% (1,5-2,5l) V1-V8 Maíz ENLIST
- Dicamba 57,7% (0,15-0,2l) V2-V8
- Picloram 27,7% (0,1-0,15l) V2-V8
- MCPA 28% (1,5l) V2-V8
- Mesotrione 48% (0,3l) Callisto V2-V6
- Topramezone 33,6% (0,08-0,1l) Convey V1-V7
- Tolpyralate 40% (0,075-0,125l) Brucia V3-V6
- Tembotrione 42% (0,25-0,3l) Laudis V3-V6
- Glufosinato de amonio 28% (1,8-2l) Maíz ENLIST V1-V8
- Pendimetalín 33% (2,5-4l) (Herbadox) V3-V4 Maleza no emergida

=== GIRASOL ===

--- GIRASOL: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI-PEE cultivo):
- 2,4D (15-20 DAS) Formulaciones éster ethyl o mictoemulsión
- Dicamba (30 DAS)
- Fluroxipir (1 DAS)
- Halauxifén (1 DAS) 120cc
- Paraquat 27,6% (1-3,5l) (Gramoxone)
- Carfentrazone 40% (50-75cc) (Shark)
- Piraflufén etil 2,5% (80-200cc) (Stagger)
- Oxifluorfén 24% (0,25-0,3l) (Galigan)
- Glifosato (dosis v.s.f.)
- Glufosinato de amonio 28% (1-3l) Lifeline
- Paraquat/diurón (1,5-2,5l) Cerillo
- Fluroxipyr/halauxifén (400-500cc) (Pixxaro)

PEE / PSI-PEE — Aplicar antes de emergencia del cultivo:
- Sulfentrazone 50% (300-400cc) (Authority/Capaz)
- Flumioxazin 48% (50-100cc) Sumisoya (20-30 DAS)
- Prometrina 50% (1-2l) (Gesagard) Gesagard
- S-metolacloro 96% (0,8-1l) (Dual Gold) Dual Gold
- Acetoclor 90% (2-3l) (Harness)
- Trifluralina 60% (1-2l) (Treflan)
- Piroxasulfone 85% (160-200g) (Yamato) Yamato (sin registro)
- Pendimetalín 45,5% (2-3,5l) (Herbadox)
- Diflufenicán 50% (0,3l) (Brodal) Brodal
- Flurocloridona 25% (2-4l) Rainbow
- Imazapyr 80% (100g) Clearsol (Girasoles Clearsol)
- Múltiples mezclas: Sulfentrazone/S-metolacloro, Flurocloridona/S-metolacloro, Diflufenicán/Acetoclor, Prometrina/Acetoclor, etc.
- Imazapyr 1,5%/Imazamox 3,3% (1,5-2l) Clearsol Plus II

POST-EMERGENCIA CULTIVO — Aplicar sobre cultivo emergido:
- Graminicidas (DIMs, FOPs): Cletodim (Select), Haloxyfop-R-metil (Galant Max), Propaquizafop (Agil), Quizalofop-p-etil (Assure)
- Aclonifén 60% (1-1,5l) Prodigio
- Benazolín 50% (0,3l) (Dasen) Dasen
- Imazapyr 80% (Clearsol) Acción POE-PEE maleza
- Imazapyr/Imazamox (Clearsol Plus II)

⚠️ NO USAR en girasol: saflufenacil, fomesafén, biciclopirona, topramezone, diclosulam, sulfonilureas

=== TRIGO ===

--- TRIGO: CONYZA SPP. ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato / 2,4D (v.s.f.)
- Glifosato / Dicamba 57,8% (0,1-0,2l) (Banvel)
- Glifosato / 2,4D + Dicamba
- Glifosato / 2,4D o MCPA / Saflufenacil 70% (35-40g) (Heat)
- Glifosato / 2,4D o MCPA / Carfentrazone 40% (70-80cc) (Shark)
- Glifosato / 2,4D o MCPA / Piraflufén 2,5% (200cc) (Stagger)
- Glifosato / 2,4D o MCPA / Epirefenacil 5,5% (600cc) (Empera)
- Glifosato / 2,4D o MCPA / Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)
- Glufosinato / 2,4D / Saflufenacil / Carfentrazone
- Glifosato / 2,4D // DG Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glifosato / 2,4D // DG Glufosinato de amonio

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre suelo sin maleza emergida (PEE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Metsulfurón 60% (8-10g) (Ally)
- Metsulfurón/Clorsulfurón (12-15g) (Finesse WG)
- Flumioxazin 48% (0,15l) 10 DAS
- Terbutrina 50% (1,2l)
- Terbutilazina 75% (1kg)
- Amicarbazone (sin registro) (Dinamic)
- Terbutilazina 50% / Flumioxazin 3,8% (1,5l) 15 DAS
- Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)

POST-EMERGENCIA CULTIVO (estadio Z2.1-Z3.0) — Aplicar sobre cultivo emergido en macollaje:
- Metsulfurón 60% (5-6g) (Ally) / Dicamba 57,8% (0,1-0,15l) (Banvel)
- Metsulfurón / Clorsulfurón (10-12g) (Finesse WG) / Dicamba 57,8% (0,4l) (Banvel)
- Metsulfurón / Clorsulfurón (10-12g) (Finesse WG) / 2,4D 64,3% e.a. (0,4l)
- 2,4D 64,3% e.a. (0,4l) / Dicamba 57,8% (0,1-0,15l) (Banvel)
- 2,4D 64,3% e.a. (0,4l) / Picloram 24% (0,1-0,12l) (Tordón)
- 2,4D 64,3% e.a. (0,4l) / Fluroxipir 48% (0,2-0,4l) (Starane)
- 2,4D 64,3% e.a. (0,4l) / Carfentrazone 40% (0,04l)
- 2,4D 64,3% e.a. (0,4l) / Terbuttrina 50% (0,8-1l)
- 2,4D 64,3% e.a. (0,4l) / Saflufenacil 70% (25g) (Heat)
- 2,4D 64,3% e.a. (0,4l) / Metribuzin 48% (0,4l) (Sencorex)
- 2,4D 64,3% e.a. (0,4l) / Piraflufén 2,5% (0,08l) (Stagger)
- Clopyralid / MCPA (1,25-1,35l) (Lontrel)
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / 2,4D 64,3% e.a. (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Metribuzin 48% (0,4l) (Sencorex) Trigos HB4
- Glufosinato de amonio 28% (2-3l) // DG Glufosinato de amonio 28% (2-3l) Trigos HB4

⚠️ CONSIDERACIONES: Evitar repetir mecanismos de acción. Usar coadyuvantes. Control POE con malezas pequeñas. Evitar aplicaciones con estrés por frío o falta de agua.
⚠️ Las opciones POE cultivo aplican ÚNICAMENTE desde Z2.1 (inicio macollaje). Para estadios anteriores no hay opciones POE registradas en esta base.

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
- Flurocloridona 25% (1,5l)
- Diflufenicán 50% (0,3l) (Brodal)
- Flumioxazin 48% (0,12l) 10 DAS
- Piroxasulfone 85% (0,12kg)
- Flurocloridona 25% (1,5l) / Piroxasulfone 48% (0,21l) 15 DAS
- Terbutrina 50% (1,2l)
- Terbutilazina 75% (1kg)
- Amicarbazone (sin registro) (Dinamic)
- Trifludimoxazin/Saflufenacil (0,1-0,15l) (Voraxor)
- Diflufenicán / Aclonifén / Fluferacet (2-2,25l)

POST-EMERGENCIA CULTIVO (estadio Z2.1-Z3.0) — Aplicar sobre cultivo emergido en macollaje:
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Bromoxinil 34,6% (0,8-1l) (Bromotril)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Metribuzin 48% (0,4l) (Sencorex)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Terbutrina 50% (0,8-1l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Diflufenicán 50% (0,15l) (Brodal)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Bentazón 60% (Basagran)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Carfentrazone 40% (0,04l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Piraflufén 2,5% (0,08l) (Stagger)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Saflufenacil 70% (25g) (Heat)
- Bromoxinil 34,6% (0,8-1l) (Bromotril) / Flurocloridona 25% (0,5l)
- Bromoxinil 34,6% (0,8-1l) (Bromotril) / Diflufenicán 50% (0,15l) (Brodal)
- Bromoxinil 34,6% (0,8-1l) (Bromotril) / Metribuzin 48% (0,4l) (Sencorex)
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / 2,4D 64,3% e.a. (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Metribuzin 48% (0,4l) (Sencorex) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Fluorocloridona 25% (0,5l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) // DG Glufosinato de amonio 28% (2-3l) Trigos HB4

⚠️ Las opciones POE cultivo aplican ÚNICAMENTE desde Z2.1 (inicio macollaje). Para estadios anteriores no hay opciones POE registradas en esta base.

--- TRIGO: RAIGRAS ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
⚠️ IMPORTANTE: Cletodim y haloxyfop en este contexto actúan sobre el RAIGRAS ya nacido, ANTES de sembrar el trigo. NO son para aplicar sobre trigo emergido.
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glufosinato de amonio 28% (1-2,5l)
- Cletodim 24% (0,7-1l) (Select); Cletodim 36% (0,5-0,7 l/ha) (Select 36)
- Haloxyfop 54% (0,25-0,35l) (Galant Max)
- Glifosato / Cletodim / Epirefenacil / Terbutilazina+Flumioxazin
- Paraquat / Cletodim / Glifosato
- DG Paraquat / Glufosinato

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre suelo sin maleza emergida (PEE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Piroxasulfone 48% (0,18-0,21l) (Yamato Top)
- Pendimetalín 45,6% (2,5-3,5l) (Herbadox)
- Flumioxazin 48% (0,15l) 10 DAS
- Terbutrina 50% (1,2l)
- Terbutilazina 75% (1kg)
- Terbutilazina 50% / Flumioxazin 3,8% (1,5l) 15 DAS
- Bidozone 40% (1,2-1,5l) 15 DAS
- Flumioxazin 48% (0,12l) / Piroxasulfone 48% (0,21l) 10 DAS
- Diflufenicán / Aclonifén / Fluferacet (2-2,25l)
- Imazapyc / Xmazapy (0,2-0,3l) Trigos CL

POST-EMERGENCIA CULTIVO (estadio Z2.3-Z3.1) — Aplicar sobre cultivo de trigo emergido en macollaje:
⚠️ IMPORTANTE: Estas opciones son para aplicar sobre el TRIGO YA EMERGIDO (macollaje Z2.3-Z3.1). Son graminicidas selectivos para trigo registrados para esa ventana. NO confundir con las opciones de barbecho anteriores.
- Pinoxaden 5% (0,6-0,8l) (Axial)
- Clodinafop 24% (0,2l) (Gizmo)
- Piroxulam 21,5% (84gr) (PowerFlex)
- Iodosulfurón/Mesosulfurón (0,2-0,3l) (Hussar Plus)
- Flucarbazone (80-100gr) (Everest 70 WDG)
- Imazamox 70-100g Trigos CL
- Imazapyc/Imazapy (0,2-0,3l) Trigos CL
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% / Pinoxaden 5% (0,6-0,8l) Trigos HB4

⚠️ CONSIDERACIONES: Graminicidas (cletodim, haloxyfop, quizalofop) 25 DAS. Paraquat solo maleza hasta 4 hojas. Glufosinato de amonio solo malezas hasta 4 hojas.
⚠️ Las opciones POE cultivo aplican ÚNICAMENTE desde Z2.3. Para estadios anteriores no hay opciones POE registradas en esta base.

=== SORGO ===

--- SORGO: LATIFOLIADAS/GRAMÍNEAS ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Glifosato
- 2,4D (carencia v.s.f.) / Picloram / Fluroxipir / Clopyralid
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
- Terbutilazina 75% (1kg)
- Atrazina 90% (1-2kg)
- S-metolacloro 96% (0,9-1,3l) (Dual Gold)* (*semilla curada con Fluxofenim 96%)
- Pendimetalín 33% (2,5-4,5l) (Herbadox)
- Imazapyc 31,8% (0,2-0,3l) Sorgos tolerantes a imidazolinonas
- Atrazina 90% (1-2kg) / S-metolacloro 96% (0,9-1,3l) (Dual Gold)*
- Atrazina 90% (1-2kg) / (Imazapyc/Imazapy) Sorgos tolerantes

POST-EMERGENCIA CULTIVO (V4-V8) — Aplicar sobre cultivo emergido:
- 2,4D (aplicación dirigida >V8)
- MCPA / Picloram / Clopyralid / Dicamba
- Bromoxinil 34,6% (0,8-1l) V2-V4
- Atrazina 90% (1-2kg) V2-V4
- Bentazón 60% (1,2-1,6l) (Basagran) V2-V8
- Pendimetalín 33% (2,5-4l) (Herbadox) V3-V4 maleza no emergida
- Imazapyc/Imazapy (0,2-0,3l) Sorgos tolerantes
- Atrazina 90% / Hormonal / Mezclas hormonales

Desecante: Paraquat / Glifosato

⚠️ *Semilla curada con Fluxofenim 96% requerida para usar atrazina + s-metolacloro

=== COLZA / CANOLA / CARINATA ===

--- COLZA: MALEZA GENERAL ---

ANTES DE SIEMBRA DEL CULTIVO — Aplicar sobre maleza nacida (POE maleza) / Cultivo aún no sembrado (PSI cultivo):
- Paraquat 27,6% (1,5-2,5l) (Gramoxone)
- Glufosinato de amonio 28% (1-2,5l)
- Glifosato
- 2,4D (15-20 DAS) / Fluroxipir / Clopyralid
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
- Cletodim / Haloxyfop (graminicidas)
- Clopyralid 47,5% (100-150cc) → riesgo Bajo
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
- Terbutilazina 75% (0,8-1kg)
- Prometrina 50% (2l) (Gesagard)
- Linurón 50% (2l) (Afalon)
- Atrazina 90% (0,5-1kg) sin registro
- Flumioxazin 48% (0,1l)
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
- Terbutilazina 75% (0,8kg)
- Bentazón 60% (1-1,5l) (Basagran)
- MCPA 28% (0,5-0,75l)

Desecante: Paraquat 27,6% / Diquat 40% / Saflufenacil 70% / Glufosinato 28%
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

Desecante: Diquat 40% / Saflufenacil 70% / Carfentrazone 40%
⚠️ Cultivo con opciones muy limitadas

=== SENECIO ARGENTINUS (Barbecho) ===

- Especie anual/bianual, emerge abril-mayo
- Asociada con Conyza spp. en barbechos largos
- Produce 15.000-25.000 semillas, viabilidad 2-4 años
- Tamaño crítico: NO superar 10 cm al aplicar

CONTROL:
- Glifosato 2000-2500 g.ea/ha (plantas juveniles, sin estrés)
- Otoño húmedo: Glifosato + hormonal (2,4D, fluroxipir, clopyralid, picloram)
- Otoño seco: Glifosato + PPO quemante (flumioxazin, saflufenacil, carfentrazone, piraflufén)
- Desecación: Diquat / Paraquat
- MEJOR COMBINACIÓN: Glifosato Premium 1080 g.ea + Flumioxazin (Sumisoya 120ml) + S-metolacloro (Dual Gold 1000ml) → 85-95% control
- Agregar cloracetamida puede tener efecto activador

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
            model="claude-haiku-4-5-20251001",
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
