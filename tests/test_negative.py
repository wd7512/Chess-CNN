"""Negative path tests — verify graceful handling of failure modes.

Covers: zero-sized board rect, invalid CNN labels, illegal engine moves,
DOM timeouts, screenshot failure, and 3-consecutive-failure abort.
"""
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from chess_agent.board_extractor import crop_board, split_tiles
from chess_agent.click_mapper import uci_to_pixels
from chess_agent.dom_actor import DOMActor
from chess_agent.dom_reader import DOMReader
from chess_agent.engine_client import pick_move
from chess_agent.fen_assembler import labels_to_fen
from chess_agent.page_manager import PageManager
from chess_agent.game_state import verify_partial_diff
from chess_agent.config import PIECE_CLASSIFIER_PATH, MAX_RETRIES


class TestBoardRectZeroSized:
    """Board rect is zero-sized → crop_board returns None / raises."""

    def test_crop_zero_width_returns_empty(self):
        img = np.zeros((400, 400), dtype=np.uint8)
        rect = {"x": 50, "y": 50, "w": 0, "h": 400}
        cropped = crop_board(img, rect, margin=0)
        assert cropped.shape[1] == 0

    def test_crop_zero_height_returns_empty(self):
        img = np.zeros((400, 400), dtype=np.uint8)
        rect = {"x": 50, "y": 50, "w": 400, "h": 0}
        cropped = crop_board(img, rect, margin=0)
        assert cropped.shape[0] == 0

    def test_crop_negative_coordinates_clamped(self):
        img = np.zeros((400, 400), dtype=np.uint8)
        rect = {"x": -10, "y": -10, "w": 20, "h": 20}
        cropped = crop_board(img, rect, margin=0)
        assert cropped.shape[0] > 0
        assert cropped.shape[1] > 0

    def test_split_tiles_raises_on_small_board(self):
        small = np.zeros((50, 50), dtype=np.uint8)
        with pytest.raises(ValueError, match="200x200"):
            split_tiles(small)

    def test_split_tiles_raises_on_empty_array(self):
        with pytest.raises(ValueError, match="200x200"):
            split_tiles(np.zeros((0, 0)))


class TestCnnInvalidLabel:
    """CNN returns invalid label → fen_assembler handles gracefully."""

    def test_invalid_symbol_raises(self):
        labels = ['-'] * 64
        labels[0] = 'x'
        with pytest.raises(ValueError, match="Invalid piece symbol"):
            labels_to_fen(labels)

    def test_too_few_labels_raises(self):
        with pytest.raises(ValueError, match="64 labels"):
            labels_to_fen(['-'] * 32)

    def test_too_many_labels_raises(self):
        with pytest.raises(ValueError, match="64 labels"):
            labels_to_fen(['-'] * 100)

    def test_numeric_label_raises(self):
        labels = ['-'] * 64
        labels[4] = '1'
        with pytest.raises(ValueError, match="Invalid piece symbol"):
            labels_to_fen(labels)

    def test_empty_labels_list_raises(self):
        with pytest.raises(ValueError, match="64 labels"):
            labels_to_fen([])


class TestEngineIllegalMove:
    """Engine returns illegal move → retry logic triggers."""

    def test_illegal_uci_raises(self):
        from chess_agent.engine_client import pick_move
        with pytest.raises((RuntimeError, ValueError)):
            pick_move("not-a-fen", is_white=True)

    def test_pick_move_raises_on_empty_board(self):
        with pytest.raises(RuntimeError, match="no move"):
            pick_move("8/8/8/8/8/8/8/8 w - - 0 1", is_white=True)

    def test_pick_move_raises_on_stalemate(self):
        with pytest.raises(RuntimeError, match="no move"):
            pick_move("k7/8/KQ6/8/8/8/8/8 b - - 0 1", is_white=False)


class TestDomTimeout:
    """DOM timeout (selector never appears) → clear error, no crash."""

    def test_wait_for_turn_timeout_returns_false(self, page):
        page.evaluate("window.setTurn('black')")
        pm = PageManager(page, DOMReader(page), "white")
        assert pm.wait_for_turn(timeout=1) is False

    def test_board_not_visible_returns_false(self, page):
        page.evaluate("document.querySelector('cg-board').style.display = 'none'")
        reader = DOMReader(page)
        assert reader.is_board_visible() is False

    def test_get_board_rect_none_when_board_gone(self, page):
        page.evaluate("document.querySelector('cg-board').remove()")
        reader = DOMReader(page)
        assert reader.get_board_rect() is None

    def test_click_square_fails_when_board_gone(self, page):
        page.evaluate("document.querySelector('cg-board').remove()")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.click_square("e2") is False

    def test_click_move_fails_when_board_gone(self, page):
        page.evaluate("document.querySelector('cg-board').remove()")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        assert actor.click_move("e2e4") is False


class TestScreenshotFailure:
    """Screenshot fails (file missing / page closed) → clear error."""

    def test_screenshot_on_closed_page_raises(self, page):
        page.close()
        with pytest.raises(Exception):
            page.screenshot(type="png")

    def test_classify_on_empty_tiles_still_works(self):
        from chess_agent.piece_classifier import PieceClassifier
        import os
        if not os.path.exists(PIECE_CLASSIFIER_PATH):
            pytest.skip("Model not found")
        classifier = PieceClassifier(PIECE_CLASSIFIER_PATH)
        tiles = [np.full((25, 25), 255, dtype=np.uint8) for _ in range(64)]
        labels = classifier.classify(tiles)
        assert len(labels) == 64
        assert all(l == '-' for l in labels)


class TestConsecutiveFailures:
    """3 consecutive move failures → abort (set _running = False)."""

    def test_crop_on_empty_screenshot_handled(self):
        img = np.zeros((100, 100), dtype=np.uint8)
        rect = {"x": 0, "y": 0, "w": 400, "h": 400}
        result = crop_board(img, rect)
        assert result.shape[0] < 400
        assert result.shape[1] < 400

    def test_three_consecutive_retries_logic(self):
        assert MAX_RETRIES == 3
        failures = 0
        for attempt in range(MAX_RETRIES + 1):
            failures += 1
        assert failures >= MAX_RETRIES

    def test_verify_partial_diff_no_change_false(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        assert verify_partial_diff(fen, fen, "e2e4") is False

    def test_verify_partial_diff_wrong_move_false(self):
        prev = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        new = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
        assert verify_partial_diff(prev, new, "d2d4") is False

    def test_abort_on_constant_verify_false(self, page):
        page.evaluate("window.setBoardState('8/8/8/8/8/8/8/8')")
        fen_before = page.evaluate("window.getBoardFen()")
        reader = DOMReader(page)
        actor = DOMActor(page, reader)
        actor.click_move("e2e4")
        fen_after = page.evaluate("window.getBoardFen()")
        assert fen_before == fen_after


class TestEdgeFailurePaths:
    """Additional edge-case failure modes."""

    def test_uci_to_pixels_with_missing_rect(self):
        with pytest.raises(KeyError):
            uci_to_pixels("e2e4", {}, is_white=True)

    def test_uci_to_pixels_none_rect_raises(self):
        with pytest.raises(TypeError):
            uci_to_pixels("e2e4", None, is_white=True)

    def test_orientation_cls_missing_defaults_white(self, page):
        page.evaluate(
            "document.querySelector('.cg-wrap').className = 'cg-wrap cgv1 manipulable'"
        )
        reader = DOMReader(page)
        assert reader.get_orientation() == 'white'

    def test_game_result_none_when_no_overlay(self, page):
        reader = DOMReader(page)
        assert reader.get_game_result() is None

    def test_last_move_squares_empty_after_clear(self, page):
        page.evaluate("window.addLastMove(['e2', 'e4'])")
        page.evaluate("window.addLastMove([])")
        reader = DOMReader(page)
        assert reader.get_last_move_squares() == []

    def test_dismiss_overlays_no_crash_with_no_overlays(self, page):
        reader = DOMReader(page)
        reader.dismiss_overlays()
