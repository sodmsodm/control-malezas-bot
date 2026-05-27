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
usage_stats = {}  # {user_id: {"first_name": str, "count": int, "queries": [str]}}

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

KNOWLEDGE_BASE += """
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
"""

KNOWLEDGE_BASE += """
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
"""

KNOWLEDGE_BASE += """
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
"""

KNOWLEDGE_BASE += """
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

# --- COMANDO /stats (solo admin) ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Acceso restringido.")
        return
    if not user_stats:
        await update.message.reply_text("📊 Sin consultas registradas todavía.")
        return
    lines = ["📊 <b>Consultas por usuario:</b>\n"]
    for uid, data in sorted(user_stats.items(), key=lambda x: x[1]["mensajes"], reverse=True):
        nombre = data.get("nombre", "Sin nombre")
        username = f"@{data['username']}" if data.get("username") else "sin @"
        mensajes = data["mensajes"]
        lines.append(f"👤 {nombre} ({username}) — {mensajes} consulta{'s' if mensajes != 1 else ''}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

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
                text=f"📨 <b>{nombre}</b> ({username}) — consulta #{total}:\n\n{user_message}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"No se pudo notificar al admin: {e}")

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
            await update.message.reply_text(main_message)
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
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
