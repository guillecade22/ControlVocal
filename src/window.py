import eel
import main as mn

# Inicialitzem eel (part grafica)
eel.init('web')
eel._exposed_functions = {}

#Funcio que graba el audio, l'envia al bucket i recupera el que la cloud function retorni
def u():
    mn.record_and_upload("audio")
    bucket_name = 'audio-script-sm'
    destination = 'to_script.json'
    blob = mn.wait_for_new_file(bucket_name)
    mn.download_file(bucket_name, blob.name, destination)
    mn.delete_file(bucket_name, blob.name)
    if (mn.scripts() == 1):
        u()


print("Exposed functions after:", eel._exposed_functions)
eel.expose(u)
print("Exposed functions after:", eel._exposed_functions)

#Es carrega la part gràfica
eel.start('index.html', size=(1200, 1000))
