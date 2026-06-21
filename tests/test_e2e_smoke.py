import signal

import pytest

from chess_agent.chess_agent import ChessAgent
from chess_agent.config import COOKIE_PATH, PIECE_CLASSIFIER_PATH, REPO_ROOT


class TestChessAgentInit:
    def test_instantiation(self):
        agent = ChessAgent(
            game_url="https://lichess.org/test",
            our_color="white",
        )
        assert agent.game_url == "https://lichess.org/test"
        assert agent.our_color == "white"
        assert agent._running is True
        assert agent._browser is None

    def test_signal_handlers_registered(self):
        agent = ChessAgent(
            game_url="https://lichess.org/test",
            our_color="black",
        )
        assert signal.getsignal(signal.SIGTERM) is not signal.SIG_DFL
        assert signal.getsignal(signal.SIGINT) is not signal.SIG_DFL

    def test_signal_handler_stops_loop(self):
        agent = ChessAgent(
            game_url="https://lichess.org/test",
            our_color="white",
        )
        assert agent._running is True
        agent._signal_handler(signal.SIGTERM, None)
        assert agent._running is False

    def test_default_cookie_path(self):
        agent = ChessAgent(
            game_url="https://lichess.org/test",
            our_color="white",
        )
        assert agent.cookie_path == COOKIE_PATH

    def test_custom_cookie_path(self):
        agent = ChessAgent(
            game_url="https://lichess.org/test",
            our_color="white",
            cookie_path="/tmp/custom_cookies.json",
        )
        assert agent.cookie_path == "/tmp/custom_cookies.json"


class TestConfig:
    def test_repo_root_resolved(self):
        assert REPO_ROOT.exists()
        assert (REPO_ROOT / "src.py").exists()

    def test_model_path_resolved(self):
        assert PIECE_CLASSIFIER_PATH is not None
        assert PIECE_CLASSIFIER_PATH.endswith(".h5")

    def test_cookie_path_resolved(self):
        assert str(COOKIE_PATH).endswith("lichess_cookies.json")


class TestImports:
    def test_all_modules_importable(self):
        from chess_agent import (
            board_extractor,
            click_mapper,
            config,
            dom_actor,
            dom_reader,
            engine_client,
            fen_assembler,
            game_state,
            page_manager,
            piece_classifier,
        )
        assert board_extractor.crop_board is not None
        assert click_mapper.uci_to_pixels is not None
        assert dom_actor.DOMActor is not None
        assert dom_reader.DOMReader is not None
        assert engine_client.pick_move is not None
        assert fen_assembler.labels_to_fen is not None
        assert game_state.verify_partial_diff is not None
        assert page_manager.PageManager is not None
        assert piece_classifier.PieceClassifier is not None
