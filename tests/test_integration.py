"""Phase 2 integration tests — full pipeline against mock Lichess DOM.

Wires all components together: page_manager → dom_reader → screenshot →
board_extractor → piece_classifier → fen_assembler → engine_client →
click_mapper → dom_actor → DOM verify.  Engine is mocked; CNN + board
extractor run live against rendered pieces in the mock HTML.
"""
from unittest.mock import patch

import chess
import cv2
import numpy as np
import pytest

from chess_agent.board_extractor import crop_board, split_tiles
from chess_agent.click_mapper import uci_to_pixels
from chess_agent.dom_actor import DOMActor
from chess_agent.dom_reader import DOMReader
from chess_agent.fen_assembler import labels_to_fen
from chess_agent.page_manager import PageManager
from chess_agent.piece_classifier import PieceClassifier
from chess_agent.config import PIECE_CLASSIFIER_PATH

pytestmark = pytest.mark.skipif(
    not __import__('os').path.exists(PIECE_CLASSIFIER_PATH),
    reason="CNN model not found — install Piece_Classifier.h5 in Models/",
)


def pick_move_fake(fen, is_white):
    board = chess.Board(fen)
    board.turn = is_white
    legal = list(board.legal_moves)
    if not legal:
        raise RuntimeError("no move")
    return legal[0].uci()


def _board_fen(page):
    return page.evaluate("window.getBoardState()").split(" ")[0]


class TestPipelineComponents:
    def test_detect_game_state(self, page):
        pm = PageManager(page, DOMReader(page), "white")
        assert pm.detect_state() == "game"

    def test_board_rect_and_orientation(self, page):
        reader = DOMReader(page)
        rect = reader.get_board_rect()
        assert rect and rect["w"] == 400 and rect["h"] == 400
        assert reader.get_orientation() == "white"

    def test_is_our_turn(self, page):
        reader = DOMReader(page)
        assert reader.is_our_turn("white") is True
        assert reader.is_our_turn("black") is False

    def test_is_game_over_false(self, page):
        page.evaluate("window.showGameOver(false)")
        reader = DOMReader(page)
        assert reader.has_game_over_dialog() is False

    def test_is_game_over_true(self, page):
        page.evaluate("window.showGameOver(true)")
        reader = DOMReader(page)
        assert reader.has_game_over_dialog() is True


class TestScreenshotToFen:
    def test_screenshot_crop_classify(self, page):
        reader = DOMReader(page)
        rect = reader.get_board_rect()
        screenshot = page.screenshot(type="png")
        img = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_GRAYSCALE)
        board_img = crop_board(img, rect)
        board_img = cv2.resize(board_img, (200, 200))
        tiles = split_tiles(board_img)
        classifier = PieceClassifier(PIECE_CLASSIFIER_PATH)
        labels = classifier.classify(tiles)
        assert len(labels) == 64
        valid = set("-KkQqRrBbNnPp")
        for label in labels:
            assert label in valid
        fen = labels_to_fen(labels)
        assert isinstance(fen, str)
        assert fen.count("/") == 7

    def test_screenshot_fen_after_move(self, page):
        fen_before = page.evaluate("window.getBoardFen()")
        page.evaluate("window.applyMove('e2e4')")
        reader = DOMReader(page)
        rect = reader.get_board_rect()
        screenshot = page.screenshot(type="png")
        img = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_GRAYSCALE)
        board_img = crop_board(img, rect)
        board_img = cv2.resize(board_img, (200, 200))
        tiles = split_tiles(board_img)
        classifier = PieceClassifier(PIECE_CLASSIFIER_PATH)
        labels = classifier.classify(tiles)
        fen = labels_to_fen(labels)
        assert isinstance(fen, str)
        assert fen.count("/") == 7
        assert fen != fen_before


class TestClickMapperAndActor:
    def test_click_square_highlights_selected(self, page):
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.click_square("e2") is True
        sel = page.evaluate("document.querySelector('square.selected')?.dataset?.coord")
        assert sel == "e2"

    def test_click_move_updates_dom(self, page):
        page.evaluate("window.setBoardState('8/8/8/8/8/8/4P3/8')")
        page.evaluate("window.setTurn('white')")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.click_move("e2e4") is True
        assert page.evaluate("document.querySelector('square.selected')") is None

    def test_verify_move_made_true(self, page):
        page.evaluate("window.addLastMove(['e2', 'e4'])")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.verify_move_made("e2e4", None) is True


class TestFullPipelineLoop:
    def _simulate_opponent_move(self, page):
        fen_parts = page.evaluate("window.getBoardState()").split()
        board = chess.Board(" ".join(fen_parts[:2]) + " KQkq - 0 1")
        if not board.is_checkmate() and not board.is_stalemate():
            legal = list(board.legal_moves)
            if legal:
                page.evaluate(f"window.applyMove('{legal[0].uci()}')")

    @patch("chess_agent.engine_client.pick_move")
    def test_five_move_loop_completes(self, mock_pick, page):
        mock_pick.side_effect = pick_move_fake
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        pm = PageManager(page, reader, "white")
        classifier = PieceClassifier(PIECE_CLASSIFIER_PATH)

        assert pm.detect_state() == "game"

        for step in range(5):
            assert pm.wait_for_turn(timeout=5), f"step {step}: not our turn"
            assert pm.is_board_stable()

            screenshot = page.screenshot(type="png")
            img = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_GRAYSCALE)
            rect = reader.get_board_rect()
            assert rect is not None

            board_img = crop_board(img, rect)
            board_img = cv2.resize(board_img, (200, 200))
            tiles = split_tiles(board_img)
            labels = classifier.classify(tiles)
            assert len(labels) == 64

            fen = labels_to_fen(labels)

            move_uci = pick_move_fake(fen, is_white=True)
            assert isinstance(move_uci, str) and len(move_uci) >= 4

            sx, sy, ex, ey = uci_to_pixels(move_uci, rect, is_white=True)
            assert rect["x"] <= sx <= rect["x"] + rect["w"]
            assert rect["y"] <= sy <= rect["y"] + rect["h"]
            assert rect["x"] <= ex <= rect["x"] + rect["w"]
            assert rect["y"] <= ey <= rect["y"] + rect["h"]

            assert actor.click_move(move_uci), f"step {step}: click_move failed"

            assert actor.verify_move_made(move_uci, fen), f"step {step}: verify failed"

            assert page.evaluate("document.querySelector('square.selected')") is None, (
                f"step {step}: square still selected"
            )

            self._simulate_opponent_move(page)

        assert step == 4
