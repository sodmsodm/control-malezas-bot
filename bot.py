import os
import logging
import anthropic
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters, CallbackQueryHandler

# --- CONFIGURACION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# --- ADMIN Y MONITOREO ---
ADMIN_USER_ID = 1146686012  # Simon — unico autorizado para /stats
user_stats = {}  # {user_id: {"first_name": str, "count": int, "queries": [str]}}

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- INFO DE COADYUVANTES ---
COADYUVANTES_INFO = (
    "💧 COADYUVANTES Y ACEITES — Opciones y dosis:\n\n"
    "Coadyuvantes:\n"
    "✅ A35 T Bio — Coadyuvante — 40-80 cc/ha\n"
    "✅ wr4 BIO — Corrector — 40-80 cc/ha\n"
    "✅ Alltec Ultra — Coadyuvante + Corrector — 80-100 cc/ha\n"
    "✅ Mso max — Coadyuvante + Aceite — 200-250 cc/ha\n"
    "✅ Version — Aceite — 0,5-1 l/ha\n"
    "✅ A35 T GOLD — Coadyuvante + Aceite — 100-150 cc/ha\n\n"
    "Compatibilizador:\n"
    "✅ ALL OK — Prevén / Correctivo — 400-600 cc/ha"
)

# --- INFO DE 2,4D ---
INFO_2_4D = (
    "📋 2,4D — FORMULACIONES Y DOSIS (Fuente: CINVARP / Ojos del Salado)\n\n"
    "DOSIS POR EQUIVALENTE ÁCIDO:\n"
    "✅ 360 g ia/ha — BAJA: malezas chicas, acompañando otros activos con buena eficacia POE\n"
    "✅ 500 g ia/ha — NORMAL: uso general, óptimo para barbechos\n"
    "⚠️ 750 g ia/ha — MODERADA: malezas fuera del tamaño óptimo, doble golpe\n"
    "⚠️ 1150 g ia/ha — ALTA: malezas comprometidas. Respetar carencias en cultivos sensibles\n\n"
    "CONVERSIÓN SEGÚN FORMULACIÓN:\n"
    "✅ Éster 643 g/L (97 Sigma, Herbifen Advance): 500 g ia = 778 cc/ha\n"
    "✅ Éster 590 g/L (Voleris, LV 89 Sigma, Tornado): 500 g ia = 847 cc/ha\n"
    "✅ Sal DMA 500 g/L (60 Sigma): 500 g ia = 1000 cc/ha\n"
    "✅ Sal Colina 456 g/L (Enlist, Empiric Fusión): 500 g ia = 1096 cc/ha\n\n"
    "⚠️ Para biotipos resistentes usar SIEMPRE formulación éster — mayor eficacia sistémica"
)

# --- INFO DE GLIFOSATO ---
INFO_GLIFOSATO = (
    "📋 GLIFOSATO — FORMULACIONES Y DOSIS (Fuente: CINVARP / Ojos del Salado)\n\n"
    "DOSIS POR EQUIVALENTE ÁCIDO:\n"
    "✅ 500 g ia/ha — BAJA: dosis acompañante, la acción principal está en otros herbicidas\n"
    "✅ 810 g ia/ha — NORMAL: uso general, óptimo para barbechos\n"
    "⚠️ 1080 g ia/ha — MODERADA: malezas sensibles sobre tamaño óptimo. Tolerantes chicas con acompañantes\n"
    "⚠️ 1350 g ia/ha — MODERADA A ALTA: malezas sensibles grandes. Tolerantes medianas con acompañantes\n"
    "🔴 1650 g ia/ha — ALTA: malezas sensibles de tamaños comprometidos\n\n"
    "CONVERSIÓN SEGÚN FORMULACIÓN:\n"
    "✅ Sal Monoamónica 720 g/L (Control Max — Bayer): 810 g ia = 1,125 L/ha\n"
    "✅ Sal Amónica 689 g/L (Max Sigma): 810 g ia = 1,177 L/ha\n"
    "✅ Sal Potásica 575 g/L (RoundUp Top — Bayer): 810 g ia = 1,409 L/ha\n"
    "✅ Sal Potásica 540 g/L (LT Platinum II, Power Plus II, Full II Sigma): 810 g ia = 1,500 L/ha\n"
    "✅ Sal Potásica 506 g/L (Sulfosato — Syngenta): 810 g ia = 1,601 L/ha\n"
    "✅ Sal Dimetilamina 480 g/L (Panzer Gold — Corteva): 810 g ia = 1,688 L/ha\n"
    "✅ Sal Isopropilamina 445 g/L (Gold Sigma): 810 g ia = 1,820 L/ha\n\n"
    "⚠️ Glifosato 48% referencia histórica: 2 L/ha = 890 g ia/ha — dosis NORMAL para barbechos"
)

KNOWLEDGE_BASE = """
=== REGLAS DEL SISTEMA ===

REGLA FUNDAMENTAL: Respondé ÚNICAMENTE con información contenida en esta base de conocimiento. NUNCA improvises ni uses conocimiento externo.

Distinguí tres situaciones:
1. CONSULTA COMPLETA (cultivo + maleza presentes en la base): respondé ÚNICAMENTE con la sección específica de esa maleza. NUNCA uses la sección "PRINCIPALES" ni "TODOS LOS HERBICIDAS POR MOMENTO" si la maleza fue especificada.
2. CONSULTA GENERAL SIN MALEZA ESPECÍFICA (pregunta sobre cultivo + momento sin mencionar maleza — ej: "PEE en trigo", "POE en soja", "herbicidas en maíz"): este es SIEMPRE caso 2, NUNCA caso 3. Buscá la sección "CULTIVO: MOMENTO — PRODUCTOS PRINCIPALES" correspondiente y volcá su contenido COMPLETO sin resumir ni recortar. NO mezcles con información de otras secciones del mismo cultivo.
3. CULTIVO AUSENTE DE LA BASE: SOLO si el cultivo mencionado no existe en la base (ej: papa, algodón, citrus, caña), respondé: "No tengo información específica para ese cultivo. Puedo ayudarte con soja, maíz, girasol, trigo, cebada, sorgo, colza, arveja o camelina."

NOTA CEBADA: Las consultas sobre cebada (forrajera o cervecera) se responden con la misma información que trigo. Las secciones TRIGO aplican a ambos cultivos.

ESTRUCTURA DE RESPUESTA OBLIGATORIA:
PARTE 1 — HERBICIDAS, DOSIS, MARCAS Y MOMENTOS DE APLICACIÓN (PEE, POE, barbecho, presiembra): usá ÚNICAMENTE información de la base. Sin excepciones. Nunca agregues productos, dosis ni momentos que no estén textualmente en la base.
PARTE 2 — ADVERTENCIAS Y CONSEJOS: podés complementar con conocimiento agronómico general para enriquecer la respuesta, siempre que no contradiga la base ni agregues productos o dosis no registrados.

REGLA DE SEGURIDAD CRÍTICA: Distinguí siempre POE/PEE del cultivo vs POE de la maleza. Un herbicida que se aplica en barbecho (POE maleza) puede ser fitotóxico en POE del cultivo. NUNCA recomiendes un ACCasa (cletodim, haloxyfop, propaquizafop) en POE de maíz convencional o RR. Son FITOTÓXICOS en maíz.

REGLA DE BIOTIPOS: Siempre presentá opciones diferenciadas por biotipo (RR, STS, CL, HB4, Enlist, convencional). Nunca colapses opciones de distintos biotipos en una sola lista.

REGLA DE MARCAS COMERCIALES: Siempre incluí el nombre comercial entre paréntesis junto al principio activo. Ej: Cletodim 24% (Select), Glifosato 48% (Roundup).

REGLA DE FORMATO — CRÍTICA Y ABSOLUTA:
PROHIBIDO ABSOLUTAMENTE: ##, ###, **texto**, *texto*, ---, tablas con |columnas|, guiones como viñeta al inicio de línea (-). Telegram muestra estos caracteres como texto plano sin ningún formato — el usuario ve símbolos basura.
OBLIGATORIO SIEMPRE: viñetas con emojis. ✅ para opciones recomendadas, ⚠️ para advertencias críticas, 🔁 para doble golpe, 🌱 para momento de aplicación.
Las secciones se separan con una línea en blanco y un título en MAYÚSCULAS sin ningún símbolo Markdown.
Esta regla aplica SIEMPRE, incluso cuando no encontrás información específica y respondés con el mensaje de "no tengo información".

EJEMPLO CORRECTO — exactamente así debe verse cada respuesta:

ANTES DE SIEMBRA
✅ Glifosato 48% (2 L/ha) + Cletodim 24% (Select) 0,7-1 L/ha
⚠️ Mínimo 10 DAS antes de siembra

PEE
✅ Piroxasulfone 85% (Yamato) 160-200 g/ha
✅ Pendimetalín (Herbadox)

EJEMPLO INCORRECTO — NUNCA hacer esto:
### Antes de siembra
- Glifosato + Cletodim
**Atención:** mínimo 10 DAS
| Producto | Dosis |
|---|---|

=== 2,4D — FORMULACIONES Y DOSIS POR EQUIVALENTE ÁCIDO ===
Fuente: CINVARP / Ojos del Salado — Ing. Agr. Mauro Mortarini MP 891

DOSIS DE REFERENCIA POR g ia/ha:
✅ 360 g ia/ha — BAJA: malezas chicas, acompañando otros activos con buena eficacia POE. Buscando selectividad en el cultivo
✅ 500 g ia/ha — NORMAL: dosis de uso general, óptimo para barbechos. Adecuada para combinar con otros hormonales complementarios
⚠️ 750 g ia/ha — MODERADA: tamaños fuera del óptimo sin llegar a comprometidos. Asociada a doble golpe. Respetar carencias en cultivos sensibles
⚠️ 1150 g ia/ha — ALTA: tamaños comprometidos. Requiere tolerancia en cultivo o respetar carencias. Asociada a planteos secuenciales

CONVERSIÓN SEGÚN FORMULACIÓN DISPONIBLE:
✅ Éster etilhexílico 643 g/L (97 Sigma, Herbifen Advance — Atanor): 500 g ia = 778 cc/ha
✅ Éster etilhexílico 590 g/L (Voleris — Syngenta, LV 89 Sigma, Tornado — UPL): 500 g ia = 847 cc/ha
✅ Sal dimetilamina 500 g/L (60 Sigma): 500 g ia = 1000 cc/ha
✅ Sal colina 456 g/L (Enlist — Corteva, Empiric Fusión): 500 g ia = 1096 cc/ha

⚠️ Para barbecho con biotipos resistentes usar SIEMPRE formulación éster — mayor eficacia sistémica que sal amina o sal colina
⚠️ La dosis "800 cc/ha éster 48%" referencia histórica equivale a ~500 g ia/ha — dosis NORMAL

=== GLIFOSATO — FORMULACIONES Y DOSIS POR EQUIVALENTE ÁCIDO ===
Fuente: CINVARP / Ojos del Salado — Ing. Agr. Mauro Mortarini MP 891

DOSIS DE REFERENCIA POR g ia/ha:
✅ 500 g ia/ha — BAJA: dosis acompañante. La acción principal está en otros herbicidas
✅ 810 g ia/ha — NORMAL: uso general, óptimo para barbechos
⚠️ 1080 g ia/ha — MODERADA: malezas sensibles sobre tamaño óptimo. Tolerantes chicas con acompañantes
⚠️ 1350 g ia/ha — MODERADA A ALTA: malezas sensibles grandes. Tolerantes medianas con acompañantes
🔴 1650 g ia/ha — ALTA: malezas sensibles de tamaños comprometidos

CONVERSIÓN SEGÚN FORMULACIÓN DISPONIBLE:
✅ Sal Monoamónica 720 g/L (Control Max — Bayer): 810 g ia = 1,125 L/ha
✅ Sal Amónica 689 g/L (Max Sigma — Sigma): 810 g ia = 1,177 L/ha
✅ Sal Potásica 575 g/L (RoundUp Top — Bayer): 810 g ia = 1,409 L/ha
✅ Sal Potásica 540 g/L (LT Platinum II — Bayer, Power Plus II — Atanor, Full II Sigma): 810 g ia = 1,500 L/ha
✅ Sal Potásica 506 g/L (Sulfosato — Syngenta): 810 g ia = 1,601 L/ha
✅ Sal Dimetilamina 480 g/L (Panzer Gold — Corteva): 810 g ia = 1,688 L/ha
✅ Sal Isopropilamina 445 g/L (Gold Sigma): 810 g ia = 1,820 L/ha

⚠️ Glifosato 48% (sal isopropilamina 445 g/L) referencia histórica: 2 L/ha = 890 g ia/ha — dosis NORMAL para barbechos

=== ACEITES Y COADYUVANTES ===

REGLA GENERAL: El coadyuvante lo determina el mecanismo de acción del herbicida principal, no el cultivo.

ACCasa (cletodim, haloxyfop, propaquizafop, quizalofop):
✅ Aceite vegetal o metilado de soja 0,5-1% v/v. SIEMPRE.

PPO contacto (saflufenacil/Heat, carfentrazone/Shark, flumioxazin/Sumisoya):
✅ Aceite vegetal 0,5% v/v. EXCEPCION: saflufenacil en trigo desde Z1.2-Z1.3 SIN aceite (fitotóxico).

Glufosinato de amonio:
✅ Surfactante no iónico 0,1% + Sulfato de amonio 2 kg/ha.

HPPD en maíz POE (mesotrione/Callisto, topramezone/Convey, tembotrione/Laudis):
✅ Aceite según marbete del producto específico.

ALS/sulfonilureas — incluye halosulfurón (Sempra):
✅ Surfactante no iónico 0,1-0,2% v/v. NUNCA aceite mineral.

Hormonales (2,4D, MCPA, dicamba, fluroxipir):
✅ Opcional. No obligatorio.

Glifosato solo:
✅ Sulfato de amonio 2 kg/ha. No aceite.

Triazinas y residuales de suelo:
✅ No necesitan coadyuvante foliar.

REGLA MEZCLAS CON GLIFOSATO: el aceite lo determina el herbicida principal de la mezcla, no el glifosato.

=== RESIDUALIDAD DE HERBICIDAS ===

Producto (p.a.) — días mínimos antes de siembra siguiente:
✅ Atrazina 90%: Maíz 0 / Sorgo 0 / Soja 365 / Girasol 365 / Trigo 365
✅ Metribuzin 48% (Sencorex): Soja 0 / Trigo 60 / Maíz 90 / Girasol 120
✅ Sulfentrazone 50% (Authority/Capaz): Soja 0 / Maíz 120 / Girasol 180 / Trigo 180
✅ Diclosulam 84% (Spider): Soja 0 / Maíz 18m / Girasol NO / Trigo NO
✅ Imazetapir 10% (Pivot): Soja 0 / Maíz 9m / Girasol 18m / Trigo 12m
✅ Fomesafén 25% (Flex): Soja 0 / Maíz 12m / Girasol RIESGO / Trigo 18m
✅ Flumioxazin 48% (Sumisoya): Soja 7d / Maíz 30d / Girasol 30d / Trigo 30d
✅ S-metolacloro 96% (Dual Gold): Maíz 0 / Soja 0 / Girasol 0 / Trigo 0
✅ Piroxasulfone 85% (Yamato): Soja 0 / Maíz 0 / Trigo 90d
✅ Clorimurón 25% (Classic): Soja 0 / Maíz 18m / Girasol 18m / Trigo 18m
✅ Saflufenacil 70% (Heat): Soja 3d / Maíz 1d / Trigo 1d / Girasol: NO usar en pre-siembra ni barbecho previo a girasol (marbete BASF)
✅ Metsulfurón 60% (Ally/Errasin): Soja 60d / Maíz 60d / Girasol: NO usar en barbecho previo a girasol
✅ Flurocloridona 25% (Rainbow): Girasol 0 / Trigo 0 / Maíz 0 / Soja: sin registro formal — en ensayos 30-40 días sin problemas (Gigón, Agroconsultas 2020)
✅ Diflufenicán 50% (Brodal): Trigo 0 / Girasol 0 / Soja 15d / Maíz 15d
✅ Halosulfurón metil 75% (Sempra): Maíz 0 / Soja 0 / Trigo NO / Girasol NO — Carencia 90 días cultivo siguiente no tolerante
✅ Imazapic 240 g/L (Pivot): Maíz CL 0 / Soja 0 / Girasol CL 0 — FITOTÓXICO en maíz convencional. Carencia 90 días.

=== FENOLOGÍA DE CULTIVOS ===

TRIGO / CEBADA — Escala Zadoks:
✅ Z1.0: Emergencia / 1 hoja
✅ Z1.2-Z1.3: 2-3 hojas (inicio aplicación saflufenacil, bromoxinil, clodinafop)
✅ Z1.5: 5 hojas
✅ Z2.1-Z2.5: Macollaje (inicio 2,4D, sulfonilureas)
✅ Z3.0: Fin macollaje / encañazón
✅ Z5.9: Espigazón
✅ Z7.7: Grano lechoso

MAÍZ — Escala Ritchie y Hanway:
✅ VE: Emergencia
✅ V1-V6: 1 a 6 hojas
✅ V8: 8 hojas (fin ventana mayoría de herbicidas POE)
✅ VT: Panojamiento
✅ R1: Floración
✅ R6: Madurez fisiológica

SORGO — Escala Vanderlip y Reeves:
✅ VE: Emergencia
✅ V2-V4: 2-4 hojas
✅ V8: 8 hojas
✅ Vn: Panojamiento

SOJA — Escala Fehr y Caviness:
✅ VE: Emergencia
✅ V1-V2: 1-2 nudos
✅ V4-V6: 4-6 nudos (ventana principal POE)
✅ R1: Floración
✅ R2: Plena floración

GIRASOL — Escala Schneiter y Miller:
✅ VE: Emergencia
✅ V2-V4: 2-4 hojas
✅ V8-V10: 8-10 hojas
✅ R1: Botón floral visible
✅ R5: Floración
✅ R9: Madurez fisiológica

COLZA / ARVEJA / CAMELINA — Escala BBCH:
✅ BBCH 10-13: Cotilédones a 3 hojas
✅ BBCH 14-16: 4-6 hojas (ventana principal POE colza/arveja)
✅ BBCH 20-29: Macollaje/ramificación

=== CONSIDERACIONES GENERALES DE MANEJO ===

GIRASOL: ESTRATEGIA Y MALEZAS PROBLEMA
Fuente: REM Aapresid / Jorgelina Montoya INTA Anguil. Campaña 2025.

BIOLOGÍA Y VENTANA CRÍTICA:
✅ Baja densidad (5 pl/m2) + crecimiento inicial lento — el cultivo tarda ~5 semanas en cerrar canopeo
✅ Los primeros 30-35 días desde emergencia son la ventana crítica de competencia de malezas
✅ Después del cierre de canopeo el cultivo gana ventaja por sombreo

MALEZAS PROBLEMA CLAVE EN GIRASOL (2025):
⚠️ Rama negra (Conyza): biotipos con resistencia múltiple — control anticipado obligatorio
⚠️ Crucíferas: biotipos resistentes a ALS, glifosato, 2,4D y RECIENTEMENTE A FLUROCLORIDONA
⚠️ Morenita: resistencia a ALS y glifosato confirmada en oeste de Buenos Aires
⚠️ Yuyo colorado: biotipos resistentes a glifosato, 2,4D, ALS, PREOCUPACION CRECIENTE por resistencia a PPO
⚠️ Gramíneas estivales: muchas con resistencia a glifosato, ALS y graminicidas
⚠️ Raigrás: avanzando del sur al centro del país

CARRY-OVER — RIESGO FITOTOXICIDAD EN CULTIVO ANTECESOR:
⚠️ Fomesafen (Flex) en soja antecesora + menos de 300mm acumulados antes de siembra — RIESGO en girasol
⚠️ Diclosulam (Spider) en soja antecesora — RESTRINGE directamente la posibilidad de sembrar girasol
⚠️ Topramezone (Convey) en maíz + campaña seca + lote de baja productividad — daños residuales posibles
⚠️ Sulfonilureas en barbecho o cultivo invernal + ambiente seco — riesgo de carry-over para girasol

ESTRATEGIA POR MOMENTO:
🌱 BARBECHO: clave para malezas otoño-invernales
🌱 PEE: momento más importante. Dosis ajustar por MO, arena, pH y humedad de suelo
🌱 POE: opciones muy limitadas


BRASICÁCEAS / CRUCÍFERAS: BIOLOGÍA, RESISTENCIAS Y ESTRATEGIA TRANSVERSAL
Fuente: Diez de Ulzurrun P., Gigón R., Yanniccari M. — REM Aapresid. Junio 2024.

IDENTIFICACIÓN:
✅ Brassica rapa (Nabo/nabolza): flor AMARILLA, silicua dehiscente, hojas amplexicaules
✅ Raphanus sativus (Nabón): flor VIOLÁCEA/ROSADA/BLANCA, silicua INDEHISCENTE y corchosa, hojas pecioladas
✅ Hirschfeldia incana (Nabillo/mostacilla): flor AMARILLO PÁLIDO, silicua adpresa al raquis
✅ Rapistrum rugosum (Mostacilla): fruto SILÍCULA indehiscente globosa

RESISTENCIAS CONFIRMADAS EN ARGENTINA (REM Aapresid 2024):
⚠️ Hirschfeldia incana: ALS / ALS+2,4D / Glifosato+2,4D
⚠️ Brassica napus (colza feral): Glifosato (transgén GT73)
⚠️ Brassica rapa: ALS+Glifosato / ALS+Glifosato+2,4D (triple)
⚠️ Rapistrum rugosum: ALS (desde 2018 Entre Ríos, expandiéndose)
⚠️ Raphanus sativus: ALS (mutación W574L)

ESTRATEGIA QUÍMICA EN BARBECHO — ROSETA CHICA menor a 10 cm:
Base: Glifosato + Hormonal (2,4D o MCPA) + acompañante:
✅ PPO: carfentrazone 40% (Shark), piraflufen 2,5% (Stagger), saflufenacil 70% (Heat), flumioxazin 48% (Sumisoya)
✅ Fotosistema II: atrazina 90%, metribuzin 48% (Sencorex), amicarbazone 70% (Dinamic), terbutilazina 75% (Terbine)
✅ HPPD/PDS: biciclopirona 20%, mesotrione 48% (Callisto), diflufenicán 50% (Brodal)

ESTRATEGIA QUÍMICA EN BARBECHO — ROSETA GRANDE mayor a 10 cm — Doble Golpe:
🔁 1° Aplicación sistémica: Glifosato + 2,4D o MCPA + PPO/Triazina/HPPD
🔁 2° Aplicación desecante: Paraquat 27,6% (Gramoxone) / Diquat 40% (Reglone) / Glufosinato 28%

REGLA CRÍTICA POR TIPO DE RESISTENCIA:
⚠️ Con resistencia a ALS: NO usar sulfonilureas ni imidazolinonas
⚠️ Con resistencia a glifosato: agregar PPO quemante (Heat, Shark) a la mezcla base
⚠️ Con TRIPLE resistencia: Glifosato+PPO/Triazina en 1° app + desecante DG


COMMELINA ERECTA: BIOLOGÍA Y ESTRATEGIA DE CONTROL
Fuente: Panigo E., Cortés E., Vernier F. — REM Aapresid. Mayo 2025.

TOLERANCIA AL GLIFOSATO:
⚠️ Plantas menores a 5 hojas de semilla: buen manejo posible con herbicidas
⚠️ Plantas mayores a 5 hojas o de rebrote de rizoma: TOLERANTES — glifosato solo alcanza menos de 30% de control

DOS ÉPOCAS CLAVE DE INTERVENCIÓN QUÍMICA:
🌱 OTOÑO: Base Glifosato + 2,4D. Opción para rizomas: Imazapir 200 cc/ha (al 48%) — ANTES de heladas
🌱 PRIMAVERA: Base Glifosato + 2,4D + acompañante residual según cultivo siguiente

Acompañantes según eficacia (REM Aapresid 2025):
✅ HPPD — promedio 72%: Biciclopirona 20% 1000 cc/ha MEJOR / Mesotrione 48% / Tembotrione 42%
✅ ALS — promedio 64%: Diclosulam 84% 30-40 g/ha MEJOR / Imazetapir 10% / Nicosulfuron
✅ PPO — promedio 63%: Flumioxazin 48% 150 cc/ha MEJOR / Saflufenacil 70% / Carfentrazone 40%
✅ TRIAZINAS — promedio 59%: Metribuzin 48% 0,8-1 l/ha / Amicarbazone 70% / Atrazina 90%

DOBLE GOLPE (DG):
🔁 2° aplicación: Paraquat 27,6% (Gramoxone) o Glufosinato de amonio 28% 2500-3000 cc/ha

ESTRATEGIA POR BIOTIPO:
✅ SOJA RR: glifosato solo menos de 30% de control. Control pre-siembra obligatorio
✅ SOJA ENLIST: POE — Glufosinato + Glifosato + 2,4D — más de 80% de control
✅ MAÍZ ENLIST: muy buenos niveles de control en POE
✅ MAÍZ SIN ENLIST: HPPD + Triazina como aplicación secuencial POE


TRÉBOL BLANCO (Trifolium repens): ESTRATEGIA DE CONTROL EN BARBECHO
Fuente: Corteva / INTA Oliveros / Marbete Starane Xtra SENASA No.35.712.

✅ OPCIÓN PRINCIPAL: Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha
✅ OPCIÓN CON PPO: + Saflufenacil 70% (Heat) 25-35 g/ha
✅ OPCIÓN MARBETE: Glifosato 48% (3 l/ha) + Fluroxipir 33% (Starane Xtra) 360 cc/ha


CYPERUS ROTUNDUS (CEBOLLÍN): BIOLOGÍA Y ESTRATEGIA TRANSVERSAL
Fuente: Uso interno / Marbete SEMPRA SENASA Nº35.981 / Marbete Pivot SENASA Nº33.606.

SENSIBILIDAD A HERBICIDAS:
✅ Glifosato: sensible a dosis altas (mayor o igual a 2000 g.e.a./ha). Requiere cebollín en activo crecimiento, 6-8 hojas
✅ Halosulfurón metil (Sempra): muy eficaz. Aplicar con cebollín a ~15 cm
✅ Imazapic (Pivot): control PARCIAL. Tiene acción residual que limita rebrotes
✅ Imazetapir 10%: buenos resultados en mezcla con glifosato. Aporta residualidad
✅ Clorimurón (Classic): buenos resultados en mezcla con glifosato
⚠️ CONTROL NUNCA ES 100% TOTAL — requiere estrategia de largo plazo

MEZCLAS CON BUENOS RESULTADOS (uso antes de siembra):
✅ Glifosato 3 L/ha + Clorimurón 25% 60-80 g/ha (Classic)
✅ Glifosato 3,5 L/ha + Imazetapir 10% 800 cc/ha + humectante — NO sembrar alfalfa pura en rotación
✅ Aplicar siempre con surfactante no iónico 0,1-0,2% v/v
"""

KNOWLEDGE_BASE += """
=== BARBECHO — ESTRATEGIAS POR MALEZA Y CULTIVO SIGUIENTE ===

NOTAS GENERALES BARBECHO:
⚠️ COADYUVANTES OBLIGATORIOS: Cletodim y graminicidas ACCasa requieren aceite vegetal o metilado 0,5-1% v/v SIEMPRE. PPO de contacto (Heat, Shark) requieren aceite vegetal 0,5% v/v. Glufosinato requiere surfactante no iónico 0,1% + sulfato de amonio 2 kg/ha. Ver sección COADYUVANTES.
⚠️ 2,4D: usar formulación éster. Dosis 500 g ia/ha = dosis NORMAL para barbecho. Ver sección 2,4D para conversión según formulación.
⚠️ GLIFOSATO: dosis 810 g ia/ha = dosis NORMAL para barbecho. Ver sección GLIFOSATO para conversión según formulación.
⚠️ PPO DE CONTACTO — DOSIS POR TAMAÑO: Saflufenacil (Heat) 35 g/ha maleza chica / 40 g/ha maleza pasada de tamaño. Carfentrazone (Shark) 75 cc/ha maleza chica / 120 cc/ha maleza pasada de tamaño.
⚠️ Heat NO usar en pre-siembra de girasol. Shark válido en todos los cultivos sin restricción.

BARBECHO LARGO: aplicación abril-junio. Objetivo: pico 1 de emergencia otoñal.
BARBECHO CORTO: aplicación agosto-septiembre. Objetivo: pico 2 de emergencia y presiembra inmediata.
TRIGO: sin distinción largo/corto — siempre presiembra por calendario de siembra invernal.

--- LOLIUM (RAIGRÁS) EN BARBECHO ---

LOLIUM — BARBECHO LARGO — SOJA / MAÍZ (abril-junio):

⚠️ MOMENTO: Aplicaciones en marzo-abril pierden eficacia a los 60-75 días si se usan solas. En abril sumar residual o usar doble golpe. Desde mayo la aplicación simple sostiene mejor el control.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ABRIL:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe con residual
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — sin residual de suelo, agrega MOA

MAYO-JUNIO:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha de resistencia ACCasa

⚠️ RESISTENCIA ACCasa: Cletodim solo puede quedar entre 5-70% según biotipo. Ante sospecha usar mezcla triple o doble golpe.

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

⚠️ Los residuales actúan en suelo sobre semillas y plántulas antes de emerger. No eliminan maleza ya nacida. Combinar siempre con sistémico si hay plantas visibles.

SOJA Y MAÍZ:
🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — mejor residualidad sostenida hasta 150 DDA. Sin restricción en soja ni maíz
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha sola — buena residualidad hasta 90 DDA
🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha — desempeño similar como opción individual
⚠️ Pyroxasulfone (Yamato) tiene restricción de 90 días antes de siembra de trigo. Sin restricción en soja ni maíz.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

SOJA Y MAÍZ — ABRIL:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe completo, máximo control
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — aplicación única con residual
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha — una opción residual

SOJA Y MAÍZ — MAYO-JUNIO:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


LOLIUM — BARBECHO LARGO — GIRASOL (abril-junio):

⚠️ Atrazina fitotóxica en girasol — NO usar.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ABRIL:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe con residual
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — sin residual de suelo, agrega MOA

MAYO-JUNIO:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha de resistencia ACCasa

⚠️ RESISTENCIA ACCasa: Ante sospecha usar mezcla triple o doble golpe.

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — mejor residualidad. Sin restricción en girasol
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha sola
🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha — desempeño similar

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

ABRIL:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha

MAYO-JUNIO:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


LOLIUM — BARBECHO — TRIGO (presiembra):

⚠️ Pyroxasulfone (Yamato): 90 días de carencia antes de trigo. Verificar fechas antes de usar.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

SITUACIÓN 1 — 1-2 hojas, baja densidad:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glufosinato 28% 2 L/ha
🥉 Paraquat 27,6% (Gramoxone) 2 L/ha

SITUACIÓN 2 — 2-4 hojas, densidad media:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 810 g ia/ha + Haloxyfop 54% (Galant Max) 0,5 L/ha
🥉 Glifosato 810 g ia/ha + Cletodim 12%/Haloxyfop 6% (Gramini Elite) 1 L/ha

SITUACIÓN 3 — más de 4 hojas o sospecha de resistencia ACCasa:
🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha
🥈 Glufosinato 28% 2 L/ha + Cletodim 24% (Select) 0,8 L/ha

SITUACIÓN 4 — resistencia confirmada O maleza muy establecida (alta densidad / 5+ macollos) — Doble Golpe:
🔁 1° Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7 días después
🔁 1° Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // 2° Glufosinato 28% 2 L/ha — 7 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Azugro (Bixlozona) FMC — residual específico para Lolium en trigo/avena. Presiembra, sin restricción de carencia en trigo
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en trigo
🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Pendimetalín (Herbadox/Satellite) — ⚠️ pyroxasulfone verificar 90 días de carencia antes de trigo

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Azugro (Bixlozona) — elimina nacida y deja residual específico para trigo
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha — sin residual, opción mínima


LOLIUM — BARBECHO CORTO — SOJA / MAÍZ (agosto-septiembre):

⚠️ MOMENTO: Agosto-septiembre es la ventana óptima. Control sostenido sin necesidad de doble golpe en la mayoría de los casos.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha de resistencia ACCasa
🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

SOJA Y MAÍZ:
🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — sin restricción en soja ni maíz
🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha — sin restricción en soja ni maíz
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


LOLIUM — BARBECHO CORTO — GIRASOL (agosto-septiembre):

⚠️ Atrazina fitotóxica en girasol — NO usar.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha
🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


--- CONYZA (RAMA NEGRA) EN BARBECHO ---

CONYZA — BARBECHO LARGO — SOJA (abril-junio):

⚠️ MOMENTO: Conyza tiene dos picos de emergencia — otoño (abril) y primavera (septiembre). Roseta menor a 10 cm responde mejor. Mayor a 10 cm requiere doble golpe.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — mejor control sostenido a 45 DDA sin paraquat
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — buena combinación hormonal
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — base mínima

PPO de contacto como apoyo (agregar a cualquiera):
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior en control
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción en ningún cultivo

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7-14 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

⚠️ Atrazina — sin registro formal en barbecho a soja. No recomendar.
🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — mejor residualidad sostenida a 120 DDA. Sin restricción en soja
🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha — registrado para barbecho de otoño a soja
🥈 Atrazina 90% 2,25 L/ha — datos de campo muy buenos a 120 DDA. ⚠️ Verificar registro local antes de usar en barbecho a soja
🥉 Finesse (Clorsulfurón + Metsulfurón) 15 g/ha — buena residualidad. ⚠️ 60 días carencia antes de soja
🥉 Metsulfurón 60% (Ally) 7 g/ha — opción económica, algo menor persistencia a 120 DDA

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO LARGO — MAÍZ (abril-junio):

OBJETIVO 1 — igual que soja

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha — combinación más potente, registrada en maíz
🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha — sin atrazina, buena residualidad
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — buena residualidad hasta 120 DDA

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO LARGO — GIRASOL (abril-junio):

⚠️ Atrazina fitotóxica — NO usar. Biciclopirone sin registro en girasol — NO usar. Saflufenacil NO usar en pre-siembra girasol. Metsulfurón NO usar en barbecho previo a girasol.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo antes de siembra girasol
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha

PPO de contacto como apoyo:
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — único PPO disponible en pre-siembra girasol

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en girasol
🥈 Atrazina 90% 2,25 L/ha — ⚠️ 90 días de intervalo antes de siembra girasol. Solo en barbecho largo con siembra a más de 90 días
🥉 Diflufenican 50% (Brodal) 250 cc/ha — 0 días intervalo en girasol. Menor residualidad que las anteriores

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Carfentrazone 40% (Shark) 75 cc/ha — ⚠️ verificar 45 días Lontrel
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Carfentrazone 40% (Shark) 75 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + residual + Shark // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO — TRIGO (presiembra):

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días intervalo en trigo
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días intervalo
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — 3-5 días intervalo

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Metsulfurón 60% (Ally/Errasin) 7-8 g/ha — 0 días intervalo en trigo. Buena residualidad para Conyza
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — buena residualidad hasta 120 DDA
🥉 Diflufenican 50% (Brodal) 250 cc/ha — 15 días intervalo en trigo. Menor residualidad

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO CORTO — SOJA / MAÍZ (agosto-septiembre):

⚠️ MOMENTO: Segundo pico de emergencia. Plántulas pequeñas — mejor momento para control.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

SOJA:
🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha — registrado barbecho otoño a soja
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — ⚠️ verificar 45 días antes de siembra soja
🥉 Voraxor (Trifludimoxazin/Saflufenacil) 0,1-0,15 L/ha — sin restricción en soja

MAÍZ:
🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

SOJA:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — ⚠️ verificar 45 días

MAÍZ:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha


CONYZA — BARBECHO CORTO — GIRASOL (agosto-septiembre):

⚠️ Pixxaro puede aplicarse hasta 0 días antes de siembra de girasol — ventaja clave en barbecho corto.
⚠️ Saflufenacil, metsulfurón NO usar en pre-siembra girasol.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 810 g ia/ha + Pixxaro (Halauxifen metil + Fluroxipir) 400-500 cc/ha + aceite mineral 1% v/v — registrado específicamente para Conyza en pre-siembra girasol, sin restricción de intervalo (SENASA N° 40.386)
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — ⚠️ 7-15 días antes de siembra girasol
🥉 Glifosato 810 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días antes de siembra girasol

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + Pixxaro 500 cc/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7-14 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en girasol
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en girasol
🥉 Diflufenican 50% (Brodal) 250 cc/ha — 0 días intervalo en girasol. Menor residualidad

⚠️ Atrazina — 90 días de intervalo. No alcanza en barbecho corto para siembra inmediata de girasol.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + Pixxaro 400-500 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite mineral 1% v/v
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar 7-15 días antes de siembra
🥉 Glifosato 810 g ia/ha + Pixxaro 400-500 cc/ha + Diflufenican 50% (Brodal) 250 cc/ha + aceite mineral 1% v/v


--- BRASSICA RAPA (NABÓN/NABO/MOSTACILLA) EN BARBECHO ---

⚠️ IDENTIFICACIÓN: Brassica rapa (nabo/nabolza) flor AMARILLA, hojas amplexicaules. Raphanus sativus (nabón) flor VIOLÁCEA/ROSADA. Hirschfeldia incana (nabillo/mostacilla) flor AMARILLO PÁLIDO. Ver sección BRASICÁCEAS para resistencias confirmadas.
⚠️ BIOTIPOS RESISTENTES: Con resistencia a ALS no usar sulfonilureas ni imidazolinonas. Con resistencia a glifosato agregar PPO quemante obligatorio. Con TRIPLE resistencia: doble golpe obligatorio con desecante.

BRASSICA — BARBECHO LARGO — SOJA / MAÍZ (abril-junio):

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 94% control a 45 DDA
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha

PPO de contacto como apoyo (agregar a cualquiera):
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior en control
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción en ningún cultivo

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7-14 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

⚠️ Para Brassica los residuales más eficaces son DIFERENTES a los de Lolium. Pyroxasulfone pierde eficacia a largo plazo para Brassica (61% a 150 DDA). Flurocloridona y Terbutilazina+Diflufenican son los mejores.

SOJA:
🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — 93-95% a 90 DDA en campo
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — 96% a 150 DDA
🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin registro formal en soja, en ensayos 30-40 días sin problemas. En barbecho largo el intervalo se cumple

MAÍZ:
🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — 96% a 150 DDA
🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz

⚠️ Pyroxasulfone (Yamato) — NO es la mejor opción residual para Brassica a largo plazo.
⚠️ Diflufenican solo — opción residual de menor eficacia que la mezcla con terbutilazina pero válida.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

SOJA:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha

MAÍZ:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha


BRASSICA — BARBECHO LARGO — GIRASOL (abril-junio):

⚠️ Biciclopirone sin registro en girasol — NO usar. Atrazina fitotóxica — NO usar. Heat NO usar en pre-siembra girasol. Flurocloridona es la estrella para Brassica en girasol.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo antes de siembra girasol
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días intervalo
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — ⚠️ 7-15 días intervalo

PPO de contacto como apoyo:
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — único PPO disponible en pre-siembra girasol

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Shark 120 cc/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — estrella para Brassica en girasol. 96-97% a 150 DDA. Sin restricción
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — 96% a 150 DDA
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia que la mezcla pero válido. 0 días intervalo girasol

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

ABRIL:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ verificar 45 días Lontrel
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

MAYO-JUNIO:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha


BRASSICA — BARBECHO — TRIGO (presiembra):

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días intervalo en trigo
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días intervalo
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — 3-5 días intervalo

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — 0 días intervalo en trigo. Mejor opción residual para Brassica
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — ⚠️ Brodal 15 días intervalo
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia, 15 días intervalo

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


BRASSICA — BARBECHO CORTO — SOJA / MAÍZ (agosto-septiembre):

⚠️ Verificar intervalos de carencia con especial atención — la siembra es inmediata.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ Lontrel 45 días en soja. Solo si siembra está a más de 45 días
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 15-20 días intervalo en soja
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — 7-15 días intervalo en soja

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción en soja ni maíz

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

SOJA:
🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — sin restricción en soja
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — sin restricción
🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar mínimo 30-40 días antes de siembra soja

MAÍZ:
🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha — sin restricción en maíz
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha
🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

SOJA:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar 30-40 días antes de soja

MAÍZ:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha + Shark 75 cc/ha
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz


BRASSICA — BARBECHO CORTO — GIRASOL (agosto-septiembre):

⚠️ Biciclopirone sin registro — NO usar. Atrazina 90 días intervalo — NO alcanza. Heat NO usar. Flurocloridona es la estrella.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo en girasol
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días intervalo
🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — ⚠️ 7-15 días intervalo

PPO de contacto como apoyo:
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — único PPO en pre-siembra girasol

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Shark 120 cc/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en girasol
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia, 0 días intervalo girasol

⚠️ Atrazina NO alcanza 90 días en barbecho corto a siembra inmediata de girasol.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ verificar 7-15 días antes de siembra
🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha
🥉 Glifosato 810 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ 15-20 días Banvel

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona + Shark // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

=== SOJA ===

SOJA: MALEZA GENERAL (No GMO)

BARBECHO INTERMEDIO (45-60 DAS):
✅ Flumioxazin 48% 150 cc (Sumisoya)
✅ Piroxasulfone 85% 160-200 g (Yamato)
✅ Diflufenicán 50% 0,3 l (Brodal) hasta 15 DAS
✅ Atrazina 90% 1-1,5 kg hasta 40 DAS
✅ Amicarbazone 70% 0,4-0,5 kg (Dinamic) hasta 45 DAS
✅ Terbutilazina 75% 1 kg (Terbine/Gesatop) hasta 45 DAS
✅ Metribuzin 48% 1 l (Sencorex)
✅ Terbutilazina 50%/Flumioxazin 3,8% 1,25 l (Terbyne Max Sipcam) hasta 30 DAS
✅ Sulfometurón 15% + Clorimurón 20% 0,1 kg (Ligate) SOJAS STS

PEE / PSI-PEE:
✅ Sulfentrazone 50% 0,4-0,5 l (Authority/Capaz) + S-metolacloro 96% 1,1-1,3 l (Dual Gold)
✅ Sulfentrazone 50% 0,5 l (Authority/Capaz) + Piroxasulfone 48% 0,355 l
✅ Sulfentrazone 50% 0,5 l (Authority/Capaz) + Imazetapir 10% 0,8-1 l (Pivot)
✅ Sulfentrazone 50% 0,5 l (Authority/Capaz) + Diclosulam 84% 0,03 kg (Spider)
✅ Sulfentrazone 50% 0,4-0,5 l (Authority/Capaz) + Metribuzin 48% 0,8-1 l (Sencorex)
✅ Flumioxazin 15%/Piroxasulfone 34,5% 0,5 l (Fierce FMC) 7 DAS
✅ Flumioxazin 4,2%/S-metolacloro 84% 1,75 l (Apresa ADAMA) 7 DAS
✅ Flumioxazin 5%/S-metolacloro 57,6%/Imazetapir 5% 1,5 l (Zethamaxx Sumitomo) 7 DAS
✅ Flumioxazin 14,5%/Diclosulam 6,5%/Imazetapir 20% 0,5 l (Predecessor DVA) 7 DAS
✅ Flumioxazin 28,8%/Diclosulam 8,4% 0,25 l + S-metolacloro 96% 1,1-1,3 l (Dual Gold) 7 DAS
✅ Flumioxazin 4,2%/Acetoclor 90% 1,5 l (Harness) 7 DAS
✅ Metribuzin 14,9%/S-metolacloro 62,8% 2,5 l (Boundary Syngenta)
✅ Fomesafén 50% 0,4-0,5 l + Metribuzin 48% 0,8-1 l (Sencorex) + Acetoclor 90% 1,5 l (Harness)
✅ Trifludimoxazin/Saflufenacil 0,1-0,2 l (Voraxor) + S-metolacloro 96% 1,1-1,3 l (Dual Gold)

POST-EMERGENCIA CULTIVO (V4-V6):
✅ Fomesafén 25% 1-1,5 l (Flex)
✅ Lactofén 24% 0,6-0,8 l (Cobra)
✅ Cletodim 24% 0,7-1 l (Select) — solo gramíneas
✅ Cletodim 36% 0,5-0,7 l/ha (Select 36) — solo gramíneas
✅ Piroxasulfone 85% 0,16-0,2 kg/ha (Yamato) hasta V4 o V8
✅ Fomesafén 25% 1-1,5 l (Flex) + Benazolín 50% 0,8 l (Dasen)
✅ Fomesafén 25% 1-1,5 l (Flex) + Clorimurón 25% 0,03 kg (Classic)
✅ Clorimurón 25% 0,04-0,05 kg (Classic)
✅ Cloransulam 84% 0,04-0,05 kg (Pacto)
✅ Imazetapir 10% 0,5-0,8 l (Pivot)
✅ 2,4DB 97% e.a. 0,04 l + Bentazón 60% 0,8-1 l (Basagran)
✅ Benazolín 50% 0,6 l (Dasen) + Clorimurón 25% 0,03 g (Classic)


SOJA: CEBOLLÍN (Cyperus rotundus)

PRE-SIEMBRA — cebollín a ~15 cm. Mínimo 10 DAS:
✅ Halosulfurón metil 75% 100-150 g/ha (Sempra) — muy eficaz
✅ Halosulfurón metil 75% 30-50 g/ha (Sempra) + Glifosato 48% 2,5 L/ha
✅ Glifosato 48% 3 L/ha + Clorimurón 25% 60-80 g/ha (Classic)
✅ Glifosato 48% 3,5 L/ha + Imazetapir 10% 800 cc/ha + humectante — NO alfalfa en rotación
✅ Glifosato mayor o igual a 2000 g.e.a./ha solo — 6-8 hojas activo crecimiento. Control parcial

POE CULTIVO:
✅ Imazapic 240 g/L 1 L/ha (Pivot) — hasta 4a hoja cebollín. Control parcial + residual
⚠️ Carencia Pivot: 90 días. Verificar tolerancia variedad soja

COADYUVANTE: Surfactante no iónico 0,1-0,2% v/v. NO aceite mineral.


SOJA: COMMELINA ERECTA

ANTES DE SIEMBRA — POE maleza / PSI cultivo — CON GLIFOSATO:
✅ Glifosato 1260 g.e.a. + 2,4D 1-1,5 l + Saflufenacil 70% 40 g (Heat)
✅ Glifosato + 2,4D + Carfentrazone 40% 70-80 cc (Shark)
✅ Glifosato + 2,4D + Epirefenacil 5,5% 600 cc (Empera)
✅ Glifosato + 2,4D + Flumioxazin 48% 150 cc (Sumisoya)
✅ Glifosato + 2,4D + Imazetapir 10% 0,8-1 l (Pivot)
✅ Glifosato + 2,4D + Trifludimoxazin/Saflufenacil 0,1-0,2 l (Voraxor)
✅ Glifosato + 2,4D + Metribuzin 48% 0,8-1 l (Sencorex)
✅ Glifosato + 2,4D + Amicarbazone 70% 0,4 g (Dinamic) — hasta 45 DAS

ANTES DE SIEMBRA — POE maleza / PSI cultivo — CON GLUFOSINATO:
✅ Glufosinato de amonio 28% 2,5 l + 2,4D
✅ Glufosinato de amonio 28% + 2,4D + Metribuzin 48% 0,8-1 l (Sencorex)
✅ Glufosinato de amonio 28% + 2,4D + Saflufenacil 70% (Heat)
✅ Glufosinato de amonio 28% + 2,4D + Carfentrazone 40% (Shark)
✅ Glufosinato de amonio 28% + 2,4D + Flumioxazin 48% (Sumisoya)
✅ Glufosinato de amonio 28% + 2,4D + Trifludimoxazin/Saflufenacil (Voraxor)

DOBLE GOLPE:
🔁 1° Glifosato + 2,4D // 2° Paraquat 27,6% (Gramoxone)
🔁 1° Glifosato + 2,4D // 2° Glufosinato de amonio 28%
🔁 1° Glifosato + 2,4D // 2° Glufosinato 28% 2-3 l + Saflufenacil 70% 35-40 g (Heat)
🔁 1° Glifosato + 2,4D // 2° Glufosinato 28% 2-3 l + Carfentrazone 40% 70-80 cc (Shark)

SOJAS ENLIST:
✅ Glifosato 1260 g.e.a. + Glufosinato de amonio 28% + 2,4D 30% e.a. 1,5-2 l — hasta V4-V6
✅ Glufosinato de amonio 28% 2-2,5 l + 2,4D 30% e.a. 1,5-2 l — hasta V4-V6


SOJA: CRUCIFERAS

ANTES DE SIEMBRA — POE maleza / PSI cultivo:
✅ Glifosato + 2,4D o Glifosato + MCPA 28% 1,5-2,5 l
✅ Glifosato + 2,4D o MCPA + Saflufenacil 70% 35-40 g (Heat)
✅ Glifosato + 2,4D o MCPA + Carfentrazone 40% 70-80 cc (Shark)
✅ Glifosato + 2,4D o MCPA + Epirefenacil 5,5% 600 cc (Empera)
✅ Glifosato + 2,4D o MCPA + Trifludimoxazin/Saflufenacil 0,1-0,15 l (Voraxor)
🔁 1° Glifosato + 2,4D // 2° Paraquat 27,6% 1,5-2,5 l (Gramoxone)

PEE / PSI-PEE:
✅ Metribuzin 48% 0,8-1 kg (Sencorex)
✅ Sulfentrazone 50% (Authority/Capaz)
✅ Flumioxazin 48% (Sumisoya) 7 DAS
✅ Diflufenicán 50% (Brodal) 15 DAS
✅ Trifludimoxazin 12,5%/Saflufenacil 25% (Voraxor) 7 DAS

POST-EMERGENCIA CULTIVO — Maleza ROSETA PEQUEÑA (5-8 cm):
✅ Fomesafén 25% 1-1,5 l (Flex)
✅ Acifluorfén 24% 1-1,5 l (Blazer)
✅ Lactofén 24% (Cobra)
✅ Bentazón 60% 1,5 l (Basagran)
✅ Imazetapir 10% 0,5-0,8 l (Pivot) + Clorimurón 25% 0,04 kg (Classic)
⚠️ En biotipos con resistencia a ALS no usar sulfonilureas ni imidazolinonas

SOJAS ENLIST:
✅ Glufosinato de amonio 28% 2-3 l hasta V4-V6
✅ 2,4D 30% e.a. 1,5-2 l hasta R2
✅ Glufosinato de amonio 28% 2-3 l + 2,4D 30% e.a. 1,5-2 l hasta V4-V6


SOJA: PARIETARIA

BARBECHO LARGO:
✅ Atrazina 90% 1-1,5 kg hasta 60 DAS
✅ Amicarbazone 70% (Dinamic) hasta 45 DAS
✅ Terbutilazina 75% (Terbine/Gesatop) hasta 45 DAS
✅ Metsulfurón 60% 6-8 g hasta 60 DAS
✅ Flumioxazin 48% (Sumisoya)

PEE / PSI-PEE:
✅ Metribuzin 48% (Sencorex)
✅ Prometrina 48% (Gesagard)
✅ Paraquat 27,6% (Gramoxone) + Metribuzin 48% (Sencorex)
✅ Trifludimoxazin/Saflufenacil (Voraxor) 7 DAS

POST-EMERGENCIA: Sin opciones efectivas.


SOJA: AMARANTHUS SPP. (Yuyo Colorado)

ANTES DE SIEMBRA:
✅ 2,4D 1-1,5 l
✅ Epirefenacil 5,5% (Empera)
✅ Glufosinato de amonio 28% 2,5 l
✅ Paraquat (Gramoxone)
✅ 2,4D + Saflufenacil 70% 40 g (Heat)
✅ 2,4D + Carfentrazone 40% (Shark)

PEE BARBECHO INTERMEDIO:
✅ Flumioxazin (Sumisoya)
✅ Piroxasulfone (Yamato)
✅ Atrazina 90%
✅ Metribuzin (Sencorex)

PEE / PSI-PEE:
✅ Sulfentrazone 50% (Authority/Capaz) + S-metolacloro 96% (Dual Gold)
✅ Flumioxazin 15%/Piroxasulfone 34,5% (Fierce FMC) 7 DAS
✅ Flumioxazin 4,2%/S-metolacloro 84% (Apresa ADAMA) 7 DAS
✅ Trifludimoxazin/Saflufenacil (Voraxor) + S-metolacloro 96% (Dual Gold)

POST-EMERGENCIA — Sojas RR:
✅ Fomesafén 25% (Flex)
✅ Lactofén 24% (Cobra)
✅ Benazolín 50% (Dasen)

SOJAS ENLIST:
✅ Glufosinato de amonio 28% 2-3 l hasta V4-V6
✅ 2,4D 30% e.a. 1,5-2 l hasta R2
"""

KNOWLEDGE_BASE += """
=== MAÍZ ===

MAÍZ: CEBOLLÍN (Cyperus rotundus)

MAÍZ CONVENCIONAL — POE:
✅ Halosulfurón metil 75% 100-150 g/ha (Sempra) — sin restricción estadio maíz. Cebollín a ~15 cm
⚠️ Coadyuvante obligatorio: surfactante no iónico 0,1-0,2% v/v

MAÍZ RR/RG — POE:
✅ Halosulfurón metil 75% 30-50 g/ha (Sempra) + Glifosato 48% 2,5 L/ha
✅ Glifosato 48% 3 L/ha + Clorimurón 25% 60-80 g/ha (Classic)

MAÍZ CLEARFIELD (CL) — POE:
✅ Imazapic 240 g/L 1 L/ha (Pivot) — cebollín hasta 4a hoja
⚠️ Pivot FITOTÓXICO en maíz convencional. Solo Clearfield.

COADYUVANTE: Surfactante no iónico 0,1-0,2% v/v.


MAÍZ: RAIGRÁS

⚠️ ADVERTENCIA CRÍTICA: Cletodim y todos los graminicidas ACCasa (fop y dim) son FITOTÓXICOS en maíz.
⚠️ NUNCA aplicar cletodim, haloxyfop, propaquizafop ni ningún ACCasa en POE de maíz convencional ni RR.
⚠️ El maíz RR no tiene tolerancia a graminicidas ACCasa. El peso del control DEBE estar en barbecho y presiembra.

ANTES DE SIEMBRA — Mínimo 10 DAS (cuanto más mejor):
✅ Glifosato + Cletodim 24% 0,7-1 l/ha (Select) — mínimo 10 DAS antes de siembra
✅ Glifosato + Haloxyfop 54% (Galant Max)
✅ Glifosato + Cletodim 12%/Haloxyfop 6% (Gramini Elite)
⚠️ El riesgo fitotóxico aumenta si llueve entre la aplicación y la emergencia del maíz. Con menos de 7 DAS el riesgo ya es significativo.

PEE:
✅ Piroxasulfone (Yamato)
✅ Pendimetalín (Herbadox)

POE — MAÍZ ENLIST ÚNICAMENTE:
✅ Glufosinato de amonio 28% 1,8-2 l/ha hasta V6
✅ Haloxyfop 54% (Galant Max) — maíz Enlist tolera ACCasa
⚠️ Estas opciones NO aplican a maíz convencional ni RR.

POE — MAÍZ CONVENCIONAL Y RR: SIN OPCIONES. No hay graminicida selectivo disponible.


MAÍZ: AMARANTHUS SPP.

ANTES DE SIEMBRA:
✅ 2,4D
✅ Picloram
✅ Epirefenacil (Empera)
✅ Glufosinato 28%
✅ Paraquat (Gramoxone)
✅ 2,4D + Carfentrazone 40% (Shark)

PEE / PSI-PEE:
✅ Atrazina 90% 1-2 kg + S-metolacloro 96% (Dual Gold)
✅ (Acuron Pack premezclado)
✅ Atrazina 90% + Biciclopirona 20%
✅ Amicarbazone (Dinamic) + S-metolacloro (Dual Gold)
✅ Mesotrione 48% (Callisto) + Piroxasulfone (Yamato)
✅ (Isoxaflutole/Thiencarbazone) (Adengo) + S-metolacloro (Dual Gold) + Atrazina

POST-EMERGENCIA CULTIVO (V2-V8):
✅ Atrazina 90% 1 kg + 2,4D
✅ Atrazina 90% 1 kg + Picloram
✅ Atrazina 90% 1 kg + Mesotrione (Callisto)
✅ Atrazina 90% 1 kg + Topramezone (Convey)
✅ Atrazina 90% 1 kg + Tolpyralate (Brucia)
✅ Atrazina 90% 1 kg + Tembotrione (Laudis)
✅ 2,4D V2-V8
✅ 2,4D sal colina V1-V8 Maíz ENLIST
✅ Mesotrione 48% (Callisto) V2-V6
✅ Topramezone 33,6% (Convey) V1-V7
✅ Glufosinato de amonio 28% 1,8-2 l Maíz ENLIST V1-V8

MAÍZ ENLIST:
✅ Glufosinato de amonio 28% 2-3 l hasta V2-V4
✅ 2,4D 45,6% e.a. 1,5-2 l hasta V8
✅ Glufosinato 28% + 2,4D 45,6% e.a. V2-V4


MAÍZ: CRUCIFERAS

ANTES DE SIEMBRA:
✅ Glifosato + 2,4D o MCPA (base susceptibles) + PPO / Fotosistema II / HPPD/PDS según biotipo

PEE:
✅ Atrazina (Gesaprim)
✅ Terbutilazina (Terbine)
✅ Flurocloridona (Rainbow)
✅ Diflufenicán (Brodal)
✅ Flumioxazin (Sumisoya)
✅ Pyroxasulfone (Yamato)

POST-EMERGENCIA V2-V8:
✅ MCPA 28% 1,5 l + Atrazina 90% 1 kg — base clásica
✅ Mesotrione 48% (Callisto) + Atrazina 90% 1 kg — excelente sobre crucíferas pequeñas
✅ Topramezone 33,6% (Convey) + Atrazina 1 kg — V1-V7
✅ Tembotrione 42% (Laudis) + Atrazina 1 kg — V3-V6
✅ Tolpyralate 40% (Brucia) + Atrazina 1 kg — V3-V6
⚠️ HPPD siempre con atrazina o terbutilazina para sinergizar

MAÍZ ENLIST:
✅ Glufosinato 28% 1,8-2 l V1-V8
✅ 2,4D 45,6% hasta V8

=== GIRASOL ===

GIRASOL: CEBOLLÍN (Cyperus rotundus)

BARBECHO:
✅ Glifosato mayor o igual a 2000 g.e.a./ha — herramienta principal

PEE:
✅ S-metolacloro 96% (Dual Gold)
✅ Acetoclor 90% (Harness) — reducen emergencia, no eliminan tubérculos

POE — SOLO GIRASOLES CLEARFIELD PLUS (CL Plus):
⚠️ ADVERTENCIA CRÍTICA: Clearsol II Plus Pack SOLO en híbridos Clearfield PLUS. Daña CL no Plus o convencionales.
✅ Clearsol II Plus Pack (Imazamox 70% + Imazapir 80%) dosis alta — control entre 3a y 7a hoja cebollín
✅ Clearsol II Plus Pack dosis media — control parcial
✅ Clearsol II Plus Pack dosis baja — supresión
⚠️ No aplicar con estrés hídrico o térmico. No usar organofosforados en mezcla.

POE — GIRASOLES CLEARFIELD (CL, no Plus):
✅ Clearsol DF (Imazapir solo) — V2-V4. Menor espectro.

POE — GIRASOLES CONVENCIONALES: Sin opciones POE. Control en barbecho y PEE únicamente.


GIRASOL: CRUCIFERAS

ANTES DE SIEMBRA:
✅ Glifosato + 2,4D + PPO
⚠️ Dicamba: 45 DAS mínimo antes de siembra
⚠️ 2,4D: 20 DAS mínimo antes de siembra

PEE:
✅ Flurocloridona (Rainbow) + Diflufenicán (Brodal) — combinar con sospecha de resistencia

POST-EMERGENCIA — MUY LIMITADAS:
✅ GIRASOLES CL: Imazapir 80% (Clearsol) V2-V4 / Imazapir+Imazamox (Clearsol Plus II) V2-V4
⚠️ GIRASOLES NO CL: Sin opciones. Control preventivo desde barbecho y PEE.


GIRASOL: MALEZA GENERAL

BARBECHO:
✅ 2,4D (20 DAS)
✅ Dicamba (45 DAS)
✅ Fluroxipir (Starane) (1 DAS)
✅ Halauxifén (Elevore) (1 DAS)
✅ Piraflufen (Stagger)
✅ Carfentrazone (Shark) (15 DAS)
✅ Flumioxazin (Sumisoya) 30-60 DAS
✅ Diquat (Reglone)
✅ Paraquat (Gramoxone)
✅ Glifosato

PEE:
✅ Sulfentrazone 50% (Authority/Capaz)
✅ Acetoclor (Harness)
✅ S-metolacloro (Dual Gold)
✅ Diflufenicán (Brodal)
✅ Flurocloridona (Rainbow)
✅ Sulfentrazone + S-metolacloro (Dual Gold)
✅ Sulfentrazone + Acetoclor (Harness)

POST-EMERGENCIA — MUY LIMITADAS:
✅ Aclonifén (Prodigio): yuyo colorado SOLO menor a 2 cm. Ventana muy estrecha.
✅ ALS solo girasoles CL: Imazapyr (Clearsol) V2-V4 / Imazapyr+Imazamox (Clearsol Plus II) V2-V4
✅ ACCasa (gramíneas): Haloxyfop-R-metil (Galant Max) / Propaquizafop (Agil) / Cletodim (Select)
✅ DESECANTE POST MF: Carfentrazone (Shark) / Saflufenacil (Heat) — SOLO POST MF
⚠️ NO USAR durante ciclo: saflufenacil, fomesafén, diclosulam, biciclopirona, topramezone, sulfonilureas
"""

KNOWLEDGE_BASE += """
=== TRIGO ===

TRIGO: CONYZA SPP.

ANTES DE SIEMBRA:
✅ Glifosato + 2,4D
✅ Glifosato + Dicamba (Banvel)
✅ Glifosato + 2,4D o MCPA + Saflufenacil (Heat)
✅ Glifosato + 2,4D o MCPA + Carfentrazone (Shark)
✅ Glifosato + 2,4D o MCPA + Epirefenacil (Empera)
🔁 1° Glifosato + 2,4D // 2° Paraquat (Gramoxone)

PEE:
✅ Metsulfurón (Ally)
✅ Flumioxazin (Sumisoya) 10 DAS
✅ Terbutrina (Igran)
✅ Terbutilazina (Terbine)
✅ Voraxor

POST-EMERGENCIA Z2.1-Z3.0:
✅ Metsulfurón (Errasin WP/Ally) + Dicamba (Banvel)
✅ 2,4D + Dicamba (Banvel)
✅ 2,4D + Picloram (Tordón)
✅ 2,4D + Saflufenacil 70% 25 g (Heat) — Malezas menores a 10 cm
✅ Saflufenacil 70% 25 g solo — Malezas menores a 10 cm
✅ Clopyralid/MCPA (Lontrel)
✅ Glufosinato 28% Trigos HB4

⚠️ VENTANA: Saflufenacil desde Z1.2-Z1.3 SIN aceite. 2,4D y sulfonilureas desde Z2.1.


TRIGO: CRUCIFERAS

ANTES DE SIEMBRA:
✅ Glifosato + 2,4D o MCPA + Saflufenacil (Heat)
✅ Glifosato + 2,4D o MCPA + Carfentrazone (Shark)

PEE:
✅ Flurocloridona (Rainbow)
✅ Diflufenicán (Brodal)
✅ Flumioxazin (Sumisoya)

POST-EMERGENCIA ESTADO DE HOJAS (Z1.2+):
✅ Bromoxinil 34,6% (Bromotril) — desde Z1.2. Crucíferas en plántula.
✅ MCPA 28% 1,5-2,5 l — desde Z1.3-Z1.5
✅ Saflufenacil 70% 25 g (Heat) — desde Z1.2-Z1.3. SIN aceite. Crucíferas menores a 10 cm.
✅ Bromoxinil + MCPA — desde Z1.3. Sinergia contacto+sistémico.
⚠️ Las crucíferas son RESISTENTES a ALS en gran parte de la zona núcleo — verificar biotipo
⚠️ Las crucíferas son TOLERANTES/RESISTENTES al dicamba solo — usar en mezcla

POST-EMERGENCIA MACOLLAJE Z2.1+:
✅ Bromoxinil (Bromotril) + 2,4D o MCPA
✅ Carfentrazone (Shark) + 2,4D o MCPA
✅ Saflufenacil 70% 25 g (Heat) + 2,4D o MCPA — Malezas menores a 10 cm
✅ Flurocloridona (Rainbow) + 2,4D o MCPA

TRIGOS HB4:
✅ Glufosinato 28%
✅ Glufosinato 28% + 2,4D
✅ Glufosinato 28% + Metribuzin (Sencorex)
✅ Glufosinato 28% + Flurocloridona (Rainbow)

⚠️ REGLA SAFLUFENACIL EN TRIGO POE: 25 g/ha mezclable con CUALQUIER hormonal desde Z1.2. SIN aceite en estado de hojas.


TRIGO: RAIGRAS

SITUACIÓN 1 — 1-2 hojas, baja densidad:
✅ Paraquat (Gramoxone)
✅ Glufosinato 28%
✅ Glifosato + Cletodim 24% (Select)

SITUACIÓN 2 — 2-4 hojas, densidad media:
✅ Glifosato + Cletodim 24% (Select)
✅ Glifosato + Haloxyfop 54% (Galant Max)
✅ Glifosato + Cletodim 12%/Haloxyfop 6% (Gramini Elite)

SITUACIÓN 3 — más de 4 hojas o sospecha de resistencia:
✅ Glifosato + Cletodim (Select) + Epirefenacil (Empera)
✅ Glufosinato 28% + Cletodim (Select)

SITUACIÓN 4 — Resistencia probable — Doble Golpe:
🔁 1° Glifosato + Cletodim (Select) // 2° Paraquat (Gramoxone) — ~7 dias
🔁 1° Glifosato + Cletodim (Select) // 2° Glufosinato 28% — ~7 dias

PEE:
✅ Piroxasulfone (Yamato Top)
✅ Pendimetalín (Herbadox)
✅ Flumioxazin (Sumisoya) 10 DAS

POST-EMERGENCIA:
✅ Pinoxaden 5% (Axial) — desde Z1.3
✅ Clodinafop 24% (Gizmo/Topick 24EC) — desde Z1.2-Z1.3
✅ Iodosulfurón/Mesosulfurón (Hussar Plus) — desde Z1.2
✅ Piroxulam 21,5% (PowerFlex) — desde Z1.3 hasta fin macollaje
✅ Imazamox (Pulsar/Trigosol) Trigos CL
✅ Glufosinato 28% Trigos HB4

=== SORGO ===

ANTES DE SIEMBRA:
✅ Glifosato
✅ 2,4D
✅ Picloram
✅ Fluroxipir (Starane)
✅ Paraquat (Gramoxone)
✅ Glufosinato 28%
✅ Cletodim 24% 0,7-1 l 20 DAS
✅ Haloxyfop 54% 20 DAS
✅ Saflufenacil (Heat)
✅ Epirefenacil (Empera)
✅ Carfentrazone (Shark)

PEE:
✅ Flumioxazin
✅ Terbutilazina (Terbine)
✅ Atrazina 90%
✅ S-metolacloro (Dual Gold) — semilla curada con Fluxofenim 96%
✅ Pendimetalín (Herbadox)

POST-EMERGENCIA V4-V8:
✅ Bromoxinil (Bromotril) V2-V4
✅ Atrazina V2-V4
✅ Bentazón (Basagran) V2-V8
✅ Foramsulfurón + Iodosulfurón (Equip) — sorgo de Alepo RG
✅ Nicosulfurón (Accent) — sorgo de Alepo RG
✅ Desecante: Paraquat (Gramoxone) / Glifosato

=== COLZA / CANOLA / CARINATA ===

ANTES DE SIEMBRA:
✅ Paraquat
✅ Glufosinato
✅ Glifosato
✅ 2,4D (15-20 DAS)
✅ Saflufenacil (Heat)
✅ Carfentrazone (Shark)

PEE:
✅ Trifluralina (Treflan)
✅ Pendimetalín (Herbadox)
⚠️ Carinata: solo trifluralina

POST-EMERGENCIA:
✅ Cletodim (Select) — solo gramíneas
✅ Haloxyfop (Galant Max) — solo gramíneas
✅ Clopyralid (Lontrel) riesgo Bajo

RIESGO ROTACIÓN:
⚠️ Imidazolinonas: Alto
⚠️ Sulfonilureas: Alto
⚠️ Diclosulam: Alto
⚠️ Flumioxazín: Bajo

=== ARVEJA ===

ANTES DE SIEMBRA:
✅ Glifosato
✅ Paraquat
✅ Glufosinato
✅ 2,4D (15 DAS)
✅ Cletodim
✅ Haloxyfop

PEE:
✅ Imazatapir 10%
✅ Metribuzin
✅ Terbutilazina
✅ Prometrina (Gesagard)
✅ Linurón
✅ Flumioxazin
✅ S-metolacloro
✅ Pendimetalín
✅ Trifluralina

POST-EMERGENCIA (BBCH 14):
✅ Cletodim
✅ Haloxyfop
✅ Imazatapir 10% 0,5 l
✅ Metribuzin (Sencorex)
✅ Bentazón (Basagran)
✅ MCPA 28% 0,5-0,75 l
✅ Desecante: Paraquat / Diquat (Reglone) / Saflufenacil / Glufosinato

=== CAMELINA ===

ANTES DE SIEMBRA:
✅ Paraquat
✅ Glufosinato
✅ Glifosato
✅ 2,4D
✅ Saflufenacil
✅ Carfentrazone

PEE:
✅ Trifluralina (Treflan) — ÚNICA opción residual

POST-EMERGENCIA (roseta BBCH 13-15):
✅ Cletodim 60% — ÚNICA opción, solo gramíneas

✅ Desecante: Diquat (Reglone) / Saflufenacil / Carfentrazone

=== CRUCÍFERAS RESISTENTES (Barbecho) ===

CONTROL TOTAL:
✅ Glifosato + 2,4D 1,5 l + Saflufenacil 70% 35 g (Heat) — mejores controles
✅ Glifosato + 2,4D 1,5 l + Carfentrazone 40% 75 cc (Shark) — mejores controles
✅ Paraquat 2,5 l (Gramoxone) + 2,4D 1,5 l — control intermedio

CONTROL + RESIDUAL Alta infestación — solo funcionan más del 80%:
✅ Glifosato + 2,4D + Diclosulam + Halauxifén (Texaro)
✅ Glifosato + 2,4D + Piroxasulfone + Saflufenacil (Zidua Pack)

=== SENECIO ARGENTINUS (Barbecho) ===

⚠️ Emerge abril-mayo. Tamaño crítico: NO superar 10 cm al aplicar.
✅ MEJOR COMBINACIÓN: Glifosato Premium 1080 g.ea + Flumioxazin (Sumisoya 120 ml) + S-metolacloro (Dual Gold 1000 ml)

=== TRÉBOL BLANCO (Trifolium repens) — Barbecho ===

✅ OPCIÓN PRINCIPAL: Glifosato 1080 g.e.a./ha + Fluroxipir 33% (Starane Xtra) 450 ml/ha
✅ OPCIÓN CON PPO: + Saflufenacil 70% (Heat) 25-35 g/ha
✅ OPCIÓN MARBETE: Glifosato 48% 3 l/ha + Fluroxipir 33% (Starane Xtra) 360 cc/ha

=== PRODUCTOS PRINCIPALES POR CULTIVO Y MOMENTO — USAR EN CONSULTAS GENERALES SIN MALEZA ===

TRIGO / CEBADA: PEE — PRODUCTOS PRINCIPALES
⚠️ INSTRUCCIÓN AL MODELO: Esta es la lista completa y definitiva para consultas generales PEE de trigo/cebada. Volcá EXACTAMENTE esta lista. No agregues ni quites productos de otras secciones.

✅ Piroxasulfone 85% (Yamato TOP) — gramíneas (raigrás y otras)
✅ Pendimetalín (Satellite / Herbadox) — gramíneas
✅ Flumioxazin (Flumyzin / Sumyzin / Gemmit TOP / Sumisoya) — latifoliadas, hasta 10 DAS
✅ Trifludimoxazin / Saflufenacil (Voraxor) — PPO+PDS, amplio espectro, hasta 10 DAS
✅ Carfentrazone-etil (Shark) — PPO, latifoliadas
✅ Saflufenacil 70% (Heat) — PPO, latifoliadas
✅ Pyraflufen-etil (Stagger) — PPO, latifoliadas
✅ Terbutrina (Igran) — FII, latifoliadas invernales
✅ Terbutilazina (Koritsu / Teliron 50 SC) — FII, latifoliadas
✅ Flurocloridona (Talis / Rainbow) — PDS, crucíferas y latifoliadas
✅ Diflufenicán (Brodal) — PDS, crucíferas y latifoliadas
✅ Metsulfurón metil (Ally / Errasin WP) — ALS, latifoliadas
✅ Clorsulfurón + Metsulfurón (Finesse) — ALS, latifoliadas
✅ Auxinas/hormonales (2,4D, Dicamba, MCPA, Fluroxipir, Picloram y mezclas) — según maleza objetivo y estadio del cultivo

💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de trigo y cebada. La elección final depende de la maleza presente en el lote y las resistencias confirmadas en la zona.

¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa.


SOJA: PEE — PRODUCTOS PRINCIPALES

✅ Flumioxazin 48% (Sumisoya) — PPO, latifoliadas, 7 DAS
✅ Trifludimoxazin / Saflufenacil (Voraxor) — PPO+PDS, amplio espectro, 7 DAS
✅ Flumioxazin / Piroxasulfone (Fierce FMC) — PPO+VLCFA, 7 DAS
✅ Flumioxazin / Acetoclor (Harness) — PPO+cloroacetamida, 7 DAS
✅ Metribuzin / S-metolacloro (Boundary Syngenta) — FII+VLCFA
✅ Sulfentrazone (Authority / Capaz) + S-metolacloro 96% (Dual Gold) — PPO+VLCFA, amplio espectro
✅ Sulfentrazone (Authority / Capaz) + Piroxasulfone — PPO+VLCFA
✅ Sulfentrazone (Authority / Capaz) + Metribuzin (Sencorex) — PPO+FII
✅ Metribuzin 48% (Sencorex) — FII, latifoliadas
✅ Sulfentrazone 50% (Authority / Capaz) — PPO, amplio espectro
✅ Piroxasulfone 85% (Yamato) — VLCFA, gramíneas y latifoliadas

💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de soja. La elección final depende de la maleza presente en el lote.

¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa.


MAÍZ: PEE — PRODUCTOS PRINCIPALES

✅ Atrazina 90% + S-metolacloro 96% (Dual Gold) — amplio espectro
✅ Atrazina 90% + Piroxasulfone (Yamato) — latifoliadas + gramíneas
✅ Atrazina 90% + Biciclopirona 20% — amplio espectro
✅ Amicarbazone (Dinamic) + S-metolacloro (Dual Gold) — amplio espectro
✅ Mesotrione 48% (Callisto) + Piroxasulfone (Yamato) — amplio espectro
✅ Isoxaflutole/Thiencarbazone (Adengo) + S-metolacloro (Dual Gold) + Atrazina — amplio espectro
✅ Acuron Pack — premezclado amplio espectro
✅ Zidua Pack (Piroxasulfone 85% 160-200 g + Saflufenacil 70% 35-45 g) — gramíneas + latifoliadas
✅ Piroxasulfone 85% (Yamato) — gramíneas
✅ Pendimetalín (Herbadox) — gramíneas
✅ Saflufenacil 70% (Heat) — PPO, latifoliadas
✅ Carfentrazone-etil (Shark) — PPO, latifoliadas
✅ Flumioxazin (Sumisoya) — PPO, latifoliadas
✅ Flurocloridona (Rainbow) — crucíferas y latifoliadas
✅ Diflufenicán (Brodal) — crucíferas y latifoliadas
✅ Terbutilazina (Terbine) — FII, latifoliadas
✅ Atrazina (Gesaprim) — FII, amplio espectro

💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de maíz. La elección final depende de la maleza presente en el lote.

¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa.


GIRASOL: PEE — PRODUCTOS PRINCIPALES
⚠️ ATENCIÓN: NO usar Saflufenacil (Heat) en girasol — fitotóxico. El PPO válido en girasol es Carfentrazone (Shark) o Pyraflufen (Stagger).

✅ Carfentrazone-etil (Shark) — PPO contacto, latifoliadas
✅ Pyraflufen-etil (Stagger) — PPO contacto, latifoliadas
✅ Sulfentrazone 50% (Authority / Capaz) — PPO, amplio espectro
✅ Sulfentrazone + S-metolacloro 96% (Dual Gold) — PPO+VLCFA, amplio espectro
✅ Sulfentrazone + Acetoclor (Harness) — PPO+cloroacetamida
✅ Piroxasulfone 85% (Yamato) — VLCFA, gramíneas
✅ Pendimetalín (Herbadox) — microtúbulos, gramíneas
✅ S-metolacloro 96% (Dual Gold) — VLCFA, gramíneas y algunas latifoliadas
✅ Acetoclor (Harness) — cloroacetamida, gramíneas y algunas latifoliadas
✅ Flurocloridona 25% (Rainbow) — PDS, crucíferas y latifoliadas
✅ Diflufenicán 50% (Brodal) — PDS, crucíferas y latifoliadas
✅ Flurocloridona (Rainbow) + Diflufenicán (Brodal) — crucíferas con resistencia

💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de girasol. Las opciones POE en girasol son muy limitadas — el PEE es el momento más importante.

¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa.


SORGO: PEE — PRODUCTOS PRINCIPALES

✅ Flumioxazin (Sumisoya) — PPO, latifoliadas
✅ Carfentrazone-etil (Shark) — PPO contacto, latifoliadas
✅ Terbutilazina (Terbine) — FII, latifoliadas
✅ Atrazina 90% — FII, amplio espectro
✅ S-metolacloro 96% (Dual Gold) — gramíneas y latifoliadas ⚠️ semilla curada con Fluxofenim 96% (Concep III) obligatorio
✅ Pendimetalín (Herbadox) — microtúbulos, gramíneas

💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de sorgo. La elección final depende de la maleza presente en el lote.

¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa.

=== PROTOCOLO INTERNO DE ENSAYOS ===

PEE:
✅ GIRASOL: Glifosato 2L/1,5kg + Flurocloridona 1,5L + Piroxasulfone 160g
✅ MAIZ: Glifosato 2L/1,5kg + Atrazina 3L/1,5kg + Zidua Pack (HEAT 45g + Pyroxasulfone 200g) + Aceite
✅ SOJA: Glifosato 2L/1,5kg + Sulfentrazone 400cc + S-Metolacloro 1,5L + Metribuzin 48% 1,5L

POE:
✅ GIRASOL CL: Clearsol DF 100g + Aceite DASH 200cc + graminicida si hace falta
✅ GIRASOL NO CL: Prodigio 1,5L + Aceite o Benazolin 50% 0,3L + graminicida
✅ MAIZ: Glifosato 2L/1,5kg (RR) + Atrazina 1,5-3L + Tordon 150cc / Glufosinato (Maiz Enlist)
✅ SOJA: Glifosato 2L/1,5kg (RR) + Fomesafen 25% 1,5L + coadyuvante + Benazolin 50% 0,8L
"""


# --- RESPUESTAS HARDCODEADAS PARA CONSULTAS GENERALES ---
RESPUESTAS_GENERALES = {
    ("trigo", "pee"): (
        "PEE EN TRIGO / CEBADA\n\n"
        "✅ Piroxasulfone 85% (Yamato TOP) — gramíneas (raigrás y otras)\n"
        "✅ Pendimetalín (Satellite / Herbadox) — gramíneas\n"
        "✅ Flumioxazin (Flumyzin / Sumyzin / Gemmit TOP / Sumisoya) — latifoliadas, hasta 10 DAS\n"
        "✅ Trifludimoxazin / Saflufenacil (Voraxor) — PPO+PDS, amplio espectro, hasta 10 DAS\n"
        "✅ Carfentrazone-etil (Shark) — PPO, latifoliadas\n"
        "✅ Saflufenacil 70% (Heat) — PPO, latifoliadas\n"
        "✅ Pyraflufen-etil (Stagger) — PPO, latifoliadas\n"
        "✅ Terbutrina (Igran) — FII, latifoliadas invernales\n"
        "✅ Terbutilazina (Koritsu / Teliron 50 SC) — FII, latifoliadas\n"
        "✅ Flurocloridona (Talis / Rainbow) — PDS, crucíferas y latifoliadas\n"
        "✅ Diflufenicán (Brodal) — PDS, crucíferas y latifoliadas\n"
        "✅ Metsulfurón metil (Ally / Errasin WP) — ALS, latifoliadas\n"
        "✅ Clorsulfurón + Metsulfurón (Finesse) — ALS, latifoliadas\n"
        "✅ Auxinas/hormonales (2,4D, Dicamba, MCPA, Fluroxipir, Picloram y mezclas) — según maleza objetivo y estadio\n\n"
        "💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de trigo y cebada. "
        "La elección final depende de la maleza presente en el lote y las resistencias confirmadas en la zona.\n\n"
        "¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa."
    ),
    ("cebada", "pee"): None,  # usa la misma que trigo
    ("soja", "pee"): (
        "PEE EN SOJA\n\n"
        "✅ Flumioxazin 48% (Sumisoya) — PPO, latifoliadas, 7 DAS\n"
        "✅ Trifludimoxazin / Saflufenacil (Voraxor) — PPO+PDS, amplio espectro, 7 DAS\n"
        "✅ Flumioxazin / Piroxasulfone (Fierce FMC) — PPO+VLCFA, 7 DAS\n"
        "✅ Flumioxazin / Acetoclor (Harness) — PPO+cloroacetamida, 7 DAS\n"
        "✅ Metribuzin / S-metolacloro (Boundary Syngenta) — FII+VLCFA\n"
        "✅ Sulfentrazone (Authority / Capaz) + S-metolacloro 96% (Dual Gold) — PPO+VLCFA, amplio espectro\n"
        "✅ Sulfentrazone (Authority / Capaz) + Piroxasulfone — PPO+VLCFA\n"
        "✅ Sulfentrazone (Authority / Capaz) + Metribuzin (Sencorex) — PPO+FII\n"
        "✅ Metribuzin 48% (Sencorex) — FII, latifoliadas\n"
        "✅ Sulfentrazone 50% (Authority / Capaz) — PPO, amplio espectro\n"
        "✅ Piroxasulfone 85% (Yamato) — VLCFA, gramíneas y latifoliadas\n\n"
        "💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de soja. "
        "La elección final depende de la maleza presente en el lote.\n\n"
        "¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa."
    ),
    ("maiz", "pee"): (
        "PEE EN MAÍZ\n\n"
        "✅ Atrazina 90% + S-metolacloro 96% (Dual Gold) — amplio espectro\n"
        "✅ Atrazina 90% + Piroxasulfone (Yamato) — latifoliadas + gramíneas\n"
        "✅ Atrazina 90% + Biciclopirona 20% — amplio espectro\n"
        "✅ Amicarbazone (Dinamic) + S-metolacloro (Dual Gold) — amplio espectro\n"
        "✅ Mesotrione 48% (Callisto) + Piroxasulfone (Yamato) — amplio espectro\n"
        "✅ Isoxaflutole/Thiencarbazone (Adengo) + S-metolacloro (Dual Gold) + Atrazina — amplio espectro\n"
        "✅ Acuron Pack — premezclado amplio espectro\n"
        "✅ Zidua Pack (Piroxasulfone 85% 160-200 g + Saflufenacil 70% 35-45 g) — gramíneas + latifoliadas\n"
        "✅ Piroxasulfone 85% (Yamato) — gramíneas\n"
        "✅ Pendimetalín (Herbadox) — gramíneas\n"
        "✅ Saflufenacil 70% (Heat) — PPO, latifoliadas\n"
        "✅ Carfentrazone-etil (Shark) — PPO, latifoliadas\n"
        "✅ Flumioxazin (Sumisoya) — PPO, latifoliadas\n"
        "✅ Flurocloridona (Rainbow) — crucíferas y latifoliadas\n"
        "✅ Diflufenicán (Brodal) — crucíferas y latifoliadas\n"
        "✅ Terbutilazina (Terbine) — FII, latifoliadas\n"
        "✅ Atrazina (Gesaprim) — FII, amplio espectro\n\n"
        "💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de maíz. "
        "La elección final depende de la maleza presente en el lote.\n\n"
        "¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa."
    ),
    ("girasol", "pee"): (
        "PEE EN GIRASOL\n\n"
        "⚠️ NO usar Saflufenacil (Heat) en girasol — fitotóxico.\n\n"
        "✅ Carfentrazone-etil (Shark) — PPO contacto, latifoliadas\n"
        "✅ Pyraflufen-etil (Stagger) — PPO contacto, latifoliadas\n"
        "✅ Sulfentrazone 50% (Authority / Capaz) — PPO, amplio espectro\n"
        "✅ Sulfentrazone + S-metolacloro 96% (Dual Gold) — PPO+VLCFA, amplio espectro\n"
        "✅ Sulfentrazone + Acetoclor (Harness) — PPO+cloroacetamida\n"
        "✅ Piroxasulfone 85% (Yamato) — VLCFA, gramíneas\n"
        "✅ Pendimetalín (Herbadox) — microtúbulos, gramíneas\n"
        "✅ S-metolacloro 96% (Dual Gold) — gramíneas y algunas latifoliadas\n"
        "✅ Acetoclor (Harness) — gramíneas y algunas latifoliadas\n"
        "✅ Flurocloridona 25% (Rainbow) — PDS, crucíferas y latifoliadas\n"
        "✅ Diflufenicán 50% (Brodal) — PDS, crucíferas y latifoliadas\n"
        "✅ Flurocloridona (Rainbow) + Diflufenicán (Brodal) — crucíferas con resistencia\n\n"
        "💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de girasol. "
        "Las opciones POE en girasol son muy limitadas — el PEE es el momento más importante.\n\n"
        "¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa."
    ),
    ("sorgo", "pee"): (
        "PEE EN SORGO\n\n"
        "✅ Flumioxazin (Sumisoya) — PPO, latifoliadas\n"
        "✅ Carfentrazone-etil (Shark) — PPO contacto, latifoliadas\n"
        "✅ Terbutilazina (Terbine) — FII, latifoliadas\n"
        "✅ Atrazina 90% — FII, amplio espectro\n"
        "✅ S-metolacloro 96% (Dual Gold) — gramíneas y latifoliadas\n"
        "⚠️ S-metolacloro en sorgo requiere semilla curada con Fluxofenim 96% (Concep III). Sin antídoto es fitotóxico.\n"
        "✅ Pendimetalín (Herbadox) — microtúbulos, gramíneas\n\n"
        "💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de sorgo. "
        "La elección final depende de la maleza presente en el lote.\n\n"
        "¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa."
    ),
}
# cebada usa la misma respuesta que trigo
RESPUESTAS_GENERALES[("cebada", "pee")] = RESPUESTAS_GENERALES[("trigo", "pee")]

CULTIVOS_ALIAS = {
    "trigo": "trigo", "cebada": "cebada",
    "soja": "soja", "soya": "soja",
    "maiz": "maiz", "maíz": "maiz",
    "girasol": "girasol",
    "sorgo": "sorgo",
}
MOMENTOS_ALIAS = {
    "pee": "pee", "pre-emergencia": "pee", "preemergencia": "pee",
    "pre emergencia": "pee",
}

def detectar_consulta_general(texto):
    """Retorna la respuesta hardcodeada si el mensaje es una consulta general, o None si no lo es."""
    t = texto.lower().strip()
    cultivo_detectado = None
    momento_detectado = None
    for palabra, cultivo in CULTIVOS_ALIAS.items():
        if palabra in t:
            cultivo_detectado = cultivo
            break
    for palabra, momento in MOMENTOS_ALIAS.items():
        if palabra in t:
            momento_detectado = momento
            break
    if cultivo_detectado and momento_detectado:
        return RESPUESTAS_GENERALES.get((cultivo_detectado, momento_detectado))
    return None

# --- FLUJO GUIADO BARBECHO ---

# Keywords nivel 1 — disparan flujo directo
BARBECHO_KEYWORDS_DIRECTAS = [
    "barbecho", "presiembra", "pre-siembra", "pre siembra",
    "barbeche", "barbechos"
]

# Keywords nivel 2 — disparan confirmación primero
BARBECHO_KEYWORDS_CONTEXTUALES = [
    "después de la cosecha", "despues de la cosecha",
    "luego de cosechar", "luego de la cosecha",
    "post cosecha", "postcosecha", "post-cosecha",
    "antes de sembrar", "antes de la siembra",
    "limpiar el lote", "limpiar lote",
    "qué aplico antes", "que aplico antes",
    "qué uso antes", "que uso antes",
    "para limpiar antes", "entre cultivos",
]

RESPUESTA_OTRA_MALEZA = (
    "⚠️ No tengo información específica para esa maleza en barbecho todavía.\n\n"
    "Sin embargo, Lolium, Conyza y Brassica representan las principales malezas "
    "problema en barbecho de cultivos extensivos.\n\n"
    "🌱 Si tu maleza es una GRAMÍNEA — las opciones de Lolium/Raigrás pueden orientarte.\n"
    "🌱 Si tu maleza es una LATIFOLIADA — las opciones de Conyza o Brassica son un buen punto de partida.\n\n"
    "Consultá con tu asesor para ajustar la estrategia al biotipo específico."
)

def detectar_nivel_barbecho(texto):
    """Retorna 1 (directo), 2 (contextual) o 0 (no es barbecho)."""
    t = texto.lower()
    for kw in BARBECHO_KEYWORDS_DIRECTAS:
        if kw in t:
            return 1
    for kw in BARBECHO_KEYWORDS_CONTEXTUALES:
        if kw in t:
            return 2
    return 0

def _lolium_soja_maiz_largo_nacida():
    return (
        "LOLIUM — BARBECHO LARGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ MOMENTO: En abril sumar residual o usar doble golpe. Desde mayo la aplicación simple sostiene mejor.\n\n"
        "ABRIL:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe con residual\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — agrega MOA, sin residual de suelo\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha resistencia ACCasa\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE\n"
        "⚠️ RESISTENCIA ACCasa: cletodim solo puede quedar entre 5-70% según biotipo."
    )

def _lolium_soja_maiz_largo_residual(cultivo):
    return (
        "LOLIUM — BARBECHO LARGO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "⚠️ Los residuales actúan sobre semillas y plántulas antes de emerger. No eliminan maleza ya nacida.\n\n"
        "🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — mejor residualidad hasta 150 DDA\n"
        "🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha sola\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Pyroxasulfone (Yamato): sin restricción en soja ni maíz. 90 días carencia antes de trigo."
    )

def _lolium_soja_maiz_largo_ambos(cultivo):
    return (
        "LOLIUM — BARBECHO LARGO — MALEZA NACIDA + RESIDUAL\n\n"
        "⚠️ MOMENTO: En abril usar doble golpe. Desde mayo la aplicación única con residual es suficiente.\n\n"
        "ABRIL:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_soja_maiz_corto_nacida():
    return (
        "LOLIUM — BARBECHO CORTO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Agosto-septiembre es la ventana óptima. Control sostenido sin doble golpe en la mayoría de los casos.\n\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n"
        "🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_soja_maiz_corto_residual(cultivo):
    return (
        "LOLIUM — BARBECHO CORTO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha"
    )

def _lolium_soja_maiz_corto_ambos(cultivo):
    return (
        "LOLIUM — BARBECHO CORTO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_girasol_largo_nacida():
    return (
        "LOLIUM — BARBECHO LARGO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Atrazina fitotóxica en girasol — NO usar.\n\n"
        "ABRIL:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_girasol_residual():
    return (
        "LOLIUM — BARBECHO — GIRASOL — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "⚠️ Atrazina fitotóxica en girasol — NO usar.\n\n"
        "🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha sola\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha"
    )

def _lolium_girasol_largo_ambos():
    return (
        "LOLIUM — BARBECHO LARGO — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "⚠️ Atrazina fitotóxica en girasol — NO usar.\n\n"
        "ABRIL:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_girasol_corto_nacida():
    return (
        "LOLIUM — BARBECHO CORTO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n"
        "🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_girasol_corto_ambos():
    return (
        "LOLIUM — BARBECHO CORTO — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "⚠️ Atrazina fitotóxica en girasol — NO usar.\n\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_trigo_nacida():
    return (
        "LOLIUM — BARBECHO TRIGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "SITUACIÓN 1 — 1-2 hojas, baja densidad:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glufosinato 28% 2 L/ha\n"
        "🥉 Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
        "SITUACIÓN 2 — 2-4 hojas, densidad media:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 810 g ia/ha + Haloxyfop 54% (Galant Max) 0,5 L/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 12%/Haloxyfop 6% (Gramini Elite) 1 L/ha\n\n"
        "SITUACIÓN 3 — más de 4 hojas o sospecha resistencia ACCasa:\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n"
        "🥈 Glufosinato 28% 2 L/ha + Cletodim 24% (Select) 0,8 L/ha\n\n"
        "SITUACIÓN 4 — resistencia confirmada O maleza muy establecida (5+ macollos):\n"
        "🔁 1° Glifosato 810 g ia/ha + Cletodim (Select) 0,8 L/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n"
        "🔁 1° Glifosato 810 g ia/ha + Cletodim (Select) 0,8 L/ha // 2° Glufosinato 28% 2 L/ha\n\n"
        "⚠️ Cletodim y haloxyfop requieren aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_trigo_residual():
    return (
        "LOLIUM — BARBECHO TRIGO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Azugro (Bixlozona) FMC — residual específico para Lolium en trigo. Sin restricción\n"
        "🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en trigo\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Pendimetalín (Herbadox) — ⚠️ pyroxasulfone verificar 90 días antes de trigo"
    )

def _lolium_trigo_ambos():
    return (
        "LOLIUM — BARBECHO TRIGO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Azugro (Bixlozona) FMC\n"
        "🥈 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 810 g ia/ha + Cletodim 24% (Select) 0,8 L/ha — sin residual\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v SIEMPRE\n"
        "⚠️ Pyroxasulfone (Yamato): 90 días de carencia antes de trigo."
    )

# --- CONYZA ---

def _conyza_largo_nacida():
    return (
        "CONYZA — BARBECHO LARGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Roseta menor a 10 cm responde mejor. Mayor a 10 cm requiere doble golpe.\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha\n\n"
        "PPO de contacto como apoyo (agregar a cualquiera):\n"
        "✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior\n"
        "✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción\n\n"
        "ROSETA MAYOR A 10 CM — Doble Golpe:\n"
        "🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _conyza_largo_residual(cultivo):
    if cultivo == "soja":
        return (
            "CONYZA — BARBECHO LARGO — SOJA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — mejor residualidad a 120 DDA\n"
            "🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha — registrado para barbecho otoño a soja\n"
            "🥈 Atrazina 90% 2,25 L/ha — ⚠️ verificar registro local antes de usar en soja\n"
            "🥉 Metsulfurón 60% (Ally) 7 g/ha — ⚠️ 60 días carencia antes de soja"
        )
    else:
        return (
            "CONYZA — BARBECHO LARGO — MAÍZ — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha"
        )

def _conyza_largo_ambos(cultivo):
    if cultivo == "soja":
        return (
            "CONYZA — BARBECHO LARGO — SOJA — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "CONYZA — BARBECHO LARGO — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )

def _conyza_corto_nacida():
    return (
        "CONYZA — BARBECHO CORTO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Segundo pico de emergencia. Plántulas pequeñas — mejor momento para control.\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _conyza_corto_residual(cultivo):
    if cultivo == "soja":
        return (
            "CONYZA — BARBECHO CORTO — SOJA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha — ⚠️ verificar 45 días antes de siembra soja\n"
            "🥉 Voraxor (Trifludimoxazin/Saflufenacil) 0,1-0,15 L/ha"
        )
    else:
        return (
            "CONYZA — BARBECHO CORTO — MAÍZ — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Terbutilazina 50% (Terbine) 1,5 kg/ha"
        )

def _conyza_corto_ambos(cultivo):
    if cultivo == "soja":
        return (
            "CONYZA — BARBECHO CORTO — SOJA — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — ⚠️ verificar 45 días\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "CONYZA — BARBECHO CORTO — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )

def _conyza_girasol_largo_nacida():
    return (
        "CONYZA — BARBECHO LARGO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Atrazina, biciclopirone, saflufenacil y metsulfurón NO usar en barbecho previo a girasol.\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha\n\n"
        "PPO (único disponible para girasol):\n"
        "✅ Carfentrazone 40% (Shark) 75-120 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _conyza_girasol_largo_residual():
    return (
        "CONYZA — BARBECHO LARGO — GIRASOL — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha\n"
        "🥈 Atrazina 90% 2,25 L/ha — ⚠️ 90 días intervalo antes de siembra girasol\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha — menor residualidad"
    )

def _conyza_girasol_largo_ambos():
    return (
        "CONYZA — BARBECHO LARGO — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha — ⚠️ verificar 45 días Lontrel\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _conyza_girasol_corto_nacida():
    return (
        "CONYZA — BARBECHO CORTO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Pixxaro puede aplicarse hasta 0 días antes de siembra de girasol.\n\n"
        "🥇 Glifosato 810 g ia/ha + Pixxaro (Halauxifen + Fluroxipir) 400-500 cc/ha + aceite mineral 1% v/v — SENASA N° 40.386\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥉 Glifosato 810 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)"
    )

def _conyza_girasol_corto_residual():
    return (
        "CONYZA — BARBECHO CORTO — GIRASOL — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "⚠️ Atrazina (90 días) no alcanza en barbecho corto. Saflufenacil NO usar en girasol.\n\n"
        "🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en girasol\n"
        "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha"
    )

def _conyza_girasol_corto_ambos():
    return (
        "CONYZA — BARBECHO CORTO — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + Pixxaro 400-500 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite mineral 1% v/v\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥉 Glifosato 810 g ia/ha + Pixxaro 400-500 cc/ha + Diflufenican 50% (Brodal) 250 cc/ha + aceite mineral 1% v/v\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)"
    )

def _conyza_trigo_nacida():
    return (
        "CONYZA — BARBECHO TRIGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días intervalo\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — 3-5 días\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _conyza_trigo_residual():
    return (
        "CONYZA — BARBECHO TRIGO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Metsulfurón 60% (Ally/Errasin) 7-8 g/ha — 0 días intervalo en trigo\n"
        "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha — 15 días intervalo"
    )

def _conyza_trigo_ambos():
    return (
        "CONYZA — BARBECHO TRIGO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

# --- BRASSICA ---

def _brassica_largo_nacida():
    return (
        "BRASSICA — BARBECHO LARGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Roseta menor a 10 cm responde mejor. Mayor a 10 cm — Doble Golpe obligatorio.\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 94% control\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "ROSETA MAYOR A 10 CM:\n"
        "🔁 1° Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _brassica_largo_residual(cultivo):
    if cultivo == "soja":
        return (
            "BRASSICA — BARBECHO LARGO — SOJA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "⚠️ Para Brassica: Pyroxasulfone cae a 61% a 150 DDA. Flurocloridona y Terbutilazina+Diflufenican son los mejores.\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — 93-95% a 90 DDA\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — 96% a 150 DDA\n"
            "🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin registro formal en soja, en barbecho largo el intervalo se cumple\n"
            "🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia"
        )
    else:
        return (
            "BRASSICA — BARBECHO LARGO — MAÍZ — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
            "🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz\n"
            "🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia"
        )

def _brassica_largo_ambos(cultivo):
    if cultivo == "soja":
        return (
            "BRASSICA — BARBECHO LARGO — SOJA — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "BRASSICA — BARBECHO LARGO — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )

def _brassica_corto_nacida():
    return _brassica_largo_nacida().replace("LARGO", "CORTO")

def _brassica_corto_residual(cultivo):
    if cultivo == "soja":
        return (
            "BRASSICA — BARBECHO CORTO — SOJA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
            "🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar 30-40 días antes de soja"
        )
    else:
        return (
            "BRASSICA — BARBECHO CORTO — MAÍZ — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
            "🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz"
        )

def _brassica_corto_ambos(cultivo):
    if cultivo == "soja":
        return (
            "BRASSICA — BARBECHO CORTO — SOJA — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ 30-40 días antes de soja\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ Shark requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "BRASSICA — BARBECHO CORTO — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha + Shark 75 cc/ha\n"
            "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha\n"
            "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ Shark requiere aceite vegetal 0,5% v/v"
        )

def _brassica_girasol_largo_nacida():
    return (
        "BRASSICA — BARBECHO LARGO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Biciclopirone y atrazina NO usar en girasol. Heat NO usar en pre-siembra girasol.\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha\n\n"
        "PPO (único disponible): ✅ Shark 75-120 cc/ha\n\n"
        "ROSETA MAYOR A 10 CM:\n"
        "🔁 1° Glifosato + 2,4D + Shark // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _brassica_girasol_residual():
    return (
        "BRASSICA — BARBECHO — GIRASOL — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "⚠️ Flurocloridona es la estrella para Brassica en girasol.\n\n"
        "🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — 96-97% a 150 DDA. Sin restricción\n"
        "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
        "🥉 Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia"
    )

def _brassica_girasol_largo_ambos():
    return (
        "BRASSICA — BARBECHO LARGO — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "ABRIL:\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ verificar 45 días Lontrel\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _brassica_girasol_corto_nacida():
    return _brassica_girasol_largo_nacida().replace("LARGO", "CORTO")

def _brassica_girasol_corto_ambos():
    return (
        "BRASSICA — BARBECHO CORTO — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _brassica_trigo_nacida():
    return (
        "BRASSICA — BARBECHO TRIGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha — 3-5 días\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "ROSETA MAYOR A 10 CM:\n"
        "🔁 1° Glifosato + 2,4D + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _brassica_trigo_residual():
    return (
        "BRASSICA — BARBECHO TRIGO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — 0 días en trigo\n"
        "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — ⚠️ Brodal 15 días\n"
        "🥉 Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — 15 días"
    )

def _brassica_trigo_ambos():
    return (
        "BRASSICA — BARBECHO TRIGO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n"
        "🥈 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 810 g ia/ha + 2,4D 500 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def get_barbecho_response(cultivo, maleza, momento, objetivo):
    """Retorna la respuesta hardcodeada para la combinación dada."""
    cultivo = cultivo.lower().strip()
    maleza = maleza.lower().strip()
    momento = momento.lower().strip() if momento else ""
    objetivo = objetivo.lower().strip()

    # LOLIUM
    if maleza == "lolium":
        if cultivo in ["soja", "maiz"]:
            if momento == "largo":
                if objetivo == "nacida": return _lolium_soja_maiz_largo_nacida()
                elif objetivo == "residual": return _lolium_soja_maiz_largo_residual(cultivo)
                else: return _lolium_soja_maiz_largo_ambos(cultivo)
            else:  # corto
                if objetivo == "nacida": return _lolium_soja_maiz_corto_nacida()
                elif objetivo == "residual": return _lolium_soja_maiz_corto_residual(cultivo)
                else: return _lolium_soja_maiz_corto_ambos(cultivo)
        elif cultivo == "girasol":
            if momento == "largo":
                if objetivo == "nacida": return _lolium_girasol_largo_nacida()
                elif objetivo == "residual": return _lolium_girasol_residual()
                else: return _lolium_girasol_largo_ambos()
            else:
                if objetivo == "nacida": return _lolium_girasol_corto_nacida()
                elif objetivo == "residual": return _lolium_girasol_residual()
                else: return _lolium_girasol_corto_ambos()
        elif cultivo == "trigo":
            if objetivo == "nacida": return _lolium_trigo_nacida()
            elif objetivo == "residual": return _lolium_trigo_residual()
            else: return _lolium_trigo_ambos()

    # CONYZA
    elif maleza == "conyza":
        if cultivo in ["soja", "maiz"]:
            if momento == "largo":
                if objetivo == "nacida": return _conyza_largo_nacida()
                elif objetivo == "residual": return _conyza_largo_residual(cultivo)
                else: return _conyza_largo_ambos(cultivo)
            else:
                if objetivo == "nacida": return _conyza_corto_nacida()
                elif objetivo == "residual": return _conyza_corto_residual(cultivo)
                else: return _conyza_corto_ambos(cultivo)
        elif cultivo == "girasol":
            if momento == "largo":
                if objetivo == "nacida": return _conyza_girasol_largo_nacida()
                elif objetivo == "residual": return _conyza_girasol_largo_residual()
                else: return _conyza_girasol_largo_ambos()
            else:
                if objetivo == "nacida": return _conyza_girasol_corto_nacida()
                elif objetivo == "residual": return _conyza_girasol_corto_residual()
                else: return _conyza_girasol_corto_ambos()
        elif cultivo == "trigo":
            if objetivo == "nacida": return _conyza_trigo_nacida()
            elif objetivo == "residual": return _conyza_trigo_residual()
            else: return _conyza_trigo_ambos()

    # BRASSICA
    elif maleza == "brassica":
        if cultivo in ["soja", "maiz"]:
            if momento == "largo":
                if objetivo == "nacida": return _brassica_largo_nacida()
                elif objetivo == "residual": return _brassica_largo_residual(cultivo)
                else: return _brassica_largo_ambos(cultivo)
            else:
                if objetivo == "nacida": return _brassica_corto_nacida()
                elif objetivo == "residual": return _brassica_corto_residual(cultivo)
                else: return _brassica_corto_ambos(cultivo)
        elif cultivo == "girasol":
            if momento == "largo":
                if objetivo == "nacida": return _brassica_girasol_largo_nacida()
                elif objetivo == "residual": return _brassica_girasol_residual()
                else: return _brassica_girasol_largo_ambos()
            else:
                if objetivo == "nacida": return _brassica_girasol_corto_nacida()
                elif objetivo == "residual": return _brassica_girasol_residual()
                else: return _brassica_girasol_corto_ambos()
        elif cultivo == "trigo":
            if objetivo == "nacida": return _brassica_trigo_nacida()
            elif objetivo == "residual": return _brassica_trigo_residual()
            else: return _brassica_trigo_ambos()

    return "⚠️ No encontré información para esa combinación. Intentá reformular la consulta o escribí /nuevo para empezar de nuevo."

def build_barbecho_prompt(cultivo, maleza, momento, objetivo):
    """Construye el prompt específico para la API cuando no hay hardcoded."""
    momento_texto = f"barbecho {momento}" if momento else "barbecho"
    return (
        f"Consulta sobre {momento_texto} para el cultivo de {cultivo}, "
        f"maleza {maleza}, objetivo: {objetivo}. "
        f"Respondé ÚNICAMENTE con la sección de BARBECHO correspondiente de la base de conocimiento."
    )

# Teclados inline para el flujo
def kb_confirmar_barbecho():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sí, es sobre barbecho", callback_data="barb_confirmar_si"),
        InlineKeyboardButton("❌ No, otra consulta", callback_data="barb_confirmar_no"),
    ]])

def kb_cultivo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌱 Soja", callback_data="barb_cultivo_soja"),
         InlineKeyboardButton("🌽 Maíz", callback_data="barb_cultivo_maiz")],
        [InlineKeyboardButton("🌻 Girasol", callback_data="barb_cultivo_girasol"),
         InlineKeyboardButton("🌾 Trigo/Cebada", callback_data="barb_cultivo_trigo")],
    ])

def kb_maleza():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Lolium/Raigrás", callback_data="barb_maleza_lolium")],
        [InlineKeyboardButton("🌿 Rama Negra (Conyza)", callback_data="barb_maleza_conyza")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="barb_maleza_brassica")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="barb_maleza_otra")],
    ])

def kb_momento():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📅 Largo (abril-junio)", callback_data="barb_momento_largo"),
        InlineKeyboardButton("📅 Corto (agosto-septiembre)", callback_data="barb_momento_corto"),
    ]])

def kb_objetivo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Eliminar maleza ya nacida", callback_data="barb_obj_nacida")],
        [InlineKeyboardButton("🛡️ Prevenir nuevos nacimientos (residual)", callback_data="barb_obj_residual")],
        [InlineKeyboardButton("🎯+🛡️ Ambos objetivos", callback_data="barb_obj_ambos")],
    ])

# --- CLIENTE ANTHROPIC ---
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def send_long_message(bot, chat_id, text, max_length=4000):
    """Divide y envía mensajes que superan el límite de Telegram (4096 chars)."""
    if len(text) <= max_length:
        await bot.send_message(chat_id=chat_id, text=text)
        return
    lines = text.split('\n')
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > max_length:
            if chunk:
                await bot.send_message(chat_id=chat_id, text=chunk)
            chunk = line
        else:
            chunk = chunk + '\n' + line if chunk else line
    if chunk:
        await bot.send_message(chat_id=chat_id, text=chunk)

async def responder_barbecho_completo(update_or_query, context, cultivo, maleza, momento, objetivo):
    """Genera y envía la respuesta final hardcodeada del flujo de barbecho."""

    # Para trigo no hay distinción largo/corto
    if cultivo == "trigo" and not momento:
        momento = "presiembra"

    chat_id = update_or_query.message.chat_id

    # Obtener respuesta hardcodeada
    if maleza == "otra":
        respuesta = RESPUESTA_OTRA_MALEZA
    else:
        respuesta = get_barbecho_response(cultivo, maleza, momento, objetivo)

    # Enviar respuesta dividida si es necesario
    await send_long_message(context.bot, chat_id, respuesta)

    # Botones informativos automáticos
    t = respuesta.lower()
    buttons = []
    HERBICIDAS_CON_COADYUVANTE = [
        "cletodim", "haloxyfop", "propaquizafop", "saflufenacil",
        "heat", "carfentrazone", "shark", "flumioxazin", "glufosinato"
    ]
    if any(w in t for w in HERBICIDAS_CON_COADYUVANTE):
        buttons.append([InlineKeyboardButton("💧 Ver coadyuvantes", callback_data="show_coadyuvantes")])
    if "2,4d" in t or "2,4 d" in t:
        buttons.append([InlineKeyboardButton("📋 Ver formulaciones 2,4D", callback_data="show_2_4d")])
    if "glifosato" in t:
        buttons.append([InlineKeyboardButton("📋 Ver formulaciones Glifosato", callback_data="show_glifosato")])
    if buttons:
        await context.bot.send_message(
            chat_id=chat_id,
            text="ℹ️ Información adicional disponible:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Limpiar estado
    context.user_data.clear()

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

# --- COMANDO /stats (solo admin) ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Acceso restringido.")
        return
    if not user_stats:
        await update.message.reply_text("📊 Sin consultas registradas todavía.")
        return
    lines = ["📊 Consultas por usuario:\n"]
    for uid, data in sorted(user_stats.items(), key=lambda x: x[1]["mensajes"], reverse=True):
        nombre = data.get("nombre", "Sin nombre")
        username = f"@{data['username']}" if data.get("username") else "sin @"
        mensajes = data["mensajes"]
        lines.append(f"👤 {nombre} ({username}) — {mensajes} consulta{'s' if mensajes != 1 else ''}")
    await update.message.reply_text("\n".join(lines))

# --- MANEJO DE MENSAJES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = update.message.from_user
    user_message = update.message.text

    # Actualizar estadísticas
    if user_id not in user_stats:
        user_stats[user_id] = {
            "nombre": user.full_name,
            "username": user.username or "",
            "mensajes": 0
        }
    user_stats[user_id]["mensajes"] += 1

    # Reenviar consulta al admin (solo si no es el admin mismo)
    if user_id != ADMIN_USER_ID:
        nombre = user.full_name
        username = f"@{user.username}" if user.username else "sin @"
        total = user_stats[user_id]["mensajes"]
        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"📨 {nombre} ({username}) — consulta #{total}:\n\n{user_message}"
            )
            logger.info(f"Notificación enviada al admin: {nombre} ({username}) consulta #{total}")
        except Exception as e:
            logger.error(f"ERROR al notificar al admin: {type(e).__name__}: {e}")

    # Si el usuario responde "si" o "sí" y el mensaje anterior del bot tenía el botón de coadyuvantes
    if user_message.lower().strip() in ["si", "sí", "s"]:
        history = conversation_history.get(user_id, [])
        if history and history[-1]["role"] == "assistant":
            last_bot_msg = history[-1]["content"]
            if "Querés ver opciones y dosis de coadyuvantes" in last_bot_msg or "💧" in last_bot_msg:
                await update.message.reply_text(COADYUVANTES_INFO)
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

    # Detectar consulta general hardcodeada (PEE, etc.)
    respuesta_hardcodeada = detectar_consulta_general(user_message)
    if respuesta_hardcodeada:
        await update.message.reply_text(respuesta_hardcodeada)
        conversation_history[user_id].append({
            "role": "assistant",
            "content": respuesta_hardcodeada
        })
        return

    # Detectar consulta de barbecho
    nivel_barbecho = detectar_nivel_barbecho(user_message)
    if nivel_barbecho == 1:
        # Trigger directo — arrancar flujo sin confirmación
        context.user_data['barbecho_estado'] = 'esperando_cultivo'
        context.user_data['barbecho_mensaje_original'] = user_message
        await update.message.reply_text(
            "Antes de comenzar, dejame hacer algunas consultas para darte la mejor recomendación 🌱\n\n"
            "¿Para qué cultivo es el barbecho?",
            reply_markup=kb_cultivo()
        )
        return
    elif nivel_barbecho == 2:
        # Trigger contextual — confirmar primero
        context.user_data['barbecho_estado'] = 'esperando_confirmacion'
        context.user_data['barbecho_mensaje_original'] = user_message
        await update.message.reply_text(
            "¿Me estás consultando sobre manejo de malezas en barbecho o presiembra?",
            reply_markup=kb_confirmar_barbecho()
        )
        return

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
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

        # Detectar si la respuesta requiere botones informativos
        # Opción B: detectar herbicidas que requieren coadyuvante, no solo la palabra "aceite"
        HERBICIDAS_CON_COADYUVANTE = [
            "cletodim", "haloxyfop", "propaquizafop", "quizalofop",
            "saflufenacil", "heat", "carfentrazone", "shark", "flumioxazin",
            "glufosinato", "piraflufen", "stagger"
        ]
        needs_coady_button = any(w in assistant_message.lower() for w in HERBICIDAS_CON_COADYUVANTE)
        needs_2_4d_button = "2,4d" in assistant_message.lower() or "2,4 d" in assistant_message.lower()
        needs_glifo_button = "glifosato" in assistant_message.lower()

        # Separar la línea de invitación del texto principal
        main_message = assistant_message
        if "💧 ¿Querés ver opciones" in assistant_message:
            parts = assistant_message.rsplit("💧 ¿Querés ver opciones", 1)
            main_message = parts[0].rstrip()

        await update.message.reply_text(main_message)

        # Construir botones según lo que aparece en la respuesta
        buttons = []
        if needs_coady_button:
            buttons.append([InlineKeyboardButton(
                "💧 Ver opciones y dosis de coadyuvantes",
                callback_data="show_coadyuvantes"
            )])
        if needs_2_4d_button:
            buttons.append([InlineKeyboardButton(
                "📋 Ver formulaciones y dosis de 2,4D",
                callback_data="show_2_4d"
            )])
        if needs_glifo_button:
            buttons.append([InlineKeyboardButton(
                "📋 Ver formulaciones y dosis de Glifosato",
                callback_data="show_glifosato"
            )])

        if buttons:
            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(
                "ℹ️ Información adicional disponible:",
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error completo: {type(e).__name__}: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error: {type(e).__name__}: {str(e)[:200]}"
        )

# --- CALLBACK HANDLER — botones inline ---
async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Botones informativos
    if data == "show_coadyuvantes":
        await query.message.reply_text(COADYUVANTES_INFO)
        return
    elif data == "show_2_4d":
        await query.message.reply_text(INFO_2_4D)
        return
    elif data == "show_glifosato":
        await query.message.reply_text(INFO_GLIFOSATO)
        return

    # Flujo barbecho — confirmación
    if data == "barb_confirmar_si":
        context.user_data['barbecho_estado'] = 'esperando_cultivo'
        await query.edit_message_text(
            "Antes de comenzar, dejame hacer algunas consultas para darte la mejor recomendación 🌱\n\n"
            "¿Para qué cultivo es el barbecho?",
            reply_markup=kb_cultivo()
        )
        return
    elif data == "barb_confirmar_no":
        context.user_data.clear()
        await query.edit_message_text(
            "Entendido. Haceme tu consulta y te ayudo 🌱"
        )
        return

    # Flujo barbecho — cultivo
    if data.startswith("barb_cultivo_"):
        cultivo = data.replace("barb_cultivo_", "")
        context.user_data['barbecho_cultivo'] = cultivo
        context.user_data['barbecho_estado'] = 'esperando_maleza'

        if cultivo == "trigo":
            await query.edit_message_text(
                f"Cultivo: Trigo/Cebada ✅\n\n¿Qué maleza querés controlar?",
                reply_markup=kb_maleza()
            )
        else:
            cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol"}.get(cultivo, cultivo)
            await query.edit_message_text(
                f"Cultivo: {cultivo_nombre} ✅\n\n¿Qué maleza querés controlar?",
                reply_markup=kb_maleza()
            )
        return

    # Flujo barbecho — maleza
    if data.startswith("barb_maleza_"):
        maleza = data.replace("barb_maleza_", "")
        context.user_data['barbecho_maleza'] = maleza
        cultivo = context.user_data.get('barbecho_cultivo', '')

        if maleza == "otra":
            context.user_data['barbecho_estado'] = 'completo'
            await query.edit_message_text("Maleza: Otra ✅")
            await responder_barbecho_completo(query, context, cultivo, "otra", None, None)
            return

        maleza_nombre = {
            "lolium": "Lolium/Raigrás",
            "conyza": "Rama Negra (Conyza)",
            "brassica": "Crucíferas (Brassica/Nabón)"
        }.get(maleza, maleza)

        # Trigo no tiene distinción largo/corto
        if cultivo == "trigo":
            context.user_data['barbecho_momento'] = 'presiembra'
            context.user_data['barbecho_estado'] = 'esperando_objetivo'
            await query.edit_message_text(
                f"Cultivo: Trigo/Cebada ✅\nMaleza: {maleza_nombre} ✅\n\n¿Qué objetivo buscás?",
                reply_markup=kb_objetivo()
            )
        else:
            context.user_data['barbecho_estado'] = 'esperando_momento'
            cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol"}.get(cultivo, cultivo)
            await query.edit_message_text(
                f"Cultivo: {cultivo_nombre} ✅\nMaleza: {maleza_nombre} ✅\n\n¿Cuándo pensás aplicar?",
                reply_markup=kb_momento()
            )
        return

    # Flujo barbecho — momento
    if data.startswith("barb_momento_"):
        momento = data.replace("barb_momento_", "")
        context.user_data['barbecho_momento'] = momento
        context.user_data['barbecho_estado'] = 'esperando_objetivo'

        cultivo = context.user_data.get('barbecho_cultivo', '')
        maleza = context.user_data.get('barbecho_maleza', '')
        cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol", "trigo": "Trigo/Cebada"}.get(cultivo, cultivo)
        maleza_nombre = {"lolium": "Lolium/Raigrás", "conyza": "Rama Negra (Conyza)", "brassica": "Crucíferas (Brassica/Nabón)"}.get(maleza, maleza)
        momento_nombre = {"largo": "Largo (abril-junio)", "corto": "Corto (agosto-septiembre)"}.get(momento, momento)

        await query.edit_message_text(
            f"Cultivo: {cultivo_nombre} ✅\nMaleza: {maleza_nombre} ✅\nMomento: Barbecho {momento_nombre} ✅\n\n¿Qué objetivo buscás?",
            reply_markup=kb_objetivo()
        )
        return

    # Flujo barbecho — objetivo (último paso)
    if data.startswith("barb_obj_"):
        objetivo = data.replace("barb_obj_", "")
        context.user_data['barbecho_objetivo'] = objetivo
        context.user_data['barbecho_estado'] = 'completo'

        cultivo = context.user_data.get('barbecho_cultivo', '')
        maleza = context.user_data.get('barbecho_maleza', '')
        momento = context.user_data.get('barbecho_momento', '')

        cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol", "trigo": "Trigo/Cebada"}.get(cultivo, cultivo)
        maleza_nombre = {"lolium": "Lolium/Raigrás", "conyza": "Rama Negra (Conyza)", "brassica": "Crucíferas (Brassica/Nabón)"}.get(maleza, maleza)
        momento_nombre = {"largo": "Largo (abril-junio)", "corto": "Corto (agosto-septiembre)", "presiembra": "Presiembra"}.get(momento, momento)
        objetivo_nombre = {"nacida": "Eliminar maleza nacida", "residual": "Prevenir nuevos nacimientos", "ambos": "Ambos objetivos"}.get(objetivo, objetivo)

        await query.edit_message_text(
            f"Cultivo: {cultivo_nombre} ✅\n"
            f"Maleza: {maleza_nombre} ✅\n"
            f"Momento: Barbecho {momento_nombre} ✅\n"
            f"Objetivo: {objetivo_nombre} ✅\n\n"
            f"Buscando recomendación... 🔍"
        )

        await responder_barbecho_completo(query, context, cultivo, maleza, momento, objetivo)
        return

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("nuevo", nuevo))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
