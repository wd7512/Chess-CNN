import pytest
from chess_agent.fen_assembler import labels_to_fen, fen_to_labels


class TestLabelsToFen:
    def test_starting_position(self):
        labels = [
            'r','n','b','q','k','b','n','r',
            'p','p','p','p','p','p','p','p',
            '-','-','-','-','-','-','-','-',
            '-','-','-','-','-','-','-','-',
            '-','-','-','-','-','-','-','-',
            '-','-','-','-','-','-','-','-',
            'P','P','P','P','P','P','P','P',
            'R','N','B','Q','K','B','N','R',
        ]
        fen = labels_to_fen(labels)
        assert fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"

    def test_empty_board(self):
        labels = ['-'] * 64
        fen = labels_to_fen(labels)
        assert fen == "8/8/8/8/8/8/8/8"

    def test_single_piece(self):
        labels = ['-'] * 64
        labels[28] = 'P'
        fen = labels_to_fen(labels)
        assert 'P' in fen

    def test_invalid_piece_symbol_raises(self):
        labels = ['-'] * 64
        labels[0] = 'x'
        with pytest.raises(ValueError, match="Invalid piece symbol"):
            labels_to_fen(labels)

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="64 labels"):
            labels_to_fen(['-'] * 32)


class TestFenToLabels:
    def test_starting_position(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        labels = fen_to_labels(fen)
        assert len(labels) == 64
        assert labels[0] == 'r'
        assert labels[63] == 'R'
        assert labels[27] == '-'

    def test_empty_board(self):
        labels = fen_to_labels("8/8/8/8/8/8/8/8")
        assert all(l == '-' for l in labels)

    def test_handles_full_fen_with_extras(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        labels = fen_to_labels(fen)
        assert len(labels) == 64

    def test_mixed_position(self):
        fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R"
        labels = fen_to_labels(fen)
        assert len(labels) == 64
        assert labels[0] == 'r'
        assert labels[63] == 'R'
        assert all(l in '-KkQqRrBbNnPp' for l in labels)

    def test_roundtrip(self):
        fens = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "8/8/8/8/8/8/8/8",
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R",
            "8/5k2/8/4K3/6P1/8/8/8",
        ]
        for fen in fens:
            labels = fen_to_labels(fen)
            result = labels_to_fen(labels)
            assert result == fen, f"Roundtrip failed for {fen}"
