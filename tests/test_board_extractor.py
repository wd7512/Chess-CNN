import numpy as np
import pytest
from chess_agent.board_extractor import crop_board, split_tiles


class TestCropBoard:
    def test_crops_correct_region(self):
        image = np.zeros((600, 800), dtype=np.uint8)
        image[200:600, 100:500] = 255
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        cropped = crop_board(image, rect, margin=0)
        assert cropped.shape == (400, 400)
        assert cropped.mean() == 255.0

    def test_crops_with_margin(self):
        image = np.zeros((800, 1000), dtype=np.uint8)
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        cropped = crop_board(image, rect, margin=2)
        assert cropped.shape == (404, 404)

    def test_clamps_out_of_bounds(self):
        image = np.zeros((100, 100), dtype=np.uint8)
        rect = {'x': 50, 'y': 50, 'w': 200, 'h': 200}
        cropped = crop_board(image, rect, margin=0)
        assert cropped.shape[0] < 200
        assert cropped.shape[1] < 200

    def test_accepts_width_height_keys(self):
        image = np.zeros((400, 400), dtype=np.uint8)
        rect = {'x': 0, 'y': 0, 'width': 400, 'height': 400}
        cropped = crop_board(image, rect, margin=0)
        assert cropped.shape == (400, 400)

    def test_handles_color_image(self):
        image = np.zeros((800, 1000, 3), dtype=np.uint8)
        image[200:600, 100:500] = [255, 0, 0]
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        cropped = crop_board(image, rect, margin=0)
        assert cropped.shape == (400, 400, 3)
        assert (cropped[0, 0] == [255, 0, 0]).all()


class TestSplitTiles:
    def test_returns_64_tiles(self):
        board = np.zeros((200, 200), dtype=np.uint8)
        tiles = split_tiles(board)
        assert len(tiles) == 64

    def test_each_tile_is_25x25(self):
        board = np.zeros((200, 200), dtype=np.uint8)
        tiles = split_tiles(board)
        for tile in tiles:
            assert tile.shape == (25, 25)

    def test_tiles_in_correct_order(self):
        board = np.zeros((200, 200), dtype=np.uint8)
        board[0:25, 0:25] = 128
        tiles = split_tiles(board)
        assert tiles[0].mean() == 128.0
        board[25:50, 0:25] = 64
        tiles = split_tiles(board)
        assert tiles[8].mean() == 64.0

    def test_wrong_board_size_raises(self):
        with pytest.raises(ValueError, match="200x200"):
            split_tiles(np.zeros((100, 100)))
