import pafy, pyglet
from pytube import YouTube
from urllib.parse import *
from googleapiclient.discovery import build
import subprocess


def play_websocket():
  # Define the command to start FFmpeg process
  ffmpeg_command = [
      'ffmpeg',
      '-re',                    # Read input at native frame rate
      '-i', 'song.mp3',         # Input audio file
      '-f', 'mp3',               # Output format
      '-vn',                     # Disable video recording
      '-content_type', 'audio/mpeg',  # Set content type for Icecast
      'icecast://source:nyCTh81k@link.zeno.fm:80/zvgtsutfmattv'  # Icecast server URL
  ]

  # Start FFmpeg process
  ffmpeg_process = subprocess.Popen(ffmpeg_command)

  # Wait for the process to finish
  ffmpeg_process.wait()

class Youtube_mp3():
    def __init__(self):
        self.lst = []
        self.dict = {}
        self.dict_names = {}
        self.playlist = []
        self.api_key = 'AIzaSyB6KEe_oeJh-LLFIopQ0w9-3yniJyLtaNM'

    def url_search(self, search_query, max_results=5):
        youtube = build('youtube', 'v3', developerKey=self.api_key)
        request = youtube.search().list(
            q=search_query,
            part='id',
            type='video',
            maxResults=max_results
        )
        response = request.execute()

        video_links = []
        i = 1
        for item in response['items']:
            video_id = item['id']['videoId']
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            self.dict[i] = video_url
        print(self.dict)



    def get_search_items(self, max_search):
      if self.dict != {}:
        i = 1
        for url in self.dict.values():
            try:
                yt = YouTube(url)
                title = yt.title
                uploader = yt.author
                duration = yt.length
                views = yt.views
                self.dict_names[i] = title
                print(f"{i}. Title: {title}")
                print(f"   Uploader: {uploader}")
                print(f"   Duration: {duration} seconds")
                print(f"   Views: {views}")
                i += 1
            except Exception as e:
                print(f"Error extracting video info: {e}")
  
    def play_media(self, num):
      url = self.dict[int(num)]
      yt = YouTube(url)
      audio_stream = yt.streams.filter(only_audio=True).first()
      audio_file = audio_stream.download(filename='song.mp3', output_path='.', skip_existing=True)
      song = pyglet.media.load(audio_file)

      play_websocket()

  
    def download_media(self, num):
          url = self.dict[int(num)]
          yt = YouTube(url)
          audio_stream = yt.streams.filter(only_audio=True).first()
          song_name = self.dict_names[int(num)]
          print("Downloading: {0}.".format(song_name))
          file_name = input("Filename (Enter to keep default): ")
          if not file_name:
              file_name = song_name
          audio_file = audio_stream.download(filename=file_name, output_path='.', skip_existing=True, filename_prefix='audio_')
          print("Downloaded as:", audio_file)


    def bulk_download(self, url):
        info = pafy.new(url)
        audio = info.getbestaudio(preftype="m4a")
        song_name = self.dict_names[int(num)]
        print("Downloading: {0}.".format(self.dict_names[int(num)]))
        print(song_name)
        song_name = input("Filename (Enter if as it is): ")
 #       file_name = song_name[:11] + '.m4a'
        file_name = song_name + '.m4a'
        if song_name == '':
            audio.download(remux_audio=True)
        else:
            audio.download(filepath = filename, remux_audio=True)

    def add_playlist(self, search_query):
        url = self.url_search(search_query, max_search=1)
        self.playlist.append(url)



if __name__ == '__main__':
    print('Welcome to the Youtube-Mp3 player.')
    x = Youtube_mp3()
    search = ''
    while search != 'q':
        search = input("Youtube Search: ")
        old_search = search
        max_search = 5
        # if search == '':
        #     print('\nFetching for: {0} on youtube.'.format(old_search.title()))
        #     x.url_search(search, max_search)
        #     x.get_search_items(max_search)
        #     song_number = input('Input song number: ')
        #     x.play_media(song_number)

        x.dict = {}
        x.dict_names = {}

        if search == 'q':
            print("Ending Youtube-Mp3 player.")
            break

        download = input('1. Play Live Music\n2. Download Mp3 from Youtube.\n')
        if search != 'q' and (download == '1' or download == ''):
            print('\nFetching for: {0} on youtube.'.format(search.title()))
            x.url_search(search, max_search)
            x.get_search_items(max_search)
            song_number = input('Input song number: ')
            x.play_media(song_number)
        elif download == '2':
            print('\nDownloading {0} (conveniently) from youtube servers.'.format(search.title()))
            x.url_search(search, max_search)
            x.get_search_items(max_search)
            song_number = input('Input song number: ')
            x.download_media(song_number)
#github commit