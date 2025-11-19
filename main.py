# -*- coding: utf-8 -*-
"""
BOT DISCORD + MQTT AVEC SYSTEME DE SALONS + NO_SLEEP PERIODIQUE

COMMENT AJOUTER / MODIFIER DES COMMANDES :
----------------------------------------
1) Rendez-vous à la SECTION "TABLE DES COMMANDES"
2) Ajoutez une entrée dans le dictionnaire `COMMANDS` sous la forme :
       "!nomcommande": {
           "action": fonction_a_executer,
           "description": "Texte optionnel"
       }
3) Créez ensuite la fonction correspondante dans la SECTION "FONCTIONS DES COMMANDES".
4) C'est tout ! Le système gère automatiquement :
       - L'exécution
       - Le filtrage par salon
       - Les réponses Discord

----------------------------------------
"""

import os
import discord
import paho.mqtt.client as mqtt
from flask import Flask
from threading import Thread
import asyncio

# -----------------------------
# CONFIGURATION BOT DISCORD
# -----------------------------
TOKEN = os.getenv("TOKEN")
SALON_COMMANDE = int(os.getenv("salon_commande", 0))
SALON_NO_SLEEP = int(os.getenv("salon_no_sleep", 0))
TIME_NO_SLEEP = int(os.getenv("time_no_sleep", 5))  # minutes

# -----------------------------
# CONFIGURATION MQTT
# -----------------------------
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")
TOPIC_CMD = os.getenv("TOPIC_CMD", "maison/esp1/cmd")

# -----------------------------
# INIT MQTT
# -----------------------------
mqtt_client = mqtt.Client(client_id="discord_bot")
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.tls_set()
mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
mqtt_client.loop_start()

# -----------------------------
# INIT DISCORD BOT
# -----------------------------
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# -------------------------------------------------
# FONCTIONS DES COMMANDES (SECTION POUR LES AJOUTER)
# -------------------------------------------------
async def cmd_on(message):
    mqtt_client.publish(TOPIC_CMD, "ON")
    await message.channel.send("LED allumée via MQTT !")

async def cmd_off(message):
    mqtt_client.publish(TOPIC_CMD, "OFF")
    await message.channel.send("LED éteinte via MQTT !")

# -----------------------------
# TABLE DES COMMANDES (ajoutez ici)
# -----------------------------
COMMANDS = {
    "!on": {"action": cmd_on, "description": "Allume la LED"},
    "!off": {"action": cmd_off, "description": "Éteint la LED"},
}

# -----------------------------
# TÂCHE PERIODIQUE NO_SLEEP
# -----------------------------
async def task_no_sleep():
    await client.wait_until_ready()
    canal = client.get_channel(SALON_NO_SLEEP)
    if canal is None:
        print("⚠️ ERREUR: salon_no_sleep introuvable.")
        return

    while not client.is_closed():
        await canal.send("no_sleep")
        await asyncio.sleep(TIME_NO_SLEEP * 60)

# -----------------------------
# ÉVÈNEMENTS DISCORD
# -----------------------------
@client.event
async def on_ready():
    print(f"Bot Discord connecté : {client.user}")
    client.loop.create_task(task_no_sleep())

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # Vérifie si la commande existe
    if content in COMMANDS:
        # Vérifie si on est dans le bon salon
        if message.channel.id != SALON_COMMANDE:
            await message.channel.send("❌ Les commandes ne sont pas activées dans ce salon.")
            return

        # Exécute la commande associée
        action = COMMANDS[content]["action"]
        await action(message)

# -----------------------------
# KEEP-ALIVE WEB SERVICE (PORT OUVERT)
# -----------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot Discord + MQTT actif 🚀"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Lancement du web service dans un thread
Thread(target=run_web).start()

# -----------------------------
# LANCE LE BOT DISCORD
# -----------------------------
client.run(TOKEN)
