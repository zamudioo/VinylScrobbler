#                                                                                     
                                                                                    
██  ██ ▄▄ ▄▄  ▄▄ ▄▄ ▄▄ ▄▄    ▄█████  ▄▄▄▄ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄    ▄▄▄▄▄ ▄▄▄▄  
██▄▄██ ██ ███▄██ ▀███▀ ██    ▀▀▀▄▄▄ ██▀▀▀ ██▄█▄ ██▀██ ██▄██ ██▄██ ██    ██▄▄  ██▄█▄ 
 ▀██▀  ██ ██ ▀██   █   ██▄▄▄ █████▀ ▀████ ██ ██ ▀███▀ ██▄█▀ ██▄█▀ ██▄▄▄ ██▄▄▄ ██ ██ 
                                                                                    

Vinyl Scrobbler is a Python project that listens to audio, mainly from physical sources like vinyl records or CDs, and scrobbles the recognized tracks to your Last.fm profile. It also shows artwork, artist, and track info while playing.

The project uses [Shazamio](https://pypi.org/project/shazamio/) to recognize music from audio samples. If the song is recognized, It will automatically send the track info to Last.fm.

## Main Purpose

The main goals of this project are:

1. Display music information such as cover art, track, and artist.
2. Keep a record of tracks you play on Last.fm.

## How It Works

Vinyl Scrobbler needs:

- An audio source (vinyl USB output, audio splitter, or microphone recording the sound)
- A video source to display artwork and info
- Last.fm account with API key and secret

There are three main ways to feed audio:

1. Direct USB output from the source. (i use an ATLP120XUSB, so this is the option that i use)
2. Use a splitter in between the signal and the output: one part goes to speakers/amplifier and the other goes to a USB audio converter.
3. Using a microphone near the speakers, but its less precise and can get activate with any ambient sound.

## Setup

1. Create a Last.fm account and get your API key and secret from [Last.fm API](https://www.last.fm/api/).
2. Run the setup script (`setup.sh`). It installs everything and configures the project automatically.
3. (Optional) To start the program automatically on a Raspberry Pi boot, use `autostart_setup.sh`.

## Usage

1. Make sure your audio source is connected.
2. Run the backend and frontend scripts.
3. Watch the artwork and track info while Vinyl Scrobbler scrobbles tracks to Last.fm automatically.

## Contributions

This was made as a personal side project, but any contribution is welcome. If you find bugs or have any improvements, feel free to open issues or pull requests.

