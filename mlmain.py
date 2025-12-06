import cv2
import mediapipe as mp
import pyautogui
import time
import ctypes
import pickle
import numpy as np
import itertools

user32 = ctypes.windll.user32 # Carrega a biblioteca user32.dll, que contém as funções da API do Windows

pyautogui.FAILSAFE = True # Mecanismo de segurança do pyautogui

with open('modelo_mouse.p', 'rb') as f: # Carrega o modelo treinado

    model = pickle.load(f)

NOME_GESTOS = { # Mapeamento dos nomes dos gestos para exibir na tela
    
    0: "Neutro",
    1: "Scroll Cima",
    2: "Scroll Baixo",
    3: "Clique Esq.",
    4: "Clique Dir.",
    5: "Duplo Clique",
    6: "Arrastar"

}

def calcular_landmarks_relativos(image, landmarks): # Converte landmarks para o formato usado no treinamento 

    image_width, image_height = image.shape[1], image.shape[0]
    landmark_point = []

    # Converte para pixels
    for _, landmark in enumerate(landmarks.landmark):

        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_point.append([landmark_x, landmark_y])

    # Converte para relativo ao pulso
    base_x, base_y = landmark_point[0][0], landmark_point[0][1]
    temp_landmark_list = []

    for index, point in enumerate(landmark_point):

        temp_landmark_list.append([point[0] - base_x, point[1] - base_y])

    # Achata a lista e normaliza
    temp_landmark_list = list(itertools.chain.from_iterable(temp_landmark_list))
    max_value = max(list(map(abs, temp_landmark_list)))
    def normalize_(n): return n / max_value
    temp_landmark_list = list(map(normalize_, temp_landmark_list))

    return temp_landmark_list

cap = cv2.VideoCapture(0) # Cria objeto para captura de vídeo

if not cap.isOpened(): # Testa se a abertura de camêra funcionou

    print("Não foi possível abrir a câmera.")
    exit()

mp_hands = mp.solutions.hands # Acessa a ferramenta de detecção de mãos do MediaPipe

hands = mp_hands.Hands(

    max_num_hands=1,                # Detectar no máximo uma mão
    min_detection_confidence=0.7,   # Confiança mínima na detecção
    min_tracking_confidence=0.5     # Confiança mínima no rastreamento

) # Cria o objeto detector da mão

mp_drawing = mp.solutions.drawing_utils # Acessa a ferramenta para desenhar os pontos e as linhas da mão detectada

prev_time = 0 # Previous Time para calcular FPS

# width = user32.GetSystemMetrics(0)
# height = user32.GetSystemMetrics(1)

width, height = pyautogui.size() # Armazena resolução da tela

cursor_x = 0 # Variavel x para filtro
cursor_y = 0 # Variavel x para filtro
smoothing = 0.8 # Variavel para suavizar movimento

last_click = 0 # Variavel para controle de multiplos cliques 
mouse_down = False # Variavel para logica de modo de botão esquerdo pressionado

xatual = 0 # X para filtro de tremida
yatual = 0 # Y para filtro de tremida

while True: # Loop principal 
    
    success, img = cap.read() # Leitura de um frame da camêra

    if not success: # Teste se a leitura funcionou
        
        print("Falha ao ler o frame da câmera.")
        break

    img = cv2.flip(img, 1) # Inverte o frame captado 

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # Converte de BGR para RGB (MediaPipe faz leituras em RGB)

    results = hands.process(img_rgb) # Processa a imagem para detectar as mãos 

    if results.multi_hand_landmarks: # Checa se uma mão foi detectada
        
        for hand_landmarks in results.multi_hand_landmarks: # Percorre a lista de mãos (que neste caso está setado para apenas uma)
            
            current_time = time.time()

            mp_drawing.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS) # Desenha os pontos e as linhas na imagem

            dados_relativos = calcular_landmarks_relativos(img, hand_landmarks) # Prepara os dados
            gesto_id = model.predict([dados_relativos])[0] # Faz a previsão do modelo

            indexfinger_tip = hand_landmarks.landmark[8] # Obtem as coordenadas normalizadas da ponta do dedo indicador    

            ix = int(indexfinger_tip.x * width) # Coordenada X da ponta do indicador 
            iy = int(indexfinger_tip.y * height) # Coordenadas Y da ponta do indicador  

            cursor_x = cursor_x + (ix - cursor_x) * smoothing # Calculo para suavizar x
            cursor_y = cursor_y + (iy - cursor_y) * smoothing # Calculo para suavizar y

            if gesto_id == 1 and (current_time - last_click) > 0.5: # Scroll para cima

                user32.mouse_event(0x0800, 0, 0, 120, 0) # 0x0800 é o evento de scroll, 120 é o valor padrão de scroll para cima (positivo)

                # pyautogui.scroll(200) # Scroll para cima (positivo)
                last_click = current_time # Atualiza o tempo para evitar multiplos scrolls

            if gesto_id == 2 and (current_time - last_click) > 0.5: # Scroll para baixo

                user32.mouse_event(0x0800, 0, 0, -120, 0) # 0x0800 é o evento de scroll, -120 é o valor padrão de scroll para baixo (negatiov)

                # pyautogui.scroll(-200) # Scroll para baixo (negativo)
                last_click = current_time # Atualiza o tempo para evitar multiplos scrolls

            elif gesto_id == 6: # Segura o botão esquerdo

                if not mouse_down: # Para evitar que sempre chame a função

                    user32.mouse_event(0x0002, 0, 0, 0, 0) # 0x0002 é o evento de pressionar o botão esquerdo do mouse

                if (xatual - ix)**2 + (yatual - iy)**2 > 50: # Filtra movimentos minusculos do cursor para evitar tremida

                    xatual = cursor_x
                    yatual = cursor_y
                    user32.SetCursorPos(int(cursor_x), int(cursor_y)) # Move o mouse para a nova coordenada
                    # pyautogui.moveTo(cursor_x, cursor_y) # Move o mouse para a nova coordenada

                mouse_down = True

                user32.SetCursorPos(int(cursor_x), int(cursor_y)) # Move o mouse para a nova coordenada

                # pyautogui.moveTo(cursor_x, cursor_y) # Move o mouse para a nova coordenada

            else: # Cliques do mouse

                if mouse_down: # Para evitar que sempre chama a função

                    user32.mouse_event(0x0004, 0, 0, 0, 0) # 0x0004 é o evento de soltar o botão esquerdo do mouse

                    # pyautogui.mouseUp(button='left') # Função para soltar o botão esquerdo
                    mouse_down = False

                if gesto_id == 3 and (current_time - last_click) > 0.5: # Clique com o botão esquerdo, evitando multiplos cliques
                    
                    user32.mouse_event(0x0002, 0, 0, 0, 0) # 0x0002 é o evento de pressionar o botão esquerdo do mouse
                    user32.mouse_event(0x0004, 0, 0, 0, 0) # 0x0004 é o evento de soltar o botão esquerdo do mouse
                    
                    # pyautogui.click() # Clica com o botão esquerdo onde o ponteiro está apontando
                    last_click = current_time # Atualiza o tempo para evitar multiplos cliques

                elif gesto_id == 4 and (current_time - last_click) > 0.5: # Clique com o botão direito, evitando multiplos cliques
                
                    user32.mouse_event(0x0008, 0, 0, 0, 0) # 0x0008 é o evento de pressionar o botão direito do mouse
                    user32.mouse_event(0x0010, 0, 0, 0, 0) # 0x0010 é o evento de soltar o botão direito do mouse

                    # pyautogui.click(button='right') # Clica com o botão direito onde o ponteiro está apontando
                    last_click = current_time # Atualiza o tempo para evitar multiplos cliques

                elif gesto_id == 5 and (current_time - last_click) > 0.5: # Duplo clique com o botão esquerdo, evitando multiplos duplos cliques
                    
                    user32.mouse_event(0x0002, 0, 0, 0, 0) # 0x0002 é o evento de pressionar o botão esquerdo do mouse
                    user32.mouse_event(0x0004, 0, 0, 0, 0) # 0x0004 é o evento de soltar o botão esquerdo do mouse

                    user32.mouse_event(0x0002, 0, 0, 0, 0) # Repete para realizar um duplo clique
                    user32.mouse_event(0x0004, 0, 0, 0, 0) 

                    # pyautogui.doubleClick(button='left') # Clica duas vezes com o botão esquerdo onde o ponteiro está apontando
                    last_click = current_time # Atualiza o tempo para evitar multiplos duplos cliques

                if (xatual - ix)**2 + (yatual - iy)**2 > 50: # Filtra movimentos minusculos do cursor para evitar tremida

                    xatual = cursor_x
                    yatual = cursor_y
                    user32.SetCursorPos(int(cursor_x), int(cursor_y)) # Move o mouse para a nova coordenada
                    # pyautogui.moveTo(cursor_x, cursor_y) # Move o mouse para a nova coordenada

    cur_time = time.time() # Current Time para calcular FPS
    fps = 1 / (cur_time - prev_time)
    prev_time = cur_time
    cv2.putText(img, f'FPS: {int(fps)}', (10, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2) # Escreve o FPS na imagem

    cv2.imshow("Mouse Gestual - Pressione 'q' para sair", img) # Exibe essa mensagem na janela aberta

    if cv2.waitKey(1) & 0xFF == ord('q'): # Aguarda 'q' ser pressionado para sair do loop
        break

cap.release() # Libera a camêra
cv2.destroyAllWindows() # Fecha todas as janelas abertas pelo OpenCV