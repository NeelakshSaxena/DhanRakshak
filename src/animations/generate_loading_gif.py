#!/usr/bin/env python3
"""
Generate a simple spinning loading animation GIF.
Run this script to create a loading.gif in the current directory.
"""

from PIL import Image, ImageDraw
import math

def create_loading_gif(filename='loading.gif', size=200, duration=50, frames=36):
    """
    Generate an animated loading spinner GIF.
    
    Parameters:
    - filename: Output GIF filename
    - size: Dimensions in pixels (size x size)
    - duration: Duration of each frame in milliseconds
    - frames: Number of animation frames (smoother = more frames)
    """
    images = []
    center = size // 2
    radius = size // 4
    
    for i in range(frames):
        # Create a new image with white background
        img = Image.new('RGB', (size, size), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw outer circle (light gray)
        draw.ellipse(
            [(center - radius, center - radius), 
             (center + radius, center + radius)],
            outline='#e0e0e0', width=4
        )
        
        # Draw rotating spinner arc
        angle = (i / frames) * 360
        start_angle = angle
        end_angle = angle + 90
        
        draw.arc(
            [(center - radius, center - radius),
             (center + radius, center + radius)],
            start=start_angle, end=end_angle,
            fill='#1f77b4', width=4
        )
        
        images.append(img)
    
    # Save as animated GIF
    images[0].save(
        filename,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0,  # Infinite loop
        optimize=False
    )
    
    print(f"✓ Created {filename} ({size}x{size}px, {frames} frames)")
    print(f"  Frame duration: {duration}ms")
    print(f"  Total animation time: {(duration * frames) / 1000:.2f}s")


if __name__ == '__main__':
    try:
        create_loading_gif()
        print("\nLoading animation created successfully!")
        print("The app will now display this animation while processing statements.")
    except ImportError:
        print("ERROR: PIL (Pillow) is not installed.")
        print("Install it with: pip install Pillow")
    except Exception as e:
        print(f"ERROR: {e}")
