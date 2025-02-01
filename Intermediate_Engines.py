import chess
from copy import deepcopy
import random
import time
import chess.polyglot
import numpy as np



'''
The main issues with this simple min max are as follows
 - It has no sense of what the actual win condition is (checkmate)
 - Therefore it does not have an ability to handle a scenario
 - where there are no legal moves
#COMPLETED

 - Also it always picks the first move from the list when
 - there are multiple moves with the same evaulation.
 - We could simply pick a random one or have a secondary
 - evaluation function.
#COMPLETED

 - Perhaps this evaluation function could be the total number
 - of possible moves as a simple concept in chess is to activate
 - pieces onto much more mobile squares
#COMPLETED

 - Openings are terrible for this ai and it will always for a min max
 - function as it can never look deep enough ahead. Therefore we can
 - try to implement an opening book.
#COMPLETED
'''


#opening book
reader = chess.polyglot.open_reader('baron30.bin')

def random_agent(BOARD):

    return random.choice(list(BOARD.legal_moves))

scoring= {'p': -100,
          'n': -300,
          'b': -300,
          'r': -500,
          'q': -900,
          'k': 000,
          'P': 100,
          'N': 300,
          'B': 300,
          'R': 500,
          'Q': 900,
          'K': 000,
          
          }

def eval_board(BOARD: chess.Board):

    score = 0
    pieces = BOARD.piece_map()
    for key in pieces:
        score += scoring[str(pieces[key])]

    return score

def eval_space(BOARD):
    no_moves = len(list(BOARD.legal_moves))

    #this function is always between 0 and 1 so we will never evaluate
    #this as being greater than a pawns value. The 20 value is arbitrary
    #but this number is chosen as it centers value around 0.5
    # attackers = set()
    # attacked_squares = set()
    # for item in BOARD.legal_moves:
    #     item = item.uci()
    #     attackers.add(item[:2])
    #     attacked_squares.add(item[2:])

    value = no_moves 
    
    if BOARD.turn == True:
        return value
    else:
        return -value
    
# def eval_king(BOARD: chess.Board):
#     white_king_loc = BOARD.king(True) # a number representing the index of the king
#     black_king_loc = BOARD.king(False) # a number representing the index of the king
    
#     if BOARD.turn == True:
#         if white_king_loc % 8 not in [2,6]:
#             return -1
#         else:
#             return 1
#     else:
#         if black_king_loc % 8 not in [2,6]:
#             return 1
#         else:
#             return -1

def min_maxN(BOARD,N):

    opening_move = reader.get(BOARD)

    if opening_move == None:
        pass
    else:
        print("Using book")
        return opening_move.move


    #generate list of possible moves
    moves = list(BOARD.legal_moves)
    scores = []

    #score each move
    for move in moves:
        #temp allows us to leave the original game state unchanged
        temp = deepcopy(BOARD)
        temp.push(move)

        #here we must check that the game is not over
        outcome = temp.outcome()
        
        #if checkmate
        if outcome == None:
            #if we have not got to the final depth
            #we search more moves ahead
            if N>1:
                temp_best_move = min_maxN(temp,N-1)
                temp.push(temp_best_move)

            scores.append(eval_board(temp))

            
            
        #if checkmate
        elif temp.is_checkmate():

            # we return this as best move as it is checkmate
            return move

        # if stalemate
        else:
            #value to disencourage a draw
            #the higher the less likely to draw
            #default value should be 0
            #we often pick 0.1 to get the bot out of loops in bot vs bot
            val = 10_000
            if BOARD.turn == True:
                scores.append(-val)
            else:
                scores.append(val)

        #this is the secondary eval function
        scores[-1] = scores[-1] + eval_space(temp)


    if BOARD.turn == True:
        
        best_move = moves[scores.index(max(scores))]

    else:
        best_move = moves[scores.index(min(scores))]

    

    return best_move
        
# a simple wrapper function as the display only gives one imput , BOARD

def min_max1(BOARD):
    return min_maxN(BOARD,1)

def min_max2(BOARD):
    return min_maxN(BOARD,2)

def min_max3(BOARD):
    return min_maxN(BOARD,3)

def min_max4(BOARD):
    return min_maxN(BOARD,4)


def min_maxN_pruned(BOARD, N, alpha=float('-inf'), beta=float('inf')):
    opening_move = reader.get(BOARD)
    if opening_move:
        print("Using book")
        return opening_move.move

    moves = list(BOARD.legal_moves)
    best_move = None

    if BOARD.turn:  # White to move (Maximizing)
        max_eval = float('-inf')
        for move in moves:
            temp = deepcopy(BOARD)
            temp.push(move)
            
            outcome = temp.outcome()
            if outcome:
                if temp.is_checkmate():
                    return move
                else:
                    return move  # Prefer a non-losing move

            if N > 1:
                temp_eval = min_maxN_pruned(temp, N - 1, alpha, beta)
                temp.push(temp_eval)

            eval_score = eval_board(temp) + eval_space(temp)
            
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cut-off

    else:  # Black to move (Minimizing)
        min_eval = float('inf')
        for move in moves:
            temp = deepcopy(BOARD)
            temp.push(move)
            
            outcome = temp.outcome()
            if outcome:
                if temp.is_checkmate():
                    return move
                else:
                    return move  # Prefer a non-losing move

            if N > 1:
                temp_eval = min_maxN_pruned(temp, N - 1, alpha, beta)
                temp.push(temp_eval)
            
            eval_score = eval_board(temp) + eval_space(temp)
            
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cut-off

    return best_move