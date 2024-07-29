import pyaudio
import wave
import os
import time
import pyautogui
import json
import pygetwindow as gw
import difflib
import webbrowser
import subprocess
import keyboard
import eel
import psutil
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'key.json'

#Serveix per poder saber quins processos estan actius
def list_active_processes():
    # Get all running process IDs
    process_ids = psutil.pids()

    # Iterate over process IDs and get their details
    processes = []
    for pid in process_ids:
        try:
            process = psutil.Process(pid)
            processes.append(process.name())
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes

#Funció que graba al usuari i puja el audio al bucket
def record_and_upload(name):
    audio = pyaudio.PyAudio()

    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    print_message("Pulsa ctrl para empezar a grabar...")

    frames = []

    while not keyboard.is_pressed('ctrl'):
        pass

    # label.config(text="Grabando, soltar el botón central del ratón para finalizar grabación.")
    print_message("Grabando, soltar ctrl para finalizar grabación.")
    while keyboard.is_pressed('ctrl'):
        data = stream.read(1024)
        frames.append(data)

    print_message("Grabación finalizada. Processando instrucciones...")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    wf = wave.open(name + '.wav', 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    wf.setframerate(44100)
    wf.writeframes(b''.join(frames))
    wf.close()

    storage_client = storage.Client()
    bucket = storage_client.bucket('input-audio-uab')
    blob = bucket.blob(name + '.wav')
    blob.upload_from_filename(name + '.wav')

    os.remove(name + '.wav')

#Espera que el bucket tingui el resultat que retorna la cloud function
def wait_for_new_file(bucket_name, timeout=300):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    start_time = time.time()
    while True:
        blobs = list(bucket.list_blobs())
        if blobs:
            return blobs[0]
        if time.time() - start_time >= timeout:
            raise TimeoutError("Timeout waiting for new file")

#Funcio que descarrega el contingut del bucket
def download_file(bucket_name, file_name, destination):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.download_to_filename(destination)

#funció que elimina el contingut del bucket
def delete_file(bucket_name, file_name):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.delete()


"""
SCRIPTS------------------------------------------------------------------------
"""

#Funció que retorna el string més semblant al recollit per per part del usuari
def find_best_match(original, candidates):
    best_match = None
    highest_ratio = 0.0
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, original, candidate).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = candidate
    if highest_ratio >= 0.01:
        return best_match
    else:
        return ""


#Serveix per saber quina es la finestra activa i opera sobre aquestes
def manage_windows(window_title, method):
    windows = gw.getAllTitles()
    windows = [title.lower() for title in windows if title]
    closest_match = find_best_match(window_title, windows)
    if closest_match == "":
        return False,closest_match
    window = gw.getWindowsWithTitle(closest_match)
    if window:
        window = window[0]
        if method == 'b':
            if window.isMinimized == False:
                window.minimize()
            window.restore()
            return True,closest_match
        elif method == 'c':
            window.close()
            return True,closest_match
    else:
        print_message("Ventana no encontrada.")
        return False,closest_match


#funció que conté les accions realitzables per al usuari
def scripts(distance=75):
    with open("to_script.json", 'r') as file:
        data = json.load(file)
    transcript = data.get('transcript')
    print("Se ha solicitado: " + transcript)
    print_heard("Se ha solicitado: " + transcript)
    instruccions = data.get('instruccions')

    for action in instruccions:
        i = 0
        while (i < len(action)):
            if action[i] == 'copiar':
                pyautogui.hotkey('ctrl', 'c')
            elif action[i] == 'pegar':
                pyautogui.hotkey('ctrl', 'v')
            elif action[i] == 'cortar':
                pyautogui.hotkey('ctrl', 'x')
            elif action[i] == 'deshacer':
                pyautogui.hotkey('ctrl', 'z')
            elif action[i] == 'rehacer':
                pyautogui.hotkey('ctrl', 'y')
            elif action[i] == 'apagar':
                print_confirm("¿Estás seguro de que quieres apagar el equipo? Responde con afirmativo o negativo")
                record_and_upload("audio")
                blob = wait_for_new_file('audio-script-sm')
                download_file('audio-script-sm', blob.name, "to_script.json")
                delete_file('audio-script-sm', blob.name)
                with open("to_script.json", 'r') as file:
                    data2 = json.load(file)
                transcript2 = data2.get('transcript')
                print_heard("Se ha solicitado: " + transcript2)
                instruccions2 = data2.get('instruccions')
                for confirmation in instruccions2:
                    if confirmation == ["afirmativo"]:
                        os.system('shutdown /s /t 1')
                    elif confirmation == ["negativo"]:
                        print_confirm('')
                        break
            elif action[i] == 'reiniciar':
                print_confirm("¿Estás seguro de que quieres reiniciar el equipo? Responde con afirmativo o negativo")
                record_and_upload("audio")
                blob = wait_for_new_file('audio-script-sm')
                download_file('audio-script-sm', blob.name, "to_script.json")
                delete_file('audio-script-sm', blob.name)
                with open("to_script.json", 'r') as file:
                    data2 = json.load(file)
                transcript2 = data2.get('transcript')
                print_heard("Se ha solicitado: " + transcript2)
                instruccions2 = data2.get('instruccions')
                for confirmation in instruccions2:
                    if confirmation == ["afirmativo"]:
                        os.system('shutdown /r /t 1')
                    elif confirmation == ["negativo"]:
                        print_confirm('')
                        break
            elif action[i] == 'cambiar':
                i += 1
                manage_windows(action[i], 'b')
            elif action[i] == 'cerrar':
                i += 1
                _, close = manage_windows(action[i], 'c')
                if (close == "control vocal"):
                    return 0
            elif action[i] == 'abrir':
                i += 1
                closest_match = find_best_match(action[i], os.listdir('../programs'))
                program_path = os.path.join('../programs', closest_match)
                os.startfile(program_path)
            elif action[i] == 'windows abrir':
                i += 1
                pyautogui.press('winleft')
                time.sleep(1)
                pyautogui.write(action[i], interval=0.1)
                time.sleep(1)
                pyautogui.press('enter')
            elif action[i] == 'escribir':
                i += 1
                pyautogui.write(action[i])
                pyautogui.press('space')
            elif action[i] == 'mover':
                i += 2
                if action[i] == 'arriba':
                    if (len(action) > 3):
                        i += 1
                        distance = int(action[i])
                        pyautogui.moveRel(xOffset=0, yOffset=-distance, duration=0.15)
                        distance = 75
                    else:
                        pyautogui.moveRel(xOffset=0, yOffset=-distance, duration=0.15)
                elif action[i] == 'abajo':
                    if (len(action) > 3):
                        i += 1
                        distance = int(action[i])
                        pyautogui.moveRel(xOffset=0, yOffset=distance, duration=0.15)
                        distance = 75
                    else:
                        pyautogui.moveRel(xOffset=0, yOffset=distance, duration=0.15)
                elif action[i] == 'derecha':
                    if (len(action) > 3):
                        i += 1
                        distance = int(action[i])
                        pyautogui.moveRel(xOffset=distance, yOffset=0, duration=0.15)
                        distance = 75
                    else:
                        pyautogui.moveRel(xOffset=distance, yOffset=0, duration=0.15)
                elif action[i] == 'izquierda':
                    if (len(action) > 3):
                        i += 1
                        distance = int(action[i])
                        pyautogui.moveRel(xOffset=-distance, yOffset=0, duration=0.15)
                        distance = 75
                    else:
                        pyautogui.moveRel(xOffset=-distance, yOffset=0, duration=0.15)
            elif action[i] == 'doble':
                i += 1
                pyautogui.doubleClick()
            elif action[i] == 'clic':
                i += 1
                if action[i] == 'derecho':
                    pyautogui.rightClick()
                if action[i] == 'izquierdo':
                    pyautogui.click()
                if action[i] == 'central':
                    pyautogui.middleClick()
            elif action[i] == 'google':
                i += 1
                search_url = f"https://www.google.com/search?q={action[i]}"
                webbrowser.open(search_url)
            elif action[i] == 'spotify':
                i += 1
                pyautogui.press('winleft')
                time.sleep(1)
                pyautogui.write('spotify', interval=0.1)
                time.sleep(1)
                pyautogui.press('enter')

                found = False
                while not found:
                    procs = list_active_processes()
                    print(procs)
                    if 'Spotify.exe' in procs:
                        found = True
                        print('trobat')

                time.sleep(5)
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(1)
                pyautogui.write(action[i], interval=0.1)
                time.sleep(1)
                pyautogui.press('enter')
                time.sleep(1)
                pyautogui.press('tab')
                time.sleep(1)
                pyautogui.press('enter')
                time.sleep(1)
                pyautogui.press('enter')
            elif action[i] == 'archivos':
                i += 1
                if i == len(action):
                    subprocess.Popen('explorer')
                else:
                    if action[i] == 'escritorio':
                        if i == len(action) - 1:
                            path = os.path.expanduser("~\Desktop")
                            subprocess.Popen(f'explorer "{path}"')
            else:
                print('Error not a scripts')
            i = i + 1
            time.sleep(1)

    return 1

#funció que imprimeix a la part grafica l'estat de la comanda
def print_message(message):
    print(message)
    eel.updateConsole(message)

#Funció que imprimeix a la part gràfica el que s'ha entés
def print_heard(message):
    eel.updateHeard(message)

#Imprimeix el missatge de confirm quan volem apagar el ordinador
def print_confirm(message):
    eel.updateConfirm(message)
