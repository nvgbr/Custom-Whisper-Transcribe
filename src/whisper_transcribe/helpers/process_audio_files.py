import sys
import tempfile
from pathlib import Path

from pydub import AudioSegment
from pydub.silence import split_on_silence
from rich.console import Console
from rich.theme import Theme

from .time_calculations import seconds_to_milliseconds

custom_theme = Theme(
        {"success": "grey3 on pale_green1 bold", "error": "grey93 on red bold"}
        )

console = Console(highlight=True, emoji=True, theme=custom_theme, emoji_variant="emoji")


def split_audio_file(audio_segment, current_status, base_file_name):
    audio_parts = []

    chunks = split_on_silence(audio_segment,
                              min_silence_len=500,
                              silence_thresh=-16,
                              keep_silence=True,
                              seek_step=5
                              )

    console.print(f"Chunks length is {len(chunks)}")
    # now recombine the chunks so that the parts are at least 8 Minutes long
    target_length = 480_000
    output_chunks = [chunks[0]]
    current_status.update("Merging Chunks...")
    for chunk in chunks[1:]:
        if len(output_chunks[-1]) < target_length:
            output_chunks[-1] += chunk
        else:
            # if the last output chunk is longer than the target length,
            # we can start a new one
            output_chunks.append(chunk)

    for i, chunk in enumerate(output_chunks):
        current_status.update(f"Saving audio chunk {i + 1}/{len(output_chunks)}...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", prefix=f"{base_file_name}_part{i}_", delete=False) as temp_audio_file:
            chunk.export(temp_audio_file, format="mp3")
            console.print(f"Saved part to: {temp_audio_file.name}")
            audio_parts.append(temp_audio_file.name)

    return audio_parts


def calculate_chunk_seek_steps(audio_segment: AudioSegment, max_chunk_size=20_000_000):
    # PyDub handles time in milliseconds
    duration = seconds_to_milliseconds(get_duration_pydub(audio_segment))
    max_chunk_duration = max_chunk_size / audio_segment.frame_width
    step_count = duration / max_chunk_duration
    step_milliseconds = int(duration) / (max_chunk_duration / duration)
    console.print(f"{step_milliseconds=}")
    return int(step_milliseconds)


def get_pydub_audio_segment(audio_file_path: Path) -> AudioSegment:
    return AudioSegment.from_file(audio_file_path)


def read_audio_file(path_to_audio: Path):
    try:
        console.print("reading audio file")
        return Path(path_to_audio).read_bytes()
    except FileNotFoundError as e:
        console.log(e)
        sys.exit(f"{e}")


def get_duration_pydub(audio_segment: AudioSegment) -> float:
    duration = audio_segment.duration_seconds
    return duration


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes.

    Args:
        file_path (Path): Path to the file

    Returns:
        file_size (str): file size in bytes.
    """
    file_size = file_path.stat().st_size
    console.print("File size :", file_size / 1000000, "MB")
    return file_size
