import os
import subprocess

FFMPEG_PATH = r"C:\Users\ACER\AppData\Roaming\anythingllm-desktop\storage\engines\ffmpeg\windows-x64\ffmpeg.exe"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
SOURCE_VIDEO = os.path.join(MEDIA_DIR, "AI for Teaching and Learning_1080p_caption.mp4")

CLIPS = [
    ("vid_01_welcome.mp4", "00:00:00", "00:00:33"),
    ("vid_02_basics.mp4", "00:00:33", "00:00:49"),
    ("vid_03_prompts.mp4", "00:02:22", "00:02:41"),
    ("vid_04_context.mp4", "00:00:49", "00:01:06"),
    ("vid_05_planning.mp4", "00:01:07", "00:01:40"),
    ("vid_06_assessment.mp4", "00:01:41", "00:02:08"),
    ("vid_07_principles.mp4", "00:02:58", "00:03:07"),
]

FRAMES = [
    ("img_01_welcome.png", "00:00:02"),
    ("img_02_scenario.png", "00:00:40"),
    ("img_03_prompt_formula.png", "00:02:39"),
    ("img_04_ethiopia.png", "00:00:55"),
    ("img_05_workflow.png", "00:01:39"),
    ("img_06_assessment.png", "00:02:06"),
    ("img_07_collaboration.png", "00:02:50"),
    ("img_08_principles.png", "00:03:05"),
]

def main():
    if not os.path.exists(SOURCE_VIDEO):
        print(f"Error: source video not found at {SOURCE_VIDEO}")
        return

    print(f"Source video found: {SOURCE_VIDEO}")
    
    # 1. Slice video clips
    for filename, start, end in CLIPS:
        out_path = os.path.join(MEDIA_DIR, filename)
        cmd = [
            FFMPEG_PATH,
            "-ss", start,
            "-to", end,
            "-i", SOURCE_VIDEO,
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
            "-y"
        ]
        print(f"Generating clip {filename} ({start} -> {end})...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            sz = os.path.getsize(out_path) / (1024 * 1024)
            print(f"  [OK] {filename}: {sz:.2f} MB")
        else:
            print(f"  [FAILED] {filename}: {res.stderr[:200]}")

    # 2. Extract key frame images
    for filename, timestamp in FRAMES:
        out_path = os.path.join(MEDIA_DIR, filename)
        cmd = [
            FFMPEG_PATH,
            "-ss", timestamp,
            "-i", SOURCE_VIDEO,
            "-vframes", "1",
            "-q:v", "2",
            out_path,
            "-y"
        ]
        print(f"Extracting frame {filename} at {timestamp}...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            sz = os.path.getsize(out_path) / 1024
            print(f"  [OK] {filename}: {sz:.1f} KB")
        else:
            print(f"  [FAILED] {filename}: {res.stderr[:200]}")

if __name__ == "__main__":
    main()
