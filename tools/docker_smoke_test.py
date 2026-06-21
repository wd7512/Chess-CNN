#!/usr/bin/env python3
"""Phase 0.3: Docker Smoke Test.

Verifies that all critical imports work inside the Docker container:
- Playwright Chromium launches and takes a screenshot
- OpenCV can read/write images
- TensorFlow loads the CNN model
"""

import os
import sys
import time

print("=" * 60)
print("Docker Smoke Test")
print("=" * 60)
errors = []

# ---- Test 1: OpenCV ----
print("\n[TEST 1] OpenCV import + basic ops...")
try:
    import cv2
    import numpy as np
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (50, 50))
    cv2.imwrite("/tmp/test_cv.png", img)
    print(f"  ✓ OpenCV version: {cv2.__version__}")
    print(f"  ✓ Can create/resize/convert/save images")
except Exception as e:
    errors.append(f"OpenCV failed: {e}")
    print(f"  ✗ {e}")

# ---- Test 2: TensorFlow ----
print("\n[TEST 2] TensorFlow import + model load...")
try:
    import tensorflow as tf
    print(f"  ✓ TensorFlow version: {tf.__version__}")

    model_path = "/app/Models/Piece_Classifier.h5"
    if os.path.exists(model_path):
        model = tf.keras.models.load_model(model_path)
        print(f"  ✓ Model loaded from {model_path}")
        print(f"  ✓ Input shape: {model.input_shape}")

        # Quick forward pass
        dummy_input = np.ones((64, 25, 25, 1), dtype=np.float32)
        preds = model(dummy_input)
        print(f"  ✓ Forward pass: {preds.shape}")
    else:
        print(f"  ⚠ Model not found at {model_path}, skipping forward pass")
except Exception as e:
    errors.append(f"TensorFlow failed: {e}")
    print(f"  ✗ {e}")

# ---- Test 3: Playwright ----
print("\n[TEST 3] Playwright Chromium launch + screenshot...")
try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # Navigate to a simple page
        page.goto("https://lichess.org/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        title = page.title()
        print(f"  ✓ Browser launched")
        print(f"  ✓ Page title: {title}")

        # Screenshot
        ss_path = "/tmp/smoke_test_screenshot.png"
        page.screenshot(path=ss_path, full_page=False)
        if os.path.exists(ss_path) and os.path.getsize(ss_path) > 1000:
            print(f"  ✓ Screenshot saved ({os.path.getsize(ss_path)} bytes)")
        else:
            errors.append("Screenshot too small or missing")

        # Check for cg-board
        has_board = page.query_selector("cg-board")
        print(f"  ✓ cg-board present: {has_board is not None}")

        browser.close()
        print(f"  ✓ Browser closed cleanly")
except Exception as e:
    errors.append(f"Playwright failed: {e}")
    print(f"  ✗ {e}")

# ---- Summary ----
print(f"\n{'='*60}")
if errors:
    print(f"SMOKE TEST FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("SMOKE TEST PASSED ✓")
    print("All components working: OpenCV, TensorFlow, Playwright")
    print(f"{'='*60}")
