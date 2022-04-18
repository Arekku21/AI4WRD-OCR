import random
import streamlit as st
import cv2
import json
import time
import numpy as np
from PIL import ImageGrab
from PIL import Image
import matplotlib.pyplot as plt
from streamlit_cropper import st_cropper
import easyocr
# import paho.mqtt.client as mqtt
from PIL import Image, ImageEnhance
import csv
from datetime import datetime

from paho.mqtt import client as mqtt_client
import pandas as pd



def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


@st.cache
def connect_mqtt(client_id, broker, port):
    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def mainApp():
    if 'cropArr' not in st.session_state:
            st.session_state['cropArr'] = []

    if 'lang' not in st.session_state:
        st.session_state['lang'] = ""



    if st.session_state.lang == "Chn":
        reader = easyocr.Reader(['ch_sim','en'], gpu=True)
        #st.write("Reading Chinese")
    elif st.session_state.lang == "":
        reader = easyocr.Reader(['en'], gpu=True)
        #st.write("Not reading chinese")



    skip_frame = True

    if 'data' not in st.session_state:
            st.session_state['data']= []

    if 'd1' not in st.session_state:
            st.session_state['d1']= {}
    zoom = st.sidebar.slider('Zoom (%)', 100, 500)

    if 'text' not in st.session_state:
            st.session_state['text']= []
    
    doneCrop = st.checkbox('Done Crop')


    if doneCrop:
        continuousSave = 0
        counter = 0
        FRAME_WINDOW = st.image([])
        header = ['Timestamp','Crop ID', 'OCR Data']

        status = st.empty()

        # todo dont use st.write
        path_to_save = st.text_input('Path to save', '')
        st.write('The current path is', path_to_save)


        saveallCSV = st.button("Save Previous to csv")

        savecontCSV = st.button("Save Continuous to csv")

        """
        Mqtt test 
        """
        status_mqtt = st.empty()
        mqtt_address = st.text_input('Mqtt Broker Address', '')
        mqtt_topic = st.text_input('Mqtt topic to publish to', '')
        publish_mqtt = st.button("Publish to Mqtt server")

        # mqtt test
        broker = 'broker.emqx.io'
        port = 1883
        topic = "test123456"
        client_id = f'python-mqtt-{random.randint(0, 1000)}'
        # username = 'emqx'
        # password = 'public
        #
        if publish_mqtt:
            client = connect_mqtt(client_id, broker, port)


        """
        end of mqtt test
        """


        file_saving_status = st.empty()


        while counter < len(st.session_state.cropArr):
            st.session_state.d1["FRAME_WINDOW{0}".format(counter)] = st.image([])
            st.session_state.d1["placeholderOCR{0}".format(counter)] = st.empty()
            counter+=1

        continuousSave = 0
        while True:
            a = time.time()
            _, frame = st.session_state.vid.read()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            FRAME_WINDOW.image(frame)

            livecounter = 0
            if len(st.session_state.cropArr) == 0:
                status.subheader("No crops made.")
            else:
                while livecounter < len(st.session_state.cropArr):

                    leftco = st.session_state.cropArr[livecounter]["left"]
                    widthco = st.session_state.cropArr[livecounter]["width"]
                    topco = st.session_state.cropArr[livecounter]["top"]
                    heightco = st.session_state.cropArr[livecounter]["height"]

                    imgcrop = frame[topco:topco+heightco, leftco:leftco+widthco]
                    cropped_img = Image.fromarray(imgcrop)
                    
                    scale_percent = zoom # percent of original size
                    rewidth = int(widthco * scale_percent / 100)
                    reheight = int(heightco * scale_percent / 100)

                    newsize = (rewidth,reheight)
                    newcrop=cropped_img.resize(newsize)
                    imgcrop = np.array(newcrop)

                    st.session_state.d1["FRAME_WINDOW%s" % livecounter].image(imgcrop)

                    result = reader.readtext(imgcrop)
                    
                    oldtext = st.session_state.text

                    st.session_state.text = ""
                    for res in result:
                        st.session_state.text += res[1] + " "

                    
                    #print(text)

                    b = time.time()
                    fps = 1/(b-a)    
                    print(fps)

                    strIDprint = "Crop " + str(livecounter+1) + ":      " + st.session_state.text

                    st.session_state.d1["placeholderOCR%s" % livecounter].write(strIDprint)
                    csvData = [datetime.now(), " Crop ID: %s" %(livecounter+1), st.session_state.text]

                    st.session_state.data.append(csvData)
                    if continuousSave == 1:
                        savecontCSV = 1

                    if saveallCSV:
                        if path_to_save != '':
                            try:
                                with open(path_to_save + ".csv", 'w', encoding='UTF8', newline='') as f:
                                    writer = csv.writer(f)

                                    # write the header
                                    writer.writerow(header)

                                    # write multiple rows
                                    writer.writerows(st.session_state.data)
                                    saveallCSV = False
                                file_saving_status.success("File Saved!")

                            except Exception as e:
                                print(e)
                                file_saving_status.error("Error saving file")
                        else:
                            file_saving_status.error("Path not specified")





                    elif savecontCSV:
                        if path_to_save != '':
                            try:
                                with open('path_to_save', 'w', encoding='UTF8', newline='') as f:
                                    writer = csv.writer(f)

                                    if continuousSave == 0:
                                        # write the header
                                        writer.writerow(header)

                                    # write multiple rows
                                    writer.writerows(st.session_state.data)

                                continuousSave = 1
                                file_saving_status.info("Data stream is being appended to csv file")

                            except Exception as e:
                                print(e)
                                file_saving_status.error("Error saving file")
                        else:
                            file_saving_status.error("Path not specified")

                    elif publish_mqtt:
                        msg_count = 0

                        time.sleep(1)
                        msg = f"messages: {msg_count}"

                        df = pd.DataFrame(csvData)

                        result = client.publish(topic, df.to_csv(index=False))

                        # result: [0, 1]
                        status = result[0]
                        if status == 0:
                            print(f"Send `{msg}` to topic `{topic}`")
                        else:
                            print(f"Failed to send message to topic {topic}")
                        msg_count += 1

                    cv2.waitKey(0)
                    livecounter+=1
