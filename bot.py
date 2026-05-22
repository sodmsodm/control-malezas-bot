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

Respondés en español, de forma clara, técnica y organizada. Usás tablas cuando es útil.
Siempre aclarás el momento de aplicación (barbecho, PEE, PSI-PEE, POE) y el biotipo de cultivo cuando es relevante.

=== SOJA ===

--- SOJA: MALEZA GENERAL (No GMO) ---
BARBECHO INTERMEDIO (45-60 DAS):
- Flumioxazin 48% (150cc)
- Piroxasulfone 85% (160-200g)
- Diflufenicán 50% (0,3l) hasta 15 DAS
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Amicarbazone 70% (0,4-0,5kg) hasta 45 DAS
- Terbutilazina 75% (1kg) hasta 45 DAS
- Metribuzin 48% (1l)
- Terbutilazina 50% / Flumioxazin 3,8% (1,25) hasta 30 DAS
- Sulfometurón 15% / Clorimurón 20% (0,1kg) SOJAS STS

PEE / PSI-PEE:
- Sulfentrazone 50% (0,4-0,5l) / S-metolacloro 96% (1,1-1,3l)
- Sulfentrazone 10% / S-metolacloro 60% (2,5l)
- Sulfentrazone 50% (0,5l) / Piroxasulfone 48% (0,355l)
- Sulfentrazone 50% (0,5l) / Imazetapir 10% (0,8-1l)
- Sulfentrazone 50% (0,5l) / Diclosulam 84% (0,03kg)
- Sulfentrazone 50% (0,4-0,5l) / Metribuzin 48% (0,8-1l)
- Sulfentrazone 50% (0,4-0,5l) / Clomazone 36% (1,75-2l)
- Flumioxazin 15% / Piroxasulfone 34,5% (0,5l) 7 DAS
- Flumioxazin 4,2% / S-metolacloro 84% (1,75l) 7 DAS
- Flumioxazin 5% / S-metolacloro 57,6% / Imazetapir 5% (1,5l) 7 DAS
- Flumioxazin 14,5% / Diclosulam 6,5% / Imazetapir 20% (0,5l) 7 DAS
- Flumioxazin 28,8% / Diclosulam 8,4% (0,25l) / S-metolacloro 96% (1,1-1,3l) 7 DAS
- Flumioxazin 4,2% / Acetoclor 90% (1,5l) 7 DAS
- Sulfentrazone 50% (0,4l) / S-metolacloro 96% (1,1-1,3l)
- Sulfometurón 30,7% (0,25l) 7 DAS SOJAS STS
- Sulfometurón 15% / Clorimurón 20% (0,1kg) / Sulfentrazone 50% (0,5l) SOJAS STS
- Metribuzin 14,9% / S-metolacloro 62,8% (2,5l)
- Fomesafén 50% (0,4-0,5l) / Metribuzin 48% (0,8-1l) / Acetoclor 90% (1,5l)
- Trifludimoxazin / Saflufenacil (0,1-0,2l) / S-metolacloro 96% (1,1-1,3l)

POST-EMERGENCIA V4-V6:
- Fomesafén 25% (1-1,5l)
- Lactofén 24% (0,6-0,8l)
- Cletodim 24% (0,7-1l); 36% (0,5-0,7 l/ha)
- Piroxasulfone 85% (0,16-0,2 kg/ha) hasta V4 o V8
- Fomesafén 25% (1-1,5l) / Benazolín 50% (0,8l)
- Fomesafén 25% (1-1,5l) / 2,4DB 97% e.a. (0,04l)
- Fomesafén 11,95% / S-metolacloro 51,8% (1,5-2,5l)
- Fomesafén 25% (1-1,5l) / Benazolín 50% (0,015kg)
- Fomesafén 25% (1-1,5l) / Clorimurón 25% (0,03kg)
- Clorimurón 25% (0,04-0,05kg)
- Cloransulam 84% (0,04-0,05kg)
- Imazetapir 10% (0,5-0,8l)
- 2,4DB 97% e.a. (0,04l) / Bentazón 60% (0,8-1l)
- Cletodim 24% (0,7-1l); 36% (0,5-0,7 l/ha)
- Benazolín 50% (0,6l) / Clorimurón 25% (0,03g)
- Benazolín 50% (0,6l) / Diclosulam 84% (0,015g)

--- SOJA: COMMELINA ERECTA ---
POE DE LA MALEZA / PSI CULTIVO:
- Glifosato 1260 g.e.a. / 2,4D (1-1,5l) / Saflufenacil 70% (40g) / DG Paraquat 27,6% (2-3l)
- Glifosato / 2,4D / Carfentrazone 40% (70-80cc) / DG Paraquat
- Glifosato / 2,4D / Epirefenacil 5,5% (600cc) / DG Paraquat
- Glifosato / 2,4D / Flumioxazin 48% (150cc) / DG Paraquat
- Glifosato / 2,4D / Iodosulfurón / Imazetapir (30-45g) 30-45 DAS / DG Paraquat
- Glifosato / 2,4D / Trifludimoxazin / Saflufenacil (0,1-0,2l) / DG Paraquat
- Glufosinato de amonio 28% (2,5l) / 2,4D / DG Paraquat
- Glufosinato de amonio / 2,4D / Metribuzin 48% (0,8-1l) / DG Paraquat
- Glufosinato de amonio / 2,4D / Amicarbazone 70% (0,4g) / DG Paraquat hasta 45 DAS
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
POE MALEZA / PSI CULTIVO:
- Glifosato / 2,4D (carencia v.s.f.)
- Glifosato / MCPA 28% (1,5-2,5l)
- Glifosato / 2,4D + Dicamba 25 DAS
- Glifosato / 2,4D o MCPA / Saflufenacil 70% (35-40g)
- Glifosato / 2,4D o MCPA / Carfentrazone 40% (70-80cc)
- Glifosato / 2,4D o MCPA / Piraflufén 2,5% (200cc)
- Glifosato / 2,4D o MCPA / Epirefenacil 5,5% (600cc)
- Glifosato / 2,4D o MCPA / Trifludimoxazin / Saflufenacil (0,1-0,15l)
- Glufosinato de amonio 28% (1-2,5l) / 2,4D
- Glufosinato de amonio / 2,4D / Saflufenacil
- Glufosinato de amonio / 2,4D / Carfentrazone
- Glifosato / 2,4D // DG Paraquat 27,6% (1,5-2,5l)
- Glifosato / 2,4D // DG Glufosinato de amonio

MALEZA PPE BARBECHO LARGO:
- Atrazina 90% (1kg) hasta 30 DAS
- Amicarbazone 70% (0,4-0,5kg) hasta 45 DAS
- Terbutilazina 75% (0,8-1kg) desde 45-60 DAS desde primera lluvia
- Flurocloridona 25% (1,5l) hasta 45 DAS
- Biciclopirona 20% (0,5l) / Atrazina 90% (0,5kg) 120 DAS
- Diflufenicán 50% (0,3l)
- Flumioxazin 48% (0,1-0,15l)
- Terbutilazina 50% / Flumioxazin 3,8% (1,15-1,25l) 30 DAS

PEE / PSI-PEE:
- Metribuzin 48% (0,8-1kg)
- Sulfentrazone 50% (0,4-0,5l)
- Flumioxazin 48% (0,1-0,15l) 7 DAS
- Piroxasulfone 85% (160-200g)
- Diflufenicán 50% (0,3l) 15 DAS
- Fomesafén 11,9% / S-metolacloro 51,8% (2,5l)
- Flumioxazin 15% / Piroxasulfone 34,5% (0,3l/0,1l) 7 DAS
- Sulfentrazone 50% / Diflufenicán 50% (0,3l/0,3l) 15 DAS
- Trifludimoxazin 12,5% / Saflufenacil 25% (0,1-0,2l) 7 DAS

POST-EMERGENCIA CULTIVO (Soja Resistente Glifosato o No GMO):
- Fomesafén 25% (1-1,5l)
- Acifluorfén 24% (1-1,5l)
- Lactofén 24% (0,6-0,8l)
- Fomesafén 25% (1-1,5l) / Benazolín 50% (0,6l)
- Bentazón 60% (1,5l)
SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) / 2,4D 30% e.a. (1,5-2l) hasta V4-V6

--- SOJA: PARIETARIA ---
BARBECHO LARGO:
- Atrazina 90% (1-1,5kg) PEE-POST MALEZA hasta 60 DAS
- Amicarbazone 70% (0,4-0,5kg) hasta 45 DAS PEE-POST MALEZA
- Terbutilazina 75% (0,8-1kg) hasta 45 DAS PEE-POST MALEZA
- Metsulfurón 60% (6-8g) hasta 60 DAS PEE MALEZA
- Metsulfurón / Clorsulfurón (12-15g) SOJAS STS o hasta 150 DAS PEE MALEZA
- Biciclopirona 20% (0,5l) / Atrazina 90% (0,5kg) 120 DAS PEE-POST MALEZA
- Flumioxazin 48% (0,1-0,15l) PEE-POST MALEZA
- Terbutilazina 75% (1kg) / Flumioxazin 48% (0,12l) PEE-POST MALEZA

PEE / PSI-PEE:
- Atrazina 90% (0,5kg) PEE-POST MALEZA hasta 30 DAS
- Metribuzin 48% (0,8-1l) PEE-POST MALEZA
- Prometrina 48% (1,5-2l) PEE-POST MALEZA
- Paraquat 27,6% (1,5-2,5l) / Metribuzin 48% (0,8-1l) PEE-POST MALEZA
- Paraquat 27,6% (1,5-2,5l) / Atrazina 90% (0,5kg) hasta 30 DAS
- Paraquat 27,6% (1,5-2,5l) / Prometrina 48% (1,5-2l)
- Paraquat 27,6% (1,5-2,5l) / Flumioxazin 48% (0,1-0,15l) 7 DAS
- Paraquat 27,6% (1,5-2,5l) / Trifludimoxazin / Saflufenacil (0,1-0,2l) PEE-POST 7 DAS
- Trifludimoxazin / Saflufenacil (0,1-0,2l) PEE-POST MALEZA 7 DAS
- Glifosato 1260 g.e.a. / Epirefenacil 5,5% (600cc) POST MALEZA

POST-EMERGENCIA CULTIVO: Sin opciones efectivas
- Dosis glifosato > 1360 g.e.a. + sulfato de amonio + aceite, controles hasta 60%

--- SOJA: AMARANTHUS SPP. (Yuyo Colorado) ---
POE MALEZA / PSI CULTIVO:
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Epirefenacil 5,5% (600cc)
- Trifludimoxazin / Saflufenacil (0,1-0,2l) Acción POE y PEE MALEZA
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l)
- 2,4D / Saflufenacil 70% (40g)
- 2,4D / Carfentrazone 40% (70-80cc)
- 2,4D / Epirefenacil 5,5% (600cc)
- Glufosinato de amonio / 2,4D / Saflufenacil / Flumioxazin / Carfentrazone / Epirefenacil

MALEZA PEE BARBECHO INTERMEDIO (45-60 DAS):
- Flumioxazin 48% (150cc)
- Piroxasulfone 85% (160-200g)
- Diflufenicán 50% (0,3l) hasta 15 DAS
- Atrazina 90% (1-1,5kg) hasta 40 DAS
- Amicarbazone 70% (0,4-0,5kg) hasta 45 DAS
- Terbutilazina 75% (1kg) hasta 45 DAS
- Metribuzin 48% (1l)
- Terbutilazina / Flumioxazin (1,25) hasta 45 DAS

PEE / PSI-PEE:
- Sulfentrazone 50% (0,4-0,5l) / S-metolacloro 96% (1,1-1,3l)
- Metribuzin 10% / S-metolacloro 60% (2,5l)
- Sulfentrazone / Piroxasulfone 48% (0,355l)
- Flumioxazin 15% / Piroxasulfone 34,5% (0,5l/0,1l) 7 DAS
- Flumioxazin 4,2% / S-metolacloro 84% (1,75l) 7 DAS
- Flumioxazin 4,2% / Acetoclor 90% (1,5l) 7 DAS
- Fomesafén 11,9% / S-metolacloro 51,8% (2,5l)
- Sulfentrazone 50% (0,4l) / S-metolacloro 96% (1,1-1,3l)
- Sulfentrazone 50% (0,4-0,5l) / Metribuzin 48% (0,8-1l) / Acetoclor 90% (1,5l)
- Trifludimoxazin / Saflufenacil / S-metolacloro 96% (1,1-1,3l)

POST-EMERGENCIA (Sojas Resistentes Glifosato):
- Fomesafén 25% (1-1,5l)
- Lactofén 24% (0,6-0,8l)
- Benazolín 50% (0,6-1l)
- Fomesafén 25% / Benazolín 50% (0,6l)
- Fomesafén 11,9% / S-metolacloro 51,8% (1,5-2l)
SOJAS ENLIST:
- Glufosinato de amonio 28% (2-3l) hasta V4-V6
- 2,4D 30% e.a. (1,5-2l) hasta R2
- Glufosinato de amonio 28% (2-3l) / 2,4D 30% e.a. (1,5-2l) hasta V4-V6

=== MAÍZ ===

--- MAÍZ: AMARANTHUS SPP. ---
POE MALEZA / PSI CULTIVO:
- 2,4D (1-1,5l formulación éster ethyl hexyl)
- Picloram (0,1-0,15l)
- Epirefenacil 5,5% (600cc)
- Trifludimoxazin / Saflufenacil (0,15-0,2l) Acción POE y PEE MALEZA 7 DAS
- Glufosinato de amonio 28% (2,5l)
- Paraquat 27,6% (1,5-2,5l)
- 2,4D / Carfentrazone 40% (70-80cc)
- 2,4D / Epirefenacil / Saflufenacil / Carfentrazone / Flumioxazin / Trifludimoxazin

PEE / PSI-PEE:
- Atrazina 90% (1-2kg) / S-metolacloro 96% (1,1-1,3l)
- Atrazina 90% (1-2kg) / Biciclopirona 20% (0,8-1l)
- Biciclopirona 20% (0,8-1l) / S-metolacloro 96% (1,1-1,3l)
- Biciclopirona 20% (0,8-1l) / Piroxasulfone 85% (0,2kg)
- Amicarbazone 70% (0,4-0,5kg) / S-metolacloro
- Terbutilazina 75% (0,8-1kg) / Piroxasulfone 85%
- Terbutilazina 50% (0,8-1kg) / S-metolacloro 96% (1,1-1,3l)
- Mesotrione 48% (0,3l) / Piroxasulfone
- Trifudimoxazin 8,1% (1,77-2,2l) / S-metolacloro 96% (1,1-1,3l)
- Flumioxazin 4,2% / Acetoclor 90% (1,5l)
- Isoxaflutole / Thiencarbazone (0,3-0,4l) / S-metolacloro / Atrazina

POST-EMERGENCIA V2-V8:
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
Acción POE maleza / Cultivo PSI:
- 2,4D (3-5 DAS) Hormonal
- 2,4D sal colina 66,9% (1,5-2,5l) Maíz ENLIST
- Dicamba 57,7% (0,15-0,2l) Hormonal
- Picloram 27,7% (0,1-0,15l)
- Paraquat 27,6% (1-3,5l) Fot.I
- Saflufenacil 70% (35g) PPO
- Carfentrazone 40% (50-75cc) PPO
- Piraflufén etil 2,5% (150-200cc) PPO
- Oxifluorfén 24% (0,25-0,3l) PPO
- Glifosato (dosis v.s.f.) EPSPS
- Glufosinato de amonio 28% (1,5-3l)
- Paraquat/diurón (1,5-2,5l)
- Fluroxipyr/halauxifén (400-500cc)

Acción PEE residual / Cultivo PSI:
- Atrazina 90% (1,8-2,2kg) Gesaprim Fot.II
- Terbutilazina 75% (1,3-1,5kg) Terbine Fot.II
- Amicarbazone 70% (0,4-0,7) Dinamic Fot.II
- Linurón 50% (2-3l) Fot.II
- S-metolacloro 96% (0,8-1,6l) Dual Gold
- Acetoclor 90% (2-3l) Harness
- Piroxazulfone 85% (0,16-0,2kg) Yamato 15 DAS
- Dimetenamida 90% (1,2-1,8l) Inh.Div.Cel.
- Diflufenicán 50% (0,2-0,3l)
- Biciclopirona 20% (0,75-1l) Acuron Uno
- Flurocloridona 25% (0,75-1,5l) Rainbow
- Piroxasulfone/saflufenacil (Zidua Pack) También POE maleza
- Piroxasulfone/flumioxazin (Fierce 10-15 DAS)
- Atrazina/s-metolacloro (BicepPack Gold)
- Isoxaflutole/thiencarbazone (ALS) Adengo

Acción POE maleza / Cultivo POE (V2-V8): Malezas <5cm, evitar estrés:
- Atrazina 90% (1,5-2kg) Gesaprim hasta V6
- Bentazón 60% (1,2-1,6l) V2-V8 (cotiledonar)
- Metribuzin 70% (210-270g) Tribune hasta V2-V8
- Linurón 50% (2-2,5l) tratamientos en bandas
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
- Pendimetalín 33% (2,5-4l) V3-V4 Maleza no emergida

=== GIRASOL ===

--- GIRASOL: MALEZA GENERAL ---
POE MALEZA / PSI-PEE:
- 2,4D (15-20 DAS) Formulaciones éster ethyl o mictoemulsión
- Dicamba (30 DAS)
- Fluroxipir (1 DAS)
- Halauxifén (1 DAS) 120cc
- Paraquat 27,6% (1-3,5l)
- Carfentrazone 40% (50-75cc) Shark
- Piraflufén etil 2,5% (80-200cc) Stagger
- Oxifluorfén 24% (0,25-0,3l) Galigan
- Glifosato (dosis v.s.f.)
- Glufosinato de amonio 28% (1-3l) Lifeline
- Paraquat/diurón (1,5-2,5l) Cerillo
- Fluroxipyr/halauxifén (400-500cc) Pixxaro

PEE / PSI-PEE:
- Sulfentrazone 50% (300-400cc) Capaz
- Flumioxazin 48% (50-100cc) Sumisoya (20-30 DAS)
- Prometrina 50% (1-2l) Gesagard
- S-metolacloro 96% (0,8-1l) Dual Gold
- Acetoclor 90% (2-3l) Harness
- Trifluralina 60% (1-2l) Adama Essentials
- Piroxasulfone 85% (160-200g) Yamato (sin registro)
- Pendimetalín 45,5% (2-3,5l) Satellite (sin registro)
- Diflufenicán 50% (0,3l) Brodal
- Flurocloridona 25% (2-4l) Rainbow
- Imazapyr 80% (100g) Clearsol (Girasoles Clearsol)
- Múltiples mezclas: Sulfentrazone/S-metolacloro, Flurocloridona/S-metolacloro, Diflufenicán/Acetoclor, Prometrina/Acetoclor, etc.
- Imazapyr 1,5%/Imazamox 3,3% (1,5-2l) Clearsol Plus II

POE CULTIVO:
- Graminicidas (DIMs, FOPs): Cletodim, Haloxyfop-R-metil, Propaquizafop, Quizalofop-p-etil
- Aclonifén 60% (1-1,5l) Prodigio
- Benazolín 50% (0,3l) Dasen
- Imazapyr 80% (Clearsol) Acción POE-PEE maleza
- Imazapyr/Imazamox (Clearsol Plus II)

⚠️ NO USAR en girasol: saflufenacil, fomesafén, biciclopirona, topramezone, diclosulam, sulfonilureas

=== TRIGO ===

--- TRIGO: CONYZA SPP. ---
POE MALEZA / PSI CULTIVO:
- Glifosato / 2,4D (v.s.f.)
- Glifosato / Dicamba 57,8% (0,1-0,2l)
- Glifosato / 2,4D + Dicamba
- Glifosato / 2,4D o MCPA / Saflufenacil 70% (35-40g)
- Glifosato / 2,4D o MCPA / Carfentrazone 40% (70-80cc)
- Glifosato / 2,4D o MCPA / Piraflufén 2,5% (200cc)
- Glifosato / 2,4D o MCPA / Epirefenacil 5,5% (600cc)
- Glifosato / 2,4D o MCPA / Trifludimoxazin / Saflufenacil (0,1-0,15l)
- Glufosinato / 2,4D / Saflufenacil / Carfentrazone
- Glifosato / 2,4D // DG Paraquat 27,6% (1,5-2,5l)
- Glifosato / 2,4D // DG Glufosinato de amonio

PEE MALEZA / PSI CULTIVO:
- Metsulfurón 60% (8-10g)
- Metsulfurón/Clorsulfurón (12-15g)
- Flumioxazin 48% (0,15l) 10 DAS
- Terbutrina 50% (1,2l)
- Terbutilazina 75% (1kg)
- Amicarbazone (sin registro)
- Terbutilazina 50% / Flumioxazin 3,8% (1,5l) 15 DAS
- Trifludimoxazin / Saflufenacil (0,1-0,15l)

POST-EMERGENCIA CULTIVO (Z2.1-Z3.0):
- Metsulfurón 60% (5-6g) / Dicamba 57,8% (0,1-0,15l)
- Metsulfurón / Clorsulfurón (10-12g) / Dicamba 57,8% (0,4l)
- Metsulfurón / Clorsulfurón (10-12g) / 2,4D 64,3% e.a. (0,4l)
- 2,4D 64,3% e.a. (0,4l) / Dicamba 57,8% (0,1-0,15l)
- 2,4D 64,3% e.a. (0,4l) / Picloram 24% (0,1-0,12l)
- 2,4D 64,3% e.a. (0,4l) / Fluroxipir 48% (0,2-0,4l)
- 2,4D 64,3% e.a. (0,4l) / Carfentrazone 40% (0,04l)
- 2,4D 64,3% e.a. (0,4l) / Terbuttrina 50% (0,8-1l)
- 2,4D 64,3% e.a. (0,4l) / Saflufenacil 70% (25g)
- 2,4D 64,3% e.a. (0,4l) / Metribuzin 48% (0,4l)
- 2,4D 64,3% e.a. (0,4l) / Piraflufén 2,5% (0,08l)
- Clopyralid / MCPA (1,25-1,35l)
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / 2,4D 64,3% e.a. (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Metribuzin 48% (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) // DG Glufosinato de amonio 28% (2-3l) Trigos HB4

⚠️ CONSIDERACIONES: Evitar repetir mecanismos de acción. Usar coadyuvantes. Control POE con malezas pequeñas. Evitar aplicaciones con estrés por frío o falta de agua.

--- TRIGO: CRUCIFERAS ---
POE MALEZA / PSI CULTIVO:
- Glifosato / 2,4D (v.s.f.)
- Glifosato / MCPA 28% (1,5-2,5l)
- Glifosato / 2,4D + Dicamba
- Glifosato / 2,4D o MCPA / Saflufenacil 70% (35-40g)
- Glifosato / 2,4D o MCPA / Carfentrazone 40% (70-80cc)
- Glifosato / 2,4D o MCPA / Piraflufén 2,5% (200cc)
- Glifosato / 2,4D o MCPA / Tiafenacil 70% (35-50g)
- Glifosato / 2,4D o MCPA / Trifludimoxazin / Saflufenacil (0,1-0,15l)
- Glufosinato de amonio 28% (1-2,5l) / 2,4D
- Glifosato / 2,4D // DG Paraquat 27,6% (1,5-2,5l)

PEE MALEZA / PSI CULTIVO:
- Flurocloridona 25% (1,5l)
- Diflufenicán 50% (0,3l)
- Flumioxazin 48% (0,12l) 10 DAS
- Piroxasulfone 85% (0,12kg)
- Flurocloridona 25% (1,5l) / Piroxasulfone 48% (0,21l) 15 DAS
- Terbutrina 50% (1,2l)
- Terbutilazina 75% (1kg)
- Amicarbazone (sin registro)
- Trifludimoxazin / Saflufenacil (0,1-0,15l)
- Diflufenicán / Aclonifén / Fluferacet (2-2,25l)

POST-EMERGENCIA CULTIVO (Z2.1-Z3.0):
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Bromoxinil 34,6% (0,8-1l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Metribuzin 48% (0,4l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Terbutrina 50% (0,8-1l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Diflufenicán 50% (0,15l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Bentazón 60%
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Carfentrazone 40% (0,04l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Piraflufén 2,5% (0,08l)
- 2,4D 64,3% e.a. (0,4l) o MCPA 75% (0,8l) / Saflufenacil 70% (25g)
- Bromoxinil 34,6% (0,8-1l) / Flurocloridona 25% (0,5l)
- Bromoxinil 34,6% (0,8-1l) / Diflufenicán 50% (0,15l)
- Bromoxinil 34,6% (0,8-1l) / Metribuzin 48% (0,4l)
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / 2,4D 64,3% e.a. (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Metribuzin 48% (0,4l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) / Fluorocloridona 25% (0,5l) Trigos HB4
- Glufosinato de amonio 28% (2-3l) // DG Glufosinato de amonio 28% (2-3l) Trigos HB4

--- TRIGO: RAIGRAS ---
POE MALEZA / PSI CULTIVO:
- Paraquat 27,6% (1,5-2,5l)
- Glufosinato de amonio 28% (1-2,5l)
- Cletodim 24% (0,7-1l); 36% (0,5-0,7 l/ha)
- Haloxyfop 54% (0,25-0,35l)
- Glifosato / Cletodim / Epirefenacil / Terbutilazina+Flumioxazin
- Paraquat / Cletodim / Glifosato
- DG Paraquat / Glufosinato

PEE MALEZA / PSI CULTIVO:
- Piroxasulfone 48% (0,18-0,21l)
- Pendimetalín 45,6% (2,5-3,5l)
- Flumioxazin 48% (0,15l) 10 DAS
- Terbutrina 50% (1,2l)
- Terbutilazina 75% (1kg)
- Terbutilazina 50% / Flumioxazin 3,8% (1,5l) 15 DAS
- Bidozone 40% (1,2-1,5l) 15 DAS
- Flumioxazin 48% (0,12l) / Piroxasulfone 48% (0,21l) 10 DAS
- Diflufenicán / Aclonifén / Fluferacet (2-2,25l)
- Imazapyc / Xmazapy (0,2-0,3l) Trigos CL

POST-EMERGENCIA CULTIVO (Z2.3-Z3.1):
- Pinoxaden 5% (0,6-0,8l)
- Clodinafop 24% (0,2l)
- Piroxulam 21,5% (84gr)
- Iodosulfurón/Mesosulfurón (0,2-0,3l)
- Flucarbazone (80-100gr)
- Imazamox 70-100g Trigos CL
- Imazapyc/Imazapy (0,2-0,3l) Trigos CL
- Glufosinato de amonio 28% (2-3l) Trigos HB4
- Glufosinato de amonio 28% / Pinoxaden 5% (0,6-0,8l) Trigos HB4

⚠️ CONSIDERACIONES: Graminicidas (cletodim, haloxyfop, quizalofop) 25 DAS. Paraquat solo maleza hasta 4 hojas. Glufosinato de amonio solo malezas hasta 4 hojas.

=== SORGO ===

--- SORGO: LATIFOLIADAS/GRAMÍNEAS ---
POE MALEZA / PSI CULTIVO:
- Glifosato
- 2,4D (carencia v.s.f.) / Picloram / Fluroxipir / Clopyralid
- Paraquat 27,6% (1,5-2,5l)
- Glufosinato de amonio 28% (1-2,5l)
- Cletodim 24% (0,7-1l); 36% (0,5-0,7 l/ha) 20 DAS
- Haloxyfop 54% (0,25-0,35l) 20 DAS
- Saflufenacil 70% (35-40g)
- Epirefenacil 5,5% (0,6l)
- Carfentrazone 40% (70-80cc)
- Piraflufén 2,5% (200cc)

PEE / PSI CULTIVO:
- Flumioxazin 48% (0,15l) 20-30 DAS
- Terbutilazina 75% (1kg)
- Atrazina 90% (1-2kg)
- S-metolacloro 96% (0,9-1,3l)* (*semilla curada con Fluxofenim 96%)
- Pendimetalín 33% (2,5-4,5l)
- Imazapyc 31,8% (0,2-0,3l) Sorgos tolerantes a imidazolinonas
- Atrazina 90% (1-2kg) / S-metolacloro 96% (0,9-1,3l)*
- Atrazina 90% (1-2kg) / (Imazapyc/Imazapy) Sorgos tolerantes

POST-EMERGENCIA V4-V8:
- 2,4D (aplicación dirigida >V8)
- MCPA / Picloram / Clopyralid / Dicamba
- Bromoxinil 34,6% (0,8-1l) V2-V4
- Atrazina 90% (1-2kg) V2-V4
- Bentazón 60% (1,2-1,6l) V2-V8
- Pendimetalín 33% (2,5-4l) V3-V4 maleza no emergida
- Imazapyc/Imazapy (0,2-0,3l) Sorgos tolerantes
- Atrazina 90% / Hormonal / Mezclas hormonales

Desecante: Paraquat / Glifosato
⚠️ *Semilla curada con Fluxofenim 96% requerida para usar atrazina + s-metolacloro

=== COLZA / CANOLA / CARINATA ===

--- COLZA: MALEZA GENERAL ---
POE MALEZA / PSI CULTIVO:
- Paraquat 27,6% (1,5-2,5l)
- Glufosinato de amonio 28% (1-2,5l)
- Glifosato
- 2,4D (15-20 DAS) / Fluroxipir / Clopyralid
- Saflufenacil 70% (35-40g)
- Carfentrazone 40% (70-80cc)

PEE / PSI CULTIVO:
- Clomazone 36% (1,5l) sin registro
- Trifluralina 60% (1,5l)
- Pendimetalín 45,6% (2,5-3,5l)
- Imidazolinonas (Colzas CL) sin registro
- Triazinas: atrazina, metribuzin, terbutilazina (Colzas con resistencia a triazinas) sin registro
- ⚠️ Carinata: solo trifluralina

POST-EMERGENCIA (estado roseta):
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
POE MALEZA / PSI CULTIVO:
- Glifosato
- Paraquat 27,6% (1,5-2,5l)
- Glufosinato de amonio 28% (1-2,5l)
- 2,4D (15 DAS) / Fluroxipir / Saflufenacil 70% / Carfentrazone 40% / Piraflufén 2,5%
- Cletodim 24% / Haloxyfop 54%

PEE / PSI CULTIVO:
- Imazatapir 10% (0,8-1l)
- Metsulfurón 60% (4-5g) sin registro 30-40 DAS
- Metribuzin 48% (0,5-0,8l)
- Terbutilazina 75% (0,8-1kg)
- Prometrina 50% (2l)
- Linurón 50% (2l)
- Atrazina 90% (0,5-1kg) sin registro
- Flumioxazin 48% (0,1l)
- S-metolacloro 96% (0,8-1l)
- Pendimetalín 45,6% (2,5-3,5l)
- Trifluralina 60% (1-2,5l)
- Piroxasulfone 48% (0,1l) sin registro 10-15 DAS
- Diflufenicán 50% (0,2l) sin registro 10-15 DAS
- Imazatapir + Atrazina

POST-EMERGENCIA (4ª hoja verdadera hasta antes de zarcillos):
- Cletodim 24% / Haloxyfop 54% (graminicidas)
- Setoxidim (no disponible en Argentina)
- Imazatapir 10% (0,5l)
- Metribuzin 48% (0,5l)
- Terbutilazina 75% (0,8kg)
- Bentazón 60% (1-1,5l)
- MCPA 28% (0,5-0,75l)

Desecante: Paraquat 27,6% / Diquat 40% / Saflufenacil 70% / Glufosinato 28%
⚠️ Evitar POE con condiciones de estrés

=== CAMELINA ===

--- CAMELINA: MALEZA GENERAL ---
POE MALEZA / PSI CULTIVO:
- Paraquat 27,6% (1,5-2,5l)
- Glufosinato de amonio 28% (1-2,5l)
- Glifosato
- 2,4D (15-20 DAS) / Fluroxipir
- Saflufenacil 70% / Carfentrazone 40%

PEE / PSI CULTIVO: Trifluralina 60% (1,5l) — ÚNICA opción residual

POST-EMERGENCIA (estado roseta): Cletodim 60% (1,5l) — ÚNICA opción, solo gramíneas

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
