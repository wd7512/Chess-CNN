from tensorflow.keras.models import load_model
import cv2
import time
import numpy as np
import chess
from PIL import ImageGrab
import pyautogui
from Intermediate_Engines import min_max2, min_max3, min_maxN_pruned
import matplotlib.pyplot as plt
from new_src import screen_grab

piece_model = load_model('Models/Piece_Classifier.h5')
orientation_model = load_model('Models/Orientation_Classifier.h5')

template = cv2.imread('Blank_Board.png', cv2.IMREAD_GRAYSCALE)
if template is None:
    print("Error loading template image.")
    exit()

black_template = cv2.imread('blank_black.png', cv2.IMREAD_GRAYSCALE)
if template is None:
    print("Error loading black template image.")
    exit()

new_opp = cv2.imread('new_opp.png', cv2.IMREAD_GRAYSCALE)
if new_opp is None:
    print("Error loading new_opp image.")
    exit()
else:
    print("Loaded Models and Template")

def prepare_fen(fen):
    fen, col = fen.split("_")
    output_arr = []
    for char in fen:
        if char.isdigit():
            output_arr += ["-"] * int(char)
        elif char == "/":
            continue
        else:
            output_arr.append(char)

    return output_arr

def undo_prepare_fen(arr):
    board = chess.Board("8/8/8/8/8/8/8/8")
    arr_rev = np.reshape(arr, (8,8))
    arr = []
    for row in arr_rev[::-1]:
        arr.append(row[::])

    arr = np.ravel(arr)

    for i, square in enumerate(chess.SQUARES):
        if arr[i] != "-":
            board.set_piece_at(square, chess.Piece.from_symbol(arr[i]))
    
    return board.fen().split(" ")[0]

def one_hot_to_label(arr):
    labels = {0: '-',
 1: 'B',
 2: 'K',
 3: 'N',
 4: 'P',
 5: 'Q',
 6: 'R',
 7: 'b',
 8: 'k',
 9: 'n',
 10: 'p',
 11: 'q',
 12: 'r'}
    
    return labels[np.argmax(arr)]


if __name__ == "__main__":
    white_small_template = cv2.resize(template, (50,50))
    black_small_template = cv2.resize(black_template, (50,50))

    print("Running Chessbot")
    time.sleep(3)

    table = {}

    fens = {"current": "",
        "move_from": "",
        "move_to": ""}
    
    time_taken = time.perf_counter()
    
    while True:
        time_taken = time.perf_counter() - time_taken
        fps = 1 / time_taken
        print(f"Time Taken: {time_taken:.2f}| FPS: {int(fps)}")

        s = time.perf_counter()
        # screenshotting
        # screenshot = ImageGrab.grab()
        screenshot = screen_grab()
        screenshot_gray = screenshot.convert('L')
        #print(f"Screenshot Time: {time.perf_counter() - s:.2f}")
        
        # extracting chess board
        grey_image = np.array(screenshot_gray)

        res = cv2.matchTemplate(grey_image, template, cv2.TM_CCOEFF_NORMED)
        opp_res = cv2.matchTemplate(grey_image, new_opp, cv2.TM_CCOEFF_NORMED)
        if np.max(opp_res) > 0.5:
            opp_loc = np.where(opp_res >= np.max(opp_res - 1e-10))
            print("Looking for new opponent")
            pyautogui.click(opp_loc[1][0], opp_loc[0][0])
            time.sleep(5)
            continue

        threshold = np.max(res) - 0.05
        if threshold < 0.1:
            print("Board not Found")
            continue
        #print("Board Match: ", threshold)

        loc = np.where(res >= threshold)

        matched_regions = []
        if len(loc[0]) > 0:
            rects = []
            for pt in zip(*loc[::-1]):
                rects.append([pt[0], pt[1], template.shape[1], template.shape[0]])
            
            rects, weights = cv2.groupRectangles(rects, groupThreshold=1, eps=0.2)
            
            for rect in rects:
                x, y, w, h = rect
                matched_region = grey_image[y:y + h, x:x + w]
                matched_regions.append(matched_region)

        image = cv2.resize(matched_regions[0], (200,200))
        orien_image = cv2.resize(matched_regions[0], (50,50))

        plt.imshow(orien_image)
        plt.savefig("foo.png")

        mse_white = np.mean((orien_image[:,-1:] - white_small_template[:,-1:]) ** 2)
        mse_black = np.mean((orien_image[:,-1:] - black_small_template[:,-1:]) ** 2)

        print(f"White MSE: {mse_white}, Black MSE: {mse_black}")

        if mse_white > mse_black:
            is_white = False
        else:
            is_white = True
        
        is_white = is_white
        # splitting chess board
        inputs = []

        for i in range(8):
            for j in range(8):
                inputs.append(image[i*25:(i+1)*25 ,j * 25: (j+1) * 25] / 255)

        preds = piece_model(np.array(inputs))
        ypred_labels = [one_hot_to_label(pred) for pred in preds]
        fens["current"] = undo_prepare_fen(ypred_labels)
        print(fens["current"])

        if is_white:
            pass
        else:
            new_f = fens["current"].split("/")
            new_f = [a[::-1] for a in new_f[::-1]]
            fens["current"] = "/".join(new_f)

        # load into chess framework
        if fens["current"] != fens["move_from"] and fens["current"] != fens["move_to"]:
            print("Table size", len(table))
            print("playing as white:", is_white)
            print(fens["current"])
            board = chess.Board(fens["current"])
            print(board)

            # get optimal move
            board.turn = is_white

            if fens["current"] in table and False:
                optimal_move = table[fens["current"]]
            else:
                optimal_move = min_maxN_pruned(board,3)
                table[fens["current"]] = optimal_move
            board.push(optimal_move)

            optimal_move = optimal_move.uci()
            print("best move", optimal_move)

            square_size = ((w + h) // 2) // 8

            # coords are a to h and 8 to 1
            if is_white:
                start_x = x + (ord(optimal_move[0]) - 97 + 0.5) * square_size
                start_y = y + (8 - int(optimal_move[1]) + 0.5) * square_size

                end_x = x + (ord(optimal_move[2]) - 97 + 0.5) * square_size
                end_y = y + (8 - int(optimal_move[3]) + 0.5) * square_size
            else:
                start_x = x + w - (ord(optimal_move[0]) - 97 + 0.5) * square_size
                start_y = y + w - (8 - int(optimal_move[1]) + 0.5) * square_size

                end_x = x + w - (ord(optimal_move[2]) - 97 + 0.5) * square_size
                end_y = y + w - (8 - int(optimal_move[3]) + 0.5) * square_size

                
            #print(start_x, start_y)
            pyautogui.click(start_x,start_y)
            #time.sleep(abs(np.random.normal(0,0.2)))
            pyautogui.click(end_x,end_y)


            fens["move_from"] = fens["current"]
            
            fens["move_to"] = board.fen().split(" ")[0]