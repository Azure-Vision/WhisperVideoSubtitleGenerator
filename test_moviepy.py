try:
    import moviepy.editor as mp
    print("moviepy.editor imported successfully")
    print(f"MoviePy version: {mp.__version__}")
except Exception as e:
    print(f"Error importing moviepy.editor: {e}")
    import traceback
    traceback.print_exc()