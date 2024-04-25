import json
import os
import subprocess
import sys
import winreg
from datetime import datetime, timedelta
from pathlib import Path

import emoji
import srt
from dotenv import load_dotenv
from onepw_receiver.usersettings import UserSettings
from openai import Client
from openai.types.audio import Transcription
from pathvalidate import sanitize_filename
from pytube import Stream, YouTube
from rich.console import Console
from rich.prompt import Prompt
from rich.status import Status
from rich.theme import Theme
from srt import Subtitle

from .helpers.process_audio_files import get_file_size, get_pydub_audio_segment, split_audio_file
from .helpers.word_grouping import main as word_grouping

custom_theme = Theme(
        {"success": "grey3 on pale_green1 bold", "error": "grey93 on red bold"}
        )

console = Console(highlight=True, emoji=True, theme=custom_theme, emoji_variant="emoji")


def main():
    file_path = Prompt.ask("Enter an audio filepath or an URL to a youtube video. ")
    language = Prompt.ask("What language is the video in?", choices=["de", "en"], default="de")
    audio_file_path = file_path.strip('"')
    if file_path.startswith("http"):
        console.print(f"Detected Link: {file_path}")
        with Status("Getting Audio from Link...") as current_status:
            audio_file_path = get_audio_from_link(file_path, current_status)

    run_script(file_path=Path(audio_file_path), language=language)

    console.print("I'm done for now. Bye 👋")
    subprocess.Popen(rf'explorer /select,{audio_file_path.parent}')


def get_save_path(audio_file_path, save_path=None):
    # audio_bytes = read_audio_file(audio_file)
    if save_path is None:
        save_path = get_downloads_folder()
    if check_file_exists(audio_file_path):
        save_path = audio_file_path.parent

    console.print(f"Transcript will be saved at: {save_path}")
    return save_path


def check_file_exists(file):
    if not Path(file).exists():
        return False


def run_script(file_path: Path, language, save_path: Path = None, ):

    with Status("Generating new File Name...") as current_status:
        save_path = get_save_path(file_path, save_path)
        all_filenames = create_all_filenames(
                file_path
                )
        suffix = file_path.suffix
        file_size = get_file_size(file_path)
        raw_transcript = Path(all_filenames.get('raw_transcript_file')).with_suffix('.txt')

    if file_size > 23_000_000:
        with Status("File size is greater than 20 MB...") as current_status:
            transcript_part = []
            audio_segment = get_pydub_audio_segment(file_path)
            current_status.update("Splitting Audio Segment...")
            audio_parts = split_audio_file(audio_segment, current_status, all_filenames.get('base_file_name'))
        for i, audio_part in enumerate(audio_parts):
            try:
                raw_transcript = raw_transcript.with_name(raw_transcript.stem + f"_{i}").with_suffix('.txt')
                new_filenames = create_all_filenames(
                        file_path, f"_{i}"
                        )
                new_save_path = get_save_path_from_existing_file(audio_part)
                transcript = run_transcript(new_save_path,
                                            current_status,
                                            language,
                                            new_filenames.get('raw_transcript_file'),
                                            )
                transcript_part.append(transcript)

                save_transcript_to_files(transcript, new_filenames)
            except Exception as e:
                console.log(e, style='error')
                continue
        transcript_text = " ".join(trans.text for trans in transcript_part)
        save_transcript(transcript_text,
                        raw_transcript.with_name(raw_transcript.stem + f"_full_text_from_all_parts").with_suffix('.txt')
                        )
    else:
        transcript = run_transcript(file_path, current_status, language, raw_transcript)
        save_transcript_to_files(transcript, all_filenames)


def run_transcript(file_path, current_status, language, raw_transcript_file):
    if not check_file_exists(raw_transcript_file):
        with Status("Generating Transcript") as current_status:
            return transcribe_audio(file_path, current_status, language, raw_transcript_file)
    else:
        transcript = eval(raw_transcript_file.read_text(encoding='utf-8'))


def save_transcript_to_files(transcript, all_filenames):

    with Status("Saving transcript...") as current_status:
        save_json(transcript.json(), all_filenames.get('full_json_file'))
        save_transcript(str(transcript), all_filenames.get('raw_transcript_file'))
        save_transcript(str(transcript.text), all_filenames.get('text_only_file'))
        save_json(transcript.words, all_filenames.get('json_file'))

    with Status("Processing transcript to srt...") as current_status:
        srt_content = create_srt(transcript.words)
        transformed_transcript = process_json_to_transcription(transcript.words)
        save_transcript(srt.compose(srt_content, reindex=False, in_place=True), all_filenames.get('srt_file_path'))
        save_transcript(transformed_transcript[1], all_filenames.get('srt_as_txt_file'))
        try:
            current_status.update("Generating word_wise_transcript...")
            word_grouping(all_filenames.get('text_only_file'), all_filenames.get('json_file'), status=current_status)
        except Exception as e:
            console.log(e, style='error')


def create_all_filenames(file_path, part_number=''):
    return {
        "base_file_name": sanitize_filename(file_path.stem),
        "text_only_file": generate_file_name(file_path,
                                             additional_text=f"only_text{part_number}",
                                             suffix=".txt", ),
        "raw_transcript_file": generate_file_name(file_path,
                                                  additional_text=f"raw_transcript{part_number}",
                                                  suffix=".txt",
                                                  ),
        "json_file": generate_file_name(file_path,
                                        additional_text=f"{part_number}",
                                        suffix='.json', ),
        "full_json_file": generate_file_name(file_path,
                                             additional_text=f"full_transcript{part_number}",
                                             suffix=".json",
                                             ),
        "srt_as_txt_file": generate_file_name(file_path,
                                              additional_text=f"srt_as_text{part_number}",
                                              suffix=".txt", ),
        "srt_file_path": generate_file_name(file_path,
                                            suffix='.srt',
                                            additional_text=f'wordwise{part_number}', ),
        }


def get_downloads_folder() -> Path:
    reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
                             )
    downloads_path = winreg.QueryValueEx(reg_key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
    winreg.CloseKey(reg_key)
    return Path(downloads_path) / "Audio"


def transcribe_audio(audio_file, current_status, language, raw_transcript_file) -> Transcription:

    openai_aip_key = get_api_key()
    current_status.update("Got API key")
    client = Client(
            api_key=openai_aip_key,
            )
    current_status.update("Got Client")

    prompt = "Hi, wir sind Nico und Vroni von salala.de und bei uns dreht sich alles um Low Carb und Keto. Und ja ähm heute machen wir äh ein hm, lass mich überlegen, ja genau ein neues Rezept. Ob zuckerfrei backen mit Erythrit und Allulose oder öhm doch kochen siehst du dann."

    try:
        current_status.update("Transcribing audio...")
        transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                # response_format="srt",
                response_format="verbose_json",
                timestamp_granularities=["word"],
                prompt=prompt if language == "de" else "Hi there",
                )
        current_status.update("Transcript Done")
        save_transcript(str(transcript), raw_transcript_file)
        return transcript
    except Exception as e:
        console.log(e, style='error')


def get_api_key():
    openai_api_key = None
    try:
        if Path(r"D:/Coding/BASICS/settings/settings.toml").exists():
            load_dotenv("D:/Coding/BASICS/.env")
            settings = UserSettings("D:/Coding/BASICS/settings/settings.toml")
            openai_api_key = settings.get_onepw_item("openai_api_key", "api").value
        else:
            openai_api_key = os.environ.get('OPENAI_API_KEY')
        return openai_api_key
    except Exception as e:
        console.log("You need to provide an 'OPENAI_API_KEY' as environment variable", style='error')
        sys.exit(f"{e}")


def get_save_path_from_existing_file(audio_file):
    transcript_path = Path(audio_file).parent / Path(audio_file).name
    return transcript_path


def save_json(transcript, save_path):
    try:
        with open(save_path, "w", encoding="utf-8") as file:
            json.dump(transcript, file, ensure_ascii=False, indent=4, sort_keys=True)
    except Exception as e:
        console.print(e, style='error')
        return


def save_transcript(transcription, file_path_to_save):
    console.print(f"Saving file: {file_path_to_save.name}")
    try:
        with open(file_path_to_save, "w", encoding="utf-8") as file:
            file.write(transcription)
    except Exception as e:
        console.log(e, style='error')
        return


def generate_file_name(filepath: Path, /, suffix: str, additional_text: str = None):
    file_name = str(filepath.stem).split()
    if not suffix.startswith('.'):
        suffix = "." + suffix
    if additional_text:
        new_file_name = f'{"_".join(file_name)}_{additional_text}'
    else:
        new_file_name = f'{"_".join(file_name)}'
    new_path = filepath.parent.joinpath(new_file_name).with_suffix(suffix)
    return new_path


def open_json(json_file_path):
    with open(json_file_path, "r") as file:
        return json.load(file)


def create_srt(transcript_json):
    subs = []
    for i, item in enumerate(list(transcript_json)):
        word = srt.make_legal_content(item['word'])
        subs.append(Subtitle(index=i,
                             start=timedelta(seconds=item['start']),
                             end=timedelta(seconds=item['end']),
                             content=word,
                             )
                    )
    srt.sort_and_reindex(subs, in_place=True, skip=False)
    return subs


def process_json_to_transcription(transcript_json):
    try:
        srt_lines = []
        txt_lines = []
        subtitle_number = 1
        for transcript in transcript_json:
            start_time = transcript["start"]
            end_time = transcript["end"]
            text = transcript["word"]
            formatted_start_time = format_timestamp_from_json(start_time)
            formatted_end_time = format_timestamp_from_json(end_time)
            # print(f"154 | process_json_to_transcription() - {formatted_end_time=}")
            srt_line = f"{subtitle_number}\n{formatted_start_time[0]} --> {formatted_end_time[0]}\n{text}\n"
            txt_line = f"{subtitle_number}\n{formatted_start_time[1]}\n{text}\n"
            srt_lines.append(srt_line)
            txt_lines.append(txt_line)
            subtitle_number += 1
        srt_lines = "\n".join(srt_lines)
        txt_lines = "\n".join(txt_lines)

        return [srt_lines, txt_lines]
    except Exception as e:
        console.log(e, style='error')
        return str(transcript_json)


def format_timestamp_from_json(time_value):
    time_value_delta = timedelta(seconds=time_value)
    time_str = str(time_value_delta)
    if time_str.startswith('0:'):
        parts = time_str.split(':')
        if time_value_delta.microseconds == 0:
            parts[-1] += '.000'
        time_value_delta = f"00:{':'.join(parts[1:])}"
    time_delta = datetime.strptime(time_value_delta, '%H:%M:%S.%f')
    srt_time = time_delta.strftime("%X.%f")
    txt_time = time_delta.strftime("%X")
    return [srt_time, txt_time]


def print_srt_stuff(srt_list):
    composed = srt.compose(srt_list)


def get_audio_from_link(link, current_status):
    video: YouTube = YouTube(link)
    download_path = get_downloads_folder()
    current_status.update(f"Downloading audio file form YouTube to '{download_path}' ...")
    audio_path = download_audio_file(video, download_path)
    return Path(audio_path)


def remove_emojis(text):
    return emoji.replace_emoji(text, '')


def download_audio_file(video, download_path):
    try:
        audio: Stream = video.streams.get_audio_only()
        # print(dir(audio))
        author = video.author
        published_date = video.publish_date.strftime("%Y-%m-%d")
        video_file_name = " - ".join([published_date, str(audio.default_filename).removesuffix(".mp4"), author])
        video_file_name = remove_emojis(video_file_name)
        filename = sanitize_filename(video_file_name)
        audio_save_path = generate_file_name(download_path / filename, suffix=".mp4")
        console.print(f"Audio Filesize: {audio.filesize_mb=}")
        audio_path = audio.download(str(audio_save_path.parent), filename=audio_save_path.name, skip_existing=True)
        return Path(audio_path)
    except Exception as e:
        console.log(e)
        sys.exit(f"220 | download_audio_file() - {e}")


if __name__ == "__main__":
    main()
