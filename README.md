# Whisper Transcription Script

## Introduction

This script is a powerful tool for transcribing audio files using the Whisper speech recognition model from OpenAI. It
can handle a wide range of audio formats, including those from YouTube videos, and provides a comprehensive set of
features to help you process and manage your transcripts.

## Installation

You'll need to have an **OpenAI API key,** which you should set as an environment variable named OPENAI_API_KEY.
If you do not have an API key, here you'll find more information: https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key

To use this script, you'll need to have Python 3.11 or later installed on your system. You can install the script using
pip:

```shell
pip install git+https://github.com/nvgbr/whisper_transcription.git
```
Once the installation is complete, you can run the script using the following command:

```shell
whisper-transcribe
```
## Usage

When you run the whisper-transcribe command, the script will prompt you to enter an audio file path or a YouTube video
URL. It will then ask you to specify the language of the audio.

The script will then process the audio file and generate several output files, including:

- `<audio_file_name>_raw_transcript.txt`: The raw transcript in plain text format.
- `<audio_file_name>_only_text.txt`: The transcript with only the text, without timestamps.
- `<audio_file_name>.json`: The transcript in JSON format, with word-level timestamps.
- `<audio_file_name>_full_transcript.json`: A full JSON file with the complete transcript returned by openai.
- `<audio_file_name>_full_transcript.json`: The full transcript in JSON format.
- `<audio_file_name>_wordwise.srt`: The transcript in SRT format, with word-level timestamps.
- `<audio_file_name>_more_words.srt`: The transcript in SRT format, with words in groups of 3-4 including timestamps.

The script can also handle large audio files by splitting them into smaller chunks and processing them individually.

The processed files will be saved in the Downloads/Audio folder on your system, or in the same directory as the input
audio file if it's not located in the Downloads folder.

Once the processing is complete, the script will open the folder containing the output files in your default file
explorer.

## Planned

- [ ] Several configuration options that you can customize to suit your needs.
- [ ] Adjusting the silence detection parameters for the audio splitting
- [ ] Changing the output file naming conventions
- [ ] Customizing the output folder
- [ ] Transcription of other publicly available video/audio sources
- [ ] ...


## Contribution

If you encounter any issues or have suggestions for improving the script, feel free to open an issue or submit a pull
request on the GitHub repository.
