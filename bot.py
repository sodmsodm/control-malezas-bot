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
    "✅ 500 g ia/ha — NORMAL: uso general, óptimo para barbechos\n"
    "⚠️ 750 g ia/ha — MODERADA: malezas fuera del tamaño óptimo, doble golpe\n"
    "⚠️ 1150 g ia/ha — ALTA: malezas comprometidas. Respetar carencias en cultivos sensibles\n\n"
    "DOSIS DE PRODUCTO FORMULADO (cc/ha) SEGÚN g ia/ha:\n\n"
    "Éster Etilhexílico 643 g/L (97 Sigma, Herbifen Advance):\n"
    "✅ 500 g ia = 778 cc/ha\n"
    "⚠️ 750 g ia = 1.166 cc/ha\n"
    "⚠️ 1150 g ia = 1.788 cc/ha\n\n"
    "Éster Etilhexílico 590 g/L (Voleris, LV 89 Sigma, Tornado):\n"
    "✅ 500 g ia = 847 cc/ha\n"
    "⚠️ 750 g ia = 1.271 cc/ha\n"
    "⚠️ 1150 g ia = 1.949 cc/ha\n\n"
    "Sal Dimetilamina 500 g/L (60 Sigma):\n"
    "✅ 500 g ia = 1.000 cc/ha\n"
    "⚠️ 750 g ia = 1.500 cc/ha\n"
    "⚠️ 1150 g ia = 2.300 cc/ha\n\n"
    "Sal Colina 456 g/L (Enlist, Empiric Fusión):\n"
    "✅ 500 g ia = 1.096 cc/ha\n"
    "⚠️ 750 g ia = 1.645 cc/ha\n"
    "⚠️ 1150 g ia = 2.522 cc/ha\n\n"
    "⚠️ Para biotipos resistentes usar SIEMPRE formulación éster — mayor eficacia sistémica"
)

# --- INFO DE GLIFOSATO ---
INFO_GLIFOSATO = (
    "📋 GLIFOSATO — FORMULACIONES Y DOSIS (Fuente: CINVARP / Ojos del Salado)\n\n"
    "DOSIS POR EQUIVALENTE ÁCIDO:\n"
    "✅ 810 g ia/ha — NORMAL: uso general, óptimo para barbechos\n"
    "⚠️ 1080 g ia/ha — MODERADA: malezas sensibles sobre tamaño óptimo. Tolerantes chicas con acompañantes\n"
    "⚠️ 1350 g ia/ha — MODERADA A ALTA: malezas sensibles grandes. Tolerantes medianas con acompañantes\n"
    "🔴 1650 g ia/ha — ALTA: malezas sensibles de tamaños comprometidos\n\n"
    "DOSIS DE PRODUCTO FORMULADO (L/ha) SEGÚN g ia/ha:\n\n"
    "Sal Monoamónica 720 g/L (Control Max — Bayer):\n"
    "✅ 810 g ia = 1,125 L/ha\n"
    "⚠️ 1080 g ia = 1,500 L/ha\n"
    "⚠️ 1350 g ia = 1,875 L/ha\n"
    "🔴 1650 g ia = 2,292 L/ha\n\n"
    "Sal Amónica 688 g/L (Max Sigma):\n"
    "✅ 810 g ia = 1,177 L/ha\n"
    "⚠️ 1080 g ia = 1,570 L/ha\n"
    "⚠️ 1350 g ia = 1,962 L/ha\n"
    "🔴 1650 g ia = 2,398 L/ha\n\n"
    "Sal Potásica 575 g/L (RoundUp Top — Bayer):\n"
    "✅ 810 g ia = 1,409 L/ha\n"
    "⚠️ 1080 g ia = 1,878 L/ha\n"
    "⚠️ 1350 g ia = 2,348 L/ha\n"
    "🔴 1650 g ia = 2,870 L/ha\n\n"
    "Sal Potásica 540 g/L (LT Platinum II, Power Plus II, Full II Sigma):\n"
    "✅ 810 g ia = 1,500 L/ha\n"
    "⚠️ 1080 g ia = 2,000 L/ha\n"
    "⚠️ 1350 g ia = 2,500 L/ha\n"
    "🔴 1650 g ia = 3,056 L/ha\n\n"
    "Sal Potásica 506 g/L (Sulfosato — Syngenta):\n"
    "✅ 810 g ia = 1,601 L/ha\n"
    "⚠️ 1080 g ia = 2,134 L/ha\n"
    "⚠️ 1350 g ia = 2,668 L/ha\n"
    "🔴 1650 g ia = 3,261 L/ha\n\n"
    "Sal Dimetilamina 480 g/L (Panzer Gold — Corteva):\n"
    "✅ 810 g ia = 1,688 L/ha\n"
    "⚠️ 1080 g ia = 2,250 L/ha\n"
    "⚠️ 1350 g ia = 2,813 L/ha\n"
    "🔴 1650 g ia = 3,438 L/ha\n\n"
    "Sal Isopropilamina 445 g/L (Gold Sigma):\n"
    "✅ 810 g ia = 1,820 L/ha\n"
    "⚠️ 1080 g ia = 2,427 L/ha\n"
    "⚠️ 1350 g ia = 3,034 L/ha\n"
    "🔴 1650 g ia = 3,708 L/ha\n\n"
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
✅ Piroxasulfone 85% (Yamato): Soja 0 / Maíz 0 / Trigo PEE (LD sin restricción / LC 15d antes siembra) / Cebada: NO en PEE — máximo PSI 10-15 DAS con riesgo si llueve antes de emergencia — requiere lluvia ≥20 mm dentro de los 15 días post-aplicación para activarse
✅ Clorimurón 25% (Classic): Soja 0 / Maíz 18m / Girasol 18m / Trigo 18m
✅ Saflufenacil 70% (Heat): Soja 3d / Maíz 1d / Trigo 1d / Girasol: NO usar en pre-siembra ni barbecho previo a girasol (marbete BASF)
✅ Metsulfurón 60% (Ally/Errasin): Soja 60d / Maíz 60d / Girasol: NO usar en barbecho previo a girasol
✅ Flurocloridona 25% (Rainbow): Girasol 0 / Trigo 0 / Maíz 0 / Soja: sin registro formal — en ensayos 30-40 días sin problemas (Gigón, Agroconsultas 2020)
✅ Diflufenicán 50% (Brodal): Trigo 10d / Girasol 0 / Soja 15d / Maíz 15d
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

=== ANTAGONISMO GRAMINICIDAS + HORMONALES ===

⚠️ REGLA DE SEPARACIÓN DE APLICACIONES:
Cuando una estrategia incluye un graminicida ACCasa (cletodim, haloxifop) junto con un herbicida hormonal (2,4D éster, 2,4D amina, dicamba), SIEMPRE recomendar aplicaciones separadas como primera opción.

ORDEN Y TIMING:
✅ Primero el graminicida — esperar 7 a 10 días
✅ Luego el hormonal (con buenas condiciones: humedad, insolación)
⚠️ Con días nublados prolongados, extender el intervalo hasta normalizar clima

MOTIVO: antagonismo bioquímico-fisiológico. Los activos compiten por zonas meristemáticas. El afectado es siempre el graminicida.
Fuente: Druetta et al. INTA EEA Santiago del Estero 2016 / Nicasio Rodriguez, Agroconsultas 2018

GRADO DE ANTAGONISMO (de mayor a menor):
🔴 2,4D éster — antagonismo severo sobre cletodim y haloxifop
🔴 2,4D amina — antagonismo severo sobre cletodim y haloxifop
⚠️ Dicamba — antagonismo intermedio
⚠️ Resto de hormonales (picloram, fluroxipir, etc.) — precaución, efecto variable según condiciones

HALOXIFOP: más sensible al antagonismo que cletodim. Separación de aplicaciones es aún más crítica.

SI LA SEPARACIÓN NO ES POSIBLE (un solo golpe):
⚠️ Aumentar dosis del graminicida un 20% sobre la dosis normal
⚠️ Usar aceite metilado de soja (MSO) al 1%
⚠️ Aplicar en condiciones óptimas: temperatura 15-25°C, humedad >50%, sin viento excesivo
Validación: criterio agronómico regional

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
BARBECHO CORTO/PRESIEMBRA: aplicación agosto-septiembre. Objetivo: pico 2 de emergencia y presiembra inmediata.
TRIGO: sin distinción largo/corto — siempre presiembra por calendario de siembra invernal.

--- LOLIUM (RAIGRÁS) EN BARBECHO ---

LOLIUM — BARBECHO LARGO — SOJA / MAÍZ (abril-junio):

⚠️ MOMENTO: Aplicaciones en marzo-abril pierden eficacia a los 60-75 días si se usan solas. En abril sumar residual o usar doble golpe. Desde mayo la aplicación simple sostiene mejor el control.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ABRIL:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe con residual
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — sin residual de suelo, agrega MOA

MAYO-JUNIO:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha de resistencia ACCasa

⚠️ RESISTENCIA ACCasa: Cletodim solo puede quedar entre 5-70% según biotipo. Ante sospecha usar mezcla triple o doble golpe.

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

⚠️ Los residuales actúan en suelo sobre semillas y plántulas antes de emerger. No eliminan maleza ya nacida. Combinar siempre con sistémico si hay plantas visibles.

SOJA Y MAÍZ:
🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — mejor residualidad sostenida hasta 150 DDA. Sin restricción en soja ni maíz
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha sola — buena residualidad hasta 90 DDA
🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha — desempeño similar como opción individual
⚠️ Pyroxasulfone (Yamato): en trigo PEE sin restricción (LD) / 15d antes siembra (LC). En cebada: NO en PEE — máximo PSI 10-15 DAS con riesgo si llueve antes de emergencia. Requiere lluvia ≥20 mm dentro de los 15 días post-aplicación.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

SOJA Y MAÍZ — ABRIL:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe completo, máximo control
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — aplicación única con residual
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha — una opción residual

SOJA Y MAÍZ — MAYO-JUNIO:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


LOLIUM — BARBECHO LARGO — GIRASOL (abril-junio):

⚠️ Atrazina fitotóxica en girasol — NO usar.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ABRIL:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe con residual
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — sin residual de suelo, agrega MOA

MAYO-JUNIO:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha de resistencia ACCasa

⚠️ RESISTENCIA ACCasa: Ante sospecha usar mezcla triple o doble golpe.

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — mejor residualidad. Sin restricción en girasol
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha sola
🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha — desempeño similar

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

ABRIL:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha

MAYO-JUNIO:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


LOLIUM — BARBECHO — TRIGO (presiembra):

⚠️ Pyroxasulfone (Yamato): PEE en trigo sin restricción de días (LD) / 15d antes siembra (LC). Cebada: NO en PEE — máximo PSI 10-15 DAS con riesgo si llueve entre aplicación y emergencia. Requiere lluvia ≥20 mm dentro de los 15 días post-aplicación para activarse.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

SITUACIÓN 1 — 1-2 hojas, baja densidad:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,6 L/ha
🥈 Glufosinato 28% 2 L/ha
🥉 Paraquat 27,6% (Gramoxone) 2 L/ha

SITUACIÓN 2 — 2-4 hojas, densidad media:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 12%/Haloxyfop 6% (Gramini Elite) 1 L/ha

SITUACIÓN 3 — más de 4 hojas o sospecha de resistencia ACCasa:
🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha
🥈 Glufosinato 28% 2 L/ha + Cletodim 24% (Select) 0,8 L/ha

SITUACIÓN 4 — resistencia confirmada O maleza muy establecida (alta densidad / 5+ macollos) — Doble Golpe:
🔁 1° Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7 días después
🔁 1° Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // 2° Glufosinato 28% 2 L/ha — 7 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Azugro (Bixlozona) FMC — residual específico para Lolium en trigo/avena. Presiembra, sin restricción de carencia en trigo
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en trigo
🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha ó Pendimetalín (Herbadox/Satellite) — ⚠️ Yamato: PEE trigo sin restricción (LD) / 15d LC y cebada. Requiere lluvia ≥20 mm post-aplicación

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Azugro (Bixlozona) — elimina nacida y deja residual específico para trigo
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha — sin residual, opción mínima


LOLIUM — BARBECHO CORTO/PRESIEMBRA — SOJA / MAÍZ (agosto-septiembre):

⚠️ MOMENTO: Agosto-septiembre es la ventana óptima. Control sostenido sin necesidad de doble golpe en la mayoría de los casos.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — ante sospecha de resistencia ACCasa
🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

SOJA Y MAÍZ:
🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — sin restricción en soja ni maíz
🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha — sin restricción en soja ni maíz
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


LOLIUM — BARBECHO CORTO/PRESIEMBRA — GIRASOL (agosto-septiembre):

⚠️ Atrazina fitotóxica en girasol — NO usar.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha
🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha
🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha


--- CONYZA (RAMA NEGRA) EN BARBECHO ---

CONYZA — BARBECHO LARGO — SOJA (abril-junio):

⚠️ MOMENTO: Conyza tiene dos picos de emergencia — otoño (abril) y primavera (septiembre). Roseta menor a 10 cm responde mejor. Mayor a 10 cm requiere doble golpe.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — mejor control sostenido a 45 DDA sin paraquat
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — buena combinación hormonal
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — base mínima

PPO de contacto como apoyo (agregar a cualquiera):
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior en control
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción en ningún cultivo

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7-14 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

⚠️ Atrazina — sin registro formal en barbecho a soja. No recomendar.
🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — mejor residualidad sostenida a 120 DDA. Sin restricción en soja
🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha — registrado para barbecho de otoño a soja
🥈 Atrazina 90% 2,25 L/ha — datos de campo muy buenos a 120 DDA. ⚠️ Verificar registro local antes de usar en barbecho a soja
🥉 Finesse (Clorsulfurón + Metsulfurón) 15 g/ha — buena residualidad. ⚠️ 60 días carencia antes de soja
🥉 Metsulfurón 60% (Ally) 7 g/ha — opción económica, algo menor persistencia a 120 DDA

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO LARGO — MAÍZ (abril-junio):

OBJETIVO 1 — igual que soja

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha — combinación más potente, registrada en maíz
🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha — sin atrazina, buena residualidad
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — buena residualidad hasta 120 DDA

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO LARGO — GIRASOL (abril-junio):

⚠️ Atrazina fitotóxica — NO usar. Biciclopirone sin registro en girasol — NO usar. Saflufenacil NO usar en pre-siembra girasol. Metsulfurón NO usar en barbecho previo a girasol.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo antes de siembra girasol
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha

PPO de contacto como apoyo:
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — único PPO disponible en pre-siembra girasol

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en girasol
🥈 Atrazina 90% 2,25 L/ha — ⚠️ 90 días de intervalo antes de siembra girasol. Solo en barbecho largo con siembra a más de 90 días
🥉 Diflufenican 50% (Brodal) 250 cc/ha — 0 días intervalo en girasol. Menor residualidad que las anteriores

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Carfentrazone 40% (Shark) 75 cc/ha — ⚠️ verificar 45 días Lontrel
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Carfentrazone 40% (Shark) 75 cc/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + residual + Shark // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO — TRIGO (presiembra):

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días intervalo en trigo
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días intervalo
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — 3-5 días intervalo

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Metsulfurón 60% (Ally/Errasin) 7-8 g/ha — 0 días intervalo en trigo. Buena residualidad para Conyza
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — buena residualidad hasta 120 DDA
🥉 Diflufenican 50% (Brodal) 250 cc/ha — 15 días intervalo en trigo. Menor residualidad

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


CONYZA — BARBECHO CORTO/PRESIEMBRA — SOJA / MAÍZ (agosto-septiembre):

⚠️ MOMENTO: Segundo pico de emergencia. Plántulas pequeñas — mejor momento para control.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

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
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — ⚠️ verificar 45 días

MAÍZ:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha


CONYZA — BARBECHO CORTO/PRESIEMBRA — GIRASOL (agosto-septiembre):

⚠️ Pixxaro puede aplicarse hasta 0 días antes de siembra de girasol — ventaja clave en barbecho corto.
⚠️ Saflufenacil, metsulfurón NO usar en pre-siembra girasol.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

🥇 Glifosato 1080 g ia/ha + Pixxaro (Halauxifen metil + Fluroxipir) 400-500 cc/ha + aceite mineral 1% v/v — registrado específicamente para Conyza en pre-siembra girasol, sin restricción de intervalo (SENASA N° 40.386)
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — ⚠️ 7-15 días antes de siembra girasol
🥉 Glifosato 1080 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días antes de siembra girasol

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + Pixxaro 500 cc/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7-14 días después

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en girasol
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en girasol
🥉 Diflufenican 50% (Brodal) 250 cc/ha — 0 días intervalo en girasol. Menor residualidad

⚠️ Atrazina — 90 días de intervalo. No alcanza en barbecho corto para siembra inmediata de girasol.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + Pixxaro 400-500 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite mineral 1% v/v
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar 7-15 días antes de siembra
🥉 Glifosato 1080 g ia/ha + Pixxaro 400-500 cc/ha + Diflufenican 50% (Brodal) 250 cc/ha + aceite mineral 1% v/v


--- BRASSICA RAPA (NABÓN/NABO/MOSTACILLA) EN BARBECHO ---

⚠️ IDENTIFICACIÓN: Brassica rapa (nabo/nabolza) flor AMARILLA, hojas amplexicaules. Raphanus sativus (nabón) flor VIOLÁCEA/ROSADA. Hirschfeldia incana (nabillo/mostacilla) flor AMARILLO PÁLIDO. Ver sección BRASICÁCEAS para resistencias confirmadas.
⚠️ BIOTIPOS RESISTENTES: Con resistencia a ALS no usar sulfonilureas ni imidazolinonas. Con resistencia a glifosato agregar PPO quemante obligatorio. Con TRIPLE resistencia: doble golpe obligatorio con desecante.

BRASSICA — BARBECHO LARGO — SOJA / MAÍZ (abril-junio):

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 94% control a 45 DDA
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha

PPO de contacto como apoyo (agregar a cualquiera):
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior en control
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción en ningún cultivo

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha — 7-14 días después

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
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha

MAÍZ:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha


BRASSICA — BARBECHO LARGO — GIRASOL (abril-junio):

⚠️ Biciclopirone sin registro en girasol — NO usar. Atrazina fitotóxica — NO usar. Heat NO usar en pre-siembra girasol. Flurocloridona es la estrella para Brassica en girasol.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo antes de siembra girasol
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días intervalo
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — ⚠️ 7-15 días intervalo

PPO de contacto como apoyo:
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — único PPO disponible en pre-siembra girasol

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 120 cc/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — estrella para Brassica en girasol. 96-97% a 150 DDA. Sin restricción
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — 96% a 150 DDA
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia que la mezcla pero válido. 0 días intervalo girasol

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

ABRIL:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha — ⚠️ verificar 45 días Lontrel
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

MAYO-JUNIO:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha


BRASSICA — BARBECHO — TRIGO (presiembra):

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días intervalo en trigo
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días intervalo
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — 3-5 días intervalo

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — 0 días intervalo en trigo. Mejor opción residual para Brassica
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha — ⚠️ Brodal 15 días intervalo
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia, 15 días intervalo

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + residual // 2° Paraquat 27,6% (Gramoxone) 2 L/ha


BRASSICA — BARBECHO CORTO/PRESIEMBRA — SOJA / MAÍZ (agosto-septiembre):

⚠️ Verificar intervalos de carencia con especial atención — la siembra es inmediata.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ Lontrel 45 días en soja. Solo si siembra está a más de 45 días
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 15-20 días intervalo en soja
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — 7-15 días intervalo en soja

PPO de contacto como apoyo:
✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción en soja ni maíz

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

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
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Heat 35-40 g/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Heat 35-40 g/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar 30-40 días antes de soja

MAÍZ:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha + Heat 35-40 g/ha
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Heat 35-40 g/ha
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz


BRASSICA — BARBECHO CORTO/PRESIEMBRA — GIRASOL (agosto-septiembre):

⚠️ Biciclopirone sin registro — NO usar. Atrazina 90 días intervalo — NO alcanza. Heat NO usar. Flurocloridona es la estrella.

OBJETIVO 1 — ELIMINAR MALEZA YA NACIDA:

ROSETA MENOR A 10 CM:
🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo en girasol
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días intervalo
🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — ⚠️ 7-15 días intervalo

PPO de contacto como apoyo:
✅ Carfentrazone 40% (Shark) 75-120 cc/ha — único PPO en pre-siembra girasol

ROSETA MAYOR A 10 CM — Doble Golpe obligatorio:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 120 cc/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

OBJETIVO 2 — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL):

🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en girasol
🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha
🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha
🥉 Diflufenican 50% (Brodal) 250 cc/ha solo — menor eficacia, 0 días intervalo girasol

⚠️ Atrazina NO alcanza 90 días en barbecho corto a siembra inmediata de girasol.

OBJETIVO 3 — ELIMINAR MALEZA NACIDA + PREVENIR NUEVOS NACIMIENTOS:

🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ verificar 7-15 días antes de siembra
🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha
🥉 Glifosato 1080 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ 15-20 días Banvel

⚠️ Roseta mayor a 10 cm:
🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona + Shark // 2° Paraquat 27,6% (Gramoxone) 2 L/ha

=== SOJA ===

SOJA: MALEZA GENERAL (No GMO)

BARBECHO CORTO/PRESIEMBRA (45-60 DAS):
✅ Flumioxazin 48% 150 cc (Sumisoya)
✅ Piroxasulfone 85% 160-200 g (Yamato)
✅ Diflufenicán 50% 0,3 l (Brodal) hasta 15 DAS
✅ Atrazina 90% 1-1,5 kg hasta 40 DAS
✅ Amicarbazone 70% (Dinamic — UPL SENASA 39.179) 320-400 g/ha soja (mínimo 45 DAS; suelos livianos hasta 120 DAS). Maíz: 320-700 g/ha barbecho/PEE. Fotosistema II. POE temprano Conyza hasta 4 hojas. NO >50% arena en soja
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
✅ Flumioxazin 15%/Pyroxasulfone 34,5% (Fierce RM — Summit Agro SENASA 39.782) 400-500 cc/ha — PEE soja/maíz/maní. Soja: 15 DAS livianos / 7 DAS medianos / PEE pesados. Maíz: 10-15 DAS. Requiere ≥20mm lluvia. LC +7 días todos los intervalos
✅ Sumyzin T Max (Terbutilazina 50% + Flumioxazin 3,8% — Sumitomo SENASA 40.689) 1,5-2,25 L/ha — barbecho largo/corto y PEE trigo. Trigo: 1,5 L/ha, 10-15 DAS, semilla ≥4 cm, ≥20mm lluvia, NO suelos livianos. Soja barbecho corto: 1,15-1,25 L/ha hasta 30-40 DAS. Maíz: hasta presiembra
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

PEE BARBECHO CORTO/PRESIEMBRA:
✅ Flumioxazin (Sumisoya)
✅ Piroxasulfone (Yamato)
✅ Atrazina 90%
✅ Metribuzin (Sencorex)

PEE / PSI-PEE:
✅ Sulfentrazone 50% (Authority/Capaz) + S-metolacloro 96% (Dual Gold)
✅ Flumioxazin 15%/Piroxasulfone 34,5% (Fierce RM Summit Agro) 7 DAS
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
✅ Terbutrina (Igran)
✅ Terbutilazina (Terbine)

PSI / Barbecho Intermedio:
✅ Flumioxazin (Sumisoya) 10 DAS
✅ Voraxor 7 DAS

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

PSI / Barbecho Intermedio:
✅ Flumioxazin (Sumisoya) 10 DAS

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

PSI / Barbecho Intermedio:
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

ANTES DE SIEMBRA (PSI — quema pre-siembra):
✅ Paraquat 27,6% 1,5-2,5 L/ha
✅ Glufosinato 28% 1-2,5 L/ha
✅ Glifosato (dosis v.s.f.)
✅ 2,4D (15-20 DAS) — formulaciones éster ethyl o mictoemia
✅ Fluroxipir / Clopyralid — hormonal amplio espectro
✅ Saflufenacil 70% (Heat) 35-40 g/ha — PPO
✅ Carfentrazone 40% (Shark) 70-80 cc/ha — PPO

PEE (Pre-emergencia del cultivo):
✅ Trifluralina 60% (Adama Essentials) 1,5 L/ha — único con registro formal
✅ Pendimetalín 45,6% (Satellite/Herbadox) 2,5-3,5 L/ha — registro
⚠️ Clomazone 36% 1,5 L/ha — sin registro en colza Argentina
⚠️ Imidazolinonas — solo Colzas CL, sin registro formal en ARG
⚠️ Triazinas (atrazina, metribuzín, terbutilazina) — sin registro en colza
⚠️ Carinata: SOLO trifluralina como residual registrado

POST-EMERGENCIA DEL CULTIVO (estado roseta BBCH 14-16):
Gramíneas:
✅ Cletodim (Select) — gramíneas. Registro
✅ Haloxyfop (Galant Max) — gramíneas. Registro
⚠️ Carinata: solo graminicidas y clopyralid

Latifoliadas (RIESGO FITOTÓXICO — respetar estrictamente estado roseta):
✅ Clopyralid 47,5% (Lontrel) 100-150 cc/ha — riesgo BAJO
✅ Halauxifén (Pixxaro) 400-500 cc/ha — riesgo BAJO. ⚠️ registro Uruguay, NO Argentina
✅ Dicamba 57,5% (Banvel) 40-60 cc/ha — riesgo MEDIO. Solo en roseta estricta
✅ Picloram 24% 40-80 cc/ha — riesgo MEDIO
⚠️ Fluroxipir 48% 200 cc/ha — riesgo MODERADO/ALTO
✅ Imidazolinonas — solo Colzas CL
✅ Triazinas (con resistencia) — solo Colzas con resistencia a triazinas

RIESGO ROTACIÓN COLZA — Residuos de herbicidas del cultivo anterior:
⚠️ ALTO (>300mm lluvia + 4-6 meses): Imidazolinonas, Sulfonilureas, Diclosulam
⚠️ MODERADO (>200mm + 4 meses): Sulfentrazone, Topramezone, Mesotrione, Biciclopirona, Thiencarbazone
⚠️ BAJO (>150mm + 2 meses): Flumioxazín, Piroxasulfone (>100mm + 2 meses)
⚠️ Esta tabla aplica especialmente cuando en la rotación anterior hubo maíz (Adengo, Acuron, Zidua) o soja (Diclosulam, ALS)

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

PEE (después de siembra, antes de emergencia del cultivo):
✅ Piroxasulfone 85% (Yamato TOP) 100-120 g/ha — VLCFA, gramíneas. Requiere ≥20mm lluvia en 15 días. Cebada: solo PSI (15 DAS)
✅ Pendimetalín 45,5% (Herbadox H2O) 2-2,5 L/ha — microtúbulos, gramíneas. Semilla trigo a ≥3 cm
✅ Mateno Plus (Flufenacet + Diflufenican + Aclonifen) 2-2,25 L/ha — triple MoA grupos 15+12+32, raigrás + crucíferas
✅ Carfentrazone-etil (Shark) — PPO, latifoliadas
✅ Saflufenacil 70% (Heat) — PPO, latifoliadas. SIN aceite desde Z1.2-Z1.3
✅ Pyraflufen-etil (Stagger) — PPO, latifoliadas
✅ Terbutrina 50% (Igran) 1,2 L/ha — PSII, latifoliadas invernales
✅ Terbutilazina 75% (Gesatop 75) 1 kg/ha — PSII, latifoliadas
✅ Flurocloridona 25% (Rainbow/Talis) 1-1,5 L/ha — PDS, crucíferas. No superar 1,5 L/ha en trigo
✅ Diflufenicán 50% (Brodal) 250-350 cc/ha — PDS, crucíferas y latifoliadas
✅ Metsulfurón 60% (Ally/Errasin WP) 8-10 g/ha — ALS, latifoliadas. NO usar previo a girasol
✅ Clorsulfurón + Metsulfurón (Finesse WG) 12-15 g/ha — ALS doble MoA, latifoliadas
✅ Auxinas/hormonales (2,4D, Dicamba, MCPA, Fluroxipir, Picloram y mezclas) — según maleza y estadio cultivo

PSI / Barbecho Intermedio (antes de siembra):
✅ Flumioxazin 48% (Sumisoya) — PPO, latifoliadas, hasta 10 DAS antes siembra
✅ Trifludimoxazin/Saflufenacil (Voraxor) 100-200 cc/ha — PPO+PDS, barbecho químico, hasta 7 DAS
✅ Azugro (Bixlozona) 1,2-1,5 L/ha — grupo 13, raigrás. Hasta 14 DAS trigo / 60 DAS cebada. Incompatible con glifosato sal potásica

💡 Estos son los productos de mayor uso y mejor desempeño general en PEE de trigo y cebada. La elección final depende de la maleza presente en el lote y las resistencias confirmadas en la zona.

¿Qué maleza o malezas tenés en el lote? Con eso te doy una recomendación más precisa.


SOJA: PEE — PRODUCTOS PRINCIPALES

✅ Flumioxazin 48% (Sumisoya) — PPO, latifoliadas, 7 DAS
✅ Trifludimoxazin / Saflufenacil (Voraxor) — PPO+PDS, amplio espectro, 7 DAS
✅ Flumioxazin / Piroxasulfone (Fierce RM Summit Agro) — PPO+VLCFA, 7 DAS
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
        "✅ Flumioxazin / Piroxasulfone (Fierce RM Summit Agro) — PPO+VLCFA, 7 DAS\n"
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
    "alfalfa": "alfalfa", "pastura": "alfalfa", "pasturas": "alfalfa",
}
MOMENTOS_ALIAS = {
    "pee": "pee", "pre-emergencia": "pee", "preemergencia": "pee",
    "pre emergencia": "pee",
}

# Principios activos y términos que indican consulta específica — no interceptar
TERMINOS_CONSULTA_ESPECIFICA = [
    "cletodim", "haloxifop", "glifosato", "glufosinato", "atrazina",
    "metribuzin", "metribuzín", "s-metolacloro", "metolacloro",
    "acetoclor", "pyroxasulfone", "piroxasulfone", "flumioxazin",
    "saflufenacil", "carfentrazone", "diclosulam", "imazetapir",
    "imazapic", "imazamox", "metsulfuron", "metsulfurón",
    "tribenuron", "clorsulfuron", "fluroxipir", "dicamba",
    "picloram", "picloran", "2,4d", "2,4 d", "mcpa",
    "terbutilazina", "terbutrina", "flurocloridona", "diflufenican",
    "diflufenicán", "bixlozona", "epyrifenacil", "trifluralina",
    "pendimetalin", "pendimetalín", "aclonifen", "bicyclopyrone",
    "biciclopirone", "isoxaflutole", "isoxaflutol", "tembotrione",
    "sulcotrione", "mesotrione", "nicosulfuron", "nicosulfurón",
    "rimsulfuron", "foramsulfuron", "topramezone", "select",
    "yamato", "heat", "shark", "authority", "capaz", "flexstar",
    "fomesafen", "lactofen", "acifluorfen", "clethodim",
    # términos que indican pregunta puntual
    "días antes", "dias antes", "cuántos días", "cuantos dias",
    "intervalo", "carencia", "restricción", "restriccion",
    "dosis", "cuánto", "cuanto", "cómo", "como aplicar",
    "se puede mezclar", "puedo mezclar", "antagonismo",
    "fitotoxic", "resistencia confirmada",
]

def detectar_consulta_general(texto):
    """Retorna la respuesta hardcodeada si el mensaje es una consulta general, o None si no lo es."""
    t = texto.lower().strip()

    # Si la consulta contiene un principio activo específico o término puntual,
    # no interceptar — dejar que la API responda con precisión
    for termino in TERMINOS_CONSULTA_ESPECIFICA:
        if termino in t:
            return None

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
        # Si es trigo/cebada PEE, ceder al flujo guiado
        if cultivo_detectado in ("trigo", "cebada", "soja", "maiz", "maíz", "girasol", "sorgo") and momento_detectado == "pee":
            return None
        return RESPUESTAS_GENERALES.get((cultivo_detectado, momento_detectado))
    return None

# --- FLUJO GUIADO PEE ---

# Keywords que indican consulta PEE con cultivo trigo/soja pero sin maleza u objetivo completos
PEE_TRIGO_KEYWORDS = [
    "pee trigo", "pee en trigo", "pee cebada", "pee en cebada",
    "pre emergencia trigo", "preemergencia trigo",
    "pre emergencia cebada", "preemergencia cebada",
    "pre-emergencia trigo", "pre-emergencia cebada",
]

PEE_SOJA_KEYWORDS = [
    "pee soja", "pee en soja",
    "pre emergencia soja", "preemergencia soja", "pre-emergencia soja",
]

PEE_GIRASOL_KEYWORDS = [
    "pee girasol", "pee en girasol",
    "pre emergencia girasol", "preemergencia girasol", "pre-emergencia girasol",
]

PEE_SORGO_KEYWORDS = [
    "pee sorgo", "pee en sorgo",
    "pre emergencia sorgo", "preemergencia sorgo", "pre-emergencia sorgo",
]

PEE_MAIZ_KEYWORDS = [
    "pee maiz", "pee maíz", "pee en maiz", "pee en maíz",
    "pre emergencia maiz", "pre emergencia maíz",
    "preemergencia maiz", "preemergencia maíz",
    "pre-emergencia maiz", "pre-emergencia maíz",
]

# Keywords de malezas para detección en consulta directa (trigo)
PEE_MALEZA_KEYWORDS_TRIGO = {
    "raigras": "raigras", "raigrás": "raigras", "lolium": "raigras",
    "conyza": "conyza", "rama negra": "conyza", "coniza": "conyza",
    "cruciferas": "cruciferas", "crucíferas": "cruciferas",
    "brassica": "cruciferas", "nabon": "cruciferas", "nabón": "cruciferas",
}

# Keywords de malezas para detección en consulta directa (soja)
PEE_MALEZA_KEYWORDS_SOJA = {
    "amaranthus": "amaranthus", "yuyo colorado": "amaranthus",
    "yuyo": "amaranthus", "palmeri": "amaranthus", "hybridus": "amaranthus",
    "cruciferas": "cruciferas", "crucíferas": "cruciferas",
    "brassica": "cruciferas", "nabon": "cruciferas", "nabón": "cruciferas",
    "commelina": "commelina", "santa lucia": "commelina", "santa lucía": "commelina",
    "parietaria": "parietaria",
    "cebollin": "cebollin", "cebollín": "cebollin", "cyperus": "cebollin",
    "conyza": "conyza", "rama negra": "conyza", "coniza": "conyza",
}

# Keywords de malezas para detección en consulta directa (maíz)
PEE_MALEZA_KEYWORDS_MAIZ = {
    "raigras": "raigras", "raigrás": "raigras", "lolium": "raigras",
    "amaranthus": "amaranthus", "yuyo colorado": "amaranthus",
    "yuyo": "amaranthus", "palmeri": "amaranthus", "hybridus": "amaranthus", "quitensis": "amaranthus",
    "cebollin": "cebollin", "cebollín": "cebollin", "cyperus": "cebollin",
    "cruciferas": "cruciferas", "crucíferas": "cruciferas",
    "brassica": "cruciferas", "nabon": "cruciferas", "nabón": "cruciferas",
}

# Keywords de malezas para detección en consulta directa (girasol)
PEE_MALEZA_KEYWORDS_GIRASOL = {
    "general": "general", "latifoliada": "general", "latifoliadas": "general",
    "cebollin": "cebollin", "cebollín": "cebollin", "cyperus": "cebollin",
    "cruciferas": "cruciferas", "crucíferas": "cruciferas",
    "brassica": "cruciferas", "nabon": "cruciferas", "nabón": "cruciferas",
}
PEE_OBJETIVO_KEYWORDS = {
    "nacida": "nacida", "nacido": "nacida", "emergida": "nacida",
    "emergido": "nacida", "ya nacio": "nacida", "ya nació": "nacida",
    "residual": "residual", "residualidad": "residual",
    "ambos": "ambos", "los dos": "ambos", "todo": "ambos",
}

def detectar_pee_guiado(texto):
    """
    Retorna:
      - None si no es consulta PEE
      - dict con claves 'cultivo', 'maleza' y/o 'objetivo' (pueden ser None)
    Detecta cultivo y momento PEE por separado (orden libre en el texto).
    """
    t = texto.lower().strip()

    # Detectar momento PEE (orden libre)
    es_pee = any(kw in t for kw in MOMENTOS_ALIAS if MOMENTOS_ALIAS[kw] == "pee")
    if not es_pee:
        return None

    # Detectar cultivo (orden libre)
    cultivo = None
    maleza_keywords = None
    for palabra, cult in CULTIVOS_ALIAS.items():
        if palabra in t:
            if cult in ("trigo", "cebada"):
                cultivo = "trigo"
                maleza_keywords = PEE_MALEZA_KEYWORDS_TRIGO
            elif cult == "soja":
                cultivo = "soja"
                maleza_keywords = PEE_MALEZA_KEYWORDS_SOJA
            elif cult in ("maiz", "maíz"):
                cultivo = "maiz"
                maleza_keywords = PEE_MALEZA_KEYWORDS_MAIZ
            elif cult == "girasol":
                cultivo = "girasol"
                maleza_keywords = PEE_MALEZA_KEYWORDS_GIRASOL
            elif cult == "sorgo":
                cultivo = "sorgo"
                maleza_keywords = {}
            break

    if not cultivo:
        return None

    maleza = None
    for kw, val in maleza_keywords.items():
        if kw in t:
            maleza = val
            break
    objetivo = None
    for kw, val in PEE_OBJETIVO_KEYWORDS.items():
        if kw in t:
            objetivo = val
            break
    return {"cultivo": cultivo, "maleza": maleza, "objetivo": objetivo}

# --- Respuestas hardcodeadas PEE trigo raigrás ---

def pee_trigo_raigras_residual():
    return (
        "TRIGO / CEBADA — RAIGRÁS — PEE RESIDUAL\n\n"
        "Opciones para evitar nacimientos de raigrás:\n\n"
        "🌾 EN TRIGO:\n"
        "✅ Piroxasulfone 85% (Yamato Top) 100-120 g/ha — VLCFA grupo K3\n"
        "   Requiere ≥20mm lluvia dentro de los 15 días post-aplicación\n"
        "   En labranza convencional: aplicar al menos 15 días antes de emergencia\n\n"
        "✅ Mateno Plus (Flufenacet 120 + Diflufenican 30 + Aclonifen 450 g/L) 2-2,25 L/ha — triple MoA grupos 15+12+32\n"
        "   Controla raigrás Y crucíferas. Requiere buena humedad al momento de aplicación\n\n"
        "🌾 EN CEBADA:\n"
        "⚠️ Pyroxasulfone NO se puede aplicar en PEE de cebada. Como máximo 10-15 días antes de siembra (PSI), con riesgo si hay lluvias entre aplicación y emergencia.\n\n"
        "✅ Mateno Plus (Flufenacet 120 + Diflufenican 30 + Aclonifen 450 g/L) 2-2,25 L/ha — mejor opción PEE en cebada\n"
        "   Controla raigrás Y crucíferas. Requiere buena humedad al momento de aplicación\n\n"
        "🥉 Pendimetalín 45,5% (Herbadox H2O) 2-2,5 L/ha suelo medio / 3 L/ha suelo pesado — opción de última instancia\n"
        "   ⚠️ Eficacia limitada sobre raigrás residual — no es la mejor opción para esta maleza\n"
        "   Semilla debe estar a ≥3 cm de profundidad y bien cubierta\n"
        "   Regar si no llueven 15mm dentro de los 5 días post-aplicación\n\n"
        "⚠️ Todos actúan sobre semillas y plántulas en germinación. No controlan raigrás ya nacido.\n"
        "⚠️ Para PSI (antes de siembra): ver opciones de Barbecho Corto/Presiembra — Azugro (Bixlozona) 1,2-1,5 L/ha hasta 14 DAS"
    )

def pee_trigo_raigras_nacida():
    return (
        "TRIGO / CEBADA — RAIGRÁS — RESCATE SOBRE MALEZA NACIDA\n\n"
        "⚠️ En PEE no hay opciones eficientes sobre raigrás ya nacido.\n"
        "Como rescate para reducir competencia:\n\n"
        "✅ Paraquat 27,6% (Gramoxone)\n"
        "   2 L/ha en hojas / 2,5-3 L/ha en macollaje\n"
        "   Contacto — quema parte aérea, puede rebrotar. No sistémico.\n\n"
        "✅ Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Paraquat 27,6%\n"
        "   2 L/ha en hojas / 2,5-3 L/ha en macollaje\n"
        "   Suma acción sistémica al contacto\n\n"
        "⚠️ Control parcial — no esperar resultado satisfactorio sobre plantas establecidas.\n\n"
        "🔁 Una vez emergido el trigo (desde Z1.2) hay opciones POE reales:\n"
        "   Pinoxaden (Axial), Clodinafop (Gizmo/Topick), Iodosulfurón+Mesosulfurón (Hussar Plus),\n"
        "   Piroxulam (PowerFlex), Imazamox (Pulsar/Trigosol) en CL, Glufosinato en HB4"
    )

def pee_trigo_raigras_ambos():
    return (
        "TRIGO / CEBADA — RAIGRÁS — RESIDUAL + RESCATE SOBRE NACIDA\n\n"
        "Estrategia: controlar lo nacido Y dejar residual para nuevos nacimientos.\n\n"
        "🌾 EN TRIGO:\n"
        "✅ Paraquat 27,6% (Gramoxone) 2 L/ha (hojas) / 2,5-3 L/ha (macollaje)\n"
        "   + Yamato Top 100-120 g/ha como residual\n"
        "   Aplicar en la misma pasada o inmediatamente después\n\n"
        "✅ Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Paraquat 27,6% 2-3 L/ha\n"
        "   + Mateno Plus 2-2,25 L/ha como residual\n\n"
        "🌾 EN CEBADA:\n"
        "⚠️ Yamato NO va en PEE de cebada. Usar Mateno Plus o Pendimetalín como residual.\n"
        "✅ Paraquat 27,6% (Gramoxone) 2-3 L/ha + Mateno Plus 2-2,25 L/ha\n"
        "🥉 Paraquat 27,6% (Gramoxone) 2-3 L/ha + Pendimetalín 45,5% (Herbadox H2O) 2,5-3 L/ha\n"
        "   ⚠️ Pendimetalín tiene eficacia limitada sobre raigrás — opción de última instancia\n\n"
        "⚠️ Aplicar residual siempre con lote sin cobertura verde activa.\n"
        "⚠️ Azugro (Bixlozona) NO mezclar con glifosato de sal potásica.\n"
        "⚠️ El rescate sobre nacida es parcial — complementar con POE desde Z1.2:\n"
        "   Pinoxaden (Axial), Clodinafop (Gizmo/Topick), Hussar Plus, PowerFlex"
    )

def pee_trigo_conyza_residual():
    return (
        "TRIGO / CEBADA — CONYZA (Rama Negra) — PEE RESIDUAL\n\n"
        "Opciones para evitar nacimientos de conyza:\n\n"
        "✅ Metsulfurón 60% (Ally/Errasin WP) 8-10 g/ha — ALS\n"
        "   Residualidad moderada. No usar en barbecho previo a girasol.\n\n"
        "✅ Finesse WG (Clorsulfurón 25% + Metsulfurón 25%) 12-15 g/ha — ALS doble MoA\n\n"
        "✅ Terbutrina 50% (Igran) 1,2 L/ha — PSII\n\n"
        "✅ Terbutilazina 75% (Gesatop 75) 1 kg/ha — PSII\n\n"
        "✅ Mateno Plus (Flufenacet 120 + Diflufenican 30 + Aclonifen 450 g/L) 2-2,25 L/ha — triple MoA grupos 15+12+32\n"
        "   Controla conyza Y raigrás. Requiere buena humedad al momento de aplicación.\n\n"
        "⚠️ Todos actúan sobre semillas y plántulas en germinación. No controlan conyza ya nacida.\n"
        "⚠️ Conyza tiene dos picos de emergencia — otoño y primavera. Monitorear ambos momentos."
    )

def pee_trigo_conyza_nacida():
    return (
        "TRIGO / CEBADA — CONYZA (Rama Negra) — RESCATE SOBRE MALEZA NACIDA\n\n"
        "Opciones de rescate antes de emergencia del trigo (hasta Z1.2):\n\n"
        "🥇 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Saflufenacil 70% (Heat) 35 g/ha + Starane Xtra (Fluroxipir) 0,5 L/ha\n"
        "   + aceite vegetal 0,5% v/v — triple MoA, mejor control\n\n"
        "🥈 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Starane Xtra (Fluroxipir) 0,5 L/ha\n"
        "   + Paraquat 27,6% (Gramoxone) 2 L/ha roseta chica / 2,5 L/ha roseta grande\n"
        "   + sulfato de amonio 2% v/v\n\n"
        "🥉 Paraquat 27,6% (Gramoxone) 2-2,5 L/ha + sulfato de amonio 2% v/v\n"
        "   Contacto — puede rebrotar, sin acción sistémica\n\n"
        "⚠️ Heat lleva aceite vegetal obligatorio antes de Z1.2 — SIN aceite desde Z1.2-Z1.3 del trigo\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe obligatorio. Eficacia cae significativamente con plantas grandes.\n"
        "⚠️ Conyza tiene dos picos de emergencia — otoño y primavera. Controlar en roseta chica es clave.\n\n"
        "🔁 Una vez emergido el trigo (Z2.1+) opciones POE:\n"
        "   Metsulfurón + Dicamba (Banvel), 2,4D + Dicamba,\n"
        "   Saflufenacil 70% (Heat) 25 g/ha SIN aceite + Metsulfurón,\n"
        "   Carfentrazone 40% (Shark) + MCPA, Terbutrina 50% (Igran) + MCPA"
    )

def pee_trigo_conyza_ambos():
    return (
        "TRIGO / CEBADA — CONYZA (Rama Negra) — RESIDUAL + RESCATE SOBRE NACIDA\n\n"
        "Estrategia: controlar lo nacido Y dejar residual para nuevos nacimientos.\n\n"
        "🥇 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Saflufenacil 70% (Heat) 35 g/ha\n"
        "   + Starane Xtra (Fluroxipir) 0,5 L/ha + aceite vegetal 0,5% v/v\n"
        "   + Metsulfurón 60% 8-10 g/ha o Terbutrina 50% 1,2 L/ha como residual\n\n"
        "🥈 Glifosato 1080 g ia/ha + Paraquat 27,6% 2-2,5 L/ha + sulfato de amonio 2% v/v\n"
        "   + Mateno Plus 2-2,25 L/ha como residual\n\n"
        "🥉 Paraquat 27,6% 2-2,5 L/ha + sulfato de amonio 2% v/v\n"
        "   + Metsulfurón 60% 8-10 g/ha o Terbutrina 50% 1,2 L/ha\n\n"
        "⚠️ Heat lleva aceite vegetal obligatorio antes de Z1.2 — SIN aceite desde Z1.2-Z1.3\n"
        "⚠️ Aplicar con lote sin cobertura verde activa\n"
        "⚠️ Roseta mayor a 10 cm: sumar auxínico (2,4D o Dicamba) al quemante\n"
        "⚠️ No usar Metsulfurón en barbecho previo a girasol"
    )

def pee_trigo_cruciferas_residual():
    return (
        "TRIGO / CEBADA — CRUCÍFERAS (Brassica/Nabón) — PEE RESIDUAL\n\n"
        "Opciones para evitar nacimientos de crucíferas:\n\n"
        "🥇 Flurocloridona 25% (Rainbow/Talis) 1-1,5 L/ha — PDS, mejor control de crucíferas\n"
        "   ⚠️ No superar 1,5 L/ha en trigo — dosis mayores retrasaron emergencia del cultivo\n"
        "   ⚠️ Respetar 30-40 días antes de soja siguiente\n\n"
        "🥈 Diflufenican 50% (Brodal) 250-350 cc/ha — PDS\n"
        "   Sin fitotoxicidad a ninguna dosis probada. Control algo inferior a flurocloridona.\n\n"
        "🥈 Mateno Plus (Flufenacet 120 + Diflufenican 30 + Aclonifen 450 g/L) 2-2,25 L/ha — triple MoA\n"
        "   Controla Brassica Y raigrás en una sola aplicación. Requiere buena humedad.\n\n"
        "⚠️ Todos actúan sobre semillas y plántulas en germinación. No controlan crucíferas ya nacidas."
    )

def pee_trigo_cruciferas_nacida():
    return (
        "TRIGO / CEBADA — CRUCÍFERAS (Brassica/Nabón) — RESCATE SOBRE MALEZA NACIDA\n\n"
        "Opciones de rescate antes de emergencia del trigo (hasta Z1.2):\n\n"
        "🥇 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Saflufenacil 70% (Heat) 35 g/ha\n"
        "   + Starane Xtra (Fluroxipir) 0,5 L/ha + aceite vegetal 0,5% v/v\n"
        "   Triple MoA — mejor control sobre plantas chicas\n\n"
        "🥈 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Paraquat 27,6% (Gramoxone)\n"
        "   2 L/ha planta chica / 2,5 L/ha planta grande + sulfato de amonio 2% v/v\n\n"
        "🥉 Paraquat 27,6% (Gramoxone) 2-2,5 L/ha + sulfato de amonio 2% v/v\n"
        "   Contacto — puede rebrotar, sin acción sistémica\n\n"
        "⚠️ Heat lleva aceite vegetal obligatorio antes de Z1.2 — SIN aceite desde Z1.2-Z1.3 del trigo\n"
        "⚠️ Crucíferas son sensibles a auxínicos — plantas chicas responden bien\n\n"
        "🔁 Una vez emergido el trigo (Z2.1+) opciones POE:\n"
        "   2,4D, MCPA, Dicamba (Banvel), Bromoxinil (Bromotril),\n"
        "   Flurocloridona 25% + Bromoxinil, Diflufenican + Bromoxinil"
    )

def pee_trigo_cruciferas_ambos():
    return (
        "TRIGO / CEBADA — CRUCÍFERAS (Brassica/Nabón) — RESIDUAL + RESCATE SOBRE NACIDA\n\n"
        "Estrategia: controlar lo nacido Y dejar residual para nuevos nacimientos.\n\n"
        "🥇 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Saflufenacil 70% (Heat) 35 g/ha\n"
        "   + Starane Xtra (Fluroxipir) 0,5 L/ha + aceite vegetal 0,5% v/v\n"
        "   + Flurocloridona 25% (Rainbow) 1-1,5 L/ha o Mateno Plus 2-2,25 L/ha como residual\n\n"
        "🥈 Glifosato 1080 g ia/ha + Paraquat 27,6% 2-2,5 L/ha + sulfato de amonio 2% v/v\n"
        "   + Diflufenican 50% (Brodal) 250-350 cc/ha como residual\n\n"
        "🥉 Paraquat 27,6% 2-2,5 L/ha + sulfato de amonio 2% v/v\n"
        "   + Flurocloridona 25% (Rainbow) 1-1,5 L/ha\n\n"
        "⚠️ Heat lleva aceite vegetal obligatorio antes de Z1.2 — SIN aceite desde Z1.2-Z1.3\n"
        "⚠️ No superar 1,5 L/ha de flurocloridona en trigo\n"
        "⚠️ Aplicar con lote sin cobertura verde activa"
    )

def pee_soja_amaranthus_residual():
    return (
        "SOJA — AMARANTHUS SPP. (Yuyo Colorado) — PEE RESIDUAL\n\n"
        "Opciones para evitar nacimientos de yuyo colorado:\n\n"
        "🥇 Sulfentrazone 50% (Authority/Capaz) 0,4-0,5 L/ha + S-metolacloro 96% (Dual Gold) 1,1-1,3 L/ha\n"
        "   VLCFA+PPO, doble espectro, estándar de la zona\n\n"
        "🥈 Flumioxazin 15%/Piroxasulfone 34,5% (Fierce RM Summit Agro) 400-500 cc/ha — 7 DAS, PPO+VLCFA\n"
        "🥈 Sulfentrazone 50% 0,4-0,5 L/ha + Metribuzin 48% (Sencorex) 0,8-1 L/ha — PPO+PSII\n\n"
        "🥉 Trifludimoxazin/Saflufenacil (Voraxor) 0,1-0,2 L/ha + S-metolacloro 96% 1,1-1,3 L/ha — 7 DAS\n\n"
        "🥉 Sulfentrazone 50% 0,4-0,5 L/ha + Clomazone 36% 1,75-2 L/ha — amplio espectro\n"
        "🥉 Sulfentrazone 50% 0,4-0,5 L/ha + Imazetapir 10% 0,8-1 L/ha — ⚠️ ALS, ver advertencia abajo\n\n"
        "⚠️ Evitar ALS solo (Imazetapir, Cloransulam) — Amaranthus con resistencia ALS confirmada en la zona\n"
        "⚠️ Todos actúan sobre semillas y plántulas en germinación. No controlan yuyo colorado ya nacido.\n\n"
        "PSI con mayor anticipación (Barbecho Corto/Presiembra — mínimo 45 DAS):\n"
        "✅ Amicarbazone 70% (Dinamic — UPL) 320-400 g/ha — Fotosistema II. Soja mín. 45 DAS. NO >50% arena"
    )

def pee_soja_amaranthus_nacida():
    return (
        "SOJA — AMARANTHUS SPP. (Yuyo Colorado) — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "⚠️ Sin hormonales en PEE (después de siembra) — fitotoxicidad en soja recién emergida.\n"
        "Opciones de rescate hasta ~5 cm de altura:\n\n"
        "🥇 Glifosato 480 g/L (1080 g ia/ha) 3 L/ha + Saflufenacil 70% (Heat) 40 g/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Carfentrazone 40% (Shark) 70-80 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Epirefenacil 5,5% (Empera) 600 cc/ha\n\n"
        "⚠️ Sobre 5 cm — eficacia cae fuerte. Doble golpe:\n"
        "   1° Glifosato + PPO (sin hormonal) // 2° Glufosinato 28% 2,5 L/ha o Paraquat 27,6% 1,5-2,5 L/ha\n"
        "⚠️ Para mayor eficacia sobre nacida combinando con 2,4D (Glifosato+2,4D+Heat/Shark) — ver Barbecho Corto/Presiembra, respetando carencia 7-15 días antes de siembra\n\n"
        "🔁 POE selectivo según biotipo (soja ya emergida):\n"
        "✅ Soja RR (resistente solo a glifosato): Fomesafén 25% (Flex) 1-1,5 L/ha, Lactofén 24% (Cobra) 0,6-0,8 L/ha, Benazolín 50% 0,6-1 L/ha\n"
        "✅ Soja Enlist (tolera glifosato + glufosinato + 2,4D Enlist): Glifosato 1080 g ia/ha + Glufosinato 28% 2-3 L/ha + 2,4D Enlist (colina) 30% e.a. 1,5-2 L/ha hasta V4-V6.\n"
        "   También Glufosinato solo o 2,4D Enlist solo hasta R2\n"
        "⚠️ Soja convencional: sin POE selectivo — todo el control debe darse antes de emergencia"
    )

def pee_soja_amaranthus_ambos():
    return (
        "SOJA — AMARANTHUS SPP. (Yuyo Colorado) — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "Estrategia: controlar lo nacido (sin hormonal en PEE) Y dejar residual para nuevos nacimientos.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 40 g/ha\n"
        "   + Sulfentrazone 50% (Authority/Capaz) 0,4-0,5 L/ha + S-metolacloro 96% (Dual Gold) 1,1-1,3 L/ha\n\n"
        "🥈 Glifosato 1080 g ia/ha + Carfentrazone 40% (Shark) 70-80 cc/ha\n"
        "   + Flumioxazin 15%/Piroxasulfone 34,5% (Fierce RM Summit Agro) 400-500 cc/ha\n\n"
        "⚠️ Sobre 5 cm: doble golpe antes del residual\n"
        "⚠️ Evitar ALS solo en el residual — resistencia confirmada\n"
        "⚠️ Para mayor eficacia sobre nacida con 2,4D — ver Barbecho Corto/Presiembra"
    )

def pee_soja_cruciferas_residual():
    return (
        "SOJA — CRUCÍFERAS (Brassica/Nabón) — PEE RESIDUAL\n\n"
        "Opciones para evitar nacimientos de crucíferas:\n\n"
        "🥇 Metribuzin 48% (Sencorex) 1-1,5 L/ha + S-metolacloro 96% (Dual Gold) 1,5 L/ha — 90% control a 60 DDA (Gigón, Agroconsultas). Dato de ensayo — crucíferas no figuran en marbete como maleza target\n"
        "🥈 (Fomesafén 11,9%/S-metolacloro 51,8%) (EDDUS) 2,5-3 L/ha — 87% a 60 DDA (Gigón)\n"
        "🥉 Sulfentrazone 50% (Authority/Capaz) 0,4-0,5 L/ha + S-metolacloro 96% (Dual Gold) 1,5 L/ha\n"
        "✅ Piroxasulfone 85% (Yamato) 160-200 g/ha\n"
        "✅ Sulfentrazone 50% 0,4-0,5 L/ha + Clomazone 36% 1,75-2 L/ha — amplio espectro\n"
        "✅ Sulfentrazone 50% 0,4-0,5 L/ha + Imazetapir 10% 0,8-1 L/ha\n\n"
        "⚠️ PSI (con restricción de días, antes de siembra — Barbecho Corto/Presiembra):\n"
        "   Flumioxazin 48% 0,1-0,15 L/ha — 7 DAS\n"
        "   Diflufenicán 50% 0,3 L/ha — 15 DAS\n"
        "   Flumioxazin 15%/Pyroxasulfone 34,5% (Fierce RM Summit Agro) 400-500 cc/ha — 7 DAS\n"
        "   Sulfentrazone 50%/Diflufenican 50% 0,3/0,3 L/ha — 15 DAS\n"
        "   Trifludimoxazin/Saflufenacil (Voraxor) 0,1-0,2 L/ha — 7 DAS\n"
        "   Sumyzin T Max (Terbutilazina/Flumioxazin) 1,15-1,25 L/ha — hasta 30-40 DAS\n\n"
        "⚠️ Todos actúan sobre semillas y plántulas en germinación. No controlan crucíferas ya nacidas."
    )

def pee_soja_cruciferas_nacida():
    return (
        "SOJA — CRUCÍFERAS (Brassica/Nabón) — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "⚠️ Sin hormonales en PEE (después de siembra) — fitotoxicidad en soja recién emergida.\n"
        "Opciones de rescate sin hormonal:\n\n"
        "✅ Glifosato + Saflufenacil 70% (Heat) 35-40 g/ha\n"
        "✅ Glifosato + Carfentrazone 40% (Shark) 70-80 cc/ha\n"
        "✅ Glifosato + Piraflufen 200 cc/ha\n"
        "✅ Glifosato + Epirefenacil 5,5% (Empera) 600 cc/ha\n"
        "✅ Glufosinato 28% 1-2,5 L/ha + Saflufenacil o Carfentrazone\n\n"
        "⚠️ ANTAGONISMO — Glifosato potásico (sal K) + Fomesafén en AGUA DURA (>300-400 ppm):\n"
        "   Daño en soja hasta 5% a 15 DDA. Agregar ALL OK 300 cc/ha o sulfato de amonio para mitigar.\n"
        "   En agua blanda el daño es mínimo (1,5%) y no requiere corrección. (Gigón, Agroconsultas)\n\n"
        "⚠️ Con hormonal (Glifosato/2,4D, Glifosato/MCPA, Glifosato/2,4D+Dicamba 25 DAS) — requiere carencia antes de siembra, ver Barbecho Corto/Presiembra\n"
        "⚠️ Doble golpe: Glifosato/2,4D // Paraquat 27,6% 1,5-2,5 L/ha o Glufosinato — ver Barbecho Corto/Presiembra\n\n"
        "🔁 POE selectivo según biotipo (soja ya emergida):\n"
        "✅ Soja RR/no-OGM: Fomesafén 25% 1-1,5 L/ha, Aciflurfén 24% 1-1,5 L/ha, Lactofén 24% 0,6-0,8 L/ha,\n"
        "   Fomesafén + Benazolín 50% 0,6 L/ha, Bentazón 60% 1,5 L/ha\n"
        "✅ Soja Enlist: Glufosinato 28% 2-3 L/ha hasta V4-V6, 2,4D Enlist (colina) 30% e.a. 1,5-2 L/ha hasta R2\n"
        "⚠️ Soja convencional: sin POE selectivo — todo el control debe darse antes de emergencia"
    )

def pee_soja_cruciferas_ambos():
    return (
        "SOJA — CRUCÍFERAS (Brassica/Nabón) — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "Estrategia: controlar lo nacido (sin hormonal en PEE) Y dejar residual para nuevos nacimientos.\n\n"
        "🥇 Glifosato + Saflufenacil 70% (Heat) 35-40 g/ha\n"
        "   + Metribuzin 48% (Sencorex) 1-1,5 L/ha + S-metolacloro 96% (Dual Gold) 1,5 L/ha\n\n"
        "🥈 Glifosato + Saflufenacil 70% (Heat) 35-40 g/ha\n"
        "   + (Fomesafén 11,9%/S-metolacloro 51,8%) (EDDUS) 2,5-3 L/ha\n\n"
        "🥉 Glifosato + Carfentrazone 40% (Shark) 70-80 cc/ha\n"
        "   + Sulfentrazone 50% (Authority/Capaz) 0,4-0,5 L/ha\n\n"
        "⚠️ Glifosato potásico + Fomesafén en agua dura (>300-400 ppm): agregar ALL OK 300 cc/ha\n"
    )

def pee_soja_commelina_general():
    return (
        "SOJA — COMMELINA ERECTA (Flor de Santa Lucía) — PEE\n\n"
        "⚠️ Commelina se controla principalmente con hormonal (2,4D), que requiere carencia antes de siembra.\n"
        "En PEE (después de siembra, soja convencional/RR) no hay opciones residuales ni de rescate efectivas para esta maleza.\n\n"
        "🔁 El control real se da en Barbecho Corto/Presiembra. Opciones allí:\n"
        "   Glifosato + 2,4D + Saflufenacil 70% (Heat) 40 g/ha\n"
        "   Glifosato + 2,4D + Carfentrazone 40% (Shark) 70-80 cc/ha\n"
        "   Glifosato + 2,4D + Epirefenacil 5,5% (Empera) 600 cc/ha\n"
        "   Glifosato + 2,4D + Flumioxazin 48% (Sumisoya) 150 cc/ha\n"
        "   Glifosato + 2,4D + Imazetapir 10% (Pivot) 0,8-1 L/ha\n"
        "   Glifosato + 2,4D + Trifludimoxazin/Saflufenacil (Voraxor) 0,1-0,2 L/ha\n"
        "   Glifosato + 2,4D + Metribuzin 48% (Sencorex) 0,8-1 L/ha\n"
        "   Glifosato + 2,4D + Amicarbazone 70% (Dinamic — UPL) 320-400 g/ha — mínimo 45 DAS. NO >50% arena\n"
        "   Doble golpe: 1° Glifosato + 2,4D // 2° Paraquat 27,6% (Gramoxone) 2-3 L/ha\n\n"
        "⚠️ Soja resistente a glifosato (RR/RR2): sin opciones efectivas en POE — el control debe lograrse antes de siembra\n\n"
        "✅ EXCEPCIÓN — Soja Enlist (tolera glifosato + glufosinato + 2,4D Enlist):\n"
        "   Esta combinación SÍ puede usarse en PEE sobre soja Enlist ya emergida, hasta V4-V6:\n"
        "   Glifosato + Glufosinato 28% + 2,4D Enlist (colina) 30% e.a. 1,5-2 L/ha\n"
        "   o Glufosinato 28% 2-2,5 L/ha + 2,4D Enlist 30% e.a. 1,5-2 L/ha\n"
        "   ⚠️ Agregar sulfato de amonio 1,5-2 L/ha en mezclas con glufosinato"
    )

def pee_soja_parietaria_residual():
    return (
        "SOJA — PARIETARIA — PEE RESIDUAL\n\n"
        "✅ Metribuzin 48% (Sencorex) 0,8-1 L/ha\n"
        "✅ Prometrina 48% (Gesagard) 1,5-2 L/ha\n"
        "✅ Trifludimoxazin/Saflufenacil (Voraxor) 0,1-0,2 L/ha — 7 DAS, ver Barbecho Corto/Presiembra\n"
        "⚠️ Atrazina 90% 0,5 kg/ha — hasta 30 DAS. Verificar registro/rotación en tu zona,\n"
        "   uso reportado en fuente 2025 pero con antecedentes de restricción en soja\n\n"
        "⚠️ Parietaria tiene control limitado en general — ningún producto da control total"
    )

def pee_soja_parietaria_nacida():
    return (
        "SOJA — PARIETARIA — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "✅ Paraquat 27,6% (Gramoxone) 1,5-2,5 L/ha + Metribuzin 48% (Sencorex) 0,8-1 L/ha\n"
        "✅ Paraquat 27,6% 1,5-2,5 L/ha + Prometrina 48% (Gesagard) 1,5-2 L/ha\n"
        "✅ Paraquat 27,6% 1,5-2,5 L/ha + Trifludimoxazin/Saflufenacil (Voraxor) 0,1-0,2 L/ha — 7 DAS\n"
        "✅ Glifosato 1260 g.e.a./ha + Epirefenacil 5,5% (Empera) 600 cc/ha\n\n"
        "⚠️ Rescate parcial sobre cultivo emergido (sin opciones POE efectivas):\n"
        "   Glifosato >1360 g.e.a./ha + sulfato de amonio + aceite → controles de hasta 60% solamente\n"
        "⚠️ Paraquat siempre + sulfato de amonio 2% v/v para mejorar cobertura"
    )

def pee_soja_parietaria_ambos():
    return (
        "SOJA — PARIETARIA — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "✅ Paraquat 27,6% (Gramoxone) 1,5-2,5 L/ha + Atrazina 90% 0,5 kg/ha — hasta 30 DAS\n"
        "   (residual + rescate en una pasada)\n"
        "✅ Paraquat 27,6% 1,5-2,5 L/ha + Flumioxazin 48% (Sumisoya) 0,1-0,15 L/ha — 7 DAS\n\n"
        "⚠️ Estas combinaciones cumplen ambos roles: Paraquat ataca lo nacido, el acompañante deja residual\n"
        "⚠️ Atrazina: verificar registro/rotación en tu zona\n"
        "⚠️ Parietaria sigue siendo de control parcial — monitorear y repetir si reaparece"
    )

def pee_soja_cebollin_residual():
    return (
        "SOJA — CEBOLLÍN (Cyperus rotundus) — PEE\n\n"
        "✅ Imazapic 240 g/L (Pivot) 1 L/ha — hasta 4ª hoja del cebollín, control parcial + algo de residualidad\n"
        "⚠️ Carencia 90 días — verificar tolerancia de la variedad de soja y restricción para el cultivo siguiente en la rotación\n\n"
        "🔁 La opción realmente eficaz es Halosulfurón (Sempra) — pero requiere mínimo 10 DAS, ver Barbecho Corto/Presiembra:\n"
        "   Halosulfurón metil 75% (Sempra) 100-150 g/ha solo, o 30-50 g/ha + Glifosato 48% 2,5 L/ha\n\n"
        "⚠️ Coadyuvante: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral."
    )

def pee_soja_cebollin_nacida():
    return (
        "SOJA — CEBOLLÍN (Cyperus rotundus) — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "✅ Glifosato ≥2000 g.e.a./ha solo — sobre cebollín en activo crecimiento (6-8 hojas), control parcial\n"
        "✅ Imazapic 240 g/L (Pivot) 1 L/ha — hasta 4ª hoja, control parcial\n\n"
        "⚠️ Ninguna opción PEE da control completo sobre cebollín nacido.\n"
        "   Para mejor resultado, ver Barbecho Corto/Presiembra con Sempra (mínimo 10 DAS, cebollín ~15cm)\n"
        "⚠️ Carencia Pivot 90 días si se usa\n"
        "⚠️ Coadyuvante: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral."
    )

def pee_soja_conyza_residual():
    return (
        "SOJA — CONYZA (Rama Negra) — PEE RESIDUAL\n\n"
        "✅ (Imazetapir/Saflufenacil) 0,140 kg/ha — Optill\n"
        "✅ (Metribuzín/S-metolacloro) 2-2,5 L/ha — Boundary\n"
        "✅ (Metribuzín/Sulfentrazone) 1-1,4 kg/ha — Capaz MTZ\n"
        "✅ (Metribuzín/Pendimetalín) 3,5 L/ha — Tripzin\n"
        "✅ (Sulfentrazone/S-metolacloro) 1,8-2,5 L/ha — Capaz Elite\n\n"
        "⚠️ Regiones con biotipos resistentes a EPSPS y ALS — verificar antes de elegir\n"
        "⚠️ Todos actúan sobre semillas y plántulas en germinación. No controlan conyza ya nacida.\n\n"
        "PSI con mayor anticipación (Barbecho Corto/Presiembra — mínimo 45 DAS):\n"
        "✅ Amicarbazone 70% (Dinamic — UPL) 320-400 g/ha — Fotosistema II. POE temprano Conyza hasta 4 hojas. NO >50% arena\n\n"
        "🔁 PSI inmediato (con DAS, antes de siembra):\n"
        "   Metsulfurón, Clorimurón, Diclosulam (Spider), Texaro, Fierce RM, Zidua, Alana, Pledge, entre otros"
    )

def pee_soja_conyza_nacida():
    return (
        "SOJA — CONYZA (Rama Negra) — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "🥇 Glifosato 1080 g ia/ha + Texaro (Diclosulam/Halauxifen) 43 g/ha + aceite metilado (Uptake Plus) 0,5% v/v\n"
        "   Dato de campo: buen desempeño en PEE sobre conyza nacida\n\n"
        "🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Starane Xtra (Fluroxipir) 0,5 L/ha\n"
        "   + aceite vegetal 0,5% v/v\n\n"
        "🥉 Glifosato 1080 g ia/ha + Paraquat 27,6% 2-2,5 L/ha + sulfato de amonio 2% v/v\n\n"
        "⚠️ Heat lleva aceite vegetal obligatorio\n"
        "⚠️ Texaro: marbete posiciona como presiembra/7DAS — dato de campo indica buen desempeño también en PEE\n"
        "⚠️ Regiones con biotipos resistentes a EPSPS y ALS — verificar antes de elegir\n\n"
        "🔁 POE posterior si reescapa: Clorimurón (Classic) 40g, Diclosulam (Spider) 15-20g, Cloransulam (Pacto) 30-50g\n"
        "✅ Soja Enlist: 2,4D Enlist 1,5-2 L/ha o Glufosinato 1,8-2 L/ha hasta R2"
    )

def pee_soja_conyza_ambos():
    return (
        "SOJA — CONYZA (Rama Negra) — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "🥇 Glifosato 1080 g ia/ha + Texaro (Diclosulam/Halauxifen) 43 g/ha + aceite metilado (Uptake Plus) 0,5% v/v\n"
        "   + (Imazetapir/Saflufenacil) 0,140 kg/ha (Optill) o (Metribuzín/S-metolacloro) 2-2,5 L/ha (Boundary) como residual\n\n"
        "🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Starane Xtra 0,5 L/ha + aceite vegetal 0,5% v/v\n"
        "   + (Sulfentrazone/S-metolacloro) 1,8-2,5 L/ha (Capaz Elite) como residual\n\n"
        "⚠️ Regiones con biotipos resistentes a EPSPS y ALS — verificar antes de elegir"
    )

def pee_maiz_raigras_residual():
    return (
        "MAÍZ — RAIGRÁS — PEE RESIDUAL\n\n"
        "✅ Piroxasulfone 85% (Yamato) — gramíneas\n"
        "✅ Pendimetalín (Herbadox) — gramíneas\n"
        "✅ S-metolacloro 96% (Dual Gold) — VLCFA, gramíneas anuales de semilla\n\n"
        "⚠️ Residual moderado. El control principal de raigrás en maíz se logra ANTES de siembra\n"
        "   con graminicidas ACCasa — ver Barbecho Corto/Presiembra:\n"
        "   Glifosato + Cletodim 24% (Select) 0,7-1 L/ha, mínimo 10 DAS (cuanto más, mejor)"
    )

def pee_maiz_raigras_nacida():
    return (
        "MAÍZ — RAIGRÁS — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "🚨 ADVERTENCIA CRÍTICA: Cletodim y todos los ACCasa (FOPs/DIMs) son FITOTÓXICOS\n"
        "   en maíz convencional y RR — NUNCA aplicar en PEE/POE de estos biotipos.\n\n"
        "⚠️ Maíz convencional/RR: sin opciones selectivas de rescate sobre raigrás nacido en PEE.\n"
        "   El control principal debió lograrse antes de siembra (Barbecho Corto/Presiembra con ACCasa, mínimo 10 DAS).\n\n"
        "🔁 Rescate escaso y parcial — solo si el maíz aún no emergió:\n"
        "✅ Paraquat 27,6% (Gramoxone) 2 L/ha + sulfato de amonio 2% v/v — quema de contacto sobre raigrás chico\n"
        "⚠️ Aplicar antes de la emergencia del maíz. Control parcial, puede rebrotar.\n\n"
        "✅ Maíz Enlist (única excepción real): Haloxyfop 54% (Galant Max) o Glufosinato 28% 1,8-2 L/ha\n"
        "   hasta V6 — el maíz Enlist tolera ACCasa"
    )

def pee_maiz_raigras_ambos():
    return (
        "MAÍZ — RAIGRÁS — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "🚨 ADVERTENCIA CRÍTICA: Cletodim y todos los ACCasa son FITOTÓXICOS en maíz convencional y RR.\n\n"
        "⚠️ Maíz convencional/RR: si hay raigrás nacido al momento de PEE, no hay combinación\n"
        "   residual+rescate selectiva posible. La estrategia debió aplicarse en Barbecho Corto/Presiembra.\n\n"
        "🔁 Rescate parcial (solo si el maíz aún no emergió) + residual:\n"
        "✅ Paraquat 27,6% (Gramoxone) 2 L/ha + sulfato de amonio 2% v/v\n"
        "   + Piroxasulfone 85% (Yamato) o Pendimetalín (Herbadox) como residual\n\n"
        "✅ Maíz Enlist: Haloxyfop 54% (Galant Max) o Glufosinato 28% 1,8-2 L/ha hasta V6 (rescate)\n"
        "   + Piroxasulfone (Yamato) o Pendimetalín (Herbadox) como residual"
    )

def pee_maiz_amaranthus_residual():
    return (
        "MAÍZ — AMARANTHUS SPP. (Yuyo Colorado) — PEE RESIDUAL\n\n"
        "PRODUCTOS SOLOS:\n"
        "✅ Atrazina 90% 1,8-2,2 kg/ha (Gesaprim) — FII\n"
        "✅ Terbutilazina 75% 1,3-1,5 kg/ha (Terbine) — FII\n"
        "✅ Amicarbazone 70% (Dinamic) 0,4-0,7 kg/ha — FII. También con acción POE temprana sobre nacida\n"
        "✅ S-metolacloro 96% 0,8-1,6 L/ha (Dual Gold) — VLCFA\n"
        "✅ Acetoclor 90% 2-3 L/ha (Harness) — VLCFA\n"
        "✅ Pendimetalín 45,6% 2,1-3,6 L/ha (Satellite) — microtúbulos\n"
        "✅ Linurón 50% (Linurón 50 FW) 2-3 L/ha — FII\n\n"
        "MEZCLAS PRINCIPALES:\n"
        "🥇 Acuron Pack: Biciclopirona (Acuron Uno) 800-1000 ml/ha + S-metolacloro (Dual Gold) 850-1000 ml/ha\n"
        "   según textura — HPPD+VLCFA, controla yuyo colorado\n"
        "🥇 Adengo (Thiencarbazone+Isoxaflutol) 300-400 cc/ha + Atrazina — ALS+HPPD\n"
        "🥇 Zidua Pack: Saflufenacil 70% (Heat) 45 g/ha + Piroxasulfone 85% 200 g/ha + aceite — PPO+VLCFA\n"
        "✅ Bicep Pack Gold: Atrazina + S-metolacloro\n"
        "✅ Amicarbazone 70% (Dinamic) + S-metolacloro 0,8-1,6 L/ha — FII+VLCFA\n\n"
        "⚠️ Biciclopirona: máximo una aplicación por campaña (Acuron Pack o Acuron Uno solo)\n"
        "⚠️ Zidua Pack: aplicar antes de emergencia del maíz. Si el maíz está cerca de emerger o ya\n"
        "   emergido, usar Adengo 280 cc/ha en su lugar — riesgo de fitotoxicidad por contacto de Heat\n"
        "⚠️ Todos requieren aplicación antes de emergencia de malezas — sin efecto sobre yuyo colorado ya nacido"
    )

def pee_maiz_amaranthus_nacida():
    return (
        "MAÍZ — AMARANTHUS SPP. (Yuyo Colorado) — RESCATE SOBRE MALEZA NACIDA\n\n"
        "🔁 El control sobre nacida se da en POE selectivo del cultivo (V1-V8 según producto):\n\n"
        "🥇 Mesotrione 48% (Callisto) — V2-V6, sobre maleza <5cm\n"
        "🥇 Topramezone 33,6% (Convey) — V1-V7\n"
        "✅ Tembotrione 42% (Laudis) — V3-V6\n"
        "✅ Tolpyralate 40% (Brucia) — V3-V6\n"
        "✅ Metribuzín 70% (Tribune 70 WG) 210-270 g/ha — FII, V2-V8, maleza cotiledón\n"
        "✅ Bentazón 60% 1,2-1,6 L/ha — FII, V2-V8\n"
        "✅ Combinaciones con Atrazina + 2,4D / Picloram / Mesotrione / Topramezone / Tolpyralate / Tembotrione\n"
        "   — HPPD+FII potencian control\n\n"
        "✅ Maíz Enlist: Glufosinato 28% 2-3 L/ha hasta V2-V4, 2,4D 1,5-2 L/ha hasta V8\n\n"
        "⚠️ Maleza <5cm — eficacia cae con plantas grandes\n"
        "⚠️ Evitar aplicación en estrés hídrico/térmico"
    )

def pee_maiz_amaranthus_ambos():
    return (
        "MAÍZ — AMARANTHUS SPP. (Yuyo Colorado) — RESIDUAL + RESCATE SOBRE NACIDA\n\n"
        "🥇 Acuron Pack (residual PEE) — si después escapa algo, completar con Mesotrione (Callisto)\n"
        "   o Topramezone (Convey) en POE V2-V6\n\n"
        "🥇 Adengo + Atrazina (residual PEE) — mismo seguimiento POE si reescapa\n\n"
        "🥇 Zidua Pack (residual PEE, antes de emergencia del maíz) — seguimiento POE igual\n\n"
        "⚠️ Biciclopirona: solo una vez por campaña — si se usó en PEE (Acuron Pack), no repetir\n"
        "   HPPD residual en POE; Mesotrione/Topramezone como rescate POE son compatibles\n"
        "⚠️ Zidua Pack: si el maíz está cerca de emerger o ya emergido, usar Adengo en su lugar"
    )

def pee_maiz_cebollin_general():
    return (
        "MAÍZ — CEBOLLÍN (Cyperus rotundus) — PEE\n\n"
        "⚠️ Cebollín no tiene opciones residuales en PEE de maíz. El control se da en POE selectivo según biotipo:\n\n"
        "✅ Maíz convencional:\n"
        "   Halosulfurón metil 75% (Sempra) 100-150 g/ha — sin restricción de estadio, aplicar con cebollín ~15cm\n"
        "   ⚠️ Coadyuvante obligatorio: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral.\n\n"
        "✅ Maíz RR/RG:\n"
        "   Halosulfurón metil 75% (Sempra) 30-50 g/ha + Glifosato 48% 2,5 L/ha\n"
        "   o Glifosato 48% 3 L/ha + Clorimurón 25% (Classic) 60-80 g/ha\n\n"
        "✅ Maíz CL (Clearfield):\n"
        "   Imazapic 240 g/L (Pivot) 1 L/ha — hasta 4ª hoja del cebollín\n"
        "   o Halosulfurón metil 75% (Sempra) 100-150 g/ha — ambas opciones válidas\n"
        "   ⚠️ Pivot FITOTÓXICO en maíz convencional — exclusivo Clearfield\n"
        "   ⚠️ Coadyuvante obligatorio: surfactante no iónico. NO aceite mineral."
    )

def pee_girasol_general_residual():
    return (
        "GIRASOL — MALEZA GENERAL — PEE RESIDUAL\n\n"
        "Productos solos:\n"
        "✅ Sulfentrazone 50% (Authority/Capaz) 300-400 cc/ha\n"
        "✅ Prometrina 50% (Gesagard) 1-2 L/ha\n"
        "✅ S-metolacloro 96% (Dual Gold) 0,8-1 L/ha\n"
        "✅ Acetoclor 90% (Harness) 2-3 L/ha\n"
        "✅ Trifluralina 60% (Adama Essentials) 1-2 L/ha\n"
        "✅ Diflufenicán 50% (Brodal) 0,3 L/ha\n"
        "✅ Flurocloridona 25% (Rainbow) 1,5-4 L/ha\n"
        "✅ Piroxasulfone 85% (Yamato) 160 g/ha — validado a campo\n"
        "✅ Pendimetalín 45,5% (Herbadox H2O/Satellite) 2-3,5 L/ha — microtúbulos, gramíneas\n"
        "✅ Oxifluorfén 24% (Galigan) 0,25-0,3 L/ha — PPO, contacto, latifoliadas nacidas chicas\n\n"
        "Mezclas principales:\n"
        "✅ (Sulfentrazone/S-metolacloro) 0,4/1 L/ha\n"
        "✅ (Sulfentrazone/Acetoclor) 0,4/2 L/ha\n"
        "✅ (Sulfentrazone/Diflufenicán) 0,3/0,3 L/ha\n"
        "✅ (Flurocloridona/S-metolacloro) 3/1 L/ha\n"
        "✅ (Flurocloridona/Acetoclor) 3/2 L/ha\n"
        "✅ (Diflufenicán/S-metolacloro) 0,3/1 L/ha\n"
        "✅ (Diflufenicán/Acetoclor) 0,3/2 L/ha\n"
        "✅ (Diflufenicán/Prometrina) 0,3/2 L/ha\n"
        "✅ (Flurocloridona/Sulfentrazone/S-metolacloro) 0,8/0,3/1 L/ha\n"
        "✅ (Prometrina/Sulfentrazone/S-metolacloro) 1,5/0,3/1 L/ha\n\n"
        "⚠️ PSI (con DAS) — ver Barbecho Corto/Presiembra: Flumioxazin 48% (Sumisoya) 50-100 cc/ha — 20-30 DAS\n\n"
        "🚫 NO usar en girasol: saflufenacil (Heat), fomesafén, biciclopirona, topramezone, diclosulam, sulfonilureas\n\n"
        "✅ Solo Girasoles Clearfield: Imazapir 80% (Clearsol DF) 100 g/ha"
    )

def pee_girasol_general_nacida():
    return (
        "GIRASOL — MALEZA GENERAL — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "⚠️ En PEE de girasol no hay rescate eficiente sobre latifoliadas nacidas.\n"
        "El control sobre nacida se da en POE muy limitado:\n\n"
        "✅ Aclonifén 60% (Prodigio) 1-1,5 L/ha + Aceite — latifoliadas SOLO menor a 2 cm. Ventana muy estrecha.\n"
        "   ⚠️ NO mezclar Prodigio con graminicidas\n"
        "✅ Benazolín 50% (Dasen) 0,3 L/ha — latifoliadas\n"
        "✅ ACCasa (gramíneas): Haloxyfop (Galant Max), Propaquizafop (Agil), Cletodim (Select)\n\n"
        "✅ Girasoles CL: Clearsol DF (Imazapir) 100 g/ha + Aceite (DASH) 200 cc/ha V2-V4\n"
        "   + Graminicida si hace falta\n\n"
        "⚠️ Para latifoliadas nacidas antes de siembra — ver Barbecho Corto/Presiembra:\n"
        "   Glifosato + 2,4D (20 DAS), Dicamba (30 DAS), Fluroxipir/Halauxifén (Pixxaro) 400-500 cc/ha (1 DAS)"
    )

def pee_girasol_general_ambos():
    return (
        "GIRASOL — MALEZA GENERAL — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "✅ Cualquiera de las opciones residuales (ver celda Residual) en PEE\n"
        "🔁 + seguimiento POE según maleza y biotipo:\n"
        "   Aclonifén (Prodigio) 1-1,5 L/ha sobre latifoliadas <2 cm\n"
        "   Benazolín 50% (Dasen) 0,3 L/ha\n"
        "   ACCasa sobre gramíneas (Galant Max, Agil, Select)\n"
        "   Girasoles CL: Clearsol DF + Graminicida si hace falta\n\n"
        "⚠️ Girasol convencional tiene POE muy limitado para latifoliadas — el control preventivo en PEE es crítico\n"
        "🚫 NO usar en girasol: saflufenacil, fomesafén, biciclopirona, topramezone, diclosulam, sulfonilureas"
    )

def pee_girasol_cruciferas_residual():
    return (
        "GIRASOL — CRUCÍFERAS (Brassica/Nabón) — PEE RESIDUAL\n\n"
        "🥇 Flurocloridona 25% (Rainbow) 1,5-4 L/ha + Diflufenicán 50% (Brodal) 0,3 L/ha\n"
        "   Combinación recomendada, especialmente ante sospecha de resistencia\n\n"
        "✅ Flurocloridona 25% (Rainbow) 1,5-4 L/ha sola\n"
        "✅ Diflufenicán 50% (Brodal) 0,3 L/ha solo\n\n"
        "🚫 NO usar en girasol: saflufenacil, metsulfurón, fomesafén, biciclopirona"
    )

def pee_girasol_cruciferas_nacida():
    return (
        "GIRASOL — CRUCÍFERAS (Brassica/Nabón) — RESCATE SOBRE MALEZA NACIDA (PEE)\n\n"
        "⚠️ Opciones limitadas — no ideales pero con algo de actividad sobre crucíferas chicas:\n\n"
        "✅ Carfentrazone 40% (Shark) 50-75 cc/ha — PPO, contacto\n"
        "✅ Fluroxipir (Starane Xtra) — auxínico, actividad en plantas chicas\n\n"
        "⚠️ Control parcial — no esperar resultado completo sobre plantas establecidas\n"
        "⚠️ Aplicar con crucíferas en roseta chica para mejor respuesta\n\n"
        "✅ Girasoles CL: Imazapir 80% (Clearsol DF) V2-V4 / (Imazapir+Imazamox) (Clearsol Plus II) V2-V4\n"
        "   — mejor opción disponible en CL\n\n"
        "🔁 Para crucíferas nacidas antes de siembra — ver Barbecho Corto/Presiembra:\n"
        "   Glifosato + 2,4D (20 DAS mínimo), Glifosato + Dicamba (45 DAS mínimo)"
    )

def pee_girasol_cruciferas_ambos():
    return (
        "GIRASOL — CRUCÍFERAS (Brassica/Nabón) — RESIDUAL + RESCATE SOBRE NACIDA (PEE)\n\n"
        "🥇 Flurocloridona 25% (Rainbow) + Diflufenicán 50% (Brodal) como residual\n"
        "   + Carfentrazone 40% (Shark) 50-75 cc/ha o Fluroxipir (Starane Xtra) sobre nacida\n\n"
        "⚠️ Control sobre nacida es parcial — priorizar el residual en PEE\n"
        "⚠️ Girasol convencional/no-CL: si hay crucíferas establecidas, el control debió lograrse en Barbecho Corto/Presiembra\n\n"
        "✅ Girasoles CL: Flurocloridona+Diflufenicán (residual PEE) — seguimiento POE con Clearsol si reescapa\n\n"
        "🚫 NO usar en girasol: saflufenacil, metsulfurón, fomesafén, biciclopirona"
    )

def pee_maiz_cruciferas_residual():
    return (
        "MAÍZ — CRUCÍFERAS (Brassica/Nabón) — PEE RESIDUAL\n\n"
        "✅ Atrazina 90% (Gesaprim) — FII\n"
        "✅ Terbutilazina 75% (Terbine) — FII\n"
        "✅ Metribuzin 48% (Sencorex) 0,5-0,8 L/ha — FII. Buena acción sobre crucíferas pequeñas\n"
        "✅ Amicarbazone 70% (Dinamic) 0,4-0,7 kg/ha — FII. También con acción POE temprana\n"
        "✅ Flurocloridona 25% (Rainbow) — PDS\n"
        "✅ Diflufenicán 50% (Brodal) 0,2-0,3 L/ha — PDS, 15 DAS\n"
        "✅ Piroxasulfone 85% (Yamato) — VLCFA\n"
        "✅ Biciclopirona (Acuron Uno) — HPPD. Máximo 1 aplicación por campaña\n"
        "✅ Linurón 50% (Linurón 50 FW) 2-3 L/ha — FII\n\n"
        "⚠️ Adengo (Thiencarbazone/Isoxaflutol): control inicial aceptable (~83% a 12 DDA) pero caída marcada a 50 DDA (~55%). No recomendado como opción principal para crucíferas — pérdida de residualidad. (Gigón, Agroconsultas)\n"
        "⚠️ Flumioxazin 48% (Sumisoya): PSI — 7-10 DAS antes de siembra, ver Barbecho Corto/Presiembra"
    )

def pee_maiz_cruciferas_nacida():
    return (
        "MAÍZ — CRUCÍFERAS (Brassica/Nabón) — RESCATE SOBRE MALEZA NACIDA (POE)\n\n"
        "🥇 Mesotrione 48% (Callisto) + Atrazina 90% 1 kg/ha — V2-V6, excelente sobre crucíferas pequeñas\n"
        "🥇 Topramezone 33,6% (Convey) + Atrazina 1 kg/ha — V1-V7\n"
        "✅ Tembotrione 42% (Laudis) + Atrazina 1 kg/ha — V3-V6\n"
        "✅ Tolpyralate 40% (Brucia) + Atrazina 1 kg/ha — V3-V6\n"
        "✅ MCPA 28% 1,5 L/ha + Atrazina 90% 1 kg/ha — base clásica\n"
        "✅ Tordon (Picloram) 27,7% 150 cc/ha — maíces RR, POE V2-V8\n\n"
        "✅ Maíz Enlist: Glufosinato 28% 1,8-2 L/ha V1-V8 o 2,4D Enlist (sal colina) hasta V8,\n"
        "   o combinación Glufosinato + 2,4D Enlist\n\n"
        "⚠️ HPPD siempre con Atrazina o Terbutilazina para sinergizar\n"
        "⚠️ Adengo + Atrazina: control inicial ~83% a 12 DDA pero cae a ~55% a 50 DDA — no recomendado como primera opción en crucíferas. (Gigón, Agroconsultas)"
    )

def pee_maiz_cruciferas_ambos():
    return (
        "MAÍZ — CRUCÍFERAS (Brassica/Nabón) — RESIDUAL + RESCATE SOBRE NACIDA\n\n"
        "🥇 Atrazina o Terbutilazina o Flurocloridona o Diflufenicán como residual en PEE\n"
        "🔁 + Mesotrione/Topramezone + Atrazina en POE V2-V6 si reescapa\n\n"
        "✅ Maíz Enlist: residual PEE + Glufosinato 28% o 2,4D Enlist en POE si reescapa\n\n"
        "⚠️ HPPD siempre con Atrazina o Terbutilazina para sinergizar"
    )

def pee_girasol_cebollin_general():
    return (
        "GIRASOL — CEBOLLÍN (Cyperus rotundus) — PEE\n\n"
        "PEE (reduce emergencia — NO elimina tubérculos):\n"
        "✅ S-metolacloro 96% (Dual Gold)\n"
        "✅ Acetoclor 90% (Harness)\n\n"
        "🔁 POE según biotipo:\n\n"
        "✅ Girasoles CL Plus: Clearsol II Plus Pack (Imazamox 70% + Imazapir 80%)\n"
        "   Entre 3a y 7a hoja del cebollín\n"
        "   ⚠️ SOLO en híbridos Clearfield PLUS — daña girasoles CL no Plus o convencionales\n"
        "   ⚠️ No aplicar con estrés hídrico/térmico. No usar organofosforados en mezcla.\n\n"
        "✅ Girasoles CL (no Plus): Clearsol DF (Imazapir solo) V2-V4 — menor espectro\n\n"
        "⚠️ Girasoles convencionales: sin opciones POE — el control es en barbecho\n"
        "   (Glifosato ≥2000 g.e.a./ha) y PEE únicamente"
    )

def pee_sorgo_residual():
    return (
        "SORGO — PEE RESIDUAL\n\n"
        "✅ Atrazina 90% 1-2 kg/ha (Gesaprim) — FII\n"
        "✅ Terbutilazina 75% 1 kg/ha (Terbine) — FII\n"
        "✅ Pendimetalín 33% 2,5-4,5 L/ha (Herbadox) — microtúbulos\n"
        "✅ S-metolacloro 96% 0,9-1,3 L/ha (Dual Gold) — VLCFA\n"
        "   ⚠️ OBLIGATORIO semilla curada con Fluxofenim 96% (Concep III) — sin Concep III causa fitotoxicidad severa\n"
        "✅ Atrazina 90% 1-2 kg/ha + S-metolacloro 96% 0,9-1,3 L/ha — FII+VLCFA ⚠️ Concep III obligatorio\n"
        "✅ Terbutilazina 75% 1 kg/ha + S-metolacloro 96% 0,9-1,3 L/ha ⚠️ Concep III obligatorio\n"
        "✅ (Imazapic/Imazapir) 0,2-0,3 L/ha — solo Sorgos tolerantes a imidazolinonas\n"
        "✅ Atrazina 90% + (Imazapic/Imazapir) 0,2-0,3 L/ha — solo Sorgos tolerantes a imidazolinonas\n\n"
        "⚠️ PSI (con DAS): Flumioxazin 48% (Sumisoya) 0,15 L/ha — 20-30 DAS, ver Barbecho Corto/Presiembra"
    )

def pee_sorgo_nacida():
    return (
        "SORGO — RESCATE SOBRE MALEZA NACIDA (POE)\n\n"
        "Latifoliadas:\n"
        "✅ Bromoxinil 34,6% 0,8-1 L/ha — V2-V4\n"
        "✅ Atrazina 90% 1-2 kg/ha — V2-V4\n"
        "✅ Bentazon 60% 1,2-1,6 L/ha — V2-V8\n"
        "✅ 2,4D / MCPA — V4-V8\n"
        "✅ Picloram / Clopyralid — V4-V8, aplicación dirigida con caño de bajada\n"
        "✅ Atrazina 90% + Hormonal — mezcla V4-V8\n"
        "✅ Pendimetalín 33% 2,5-4,5 L/ha — V3-V4, maleza no emergida\n"
        "✅ (Imazapic/Imazapir) 0,2-0,3 L/ha — solo Sorgos tolerantes a imidazolinonas\n\n"
        "Gramíneas:\n"
        "✅ Cletodim 24% 0,7-1 L/ha o 36% 0,5-0,7 L/ha — 20 DAS, solo gramíneas\n"
        "✅ Haloxyfop 54% 0,25-0,35 L/ha — 20 DAS, solo gramíneas\n"
        "⚠️ ACCasa FITOTÓXICO en sorgo convencional — verificar biotipo antes de aplicar"
    )

def pee_sorgo_ambos():
    return (
        "SORGO — RESIDUAL + RESCATE SOBRE NACIDA\n\n"
        "🥇 Atrazina 90% + S-metolacloro 96% (residual PEE ⚠️ Concep III obligatorio)\n"
        "   + Bromoxinil o Bentazon en POE si reescapa latifoliada\n\n"
        "🥇 Terbutilazina 75% + S-metolacloro 96% (residual PEE ⚠️ Concep III obligatorio)\n"
        "   + 2,4D/MCPA en POE V4-V8 si reescapa\n\n"
        "✅ Pendimetalín (residual PEE) + Cletodim/Haloxyfop en POE si hay gramíneas (20 DAS)\n\n"
        "⚠️ S-metolacloro: SIEMPRE con semilla curada Concep III — sin esto, fitotoxicidad severa\n"
        "⚠️ ACCasa: FITOTÓXICO en sorgo convencional"
    )

async def responder_pee_guiado(query_or_message, context, cultivo, maleza, objetivo, es_callback=True):
    """Dispatcher de respuestas PEE guiadas."""
    respuesta = None

    if cultivo == "trigo":
        if maleza == "raigras":
            if objetivo == "residual":
                respuesta = pee_trigo_raigras_residual()
            elif objetivo == "nacida":
                respuesta = pee_trigo_raigras_nacida()
            elif objetivo == "ambos":
                respuesta = pee_trigo_raigras_ambos()
        elif maleza == "conyza":
            if objetivo == "residual":
                respuesta = pee_trigo_conyza_residual()
            elif objetivo == "nacida":
                respuesta = pee_trigo_conyza_nacida()
            elif objetivo == "ambos":
                respuesta = pee_trigo_conyza_ambos()
        elif maleza == "cruciferas":
            if objetivo == "residual":
                respuesta = pee_trigo_cruciferas_residual()
            elif objetivo == "nacida":
                respuesta = pee_trigo_cruciferas_nacida()
            elif objetivo == "ambos":
                respuesta = pee_trigo_cruciferas_ambos()
    elif cultivo == "soja":
        if maleza == "amaranthus":
            if objetivo == "residual":
                respuesta = pee_soja_amaranthus_residual()
            elif objetivo == "nacida":
                respuesta = pee_soja_amaranthus_nacida()
            elif objetivo == "ambos":
                respuesta = pee_soja_amaranthus_ambos()
        elif maleza == "cruciferas":
            if objetivo == "residual":
                respuesta = pee_soja_cruciferas_residual()
            elif objetivo == "nacida":
                respuesta = pee_soja_cruciferas_nacida()
            elif objetivo == "ambos":
                respuesta = pee_soja_cruciferas_ambos()
        elif maleza == "commelina":
            respuesta = pee_soja_commelina_general()
        elif maleza == "parietaria":
            if objetivo == "residual":
                respuesta = pee_soja_parietaria_residual()
            elif objetivo == "nacida":
                respuesta = pee_soja_parietaria_nacida()
            elif objetivo == "ambos":
                respuesta = pee_soja_parietaria_ambos()
        elif maleza == "cebollin":
            if objetivo == "nacida":
                respuesta = pee_soja_cebollin_nacida()
            else:
                respuesta = pee_soja_cebollin_residual()
        elif maleza == "conyza":
            if objetivo == "residual":
                respuesta = pee_soja_conyza_residual()
            elif objetivo == "nacida":
                respuesta = pee_soja_conyza_nacida()
            elif objetivo == "ambos":
                respuesta = pee_soja_conyza_ambos()
    elif cultivo == "maiz":
        if maleza == "raigras":
            if objetivo == "residual":
                respuesta = pee_maiz_raigras_residual()
            elif objetivo == "nacida":
                respuesta = pee_maiz_raigras_nacida()
            elif objetivo == "ambos":
                respuesta = pee_maiz_raigras_ambos()
        elif maleza == "amaranthus":
            if objetivo == "residual":
                respuesta = pee_maiz_amaranthus_residual()
            elif objetivo == "nacida":
                respuesta = pee_maiz_amaranthus_nacida()
            elif objetivo == "ambos":
                respuesta = pee_maiz_amaranthus_ambos()
        elif maleza == "cebollin":
            respuesta = pee_maiz_cebollin_general()
        elif maleza == "cruciferas":
            if objetivo == "residual":
                respuesta = pee_maiz_cruciferas_residual()
            elif objetivo == "nacida":
                respuesta = pee_maiz_cruciferas_nacida()
            elif objetivo == "ambos":
                respuesta = pee_maiz_cruciferas_ambos()
    elif cultivo == "girasol":
        if maleza == "general":
            if objetivo == "residual":
                respuesta = pee_girasol_general_residual()
            elif objetivo == "nacida":
                respuesta = pee_girasol_general_nacida()
            elif objetivo == "ambos":
                respuesta = pee_girasol_general_ambos()
        elif maleza == "cruciferas":
            if objetivo == "residual":
                respuesta = pee_girasol_cruciferas_residual()
            elif objetivo == "nacida":
                respuesta = pee_girasol_cruciferas_nacida()
            elif objetivo == "ambos":
                respuesta = pee_girasol_cruciferas_ambos()
        elif maleza == "cebollin":
            respuesta = pee_girasol_cebollin_general()
    elif cultivo == "sorgo":
        if objetivo == "residual":
            respuesta = pee_sorgo_residual()
        elif objetivo == "nacida":
            respuesta = pee_sorgo_nacida()
        elif objetivo == "ambos":
            respuesta = pee_sorgo_ambos()

    if respuesta is None:
        respuesta = "⚠️ No tengo información específica para esa combinación todavía."

    if es_callback:
        await query_or_message.message.reply_text(respuesta)
    else:
        await query_or_message.reply_text(respuesta)
    context.user_data.clear()


# --- FLUJO GUIADO POE MAÍZ ---

POE_MAIZ_KEYWORDS = [
    "poe maiz", "poe maíz", "poe en maiz", "poe en maíz",
    "post emergencia maiz", "post emergencia maíz",
    "postemergencia maiz", "postemergencia maíz",
    "post-emergencia maiz", "post-emergencia maíz",
    "postemer maiz", "postemer maíz",
]

POE_MAIZ_BIOTIPO_KEYWORDS = {
    "convencional": "convencional", "conv": "convencional",
    "rr": "rr", "roundup ready": "rr",
    "cl": "cl", "clearfield": "cl",
    "enlist": "enlist",
}

def detectar_cultivo_maleza_sin_momento(texto):
    """
    Detecta consultas con cultivo + maleza conocida pero SIN momento explícito.
    Retorna dict {'cultivo': ..., 'maleza': ...} o None.
    """
    t = texto.lower().strip()

    # Si tiene momento explícito, no interceptar — otros detectores lo manejan
    MOMENTOS_EXPLICITOS = [
        "pee", "pre-emergencia", "preemergencia", "pre emergencia",
        "poe", "post-emergencia", "postemergencia", "post emergencia",
        "barbecho", "presiembra", "pre-siembra", "pre siembra",
        "psi", "pre-siembra incorporado"
    ]
    if any(m in t for m in MOMENTOS_EXPLICITOS):
        return None

    # Detectar cultivo
    cultivo = None
    for palabra, cult in CULTIVOS_ALIAS.items():
        if palabra in t:
            if cult in ("trigo", "cebada"):
                cultivo = "trigo"
            elif cult == "soja":
                cultivo = "soja"
            elif cult in ("maiz", "maíz"):
                cultivo = "maiz"
            elif cult == "girasol":
                cultivo = "girasol"
            elif cult == "sorgo":
                cultivo = "sorgo"
            break

    if not cultivo:
        return None

    # Detectar maleza según cultivo
    maleza_map = {
        "trigo": PEE_MALEZA_KEYWORDS_TRIGO,
        "soja": PEE_MALEZA_KEYWORDS_SOJA,
        "maiz": PEE_MALEZA_KEYWORDS_MAIZ,
        "girasol": PEE_MALEZA_KEYWORDS_GIRASOL,
        "sorgo": {},
    }
    maleza = None
    for kw, val in maleza_map.get(cultivo, {}).items():
        if kw in t:
            maleza = val
            break

    if not maleza:
        return None

    return {"cultivo": cultivo, "maleza": maleza}


def kb_momento_manejo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Barbecho Largo (abril-junio)", callback_data="momento_barb_largo")],
        [InlineKeyboardButton("📅 Barbecho Corto / Presiembra (ago-sep)", callback_data="momento_barb_corto")],
        [InlineKeyboardButton("🌾 PEE (Pre-emergencia del cultivo)", callback_data="momento_pee")],
        [InlineKeyboardButton("🌿 POE (Post-emergencia del cultivo)", callback_data="momento_poe")],
    ])


def detectar_poe_maiz_guiado(texto):
    t = texto.lower().strip()
    # Detectar momento POE (orden libre)
    POE_MOMENTOS = ["poe", "post-emergencia", "postemergencia", "post emergencia", "postemer"]
    es_poe = any(kw in t for kw in POE_MOMENTOS)
    if not es_poe:
        return None
    # Detectar cultivo maíz (orden libre)
    es_maiz = any(kw in t for kw in ["maiz", "maíz", "maice", "maíce"])
    if not es_maiz:
        return None
    biotipo = None
    for kw, val in POE_MAIZ_BIOTIPO_KEYWORDS.items():
        if kw in t:
            biotipo = val
            break
    maleza = None
    for kw, val in PEE_MALEZA_KEYWORDS_MAIZ.items():
        if kw in t:
            maleza = val
            break
    if not maleza:
        if "conyza" in t or "rama negra" in t or "coniza" in t:
            maleza = "conyza"
    return {"biotipo": biotipo, "maleza": maleza}

def kb_poe_maiz_biotipo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌽 Convencional", callback_data="poe_maiz_biotipo_convencional")],
        [InlineKeyboardButton("🌽 RR (Roundup Ready)", callback_data="poe_maiz_biotipo_rr")],
        [InlineKeyboardButton("🌽 CL (Clearfield)", callback_data="poe_maiz_biotipo_cl")],
        [InlineKeyboardButton("🌽 Enlist", callback_data="poe_maiz_biotipo_enlist")],
    ])

def kb_poe_maiz_maleza():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Raigrás / Lolium", callback_data="poe_maiz_maleza_raigras")],
        [InlineKeyboardButton("🌿 Yuyo Colorado (Amaranthus)", callback_data="poe_maiz_maleza_amaranthus")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="poe_maiz_maleza_cruciferas")],
        [InlineKeyboardButton("🌿 Cebollín (Cyperus)", callback_data="poe_maiz_maleza_cebollin")],
        [InlineKeyboardButton("🌿 Rama Negra (Conyza)", callback_data="poe_maiz_maleza_conyza")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="poe_maiz_maleza_otra")],
    ])

def poe_maiz_raigras_conv_rr():
    return (
        "MAÍZ CONVENCIONAL / RR — RAIGRÁS — POE\n\n"
        "🚨 Sin opciones selectivas disponibles.\n\n"
        "⚠️ ACCasa (cletodim, haloxyfop) son FITOTÓXICOS en maíz convencional y RR.\n"
        "   NUNCA aplicar en POE de estos biotipos.\n\n"
        "El control debió lograrse en barbecho o presiembra:\n"
        "✅ Glifosato + Cletodim 24% (Select) 0,7-1 L/ha — mínimo 10 DAS antes de siembra"
    )

def poe_maiz_raigras_cl():
    return (
        "MAÍZ CL (Clearfield) — RAIGRÁS — POE\n\n"
        "⚠️ Sin opciones selectivas con buena eficacia sobre raigrás en CL.\n"
        "   Onduty no controla Lolium — no figura en marbete.\n\n"
        "El control debió lograrse en barbecho o presiembra:\n"
        "✅ Glifosato + Cletodim 24% (Select) 0,7-1 L/ha — mínimo 10 DAS antes de siembra"
    )

def poe_maiz_raigras_enlist():
    return (
        "MAÍZ ENLIST — RAIGRÁS — POE\n\n"
        "🥇 Haloxyfop 54% (Galant Max) 0,08-0,15 L/ha — ACCasa, el maíz Enlist tolera\n"
        "   ⚠️ Coadyuvante: aceite vegetal o metilado 0,5-1% v/v obligatorio\n\n"
        "🥈 Glufosinato de amonio 28% (Lifeline) 1,8-2 L/ha — hasta V6\n"
        "   ⚠️ Coadyuvante: surfactante no iónico 0,1% + sulfato de amonio 2 kg/ha\n\n"
        "⚠️ Estas opciones son EXCLUSIVAS de maíz Enlist — no usar en convencional ni RR"
    )

def poe_maiz_amaranthus_conv_rr():
    return (
        "MAÍZ CONVENCIONAL / RR — AMARANTHUS (Yuyo Colorado) — POE\n\n"
        "🥇 Mesotrione 48% (Callisto) 0,3 L/ha + Atrazina 90% 1,8 kg/ha — V2-V6\n"
        "🥇 Topramezone 33,6% (Convey) 0,08-0,1 L/ha + Atrazina 90% 1,8 kg/ha — V1-V7\n"
        "   Maleza hasta 5 cm — eficacia cae con plantas grandes\n\n"
        "🥈 Tembotrione 42% (Laudis) + Atrazina 90% 1,8 kg/ha — V3-V6\n"
        "🥈 Tolpyralate 40% (Brucia) 0,075-0,125 L/ha + Atrazina 90% 1,8 kg/ha — desde V3\n\n"
        "🥉 2,4D + Atrazina 90% 1,8 kg/ha — V2-V8\n"
        "   ⚠️ 2,4D puede generar leve fitotoxicidad en maíz — evitar en estrés\n\n"
        "⚠️ HPPD siempre con Atrazina para sinergizar — no aplicar solos\n"
        "⚠️ Aplicar con maleza chica y sin estrés hídrico/térmico"
    )

def poe_maiz_amaranthus_cl():
    return (
        "MAÍZ CL (Clearfield) — AMARANTHUS (Yuyo Colorado) — POE\n\n"
        "🥇 Onduty (Imazapic+Imazapir) 114 g/ha — hasta 10ª hoja de yuyo colorado\n"
        "   ⚠️ Maíz CL no debe superar 6ª hoja al aplicar\n"
        "   ⚠️ Con resistencia ALS confirmada: Onduty pierde eficacia\n"
        "   ⚠️ No mezclar con organofosforados ni otros ALS\n\n"
        "🥇 Onduty + Atrazina 90% 1,1 kg/ha — para Amaranthus resistente a ALS hasta 1° par hojas\n\n"
        "🥈 Mesotrione 48% (Callisto) + Atrazina 90% 1,8 kg/ha — V2-V6\n"
        "🥈 Topramezone 33,6% (Convey) + Atrazina 90% 1,8 kg/ha — V1-V7\n\n"
        "🥉 Tembotrione (Laudis) + Atrazina — V3-V6\n"
        "🥉 Tolpyralate (Brucia) + Atrazina — desde V3\n\n"
        "⚠️ HPPD siempre con Atrazina para sinergizar"
    )

def poe_maiz_amaranthus_enlist():
    return (
        "MAÍZ ENLIST — AMARANTHUS (Yuyo Colorado) — POE\n\n"
        "🥇 Glifosato + 2,4D sal colina (Enlist) 1,5-2,5 L/ha + Glufosinato 28% 1,8-2 L/ha — V1-V6\n\n"
        "🥈 2,4D sal colina (Enlist) 1,5-2,5 L/ha ± Atrazina 90% 1,8 kg/ha — hasta V8\n\n"
        "🥉 Glufosinato 28% (Lifeline) 1,8-2 L/ha — hasta V6\n\n"
        "⚠️ 2,4D Enlist: respetar ventana V1-V8\n"
        "⚠️ Coadyuvante glufosinato: surfactante no iónico 0,1% + sulfato de amonio 2 kg/ha"
    )

def poe_maiz_cruciferas_conv_rr():
    return (
        "MAÍZ CONVENCIONAL / RR — CRUCÍFERAS (Brassica/Nabón) — POE\n\n"
        "🥇 Mesotrione 48% (Callisto) 0,3 L/ha + Atrazina 90% 1,8 kg/ha — V2-V6\n"
        "   Excelente sobre crucíferas pequeñas\n"
        "🥇 Topramezone 33,6% (Convey) 0,08-0,1 L/ha + Atrazina 90% 1,8 kg/ha — V1-V7\n\n"
        "🥈 Tembotrione 42% (Laudis) + Atrazina 90% 1,8 kg/ha — V3-V6\n"
        "🥈 Tolpyralate 40% (Brucia) + Atrazina 90% 1,8 kg/ha — desde V3\n\n"
        "🥉 MCPA 28% 1,5 L/ha + Atrazina 90% 1,8 kg/ha — V2-V8\n"
        "🥉 Picloram (Tordón) 0,1-0,15 L/ha + Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "⚠️ HPPD siempre con Atrazina para sinergizar\n"
        "⚠️ Aplicar con crucíferas en roseta chica — eficacia cae rápido con tamaño"
    )

def poe_maiz_cruciferas_cl():
    return (
        "MAÍZ CL (Clearfield) — CRUCÍFERAS (Brassica/Nabón) — POE\n\n"
        "🥇 Onduty (Imazapic+Imazapir) 114 g/ha — Nabo hasta 4ª hoja verdadera\n"
        "   ⚠️ Maíz CL no debe superar 6ª hoja al aplicar\n"
        "   ⚠️ Con resistencia ALS en Brassica — perder eficacia, caer a opciones abajo\n\n"
        "🥈 Mesotrione 48% (Callisto) + Atrazina 90% 1,8 kg/ha — V2-V6\n"
        "🥈 Topramezone 33,6% (Convey) + Atrazina 90% 1,8 kg/ha — V1-V7\n\n"
        "🥉 MCPA 28% 1,5 L/ha + Atrazina 90% 1,8 kg/ha — V2-V8\n"
        "🥉 Picloram (Tordón) + Atrazina — V2-V8\n\n"
        "⚠️ HPPD siempre con Atrazina para sinergizar"
    )

def poe_maiz_cruciferas_enlist():
    return (
        "MAÍZ ENLIST — CRUCÍFERAS (Brassica/Nabón) — POE\n\n"
        "🥇 Glifosato + 2,4D sal colina (Enlist) 1,5-2,5 L/ha + Glufosinato 28% 1,8-2 L/ha — V1-V6\n\n"
        "🥈 2,4D sal colina (Enlist) 1,5-2,5 L/ha ± Atrazina 90% 1,8 kg/ha — hasta V8\n\n"
        "🥉 Glufosinato 28% (Lifeline) 1,8-2 L/ha — hasta V6\n\n"
        "⚠️ 2,4D Enlist: respetar ventana V1-V8"
    )

def poe_maiz_cebollin_conv():
    return (
        "MAÍZ CONVENCIONAL — CEBOLLÍN (Cyperus rotundus) — POE\n\n"
        "🥇 Halosulfurón metil 75% (Sempra) 100-150 g/ha\n"
        "   Aplicar con cebollín a ~15 cm de altura, en activo crecimiento\n"
        "   ⚠️ Coadyuvante: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral."
    )

def poe_maiz_cebollin_rr():
    return (
        "MAÍZ RR — CEBOLLÍN (Cyperus rotundus) — POE\n\n"
        "🥇 Halosulfurón metil 75% (Sempra) 30-50 g/ha + Glifosato 48% 2,5 L/ha\n"
        "   Aplicar con cebollín a ~15 cm, en activo crecimiento\n\n"
        "🥈 Glifosato 48% 3 L/ha + Clorimurón 25% (Classic) 60-80 g/ha\n\n"
        "⚠️ Coadyuvante Sempra: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral."
    )

def poe_maiz_cebollin_cl():
    return (
        "MAÍZ CL (Clearfield) — CEBOLLÍN (Cyperus rotundus) — POE\n\n"
        "🥇 Halosulfurón metil 75% (Sempra) 100-150 g/ha\n"
        "   Aplicar con cebollín a ~15 cm, en activo crecimiento\n\n"
        "🥈 Onduty (Imazapic+Imazapir) 114 g/ha — cebollín hasta 7ª hoja\n"
        "   ⚠️ Maíz CL no debe superar 6ª hoja al aplicar\n\n"
        "⚠️ Coadyuvante Sempra: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral.\n"
        "⚠️ No mezclar Onduty con organofosforados"
    )

def poe_maiz_cebollin_enlist():
    return (
        "MAÍZ ENLIST — CEBOLLÍN (Cyperus rotundus) — POE\n\n"
        "🥇 Halosulfurón metil 75% (Sempra) 30-50 g/ha + Glifosato 48% 2,5 L/ha\n"
        "   Aplicar con cebollín a ~15 cm, en activo crecimiento\n\n"
        "🥈 Glifosato 48% 3 L/ha + Clorimurón 25% (Classic) 60-80 g/ha\n\n"
        "⚠️ Coadyuvante Sempra: surfactante no iónico 0,1-0,2% v/v. NO aceite mineral."
    )

def poe_maiz_conyza_conv_rr():
    return (
        "MAÍZ CONVENCIONAL / RR — CONYZA (Rama Negra) — POE\n\n"
        "⚠️ Aplicar con roseta chica (<10 cm) — eficacia cae fuerte con plantas grandes.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Picloram 27,7% (Tordón) 0,1-0,15 L/ha ± Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "🥈 Glifosato 1080 g ia/ha + Dicamba 57,7% 0,15-0,2 L/ha ± Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "🥉 Glifosato 1080 g ia/ha + Clopyralid 47,5% (Lontrel) 0,1-0,15 L/ha ± Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "⚠️ Alternativa (último recurso):\n"
        "   Glifosato 1080 g ia/ha + 2,4D ± Atrazina — V2-V8\n"
        "   ⚠️ 2,4D puede causar fitotoxicidad en maíz — evitar si hay otra opción\n\n"
        "⚠️ Atrazina suma residualidad y amplía espectro — recomendada en todas las opciones"
    )

def poe_maiz_conyza_cl():
    return (
        "MAÍZ CL (Clearfield) — CONYZA (Rama Negra) — POE\n\n"
        "⚠️ Onduty no controla Conyza — no figura en marbete.\n"
        "   Usar las mismas opciones que convencional/RR:\n\n"
        "🥇 Glifosato 1080 g ia/ha + Picloram 27,7% (Tordón) 0,1-0,15 L/ha ± Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "🥈 Glifosato 1080 g ia/ha + Dicamba 57,7% 0,15-0,2 L/ha ± Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "🥉 Glifosato 1080 g ia/ha + Clopyralid 47,5% (Lontrel) 0,1-0,15 L/ha ± Atrazina 90% 1,8 kg/ha — V2-V8\n\n"
        "⚠️ Alternativa (último recurso):\n"
        "   Glifosato + 2,4D ± Atrazina — ⚠️ fitotoxicidad posible en maíz\n\n"
        "⚠️ Aplicar con roseta chica (<10 cm)"
    )

def poe_maiz_conyza_enlist():
    return (
        "MAÍZ ENLIST — CONYZA (Rama Negra) — POE\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D sal colina (Enlist) 1,5-2,5 L/ha + Glufosinato 28% 1,8-2 L/ha — V1-V6\n\n"
        "🥈 2,4D sal colina (Enlist) 1,5-2,5 L/ha ± Atrazina 90% 1,8 kg/ha — hasta V8\n\n"
        "🥉 Glufosinato 28% (Lifeline) 1,8-2 L/ha — hasta V6\n\n"
        "⚠️ 2,4D Enlist: respetar ventana V1-V8\n"
        "⚠️ Aplicar con roseta chica — eficacia cae con plantas grandes"
    )

async def responder_poe_maiz(query_or_message, context, biotipo, maleza, es_callback=True):
    """Dispatcher POE maíz."""
    respuesta = None
    if maleza == "raigras":
        if biotipo in ["convencional", "rr"]:
            respuesta = poe_maiz_raigras_conv_rr()
        elif biotipo == "cl":
            respuesta = poe_maiz_raigras_cl()
        elif biotipo == "enlist":
            respuesta = poe_maiz_raigras_enlist()
    elif maleza == "amaranthus":
        if biotipo in ["convencional", "rr"]:
            respuesta = poe_maiz_amaranthus_conv_rr()
        elif biotipo == "cl":
            respuesta = poe_maiz_amaranthus_cl()
        elif biotipo == "enlist":
            respuesta = poe_maiz_amaranthus_enlist()
    elif maleza == "cruciferas":
        if biotipo in ["convencional", "rr"]:
            respuesta = poe_maiz_cruciferas_conv_rr()
        elif biotipo == "cl":
            respuesta = poe_maiz_cruciferas_cl()
        elif biotipo == "enlist":
            respuesta = poe_maiz_cruciferas_enlist()
    elif maleza == "cebollin":
        if biotipo == "convencional":
            respuesta = poe_maiz_cebollin_conv()
        elif biotipo == "rr":
            respuesta = poe_maiz_cebollin_rr()
        elif biotipo == "cl":
            respuesta = poe_maiz_cebollin_cl()
        elif biotipo == "enlist":
            respuesta = poe_maiz_cebollin_enlist()
    elif maleza == "conyza":
        if biotipo in ["convencional", "rr"]:
            respuesta = poe_maiz_conyza_conv_rr()
        elif biotipo == "cl":
            respuesta = poe_maiz_conyza_cl()
        elif biotipo == "enlist":
            respuesta = poe_maiz_conyza_enlist()
    elif maleza == "otra":
        bname = {"convencional": "convencional", "rr": "RR", "cl": "CL", "enlist": "Enlist"}.get(biotipo, biotipo)
        respuesta = (
            f"⚠️ No tengo información específica para esa maleza en POE de maíz {bname} todavía.\n\n"
            "🌱 Si es una GRAMÍNEA — recordá que ACCasa es fitotóxico en convencional y RR.\n"
            "🌱 Si es una LATIFOLIADA — los HPPD + Atrazina son el punto de partida en convencional/RR.\n\n"
            "Consultá con tu asesor para ajustar al caso específico."
        )
    if respuesta is None:
        respuesta = "⚠️ No tengo información específica para esa combinación todavía."
    if es_callback:
        await query_or_message.message.reply_text(respuesta)
    else:
        await query_or_message.reply_text(respuesta)
    context.user_data.clear()

# Teclados inline PEE

def kb_pee_maleza_trigo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Raigrás / Lolium", callback_data="pee_maleza_raigras")],
        [InlineKeyboardButton("🌿 Rama Negra (Conyza)", callback_data="pee_maleza_conyza")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="pee_maleza_cruciferas")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="pee_maleza_otra")],
    ])

def kb_pee_maleza_soja():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Yuyo Colorado (Amaranthus)", callback_data="pee_maleza_amaranthus")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="pee_maleza_cruciferas")],
        [InlineKeyboardButton("🌿 Flor de Santa Lucía (Commelina)", callback_data="pee_maleza_commelina")],
        [InlineKeyboardButton("🌿 Parietaria", callback_data="pee_maleza_parietaria")],
        [InlineKeyboardButton("🌿 Cebollín (Cyperus)", callback_data="pee_maleza_cebollin")],
        [InlineKeyboardButton("🌿 Rama Negra (Conyza)", callback_data="pee_maleza_conyza")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="pee_maleza_otra")],
    ])

def kb_pee_maleza_maiz():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Raigrás / Lolium", callback_data="pee_maleza_raigras")],
        [InlineKeyboardButton("🌿 Yuyo Colorado (Amaranthus)", callback_data="pee_maleza_amaranthus")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="pee_maleza_cruciferas")],
        [InlineKeyboardButton("🌿 Cebollín (Cyperus)", callback_data="pee_maleza_cebollin")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="pee_maleza_otra")],
    ])

def kb_pee_maleza_girasol():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Maleza General / Latifoliadas", callback_data="pee_maleza_general")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="pee_maleza_cruciferas")],
        [InlineKeyboardButton("🌿 Cebollín (Cyperus)", callback_data="pee_maleza_cebollin")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="pee_maleza_otra")],
    ])

def kb_pee_objetivo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Maleza ya nacida (rescate)", callback_data="pee_objetivo_nacida")],
        [InlineKeyboardButton("🛡️ Residual (evitar nacimientos)", callback_data="pee_objetivo_residual")],
        [InlineKeyboardButton("🎯+🛡️ Ambos", callback_data="pee_objetivo_ambos")],
    ])

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
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine/Gesatop) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — doble golpe con residual\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — agrega MOA, sin residual de suelo\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha — triple MOA, máxima eficacia en matas (Gigón, Agroconsultas 2025)\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE\n"
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
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
    )

def _lolium_soja_maiz_corto_nacida():
    return (
        "LOLIUM — BARBECHO CORTO/PRESIEMBRA — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Agosto-septiembre es la ventana óptima. Control sostenido sin doble golpe en la mayoría de los casos.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n"
        "🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
    )

def _lolium_soja_maiz_corto_residual(cultivo):
    base = (
        "LOLIUM — BARBECHO CORTO/PRESIEMBRA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha\n\n"
        "PSI inmediato (quema + residual corto):\n"
        "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS (15 DAS en suelos alcalinos o arenosos)\n"
        "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla"
    )
    return base

def _lolium_soja_maiz_corto_ambos(cultivo):
    return (
        "LOLIUM — BARBECHO CORTO/PRESIEMBRA — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "PSI inmediato (quema + residual corto):\n"
        "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS (15 DAS en suelos alcalinos o arenosos)\n"
        "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
    )

def _lolium_girasol_largo_nacida():
    return (
        "LOLIUM — BARBECHO LARGO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Atrazina fitotóxica en girasol — NO usar.\n\n"
        "ABRIL:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
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
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha // Glufosinato 28% 2 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
    )

def _lolium_girasol_corto_nacida():
    return (
        "LOLIUM — BARBECHO CORTO/PRESIEMBRA — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n"
        "🥉 Glufosinato 28% 2 L/ha — para poblaciones resistentes confirmadas\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
    )

def _lolium_girasol_corto_ambos():
    return (
        "LOLIUM — BARBECHO CORTO/PRESIEMBRA — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "⚠️ Atrazina fitotóxica en girasol — NO usar.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha ó Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE"
    )


# === DOBLE MALEZA: BRASSICA + LOLIUM × TRIGO ===

def _doble_trigo_bn_ln():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — AMBAS NACIDAS\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — se recomienda estrategia en dos golpes por antagonismo\n\n"
        "OPCIÓN A — DOS GOLPES (recomendada):\n\n"
        "GOLPE 1 — Graminicida primero:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,6 L/ha (1-2 hojas) / 0,8 L/ha (2-4 hojas)\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada\n\n"
        "Esperar 7-10 días con buenas condiciones (humedad, insolación)\n\n"
        "GOLPE 2 — Hormonal + PPO sobre Brassica:\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + aceite vegetal 0,5%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Carfentrazone 40% (Shark) 75-120 cc/ha\n"
        "⚠️ PPO obligatorio ante sospecha o confirmación de resistencia a glifosato en Brassica\n\n"
        "OPCIÓN B — UN SOLO GOLPE (cuando el timing no permite separar):\n"
        "⚠️ Dosis de cletodim aumentada 20% por antagonismo con 2,4D\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + aceite metilado de soja 1%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Shark 75-120 cc/ha + aceite metilado de soja 1%"
    )

def _doble_trigo_bn_lr():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — BRASSICA NACIDA + LOLIUM RESIDUAL\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — Brassica ya emergida, Lolium aún no nació\n\n"
        "UN SOLO GOLPE — no hay antagonismo (sin graminicida foliar):\n\n"
        "ELIMINAR BRASSICA + RESIDUAL LOLIUM:\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha + aceite vegetal 0,5%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + aceite vegetal 0,5%\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 75-120 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ PPO obligatorio ante sospecha o confirmación de resistencia a glifosato en Brassica\n"
        "⚠️ Yamato requiere lluvia ≥20 mm dentro de los 15 días post-aplicación"
    )

def _doble_trigo_bn_la():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — BRASSICA NACIDA + LOLIUM NACIDO Y RESIDUAL\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — ambas nacidas + residual para Lolium\n\n"
        "OPCIÓN A — DOS GOLPES (recomendada):\n\n"
        "GOLPE 1 — Graminicida + residual Lolium:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada\n\n"
        "Esperar 7-10 días con buenas condiciones (humedad, insolación)\n\n"
        "GOLPE 2 — Hormonal + PPO sobre Brassica:\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + aceite vegetal 0,5%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 75-120 cc/ha\n\n"
        "OPCIÓN B — UN SOLO GOLPE:\n"
        "⚠️ Dosis de cletodim aumentada 20% por antagonismo con 2,4D\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + Yamato 210 cc/ha + aceite metilado de soja 1%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + Terbine 1,5 kg/ha + aceite metilado de soja 1%\n\n"
        "⚠️ PPO obligatorio ante sospecha o confirmación de resistencia a glifosato en Brassica\n"
        "⚠️ Yamato requiere lluvia ≥20 mm dentro de los 15 días post-aplicación"
    )

def _doble_trigo_br_ln():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — BRASSICA RESIDUAL + LOLIUM NACIDO\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — Lolium ya emergido, Brassica aún no nació\n\n"
        "UN SOLO GOLPE — sin antagonismo (sin hormonal):\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenicán 50% (Brodal) 250 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada\n"
        "⚠️ Diflufenicán (Brodal): 10 días intervalo antes de siembra trigo/cebada\n"
        "⚠️ Flurocloridona (Rainbow): 0 días intervalo — presiembra inmediata sin problema"
    )

def _doble_trigo_br_lr():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — AMBAS RESIDUAL\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — ninguna emergida, objetivo 100% residual\n\n"
        "UN SOLO GOLPE — sin antagonismo:\n\n"
        "🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Flurocloridona 25% (Rainbow) 1,5 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenicán 50% (Brodal) 250 cc/ha\n\n"
        "⚠️ Yamato requiere lluvia ≥20 mm dentro de los 15 días post-aplicación\n"
        "⚠️ Diflufenicán (Brodal): 10 días intervalo antes de siembra trigo/cebada\n"
        "⚠️ Flurocloridona (Rainbow): 0 días intervalo — presiembra inmediata\n"
        "⚠️ Agregar glifosato si hay malezas anuales nacidas en el momento de aplicación"
    )

def _doble_trigo_br_la():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — BRASSICA RESIDUAL + LOLIUM NACIDO Y RESIDUAL\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — Lolium nacido + prevenir nuevos nacimientos de ambas\n\n"
        "UN SOLO GOLPE — sin antagonismo (sin hormonal):\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenicán 50% (Brodal) 250 cc/ha\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada\n"
        "⚠️ Yamato requiere lluvia ≥20 mm dentro de los 15 días post-aplicación\n"
        "⚠️ Diflufenicán (Brodal): 10 días intervalo antes de siembra trigo/cebada\n"
        "⚠️ Flurocloridona (Rainbow): 0 días intervalo"
    )

def _doble_trigo_ba_ln():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — BRASSICA NACIDA Y RESIDUAL + LOLIUM NACIDO\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — ambas nacidas + residual para Brassica\n\n"
        "OPCIÓN A — DOS GOLPES (recomendada):\n\n"
        "GOLPE 1 — Graminicida primero:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,6 L/ha (1-2 hojas) / 0,8 L/ha (2-4 hojas)\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada\n\n"
        "Esperar 7-10 días con buenas condiciones (humedad, insolación)\n\n"
        "GOLPE 2 — Hormonal + PPO + residual Brassica:\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite vegetal 0,5%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + aceite vegetal 0,5%\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 75-120 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n\n"
        "OPCIÓN B — UN SOLO GOLPE:\n"
        "⚠️ Dosis de cletodim aumentada 20% por antagonismo con 2,4D\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite metilado de soja 1%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + Terbine 1,5 kg/ha + aceite metilado de soja 1%\n\n"
        "⚠️ PPO obligatorio ante sospecha o confirmación de resistencia a glifosato en Brassica\n"
        "⚠️ Flurocloridona (Rainbow): 0 días intervalo trigo/cebada"
    )

def _doble_trigo_ba_lr():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — BRASSICA NACIDA Y RESIDUAL + LOLIUM RESIDUAL\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — Brassica nacida + residual para ambas\n\n"
        "UN SOLO GOLPE — sin antagonismo (sin graminicida foliar):\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha + aceite vegetal 0,5%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + aceite vegetal 0,5%\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 75-120 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenicán 50% (Brodal) 250 cc/ha\n\n"
        "⚠️ PPO obligatorio ante sospecha o confirmación de resistencia a glifosato en Brassica\n"
        "⚠️ Yamato requiere lluvia ≥20 mm dentro de los 15 días post-aplicación\n"
        "⚠️ Diflufenicán (Brodal): 10 días intervalo antes de siembra trigo/cebada\n"
        "⚠️ Flurocloridona (Rainbow): 0 días intervalo\n"
        "⚠️ Opción 🥇 es una mezcla compleja — verificar compatibilidad física antes de aplicar"
    )

def _doble_trigo_ba_la():
    return (
        "BRASSICA + LOLIUM — BARBECHO TRIGO — AMBAS NACIDAS Y RESIDUAL\n\n"
        "⚠️ DOS MALEZAS PROBLEMA — máxima complejidad, ambas nacidas + residual para ambas\n\n"
        "OPCIÓN A — DOS GOLPES (recomendada):\n\n"
        "GOLPE 1 — Graminicida + residual Lolium:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,6 L/ha (1-2 hojas) / 0,8 L/ha (2-4 hojas) + Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada\n\n"
        "Esperar 7-10 días con buenas condiciones (humedad, insolación)\n\n"
        "GOLPE 2 — Hormonal + PPO + residual Brassica:\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite vegetal 0,5%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Heat 35-40 g/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + aceite vegetal 0,5%\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Shark 75-120 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n\n"
        "OPCIÓN B — UN SOLO GOLPE:\n"
        "⚠️ Dosis de cletodim aumentada 20% por antagonismo con 2,4D\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Yamato 210 cc/ha + aceite metilado de soja 1%\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Cletodim 24% (Select) 1,0 L/ha + Heat 35-40 g/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Terbine 1,5 kg/ha + aceite metilado de soja 1%\n\n"
        "⚠️ PPO obligatorio ante sospecha o confirmación de resistencia a glifosato en Brassica\n"
        "⚠️ Yamato requiere lluvia ≥20 mm dentro de los 15 días post-aplicación\n"
        "⚠️ Flurocloridona (Rainbow): 0 días intervalo trigo/cebada\n"
        "⚠️ Opción B es una mezcla de tanque muy compleja — verificar compatibilidad física antes de aplicar"
    )

def get_doble_trigo_respuesta(b_obj, l_obj):
    """Dispatcher para combinaciones Brassica + Lolium en trigo."""
    mapping = {
        ("nacida",   "nacida"):   _doble_trigo_bn_ln,
        ("nacida",   "residual"): _doble_trigo_bn_lr,
        ("nacida",   "ambos"):    _doble_trigo_bn_la,
        ("residual", "nacida"):   _doble_trigo_br_ln,
        ("residual", "residual"): _doble_trigo_br_lr,
        ("residual", "ambos"):    _doble_trigo_br_la,
        ("ambos",    "nacida"):   _doble_trigo_ba_ln,
        ("ambos",    "residual"): _doble_trigo_ba_lr,
        ("ambos",    "ambos"):    _doble_trigo_ba_la,
    }
    fn = mapping.get((b_obj, l_obj))
    return fn() if fn else None

def _lolium_trigo_nacida():
    return (
        "LOLIUM — BARBECHO TRIGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "SITUACIÓN 1 — 1-2 hojas, baja densidad:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,6 L/ha\n"
        "🥈 Glufosinato 28% 2 L/ha\n"
        "🥉 Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
        "SITUACIÓN 2 — 2-4 hojas, densidad media:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 12%/Haloxyfop 6% (Gramini Elite) 1 L/ha\n\n"
        "SITUACIÓN 3 — más de 4 hojas o sospecha resistencia ACCasa:\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Epyrifenacil 5,5% (Empera) 600-800 cc/ha\n"
        "🥈 Glufosinato 28% 2 L/ha + Cletodim 24% (Select) 0,8 L/ha\n\n"
        "SITUACIÓN 4 — resistencia confirmada O maleza muy establecida (5+ macollos):\n"
        "🔁 1° Glifosato 1080 g ia/ha + Cletodim (Select) 0,8 L/ha // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n"
        "🔁 1° Glifosato 1080 g ia/ha + Cletodim (Select) 0,8 L/ha // 2° Glufosinato 28% 2 L/ha\n\n"
        "⚠️ Cletodim y haloxyfop requieren aceite vegetal o metilado 0,5-1% v/v SIEMPRE"
    )

def _lolium_trigo_residual():
    return (
        "LOLIUM — BARBECHO TRIGO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Azugro (Bixlozona) FMC — residual específico para Lolium en trigo. Sin restricción\n"
        "🥈 Terbutilazina 50% (Terbine/Gesatop/Koritsu) 1,5 kg/ha — sin restricción en trigo\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha — sin restricción en LD; LC y cebada: 15 días. Requiere ≥20mm\n"
        "🥉 Pendimetalín 45,5% (Herbadox H2O) 2-2,5 L/ha — semilla trigo a ≥3 cm\n\n"
        "PSI trigo con doble MOA (Fotosistema II + PPO):\n"
        "✅ Sumyzin T Max (Terbutilazina/Flumioxazin) 1,5 L/ha — 10-15 DAS, semilla ≥4 cm, ≥20mm lluvia, NO suelos livianos\n"
        "✅ Mateno Plus (Flufenacet/Diflufenican/Aclonifen) 2-2,25 L/ha — PEE maleza + cultivo, trigo y raigrás/crucíferas"
    )

def _lolium_trigo_ambos():
    return (
        "LOLIUM — BARBECHO TRIGO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Azugro (Bixlozona) FMC\n"
        "🥈 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Sumyzin T Max (Terbutilazina/Flumioxazin) 1,5 L/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Cletodim 24% (Select) 0,8 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "Alternativa PEE (sobre lote limpio posterior):\n"
        "✅ Mateno Plus (Flufenacet/Diflufenican/Aclonifen) 2-2,25 L/ha — PEE cultivo+maleza\n\n"
        "⚠️ Cletodim requiere aceite vegetal o metilado 0,5-1% v/v\n"
        "⚠️ Cletodim (Select): 15 días intervalo antes de siembra trigo/cebada SIEMPRE\n"
        "⚠️ Sumyzin T Max: semilla trigo a ≥4 cm, NO suelos livianos, requiere ≥20mm lluvia"
    )

# --- CONYZA ---

def _conyza_largo_nacida():
    return (
        "CONYZA — BARBECHO LARGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Roseta menor a 10 cm responde mejor. Mayor a 10 cm requiere doble golpe.\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha\n\n"
        "PPO de contacto como apoyo (agregar a cualquiera):\n"
        "✅ Saflufenacil 70% (Heat) 35-40 g/ha — levemente superior\n"
        "✅ Carfentrazone 40% (Shark) 75-120 cc/ha — sin restricción\n\n"
        "ROSETA MAYOR A 10 CM — Doble Golpe:\n"
        "🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
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
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "CONYZA — BARBECHO LARGO — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )

def _conyza_corto_nacida():
    return (
        "CONYZA — BARBECHO CORTO/PRESIEMBRA — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Segundo pico de emergencia. Plántulas pequeñas — mejor momento para control.\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _conyza_corto_residual(cultivo):
    if cultivo == "soja":
        return (
            "CONYZA — BARBECHO CORTO/PRESIEMBRA — SOJA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha — ⚠️ verificar 45 días antes de siembra soja\n"
            "🥉 Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla"
        )
    else:
        return (
            "CONYZA — BARBECHO CORTO/PRESIEMBRA — MAÍZ — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla"
        )

def _conyza_corto_ambos(cultivo):
    if cultivo == "soja":
        return (
            "CONYZA — BARBECHO CORTO/PRESIEMBRA — SOJA — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha — ⚠️ verificar 45 días\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla\n\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "CONYZA — BARBECHO CORTO/PRESIEMBRA — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla\n\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )

def _conyza_girasol_largo_nacida():
    return (
        "CONYZA — BARBECHO LARGO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Atrazina, biciclopirone, saflufenacil y metsulfurón NO usar en barbecho previo a girasol.\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha\n\n"
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
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha — ⚠️ verificar 45 días Lontrel\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _conyza_girasol_corto_nacida():
    return (
        "CONYZA — BARBECHO CORTO/PRESIEMBRA — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Pixxaro puede aplicarse hasta 0 días antes de siembra de girasol.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Pixxaro (Halauxifen + Fluroxipir) 400-500 cc/ha + aceite mineral 1% v/v — SENASA N° 40.386\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥉 Glifosato 1080 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — ⚠️ 15-20 días\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)"
    )

def _conyza_girasol_corto_residual():
    return (
        "CONYZA — BARBECHO CORTO/PRESIEMBRA — GIRASOL — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "⚠️ Atrazina (90 días) no alcanza en barbecho corto. Saflufenacil NO usar en girasol.\n\n"
        "🥇 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en girasol\n"
        "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha"
    )

def _conyza_girasol_corto_ambos():
    return (
        "CONYZA — BARBECHO CORTO/PRESIEMBRA — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Pixxaro 400-500 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + aceite mineral 1% v/v\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥉 Glifosato 1080 g ia/ha + Pixxaro 400-500 cc/ha + Diflufenican 50% (Brodal) 250 cc/ha + aceite mineral 1% v/v\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)"
    )

def _conyza_trigo_nacida():
    return (
        "CONYZA — BARBECHO TRIGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días intervalo\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — 3-5 días\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _conyza_trigo_residual():
    return (
        "CONYZA — BARBECHO TRIGO — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Metsulfurón 60% (Ally/Errasin) 7-8 g/ha — 0 días intervalo en trigo\n"
        "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
        "🥉 Diflufenican 50% (Brodal) 250 cc/ha — 15 días intervalo\n\n"
        "PSI inmediato (quema + residual):\n"
        "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS (15 DAS suelos alcalinos/arenosos)\n"
        "✅ Sumyzin T Max (Terbutilazina/Flumioxazin) 1,5 L/ha — 10-15 DAS, semilla ≥4 cm, ≥20mm, NO suelos livianos\n"
        "✅ Flumioxazin 48% (Sumisoya) 0,15 L/ha + Glifosato — 10 DAS"
    )

def _conyza_trigo_ambos():
    return (
        "CONYZA — BARBECHO TRIGO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Metsulfurón 60% (Ally) 7-8 g/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n"
        "PSI inmediato (quema + residual):\n"
        "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
        "✅ Sumyzin T Max (Terbutilazina/Flumioxazin) 1,5 L/ha + Glifosato — 10-15 DAS\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ Sumyzin T Max: semilla trigo ≥4 cm, NO suelos livianos, ≥20mm lluvia"
    )

# --- BRASSICA ---

def _brassica_largo_nacida():
    return (
        "BRASSICA — BARBECHO LARGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Roseta menor a 10 cm responde mejor. Mayor a 10 cm — Doble Golpe obligatorio.\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 94% control\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha\n\n"
        "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
        "ROSETA MAYOR A 10 CM:\n"
        "🔁 1° Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + PPO // 2° Paraquat 27,6% (Gramoxone) 2 L/ha\n\n"
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
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "BRASSICA — BARBECHO LARGO — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
            "PPO como apoyo: ✅ Heat 35-40 g/ha ✅ Shark 75-120 cc/ha\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ PPO requiere aceite vegetal 0,5% v/v"
        )

def _brassica_corto_nacida():
    return _brassica_largo_nacida().replace("LARGO", "CORTO")

def _brassica_corto_residual(cultivo):
    if cultivo == "soja":
        return (
            "BRASSICA — BARBECHO CORTO/PRESIEMBRA — SOJA — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
            "🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ respetar 30-40 días antes de soja\n\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla"
        )
    else:
        return (
            "BRASSICA — BARBECHO CORTO/PRESIEMBRA — MAÍZ — PREVENIR NUEVOS NACIMIENTOS (RESIDUAL)\n\n"
            "🥇 Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha\n"
            "🥈 Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
            "🥉 Flurocloridona 25% (Rainbow) 1,5 L/ha — sin restricción en maíz\n\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla"
        )

def _brassica_corto_ambos(cultivo):
    if cultivo == "soja":
        return (
            "BRASSICA — BARBECHO CORTO/PRESIEMBRA — SOJA — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Shark 75 cc/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha — ⚠️ 30-40 días antes de soja\n\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ Shark requiere aceite vegetal 0,5% v/v"
        )
    else:
        return (
            "BRASSICA — BARBECHO CORTO/PRESIEMBRA — MAÍZ — MALEZA NACIDA + RESIDUAL\n\n"
            "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Biciclopirone 20% (Acuron Uno) 0,75-1 L/ha + Atrazina 90% 1 kg/ha + Shark 75 cc/ha\n"
            "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha\n"
            "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n\n"
            "PSI inmediato (quema + residual corto):\n"
            "✅ Voraxor (Trifludimoxazin/Saflufenacil) 100-150 cc/ha + Glifosato — 7 DAS\n"
            "✅ Flumioxazin 48% (Sumisoya) 50-100 cc/ha + Glifosato — PSI en mezcla\n\n"
            "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
            "⚠️ Shark requiere aceite vegetal 0,5% v/v"
        )

def _brassica_girasol_largo_nacida():
    return (
        "BRASSICA — BARBECHO LARGO — GIRASOL — ELIMINAR MALEZA YA NACIDA\n\n"
        "⚠️ Biciclopirone y atrazina NO usar en girasol. Heat NO usar en pre-siembra girasol.\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — ⚠️ 45 días intervalo\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha\n\n"
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
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ verificar 45 días Lontrel\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
        "MAYO-JUNIO:\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _brassica_girasol_corto_nacida():
    return _brassica_girasol_largo_nacida().replace("LARGO", "CORTO")

def _brassica_girasol_corto_ambos():
    return (
        "BRASSICA — BARBECHO CORTO/PRESIEMBRA — GIRASOL — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha + Shark 75 cc/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Shark 75 cc/ha\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ Shark requiere aceite vegetal 0,5% v/v"
    )

def _brassica_trigo_nacida():
    return (
        "BRASSICA — BARBECHO TRIGO — ELIMINAR MALEZA YA NACIDA\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha — 0 días\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Dicamba 48% (Banvel) 200 cc/ha — 0 días\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — 3-5 días\n\n"
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
        "🥉 Pyroxasulfone 85% (Yamato) 120 g/ha — LD sin restricción; LC 15 días. Requiere ≥20mm\n"
        "🥉 Terbutilazina 50% (Terbine) 1,5 kg/ha\n\n"
        "PSI doble MOA:\n"
        "✅ Sumyzin T Max (Terbutilazina/Flumioxazin) 1,5 L/ha — 10-15 DAS, semilla ≥4 cm, ≥20mm, NO suelos livianos\n"
        "✅ Mateno Plus (Flufenacet/Diflufenican/Aclonifen) 2-2,25 L/ha — PEE cultivo+maleza, cubre raigrás y crucíferas"
    )

def _brassica_trigo_ambos():
    return (
        "BRASSICA — BARBECHO TRIGO — MALEZA NACIDA + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Clopyralid 75% (Lontrel) 150 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha + Heat 35-40 g/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Terbutilazina 50% (Terbine) 1,5 kg/ha + Diflufenican 50% (Brodal) 250 cc/ha\n\n"
        "PSI doble MOA (sobre lote limpio o en mezcla si maleza <30% cobertura):\n"
        "✅ Sumyzin T Max (Terbutilazina/Flumioxazin) 1,5 L/ha + Glifosato — 10-15 DAS\n"
        "✅ Mateno Plus (Flufenacet/Diflufenican/Aclonifen) 2-2,25 L/ha — PEE cultivo+maleza\n\n"
        "⚠️ Roseta mayor a 10 cm: doble golpe con Paraquat 27,6% (Gramoxone)\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ Sumyzin T Max: semilla trigo ≥4 cm, NO suelos livianos, ≥20mm lluvia"
    )

# ─── ALFALFA ──────────────────────────────────────────────────────────────────

def _alfalfa_barbecho():
    return (
        "ALFALFA — BARBECHO / PRESIEMBRA\n\n"
        "Herbicidas de acción total:\n"
        "✅ Glifosato 1080 g ia/ha — estándar\n"
        "✅ Glufosinato de amonio 28% (Empera/Finale) 2 L/ha — para biotipos RR\n"
        "✅ Paraquat 27,6% (Gramoxone) 2 L/ha — quema rápida\n\n"
        "Herbicidas postemergentes de malezas (agregar a glifosato):\n"
        "✅ Fluroxipir (Starane Xtra) 400-500 cc/ha — crucíferas, cardos\n"
        "✅ Carfentrazone 40% (Shark) 50-75 cc/ha — PPO de contacto\n\n"
        "Residual (presiembra):\n"
        "✅ Flumetsulam 12% (Preside) 300-500 cc/ha — crucíferas, rama negra, capiquí\n\n"
        "⚠️ Fuente: INTA (Montoya), marbetes SENASA"
    )

def _alfalfa_pee():
    return (
        "ALFALFA — PEE (VENTANA PREEMERGENTE)\n\n"
        "🥇 Flumetsulam 12% (Preside) 400-600 cc/ha\n"
        "   Malezas: crucíferas, rama negra (Conyza), capiquí\n"
        "   Usar dosis máxima en manzanilla, nabón, rábano o cuando se quiere mayor residualidad\n"
        "   ⚠️ Posible fitotoxicidad al acompañante gramíneo (avena) — reduce producción\n\n"
        "Mezcla para ampliar espectro (también PEE o POE temprana):\n"
        "✅ Flumetsulam 12% 300-400 cc/ha + 2,4-DB éster (2,4-DB Sigma) 1-1,5 L/ha\n"
        "   Amplía control a cardos, yuyo colorado, sanguinaria\n"
        "   ⚠️ NO mezclar con MCPA si hay alfalfa en la mezcla\n"
        "   ⚠️ NO usar si hay trébol rojo en la pastura\n\n"
        "⚠️ Para control óptimo el suelo necesita humedad adecuada post-aplicación\n"
        "⚠️ Fuente: Preside SENASA 32.110 (Corteva), INTA (Montoya)"
    )

def _alfalfa_poe_implantacion():
    return (
        "ALFALFA — POE EN IMPLANTACIÓN\n\n"
        "⚠️ Aplicar desde 2-3 trifolios de leguminosas. Malezas pequeñas (3-6 hojas o rosetas ≤10 cm).\n"
        "⚠️ 15 días entre aplicación y primer pastoreo o corte (marbete Preside)\n\n"
        "LATIFOLIADAS GENERALES:\n"
        "🥇 Flumetsulam 12% (Preside) 200-250 cc/ha + coadyuvante no iónico 0,15%\n"
        "   Crucíferas, rama negra, capiquí, manzanilla, mostacilla\n"
        "🥈 Flumetsulam 12% 150-200 cc/ha + Diflufenican 50% (Brodal) 100 cc/ha\n"
        "   Amplía a: algodonosa, linaria, viola, ortiga mansa, borraja, lengua de vaca\n"
        "   ⚠️ Diflufenican: posible clorosis leve en alfalfa (síntoma transitorio)\n"
        "🥉 Flumetsulam 12% 150-200 cc/ha + Bromoxinil 24% (Bromotril) 700 cc/ha\n"
        "   Amplía a: poligonáceas, senecio\n\n"
        "CARDOS + LATIFOLIADAS:\n"
        "✅ 2,4-DB éster (2,4-DB Sigma) 1-1,5 L/ha — cardos, crucíferas, yuyo colorado, sanguinaria\n"
        "   Aplicar con plantas pequeñas o en 3ª hoja trifoliada / rebrote de pastoreo\n"
        "   ⚠️ Carencia forraje: 20 días. NO en floración\n"
        "✅ Cloroimurón 75% (Clorimuron 75 Max) 7-10 g/ha — rama negra, crucíferas, ortiga mansa, cardos\n"
        "   ⚠️ Fitotoxicidad en avena acompañante — menor crecimiento de alfalfa en implantación\n"
        "   ⚠️ Carencia pasturas: 30 días antes de pastoreo. NO sorgo, girasol, arroz ni maní en 9 meses\n\n"
        "GRAMÍNEAS (en alfalfa pura):\n"
        "✅ Cletodim 24% (Select) 300-500 cc/ha — pasto puna, sorgo de Alepo, gramón\n"
        "✅ Haloxifop 12% 500-700 cc/ha — ídem\n"
        "✅ Propaquizafop 10% 750 cc/ha — ídem\n"
        "   ACCase — solo en alfalfa pura. Todos requieren aceite vegetal o metilado\n\n"
        "PRIMAVERA (malezas estivales, alfalfa pura):\n"
        "✅ Imazetapir 10,59% 600 cc/ha — roseta, pasto cuaresma, chloris, cardo ruso, lecheron, roseta francesa\n"
        "   Solo en primavera, alfalfa pura\n\n"
        "⚠️ Fuente: INTA (Montoya), marbetes Preside SENASA 32.110, 2,4-DB SENASA 38.806, Clorimuron SENASA 38.863, Diflufenican SENASA 40.427, Bromotril SENASA 30.009"
    )

def _alfalfa_poe_establecida():
    return (
        "ALFALFA ESTABLECIDA — POE (POST-IMPLANTACIÓN)\n\n"
        "GRAMÍNEAS (sorgo de Alepo, pasto puna, gramón):\n"
        "🥇 Cletodim 24% (Select) 300-500 cc/ha — alfalfa pura\n"
        "🥈 Haloxifop 12% 500-700 cc/ha — alfalfa pura\n"
        "🥉 Propaquizafop 10% 750 cc/ha — alfalfa pura\n"
        "   ⚠️ ACCase — NO en pasturas con gramíneas forrajeras (fitotóxico al acompañante)\n"
        "   ⚠️ Todos requieren aceite vegetal o metilado 0,5-1% v/v\n\n"
        "LATIFOLIADAS (rebrote o malezas nuevas):\n"
        "✅ 2,4-DB éster 1-1,5 L/ha — cardos en roseta, crucíferas, yuyo colorado\n"
        "   Aplicar cuando alfalfa rebrota de pastoreo o corte, plantas pequeñas\n"
        "   ⚠️ NO en floración. Carencia forraje 20 días\n"
        "✅ Flumetsulam 12% (Preside) 200-250 cc/ha + no iónico — crucíferas, rama negra\n"
        "   ⚠️ 15 días antes de pastoreo o corte\n\n"
        "ALFALFA RR (variedades resistentes a glifosato):\n"
        "✅ Glifosato 1200-3000 g ia/ha — cuscuta y malezas sensibles\n"
        "   Se recomienda mezclar con otro MOA para ampliar espectro y mitigar resistencia\n\n"
        "⚠️ Fuente: INTA (Montoya), marbetes SENASA"
    )

# ─── FIN ALFALFA ───────────────────────────────────────────────────────────────



def _amaranthus_soja_maiz_largo_nacida():
    return (
        "AMARANTHUS — BARBECHO LARGO — ELIMINAR YUYO COLORADO NACIDO\n\n"
        "⚠️ Glifosato solo: <20% control a 45 DDA en biotipos resistentes. Necesita mezcla con PPO obligatoriamente.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + 2,4D 750 g ia/ha\n\n"
        "⚠️ PPO requiere aceite vegetal o metilado 0,5% v/v\n"
        "⚠️ Empera 600 cc/ha es mínima dosis eficaz; 800 cc/ha para plantas de 5-10 cm (Gigón, Agroconsultas 2025)\n"
        "⚠️ Amaranthus resistente: evaluar rotación de MOA — resistencia PPO en aumento"
    )

def _amaranthus_soja_maiz_largo_residual(cultivo):
    soja_extra = (
        "\n✅ Metribuzin 48% (Sencorex) 500-700 cc/ha — SOLO soja RR/STS, excelente residual Amaranthus\n"
        "✅ Flumioxazin 48% (Sumisoya) 100 cc/ha — residual corto, mejor en mezcla"
    ) if cultivo == "soja" else (
        "\n✅ Atrazina 90% 1,5-2 kg/ha + Biciclopirone 20% (Acuron Uno) 0,75 L/ha — mejor opción residual maíz\n"
        "✅ Atrazina 90% 2 kg/ha — residual solo, cubre Amaranthus"
    )
    return (
        "AMARANTHUS — BARBECHO LARGO — PREVENIR NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Sulfentrazone 50% (Authority/Capaz) 300-350 cc/ha — PPO, excelente residual Amaranthus\n"
        "🥈 Flumioxazin 48% (Sumisoya) 100 cc/ha — residual corto, rotar MOA\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha — VLCFA, complementa PPO"
        + soja_extra + "\n\n"
        "⚠️ Residuales actúan sobre semillas. No controlan plantas ya emergidas."
    )

def _amaranthus_soja_maiz_largo_ambos(cultivo):
    soja_extra = (
        "\n🥈 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Metribuzin 48% (Sencorex) 500 cc/ha — SOLO soja RR/STS"
    ) if cultivo == "soja" else (
        "\n🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Atrazina 90% 1,5 kg/ha"
    )
    return (
        "AMARANTHUS — BARBECHO LARGO — YUYO NACIDO + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Sulfentrazone 50% (Authority/Capaz) 300 cc/ha"
        + soja_extra + "\n"
        "🥉 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ Authority/Capaz: 0 días intervalo en soja y maíz"
    )

def _amaranthus_soja_maiz_corto_nacida():
    return (
        "AMARANTHUS — BARBECHO CORTO/PRESIEMBRA — ELIMINAR YUYO COLORADO NACIDO\n\n"
        "⚠️ Agosto-octubre: segunda oleada de emergencia. Controlar antes de siembra.\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha — mejor sostenimiento a 45 DDA\n"
        "🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + 2,4D 750 g ia/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ Glifosato solo: ineficaz en biotipos resistentes"
    )

def _amaranthus_soja_maiz_corto_residual(cultivo):
    soja_extra = (
        "\n✅ Metribuzin 48% (Sencorex) 500-700 cc/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — SOLO soja RR/STS"
    ) if cultivo == "soja" else (
        "\n✅ Biciclopirone 20% (Acuron Uno) 0,75 L/ha + Atrazina 90% 1 kg/ha — excelente para maíz"
    )
    return (
        "AMARANTHUS — BARBECHO CORTO/PRESIEMBRA — PREVENIR NACIMIENTOS (RESIDUAL)\n\n"
        "🥇 Sulfentrazone 50% (Authority/Capaz) 300-350 cc/ha — sin restricción en soja y maíz\n"
        "🥈 Pyroxasulfone 85% (Yamato) 210 cc/ha\n"
        "🥉 Flumioxazin 48% (Sumisoya) 100 cc/ha — PSI mezcla, residual corto"
        + soja_extra + "\n\n"
        "⚠️ Voraxor (Trifludimoxazin/Saflufenacil): sin registro para Amaranthus como maleza objetivo principal"
    )

def _amaranthus_soja_maiz_corto_ambos(cultivo):
    soja_extra = (
        "\n🥈 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Metribuzin 48% (Sencorex) 500 cc/ha — SOLO soja RR/STS"
    ) if cultivo == "soja" else (
        "\n🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Atrazina 90% 1,5 kg/ha"
    )
    return (
        "AMARANTHUS — BARBECHO CORTO/PRESIEMBRA — YUYO NACIDO + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Sulfentrazone 50% (Authority/Capaz) 300 cc/ha"
        + soja_extra + "\n"
        "🥉 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ 2,4D: respetar 7-15 días antes de siembra soja"
    )

def _amaranthus_girasol_largo_nacida():
    return (
        "AMARANTHUS — BARBECHO LARGO — GIRASOL — ELIMINAR YUYO NACIDO\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + 2,4D 750 g ia/ha — ⚠️ 7-15 días antes de siembra\n"
        "🥉 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ Saflufenacil (Heat): NO usar en presiembra inmediata de girasol (sin registro)"
    )

def _amaranthus_girasol_largo_residual():
    return (
        "AMARANTHUS — BARBECHO LARGO — GIRASOL — RESIDUAL\n\n"
        "🥇 Sulfentrazone 50% (Authority/Capaz) 300-350 cc/ha — 0 días intervalo en girasol\n"
        "🥈 Flurocloridona 25% (Rainbow) 1,5 L/ha — 0 días intervalo en girasol, buen perfil Amaranthus\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha\n\n"
        "⚠️ Atrazina: 90 días en girasol — no usar en barbecho corto\n"
        "⚠️ Metribuzin: NO en girasol"
    )

def _amaranthus_girasol_largo_ambos():
    return (
        "AMARANTHUS — BARBECHO LARGO — GIRASOL — YUYO NACIDO + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Sulfentrazone 50% (Authority/Capaz) 300 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n"
        "🥉 Glifosato 1080 g ia/ha + Saflufenacil 70% (Heat) 35-40 g/ha + Pyroxasulfone 85% (Yamato) 210 cc/ha — ⚠️ Heat sin registro PSI girasol\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _amaranthus_girasol_corto_nacida():
    return (
        "AMARANTHUS — BARBECHO CORTO/PRESIEMBRA — GIRASOL — ELIMINAR YUYO NACIDO\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha — ⚠️ 7-15 días antes de siembra girasol\n"
        "🥉 Glifosato 1080 g ia/ha — solo en biotipos susceptibles\n\n"
        "⚠️ Saflufenacil (Heat): NO usar en presiembra girasol\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v"
    )

def _amaranthus_girasol_corto_residual():
    return (
        "AMARANTHUS — BARBECHO CORTO/PRESIEMBRA — GIRASOL — RESIDUAL\n\n"
        "🥇 Sulfentrazone 50% (Authority/Capaz) 300-350 cc/ha — 0 días intervalo en girasol\n"
        "🥈 Flurocloridona 25% (Rainbow) 1,5 L/ha — 0 días intervalo en girasol\n"
        "🥉 Pyroxasulfone 85% (Yamato) 210 cc/ha\n\n"
        "⚠️ Saflufenacil (Heat), Flumioxazin (Sumisoya): NO usar en presiembra girasol\n"
        "⚠️ Atrazina: 90 días — no alcanza para siembra inmediata"
    )

def _amaranthus_girasol_corto_ambos():
    return (
        "AMARANTHUS — BARBECHO CORTO/PRESIEMBRA — GIRASOL — YUYO NACIDO + RESIDUAL\n\n"
        "🥇 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Sulfentrazone 50% (Authority/Capaz) 300 cc/ha\n"
        "🥈 Glifosato 1080 g ia/ha + Epyrifenacil 5,5% (Empera) 800 cc/ha + Flurocloridona 25% (Rainbow) 1,5 L/ha\n"
        "🥉 Glifosato 1080 g ia/ha + 2,4D 750 g ia/ha + Sulfentrazone 50% (Authority/Capaz) 300 cc/ha — ⚠️ 7-15 días antes de siembra\n\n"
        "⚠️ PPO requiere aceite vegetal 0,5% v/v\n"
        "⚠️ Saflufenacil (Heat), Flumioxazin: NO usar en presiembra girasol"
    )

def get_barbecho_response(cultivo, maleza, momento, objetivo):
    """Retorna la respuesta hardcodeada para la combinación dada."""
    cultivo = cultivo.lower().strip()
    maleza = maleza.lower().strip()
    momento = momento.lower().strip() if momento else ""
    objetivo = objetivo.lower().strip()
    # Cebada usa las mismas respuestas que trigo en barbecho
    if cultivo == "cebada":
        cultivo = "trigo"

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

    # AMARANTHUS
    elif maleza == "amaranthus":
        if cultivo in ["soja", "maiz"]:
            if momento == "largo":
                if objetivo == "nacida": return _amaranthus_soja_maiz_largo_nacida()
                elif objetivo == "residual": return _amaranthus_soja_maiz_largo_residual(cultivo)
                else: return _amaranthus_soja_maiz_largo_ambos(cultivo)
            else:
                if objetivo == "nacida": return _amaranthus_soja_maiz_corto_nacida()
                elif objetivo == "residual": return _amaranthus_soja_maiz_corto_residual(cultivo)
                else: return _amaranthus_soja_maiz_corto_ambos(cultivo)
        elif cultivo == "girasol":
            if momento == "largo":
                if objetivo == "nacida": return _amaranthus_girasol_largo_nacida()
                elif objetivo == "residual": return _amaranthus_girasol_largo_residual()
                else: return _amaranthus_girasol_largo_ambos()
            else:
                if objetivo == "nacida": return _amaranthus_girasol_corto_nacida()
                elif objetivo == "residual": return _amaranthus_girasol_corto_residual()
                else: return _amaranthus_girasol_corto_ambos()

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
        [InlineKeyboardButton("🌿 Alfalfa/Pasturas", callback_data="barb_cultivo_alfalfa")],
    ])

def kb_maleza():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌿 Lolium/Raigrás", callback_data="barb_maleza_lolium")],
        [InlineKeyboardButton("🌿 Rama Negra (Conyza)", callback_data="barb_maleza_conyza")],
        [InlineKeyboardButton("🌿 Crucíferas (Brassica/Nabón)", callback_data="barb_maleza_brassica")],
        [InlineKeyboardButton("🌿 Raigrás + 🌿 Crucíferas", callback_data="barb_maleza_doble")],
        [InlineKeyboardButton("🌿 Yuyo Colorado (Amaranthus)", callback_data="barb_maleza_amaranthus")],
        [InlineKeyboardButton("❓ Otra maleza", callback_data="barb_maleza_otra")],
    ])

def kb_brassica_obj():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Eliminar Brassica nacida", callback_data="barb_dobj_b_nacida")],
        [InlineKeyboardButton("🛡️ Residual Brassica", callback_data="barb_dobj_b_residual")],
        [InlineKeyboardButton("🎯+🛡️ Ambos para Brassica", callback_data="barb_dobj_b_ambos")],
    ])

def kb_lolium_obj():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Eliminar Raigrás nacido", callback_data="barb_dobj_l_nacida")],
        [InlineKeyboardButton("🛡️ Residual Raigrás", callback_data="barb_dobj_l_residual")],
        [InlineKeyboardButton("🎯+🛡️ Ambos para Raigrás", callback_data="barb_dobj_l_ambos")],
    ])

def kb_momento():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📅 Barbecho Largo", callback_data="barb_momento_largo"),
        InlineKeyboardButton("📅 Barbecho Intermedio", callback_data="barb_momento_corto"),
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

    # Para trigo/cebada no hay distinción largo/corto
    if cultivo in ("trigo", "cebada") and not momento:
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

    # Detectar consulta PEE guiada
    pee_info = detectar_pee_guiado(user_message)
    if pee_info is not None:
        cultivo = pee_info.get("cultivo")
        maleza = pee_info.get("maleza")
        objetivo = pee_info.get("objetivo")
        cultivo_nombre = {"trigo": "Trigo/Cebada", "soja": "Soja", "maiz": "Maíz", "girasol": "Girasol", "sorgo": "Sorgo"}.get(cultivo, cultivo)
        if cultivo == "trigo":
            kb_maleza = kb_pee_maleza_trigo()
        elif cultivo == "maiz":
            kb_maleza = kb_pee_maleza_maiz()
        elif cultivo == "girasol":
            kb_maleza = kb_pee_maleza_girasol()
        else:
            kb_maleza = kb_pee_maleza_soja()
        # Si tiene todo — respuesta directa
        if maleza and objetivo:
            context.user_data['pee_cultivo'] = cultivo
            context.user_data['pee_maleza'] = maleza
            context.user_data['pee_objetivo'] = objetivo
            await responder_pee_guiado(update.message, context, cultivo, maleza, objetivo, es_callback=False)
            return
        # Sorgo — va directo a objetivo sin preguntar maleza
        if cultivo == "sorgo" and not objetivo:
            context.user_data['pee_cultivo'] = 'sorgo'
            context.user_data['pee_maleza'] = 'general'
            context.user_data['pee_estado'] = 'esperando_objetivo'
            await update.message.reply_text(
                "Antes de responder, repasemos algunos parámetros para darte una recomendación ajustada a tu realidad 🌱\n\n"
                "Cultivo: Sorgo ✅\n\n"
                "¿Cuál es tu objetivo?",
                reply_markup=kb_pee_objetivo()
            )
            return
        # Si falta algo — arrancar flujo guiado
        context.user_data['pee_estado'] = 'esperando_maleza'
        context.user_data['pee_cultivo'] = cultivo
        if maleza:
            context.user_data['pee_maleza'] = maleza
            context.user_data['pee_estado'] = 'esperando_objetivo'
            await update.message.reply_text(
                "Antes de responder, repasemos algunos parámetros para darte una recomendación ajustada a tu realidad 🌱\n\n"
                f"Cultivo: {cultivo_nombre} ✅\n"
                f"Maleza: {maleza.capitalize()} ✅\n\n"
                "¿Cuál es tu objetivo?",
                reply_markup=kb_pee_objetivo()
            )
        else:
            await update.message.reply_text(
                "Antes de responder, repasemos algunos parámetros para darte una recomendación ajustada a tu realidad 🌱\n\n"
                f"Cultivo: {cultivo_nombre} ✅\n\n"
                "¿Qué maleza tenés en el lote?",
                reply_markup=kb_maleza
            )
        return

    # Detectar consulta POE maíz guiada
    poe_maiz_info = detectar_poe_maiz_guiado(user_message)
    if poe_maiz_info is not None:
        biotipo = poe_maiz_info.get("biotipo")
        maleza = poe_maiz_info.get("maleza")
        if biotipo and maleza:
            context.user_data['poe_maiz_biotipo'] = biotipo
            context.user_data['poe_maiz_maleza'] = maleza
            await responder_poe_maiz(update.message, context, biotipo, maleza, es_callback=False)
            return
        context.user_data['poe_maiz_estado'] = 'esperando_biotipo'
        if biotipo:
            context.user_data['poe_maiz_biotipo'] = biotipo
            context.user_data['poe_maiz_estado'] = 'esperando_maleza'
            bname = {"convencional": "Convencional", "rr": "RR", "cl": "CL", "enlist": "Enlist"}.get(biotipo, biotipo)
            await update.message.reply_text(
                f"Cultivo: Maíz ✅\nBiotipo: {bname} ✅\n\n¿Qué maleza tenés en el lote?",
                reply_markup=kb_poe_maiz_maleza()
            )
        else:
            await update.message.reply_text(
                "Antes de responder, repasemos algunos parámetros 🌽\n\n¿Qué biotipo de maíz tenés?",
                reply_markup=kb_poe_maiz_biotipo()
            )
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

    # Detectar cultivo + maleza conocida sin momento — preguntar momento
    cm_info = detectar_cultivo_maleza_sin_momento(user_message)
    if cm_info is not None:
        context.user_data['cm_cultivo'] = cm_info['cultivo']
        context.user_data['cm_maleza'] = cm_info['maleza']
        cultivo_nombre = {"trigo": "Trigo/Cebada", "soja": "Soja", "maiz": "Maíz", "girasol": "Girasol", "sorgo": "Sorgo"}.get(cm_info['cultivo'], cm_info['cultivo'])
        maleza_nombre = cm_info['maleza'].replace("_", " ").capitalize()
        await update.message.reply_text(
            f"Cultivo: {cultivo_nombre} ✅\nMaleza: {maleza_nombre} ✅\n\n¿En qué momento de manejo estás?",
            reply_markup=kb_momento_manejo()
        )
        return

    # Detectar POE sin cultivo — preguntar cultivo con botones
    t_lower = user_message.lower().strip()
    POE_MOMENTOS = ["poe", "post-emergencia", "postemergencia", "post emergencia", "postemer"]
    PEE_MOMENTOS_SOLOS = ["pee", "pre-emergencia", "preemergencia", "pre emergencia"]
    CULTIVOS_KEYS = ["soja", "soya", "maiz", "maíz", "trigo", "cebada", "girasol", "sorgo"]

    # Detectar POE sin cultivo — preguntar cultivo con botones
    if any(kw in t_lower for kw in POE_MOMENTOS) and not any(kw in t_lower for kw in CULTIVOS_KEYS):
        context.user_data['momento_pendiente'] = 'poe'
        await update.message.reply_text(
            "¿POE de qué cultivo?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌱 Soja", callback_data="cultivo_poe_soja")],
                [InlineKeyboardButton("🌽 Maíz", callback_data="cultivo_poe_maiz")],
                [InlineKeyboardButton("🌻 Girasol", callback_data="cultivo_poe_girasol")],
                [InlineKeyboardButton("🌾 Trigo / Cebada", callback_data="cultivo_poe_trigo")],
                [InlineKeyboardButton("🌿 Sorgo", callback_data="cultivo_poe_sorgo")],
                [InlineKeyboardButton("🌿 Alfalfa/Pasturas", callback_data="cultivo_poe_alfalfa")],
                [InlineKeyboardButton("❓ Otro", callback_data="cultivo_poe_otro")],
            ])
        )
        return

    # Detectar PEE sin cultivo — preguntar cultivo con botones
    if any(kw in t_lower for kw in PEE_MOMENTOS_SOLOS) and not any(kw in t_lower for kw in CULTIVOS_KEYS):
        context.user_data['momento_pendiente'] = 'pee'
        await update.message.reply_text(
            "¿PEE de qué cultivo?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌱 Soja", callback_data="cultivo_pee_soja")],
                [InlineKeyboardButton("🌽 Maíz", callback_data="cultivo_pee_maiz")],
                [InlineKeyboardButton("🌻 Girasol", callback_data="cultivo_pee_girasol")],
                [InlineKeyboardButton("🌾 Trigo / Cebada", callback_data="cultivo_pee_trigo")],
                [InlineKeyboardButton("🌿 Sorgo", callback_data="cultivo_pee_sorgo")],
                [InlineKeyboardButton("🌿 Alfalfa/Pasturas", callback_data="cultivo_pee_alfalfa")],
                [InlineKeyboardButton("❓ Otro", callback_data="cultivo_pee_otro")],
            ])
        )
        return

    # Detectar cultivo solo sin momento ni maleza — preguntar momento con botones
    MOMENTOS_KEYS = ["pee", "pre-emergencia", "preemergencia", "poe", "post-emergencia",
                     "postemergencia", "barbecho", "presiembra", "pre-siembra"]
    tiene_momento = any(kw in t_lower for kw in MOMENTOS_KEYS)
    cultivo_detectado = next((v for k, v in CULTIVOS_ALIAS.items() if k in t_lower), None)
    if cultivo_detectado and not tiene_momento and len(t_lower.split()) <= 3:
        cultivo_nombre = {"trigo": "Trigo/Cebada", "cebada": "Trigo/Cebada", "soja": "Soja",
                          "maiz": "Maíz", "girasol": "Girasol", "sorgo": "Sorgo"}.get(cultivo_detectado, cultivo_detectado)
        context.user_data['cultivo_solo'] = cultivo_detectado
        await update.message.reply_text(
            f"Cultivo: {cultivo_nombre} ✅\n\n¿En qué momento de manejo estás?",
            reply_markup=kb_momento_manejo()
        )
        return

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=KNOWLEDGE_BASE,
            messages=[{"role": "user", "content": user_message}]
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

    # Selección de momento (cultivo+maleza detectados sin momento)
    if data in ("momento_barb_largo", "momento_barb_corto", "momento_pee", "momento_poe"):
        cultivo = context.user_data.get('cm_cultivo') or context.user_data.get('cultivo_solo')
        maleza = context.user_data.get('cm_maleza')
        logger.info(f"[CALLBACK] data={data} cultivo={cultivo} maleza={maleza} user_data={dict(context.user_data)}")
        context.user_data.pop('cm_cultivo', None)
        context.user_data.pop('cm_maleza', None)
        context.user_data.pop('cultivo_solo', None)

        if data in ("momento_barb_largo", "momento_barb_corto"):
            momento_barb = "largo" if data == "momento_barb_largo" else "corto"
            context.user_data['barbecho_estado'] = 'esperando_maleza'
            context.user_data['barbecho_momento'] = momento_barb
            if cultivo:
                cultivo_barb = {"soja": "soja", "maiz": "maiz", "girasol": "girasol", "trigo": "trigo"}.get(cultivo, cultivo)
                context.user_data['barbecho_cultivo'] = cultivo_barb
                cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol", "trigo": "Trigo/Cebada"}.get(cultivo_barb, cultivo_barb)
                momento_nombre = "Largo (abril-junio)" if momento_barb == "largo" else "Corto / Presiembra (ago-sep)"
                await query.message.reply_text(
                    f"Cultivo: {cultivo_nombre} ✅\nMomento: Barbecho {momento_nombre} ✅\n\n¿Qué maleza querés controlar?",
                    reply_markup=kb_maleza()
                )
            else:
                context.user_data['barbecho_estado'] = 'esperando_cultivo'
                await query.message.reply_text(
                    "¿Para qué cultivo es el barbecho?",
                    reply_markup=kb_cultivo()
                )
        elif data == "momento_pee":
            # Inyectar cultivo y maleza al flujo PEE
            context.user_data['pee_cultivo'] = cultivo
            if cultivo == "alfalfa":
                await query.message.reply_text(_alfalfa_pee())
                return
            if maleza:
                context.user_data['pee_maleza'] = maleza
                await query.message.reply_text(
                    f"Cultivo: {cultivo} ✅\nMaleza: {maleza} ✅\n\n¿Cuál es el objetivo?",
                    reply_markup=kb_pee_objetivo()
                )
            else:
                kb_maleza_fn = {
                    "trigo": kb_pee_maleza_trigo,
                    "soja": kb_pee_maleza_soja,
                    "maiz": kb_pee_maleza_maiz,
                    "girasol": kb_pee_maleza_girasol,
                }.get(cultivo, kb_pee_maleza_soja)
                await query.message.reply_text(
                    "¿Qué maleza tenés en el lote?",
                    reply_markup=kb_maleza_fn()
                )
        elif data == "momento_poe":
            if cultivo == "alfalfa":
                await query.message.reply_text(
                    "¿En qué etapa está la alfalfa?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌱 En implantación", callback_data="alfalfa_poe_implantacion")],
                        [InlineKeyboardButton("🌿 Establecida (ya pastorea/corta)", callback_data="alfalfa_poe_establecida")],
                    ])
                )
                return
            if cultivo == "maiz":
                context.user_data['poe_maiz_estado'] = 'esperando_biotipo'
                if maleza:
                    context.user_data['poe_maiz_maleza'] = maleza
                await query.message.reply_text(
                    "Antes de responder, repasemos algunos parámetros 🌽\n\n¿Qué biotipo de maíz tenés?",
                    reply_markup=kb_poe_maiz_biotipo()
                )
            else:
                if cultivo and maleza:
                    texto_api = f"herbicidas para {maleza} en {cultivo} en POE post-emergencia"
                elif cultivo:
                    texto_api = f"herbicidas POE post-emergencia en {cultivo}"
                else:
                    await query.message.reply_text("¿POE de qué cultivo?", reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌱 Soja", callback_data="cultivo_poe_soja")],
                        [InlineKeyboardButton("🌽 Maíz", callback_data="cultivo_poe_maiz")],
                        [InlineKeyboardButton("🌻 Girasol", callback_data="cultivo_poe_girasol")],
                        [InlineKeyboardButton("🌾 Trigo / Cebada", callback_data="cultivo_poe_trigo")],
                        [InlineKeyboardButton("🌿 Sorgo", callback_data="cultivo_poe_sorgo")],
                        [InlineKeyboardButton("🌿 Alfalfa/Pasturas", callback_data="cultivo_poe_alfalfa")],
                    ]))
                    return
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=3000,
                    system=KNOWLEDGE_BASE,
                    messages=[{"role": "user", "content": texto_api}]
                )
                await query.message.reply_text(response.content[0].text)
        return

    # Cultivo seleccionado desde "PEE sin cultivo"
    if data.startswith("cultivo_pee_"):
        cultivo_elegido = data.replace("cultivo_pee_", "")
        context.user_data.pop('momento_pendiente', None)
        if cultivo_elegido == "otro":
            await query.message.reply_text(
                "Para cultivos como Colza, Arveja o Camelina escribí tu consulta directamente con cultivo + maleza + PEE."
            )
            return
        if cultivo_elegido == "alfalfa":
            await query.message.reply_text(_alfalfa_pee())
            return
        cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol",
                          "trigo": "Trigo/Cebada", "sorgo": "Sorgo"}.get(cultivo_elegido, cultivo_elegido)
        context.user_data['pee_cultivo'] = cultivo_elegido
        if cultivo_elegido == "trigo":
            kb_maleza_fn = kb_pee_maleza_trigo()
        elif cultivo_elegido == "maiz":
            kb_maleza_fn = kb_pee_maleza_maiz()
        elif cultivo_elegido == "girasol":
            kb_maleza_fn = kb_pee_maleza_girasol()
        elif cultivo_elegido == "sorgo":
            # Sorgo va directo a objetivo
            await query.message.reply_text(
                f"Cultivo: {cultivo_nombre} ✅\n\n¿Cuál es el objetivo?",
                reply_markup=kb_pee_objetivo()
            )
            return
        else:
            kb_maleza_fn = kb_pee_maleza_soja()
        await query.message.reply_text(
            f"Cultivo: {cultivo_nombre} ✅\n\n¿Qué maleza tenés en el lote?",
            reply_markup=kb_maleza_fn
        )
        return

    # Cultivo seleccionado desde "POE sin cultivo"
    if data.startswith("cultivo_poe_"):
        cultivo_elegido = data.replace("cultivo_poe_", "")
        context.user_data.pop('momento_pendiente', None)
        if cultivo_elegido == "otro":
            await query.message.reply_text(
                "Para cultivos como Colza, Arveja o Camelina escribí tu consulta directamente con cultivo + maleza + POE."
            )
            return
        if cultivo_elegido == "alfalfa":
            await query.message.reply_text(
                "¿En qué etapa está la alfalfa?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌱 En implantación", callback_data="alfalfa_poe_implantacion")],
                    [InlineKeyboardButton("🌿 Establecida (ya pastorea/corta)", callback_data="alfalfa_poe_establecida")],
                ])
            )
            return
        if cultivo_elegido == "maiz":
            context.user_data['poe_maiz_estado'] = 'esperando_biotipo'
            await query.message.reply_text(
                "Antes de responder, repasemos algunos parámetros 🌽\n\n¿Qué biotipo de maíz tenés?",
                reply_markup=kb_poe_maiz_biotipo()
            )
        else:
            cultivo_nombre = {"soja": "Soja", "girasol": "Girasol", "trigo": "Trigo/Cebada", "sorgo": "Sorgo"}.get(cultivo_elegido, cultivo_elegido)
            context.user_data['cm_cultivo'] = cultivo_elegido
            await query.message.reply_text(
                f"Cultivo: {cultivo_nombre} ✅\n\n¿Qué maleza querés controlar?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌿 Especificá la maleza escribiéndola", callback_data="poe_maleza_texto")]
                ])
            )
            # Para soja/girasol/trigo/sorgo POE — mandar a la API con cultivo+POE
            texto_api = f"herbicidas POE post-emergencia en {cultivo_elegido}"
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=3000,
                system=KNOWLEDGE_BASE,
                messages=[{"role": "user", "content": texto_api}]
            )
            await query.message.reply_text(response.content[0].text)
        return

    # Flujo PEE guiado — maleza
    if data.startswith("pee_maleza_"):
        maleza = data.replace("pee_maleza_", "")
        cultivo = context.user_data.get('pee_cultivo', 'trigo')
        if maleza == "otra":
            cultivo_nombre = {"trigo": "trigo/cebada", "maiz": "maíz", "girasol": "girasol"}.get(cultivo, "soja")
            context.user_data.clear()
            if cultivo == "trigo":
                orientacion = (
                    "🌱 Si es una GRAMÍNEA — las opciones de Raigrás/Lolium pueden orientarte.\n"
                    "🌱 Si es una LATIFOLIADA — las opciones de Conyza o Crucíferas son un buen punto de partida.\n\n"
                )
            elif cultivo == "maiz":
                orientacion = (
                    "🌱 Si es una GRAMÍNEA — las opciones de Raigrás pueden orientarte, pero recordá\n"
                    "   la restricción crítica de ACCasa en maíz convencional/RR.\n\n"
                )
            elif cultivo == "girasol":
                orientacion = (
                    "🌱 Para latifoliadas en general — las opciones de Maleza General pueden orientarte.\n"
                    "🌱 Recordá que las opciones POE en girasol son muy limitadas — el control preventivo en PEE es clave.\n\n"
                )
            else:
                orientacion = (
                    "🌱 Si es una LATIFOLIADA — las opciones de Yuyo Colorado pueden orientarte como punto de partida.\n\n"
                )
            await query.message.reply_text(
                f"⚠️ No tengo información específica para esa maleza en PEE de {cultivo_nombre} todavía.\n\n"
                f"{orientacion}"
                "Consultá con tu asesor para ajustar al biotipo específico."
            )
            return
        context.user_data['pee_maleza'] = maleza
        context.user_data['pee_estado'] = 'esperando_objetivo'
        maleza_nombre = {
            "raigras": "Raigrás/Lolium", "conyza": "Rama Negra (Conyza)", "cruciferas": "Crucíferas",
            "amaranthus": "Yuyo Colorado (Amaranthus)", "commelina": "Flor de Santa Lucía (Commelina)", "parietaria": "Parietaria", "cebollin": "Cebollín (Cyperus)", "conyza": "Rama Negra (Conyza)", "general": "Maleza General/Latifoliadas"
        }.get(maleza, maleza)
        await query.message.reply_text(
            f"Maleza: {maleza_nombre} ✅\n\n¿Cuál es tu objetivo?",
            reply_markup=kb_pee_objetivo()
        )
        return

    # Flujo PEE guiado — objetivo
    if data.startswith("pee_objetivo_"):
        objetivo = data.replace("pee_objetivo_", "")
        cultivo = context.user_data.get('pee_cultivo', 'trigo')
        maleza = context.user_data.get('pee_maleza', '')
        objetivo_nombre = {"nacida": "Maleza nacida (rescate)", "residual": "Residual", "ambos": "Ambos"}.get(objetivo, objetivo)
        await query.message.reply_text(
            f"Objetivo: {objetivo_nombre} ✅\n\nBuscando recomendación..."
        )
        await responder_pee_guiado(query, context, cultivo, maleza, objetivo, es_callback=True)
        return

    # Flujo POE maíz — biotipo
    if data.startswith("poe_maiz_biotipo_"):
        biotipo = data.replace("poe_maiz_biotipo_", "")
        context.user_data['poe_maiz_biotipo'] = biotipo
        context.user_data['poe_maiz_estado'] = 'esperando_maleza'
        bname = {"convencional": "Convencional", "rr": "RR", "cl": "CL", "enlist": "Enlist"}.get(biotipo, biotipo)
        await query.message.reply_text(
            f"Biotipo: {bname} ✅\n\n¿Qué maleza tenés en el lote?",
            reply_markup=kb_poe_maiz_maleza()
        )
        return

    # Flujo POE maíz — maleza
    if data.startswith("poe_maiz_maleza_"):
        maleza = data.replace("poe_maiz_maleza_", "")
        biotipo = context.user_data.get('poe_maiz_biotipo', 'convencional')
        bname = {"convencional": "Convencional", "rr": "RR", "cl": "CL", "enlist": "Enlist"}.get(biotipo, biotipo)
        if maleza == "otra":
            context.user_data.clear()
            await query.message.reply_text(
                f"⚠️ No tengo información específica para esa maleza en POE de maíz {bname} todavía.\n\n"
                "🌱 Si es una GRAMÍNEA — recordá que ACCasa es fitotóxico en convencional y RR.\n"
                "🌱 Si es una LATIFOLIADA — los HPPD + Atrazina son el punto de partida en convencional/RR.\n\n"
                "Consultá con tu asesor para ajustar al caso específico."
            )
            return
        maleza_nombre = {
            "raigras": "Raigrás/Lolium", "amaranthus": "Yuyo Colorado (Amaranthus)",
            "cruciferas": "Crucíferas", "cebollin": "Cebollín (Cyperus)", "conyza": "Rama Negra (Conyza)"
        }.get(maleza, maleza)
        await query.message.reply_text(
            f"Biotipo: {bname} ✅\nMaleza: {maleza_nombre} ✅\n\nBuscando recomendación..."
        )
        await responder_poe_maiz(query, context, biotipo, maleza, es_callback=True)
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

        if cultivo == "alfalfa":
            context.user_data.clear()
            await query.edit_message_text("Cultivo: Alfalfa/Pasturas ✅")
            await query.message.reply_text(_alfalfa_barbecho())
            return

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
    if data == "alfalfa_poe_implantacion":
        await query.message.reply_text(_alfalfa_poe_implantacion())
        return

    if data == "alfalfa_poe_establecida":
        await query.message.reply_text(_alfalfa_poe_establecida())
        return

    if data.startswith("barb_maleza_"):
        maleza = data.replace("barb_maleza_", "")
        context.user_data['barbecho_maleza'] = maleza
        cultivo = context.user_data.get('barbecho_cultivo', '')

        if maleza == "otra":
            context.user_data['barbecho_estado'] = 'completo'
            await query.edit_message_text("Maleza: Otra ✅")
            await responder_barbecho_completo(query, context, cultivo, "otra", None, None)
            return

        if maleza == "doble":
            if cultivo != "trigo":
                await query.edit_message_text(
                    "Cultivo: " + {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol"}.get(cultivo, cultivo) +
                    " ✅\n\nRaigrás + Crucíferas simultáneas — por ahora solo disponible para Trigo/Cebada.\n"
                    "Podés consultar cada maleza por separado usando el flujo anterior."
                )
                context.user_data.clear()
                return
            context.user_data['barbecho_estado'] = 'esperando_brassica_obj'
            await query.edit_message_text(
                "Cultivo: Trigo/Cebada ✅\nMalezas: Raigrás + Crucíferas ✅\n\n¿Qué necesitás para las Crucíferas/Nabo?",
                reply_markup=kb_brassica_obj()
            )
            return

        maleza_nombre = {
            "lolium": "Lolium/Raigrás",
            "conyza": "Rama Negra (Conyza)",
            "brassica": "Crucíferas (Brassica/Nabón)",
            "amaranthus": "Yuyo Colorado (Amaranthus)"
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
            cultivo_nombre = {"soja": "Soja", "maiz": "Maíz", "girasol": "Girasol"}.get(cultivo, cultivo)
            momento_ya = context.user_data.get('barbecho_momento')
            if momento_ya:
                context.user_data['barbecho_estado'] = 'esperando_objetivo'
                momento_nombre = "Largo (abril-junio)" if momento_ya == "largo" else "Corto / Presiembra (ago-sep)"
                await query.edit_message_text(
                    f"Cultivo: {cultivo_nombre} ✅\nMaleza: {maleza_nombre} ✅\nMomento: Barbecho {momento_nombre} ✅\n\n¿Qué objetivo buscás?",
                    reply_markup=kb_objetivo()
                )
            else:
                context.user_data['barbecho_estado'] = 'esperando_momento'
                await query.edit_message_text(
                    f"Cultivo: {cultivo_nombre} ✅\nMaleza: {maleza_nombre} ✅\n\n¿Cuándo pensás aplicar?\n📅 Barbecho Largo: abril-junio\n📅 Barbecho Corto/Presiembra: agosto-septiembre",
                    reply_markup=kb_momento()
                )
        return

    # Flujo barbecho — doble maleza: objetivo Brassica
    if data.startswith("barb_dobj_b_"):
        b_obj = data.replace("barb_dobj_b_", "")
        context.user_data['barbecho_doble_b_obj'] = b_obj
        context.user_data['barbecho_estado'] = 'esperando_lolium_obj'
        b_nombre = {"nacida": "Eliminar nacida", "residual": "Residual", "ambos": "Ambos"}.get(b_obj, b_obj)
        await query.edit_message_text(
            f"Cultivo: Trigo/Cebada ✅\nMalezas: Raigrás + Crucíferas ✅\nCrucíferas: {b_nombre} ✅\n\n¿Y para el Raigrás?",
            reply_markup=kb_lolium_obj()
        )
        return

    # Flujo barbecho — doble maleza: objetivo Lolium → respuesta final
    if data.startswith("barb_dobj_l_"):
        l_obj = data.replace("barb_dobj_l_", "")
        b_obj = context.user_data.get('barbecho_doble_b_obj', 'nacida')
        context.user_data['barbecho_estado'] = 'completo'
        b_nombre = {"nacida": "Eliminar nacida", "residual": "Residual", "ambos": "Ambos"}.get(b_obj, b_obj)
        l_nombre = {"nacida": "Eliminar nacido", "residual": "Residual", "ambos": "Ambos"}.get(l_obj, l_obj)
        await query.edit_message_text(
            f"Cultivo: Trigo/Cebada ✅\nMalezas: Raigrás + Crucíferas ✅\n"
            f"Crucíferas: {b_nombre} ✅\nRaigrás: {l_nombre} ✅\n\nBuscando estrategia..."
        )
        respuesta = get_doble_trigo_respuesta(b_obj, l_obj)
        if respuesta:
            await send_long_message(context.bot, query.message.chat_id, respuesta)
        else:
            await send_long_message(context.bot, query.message.chat_id,
                "No tengo una respuesta específica para esa combinación. Consultá cada maleza por separado.")
        context.user_data.clear()
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
        momento_nombre = {"largo": "Largo (abril-junio)", "corto": "Intermedio (agosto-septiembre)"}.get(momento, momento)

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
        momento_nombre = {"largo": "Largo (abril-junio)", "corto": "Intermedio (agosto-septiembre)", "presiembra": "Presiembra"}.get(momento, momento)
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
