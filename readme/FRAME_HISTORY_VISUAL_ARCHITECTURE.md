# Frame History NG/OK Status Display - Visual Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAMERA INPUT                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DETECT TOOL                                  │
│              (Process Objects/Classifications)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RESULT MANAGER                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ evaluate_detect_results()                                 │  │
│  │  - Compare with reference                                 │  │
│  │  - Calculate similarity                                   │  │
│  │  - Determine OK/NG                                        │  │
│  │  - Store in frame_status_history ◄── NEW                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  frame_status_history (Last 5 frames):                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ [0]: {status: 'NG',  similarity: 0.25}  ◄── Oldest     │    │
│  │ [1]: {status: 'OK',  similarity: 0.92}                 │    │
│  │ [2]: {status: 'OK',  similarity: 0.88}                 │    │
│  │ [3]: {status: 'NG',  similarity: 0.42}                 │    │
│  │ [4]: {status: 'OK',  similarity: 0.95}  ◄── Newest     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  get_frame_status_history() ◄── NEW                             │
│  Returns above list for display                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
┌──────────────────────┐     ┌──────────────────────┐
│  CAMERA VIEW         │     │   CAMERA VIEW        │
│  Frame History       │     │  Label Display       │
│                      │     │  (NEW)               │
│  [Frame Data]        │     │                      │
│  [Frame Data]        │     │  review_labels = [   │
│  [Frame Data]        │     │    reviewLabel_1,    │
│  [Frame Data]        │     │    reviewLabel_2,    │
│  [Frame Data]        │     │    ...               │
│                      │     │    reviewLabel_5]    │
└──────────────────────┘     └──────────────────────┘
            │                         │
            │   _update_review_views_with_frames()
            │   ┌────────────────────────┐
            │   │ 1. Get frame history   │ (existing)
            │   │ 2. Get status history  │ (NEW)
            │   │ 3. Match frames/status │ (NEW)
            │   │ 4. Display frames      │ (existing)
            │   │ 5. Update labels       │ (NEW)
            │   └────────────────────────┘
            │
            ├─────────────────────┬──────────────────────┐
            ▼                     ▼                      ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │ reviewView_1 │      │ reviewLabel_1│      │ reviewLabel_2│
    │              │      │              │      │              │
    │  [Frame 1]   │      │  ✓ OK        │      │  ✗ NG        │
    │              │      │  (95%)       │      │  (42%)       │
    │              │      │  GREEN BG    │      │  RED BG      │
    └──────────────┘      └──────────────┘      └──────────────┘
    
    [Similar for reviewView_2-5 and reviewLabel_3-5]
```

## Data Flow Timeline

```
FRAME 1 (T=0ms):
  Camera Capture
      ↓
  DetectTool Process
      ↓
  ResultManager.evaluate_detect_results()
      ├─ similarity = 0.95
      ├─ status = 'OK'
      └─ _add_frame_status_to_history(t1, 'OK', 0.95)
          └─ frame_status_history[4] = {t1, 'OK', 0.95}
      ↓
  CameraView stores frame in frame_history[4]
      ↓
  _update_review_views_with_frames() called
      ├─ Gets frame_status_history from ResultManager
      ├─ reviewView_1 ← frame_history[4]
      └─ reviewLabel_1 ← frame_status_history[4]
          └─ Displays: "✓ OK (95%)" with GREEN background


FRAME 2 (T=100ms):
  [Previous frame shifts]
  Camera Capture
      ↓
  DetectTool Process
      ↓
  ResultManager.evaluate_detect_results()
      ├─ similarity = 0.42
      ├─ status = 'NG'
      └─ _add_frame_status_to_history(t2, 'NG', 0.42)
          └─ frame_status_history[4] = {t2, 'NG', 0.42}
          └─ frame_status_history[0] remains unchanged
      ↓
  CameraView frame_history shifts:
      ├─ frame_history[0] ← (removed)
      ├─ frame_history[1-4] ← shift from [0-3]
      └─ frame_history[4] ← new frame
      ↓
  _update_review_views_with_frames() called
      ├─ reviewView_1 ← frame_history[4]  (Frame 2)
      ├─ reviewLabel_1 ← frame_status_history[4]  ("✗ NG (42%)" RED)
      ├─ reviewView_2 ← frame_history[3]  (Frame 1)
      └─ reviewLabel_2 ← frame_status_history[3]  ("✓ OK (95%)" GREEN)


FRAME 5 (T=400ms):
  [All 5 frames populated]
  frame_history = [Frame1, Frame2, Frame3, Frame4, Frame5]
  frame_status_history = [OK, NG, OK, NG, OK] (statuses)
  
  Display:
  ┌─────────────────────────────────────┐
  │ reviewView_1 │ ✓ OK (95%) │ GREEN   │ ← Frame 5 (newest)
  │ reviewView_2 │ ✗ NG (42%) │ RED     │ ← Frame 4
  │ reviewView_3 │ ✓ OK (88%) │ GREEN   │ ← Frame 3
  │ reviewView_4 │ ✗ NG (35%) │ RED     │ ← Frame 2
  │ reviewView_5 │ ✓ OK (92%) │ GREEN   │ ← Frame 1 (oldest)
  └─────────────────────────────────────┘


FRAME 6 (T=500ms):
  frame_history:
  ├─ frame_history[0] ← (Frame 1 removed)
  ├─ frame_history[1-4] ← shift from [1-4]
  └─ frame_history[4] ← Frame 6 (NEW)
  
  frame_status_history:
  ├─ frame_status_history[0] ← (Status 1 removed)
  ├─ frame_status_history[1-4] ← shift from [1-4]
  └─ frame_status_history[4] ← Status 6 (NEW)
  
  Display:
  ┌─────────────────────────────────────┐
  │ reviewView_1 │ ✓ NG (45%) │ RED     │ ← Frame 6 (newest)
  │ reviewView_2 │ ✓ OK (95%) │ GREEN   │ ← Frame 5
  │ reviewView_3 │ ✗ NG (42%) │ RED     │ ← Frame 4
  │ reviewView_4 │ ✓ OK (88%) │ GREEN   │ ← Frame 3
  │ reviewView_5 │ ✗ NG (35%) │ RED     │ ← Frame 2 (oldest)
  └─────────────────────────────────────┘
  (Frame 1 is now outside history)
```

## Class Responsibility Diagram

```
┌──────────────────────────────────────┐
│        MainWindow                    │
│  ┌────────────────────────────────┐  │
│  │ _setup_review_views()          │  │
│  │ • Collects reviewLabel_1-5     │  │
│  │ • Passes to camera_view        │  │
│  │ • Auto-runs on startup         │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
           │
           │ set_review_labels()
           ▼
┌──────────────────────────────────────────────────────────┐
│          CameraView                                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Properties:                                      │   │
│  │ • review_labels (QLabel[5])                     │   │
│  │ • frame_history (frame data)                    │   │
│  │ • max_history_frames = 5                        │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Methods:                                         │   │
│  │ • set_review_labels() - Register labels         │   │
│  │ • _update_review_label() - Format/style label   │   │
│  │ • _update_review_views_with_frames() -          │   │
│  │   Main update loop (ENHANCED)                   │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
           │ get_frame_status_history()
           ▼
┌──────────────────────────────────────────────────────────┐
│          ResultManager                                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Properties:                                      │   │
│  │ • frame_status_history (dict[5])               │   │
│  │ • last_result (OK/NG + similarity)             │   │
│  │ • reference_data (detections to compare)       │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Methods:                                         │   │
│  │ • evaluate_detect_results() - Calculate status │   │
│  │ • _add_frame_status_to_history() - Store result│   │
│  │ • get_frame_status_history() - Return history  │   │
│  │ • set_reference_from_detect_tool() - Set ref   │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
           │
           │ detections
           ▼
┌──────────────────────────────────────────────────────────┐
│          DetectTool                                      │
│  • Process objects from frame                           │
│  • Return detection list                                │
└──────────────────────────────────────────────────────────┘
```

## Update Cycle Diagram

```
MAIN THREAD (UI):
  Timer (300ms interval)
      │
      ├─ _update_review_views_threaded()
      │      │
      │      └─ Copy frame_history (thread-safe)
      │             │
      │             ▼
      │      _update_review_views_with_frames()
      │             │
      │             ├─ Get frame_history
      │             ├─ Get status_history from ResultManager
      │             │
      │             ├─ For each frame (1-5):
      │             │  ├─ Display in reviewView_X
      │             │  ├─ Get status from history[i]
      │             │  └─ Update reviewLabel_X:
      │             │     ├─ Set text (✓ OK / ✗ NG + %)
      │             │     └─ Set color (GREEN / RED)
      │             │
      │             └─ If no frame:
      │                └─ Clear label
      │
      └─ UI Updates (no lag)


BACKGROUND THREAD (Frame Processing):
  Update event (from DetectTool)
      │
      ├─ evaluate_detect_results()
      │      │
      │      └─ _add_frame_status_to_history()
      │             └─ Status added to queue
      │
      ├─ update_frame_history()
      │      └─ Frame added to queue
      │
      └─ (Safe - separate from UI updates)
```

## Label Styling State Machine

```
┌─ LABEL STATE ─┐
│               │
├─ INITIALIZED ─┐
│  • Text align │
│  • Font setup │
│  • Ready      │
│               ▼
├─ EMPTY/WAITING
│  • Text = ""
│  • BG = #2b2b2b (gray)
│  • Border = #555
│               │
├─ UPDATING ────┘
│  • Get status from history
│  • Calculate display text
│  └─ ┌─────────────────┐
│     │ status == 'OK'? │
│     └──┬──────────────┘
│        │
│     YES  NO
│     │     │
│     ▼     ▼
│  [GREEN] [RED]
│  • BG #00AA00  • BG #AA0000
│  • Text "OK"    • Text "NG"
│  • Show %      • Show %
│  • Bold        • Bold
│
└─ REFRESH (300ms cycle)
   └─ Back to UPDATING
```

## Integration Points

```
┌────────────────┐
│  ResultManager │  ◄─── NEW: frame_status_history
│                │       NEW: _add_frame_status_to_history()
│                │       NEW: get_frame_status_history()
│                │  
│ Existing:      │  ✓ evaluate_detect_results()
│ • Reference    │  ✓ set_reference_from_detect_tool()
│ • Threshold    │  ✓ last_result storage
│ • Similarity   │
└────────────────┘
        ▲
        │ Uses
        │
┌────────────────────────┐
│  CameraView            │  ◄─── NEW: review_labels
│                        │       NEW: set_review_labels()
│ Existing:              │       NEW: _update_review_label()
│ • frame_history        │       ENHANCED: _update_review_views_with_frames()
│ • reviewView setup     │  
│ • Display logic        │  ✓ Frame capture
│                        │  ✓ Frame storage
└────────────────────────┘
        ▲
        │ Uses
        │
┌────────────────────────────┐
│  MainWindow                │  ◄─── ENHANCED: _setup_review_views()
│                            │ 
│ NEW:                       │       1. Collect reviewLabel_1-5
│ • Collect review labels    │       2. Pass to camera_view
│ • Set labels on camera_view│       3. Auto-initialize
│                            │
│ Existing:                  │  ✓ UI initialization
│ • Create widgets           │  ✓ Manager setup
│ • Connect signals          │
└────────────────────────────┘
```

## Status Display Logic Flowchart

```
┌─ Frame Captured ─┐
│                  │
│  evaluate_detect_results(detections)
│                  │
│  ├─ Is reference set?
│  │  NO: status = 'NG', similarity = 0.0
│  │  YES: Continue
│  │
│  ├─ Are there detections?
│  │  NO: status = 'NG', similarity = 0.0
│  │  YES: Continue
│  │
│  ├─ Calculate similarity
│  │  using _compare_detections()
│  │
│  ├─ Is similarity >= threshold (0.8)?
│  │  YES: status = 'OK'
│  │  NO:  status = 'NG'
│  │
│  └─ Store: _add_frame_status_to_history()
│             {timestamp, status, similarity}
│
└─ _update_review_label() ─┐
                           │
   Get status from history │
                           │
   status == 'OK'?         │
   ├─ YES:                 │
   │  • Text = "✓ OK"      │
   │  • Append similarity %│
   │  • Set BG = GREEN     │
   │                       │
   ├─ NO:                  │
   │  • Text = "✗ NG"      │
   │  • Append similarity %│
   │  • Set BG = RED       │
   │                       │
   └─ Display on Label ────┘
```

---

This visual architecture shows how the frame history NG/OK status display system integrates with the existing application and manages the flow of data from camera input to final UI display.

