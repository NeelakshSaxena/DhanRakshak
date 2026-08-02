# Loading Animations

This folder contains animation assets for the DhanRakshak application.

## Current Setup

The app expects a `loading.gif` file in this directory to display as a loading animation when processing bank statements.

### How to Add a Loading Animation

1. **Option A: Use an existing GIF**
   - Find a loading/spinner GIF you like (e.g., from GIPHY, Tenor, or create one)
   - Place it in this folder with the filename **`loading.gif`**
   - The app will automatically detect and display it

2. **Option B: Create a custom animated GIF**
   - You can use tools like:
     - **Photoshop** or **GIMP** (free) to create an animation
     - **Python + PIL** to generate programmatically
     - **Online tools** like ezgif.com to create from images/frames

3. **Recommended GIF Specifications**
   - **Size**: 200-300px width (app displays at 200px)
   - **Format**: Animated GIF (.gif)
   - **Duration**: 1-3 seconds per frame for smooth looping
   - **File size**: Keep under 500KB for fast loading

### Example: Create GIF with Python

```python
from PIL import Image

# Create a list of frames
frames = [Image.new('RGB', (200, 200), color=color) for color in ['red', 'blue', 'green']]

# Save as animated GIF
frames[0].save('loading.gif', save_all=True, append_images=frames[1:], 
               duration=100, loop=0)
```

### Current Fallback Behavior

If `loading.gif` is not found, the app will display:
- A text message: "⏳ Analyzing your statement..."
- Instructions to add the GIF

Once you add `loading.gif` to this folder, it will automatically be used during model processing.
